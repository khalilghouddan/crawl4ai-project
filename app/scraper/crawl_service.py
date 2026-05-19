"""Crawl4AI integration and scrape result normalization."""

import asyncio
import re
from html.parser import HTMLParser

from app.utils.logger import logger
from app.schemas.scrape_schema import ScrapeRequest, ScrapeResultItem
from app.scraper.headers import prepare_headers
from app.scraper.proxy import format_proxy
from app.scraper.retry import CrawlError, EmptyContentError, get_retry_decorator
from app.utils.validators import is_valid_url
from app.db.repository import db_repository

from crawl4ai import AsyncWebCrawler
try:
    from crawl4ai import BrowserConfig, CrawlerRunConfig, CacheMode
    HAS_CRAWL4AI_V4 = True
except ImportError:
    HAS_CRAWL4AI_V4 = False

class TextExtractor(HTMLParser):
    """Extract readable text from HTML while skipping non-content tags."""

    def __init__(self):
        """Initialize parser state for collected text fragments."""
        super().__init__()
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        """Track entry into tags whose text should be ignored."""
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1

    def handle_endtag(self, tag):
        """Track exit from ignored tags."""
        if tag in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data):
        """Collect visible text data outside ignored tags."""
        text = data.strip()
        if text and not self.skip_depth:
            self.parts.append(text)

    def get_text(self):
        """Return normalized plain text collected from the HTML document."""
        return re.sub(r"\n{3,}", "\n\n", "\n".join(self.parts)).strip()

def html_to_text(html: str) -> str:
    """Convert an HTML string into readable plain text."""
    parser = TextExtractor()
    parser.feed(html)
    return parser.get_text()

def get_text_value(value):
    """Extract text from a Crawl4AI markdown value or markdown-like object."""
    if isinstance(value, str) and value.strip():
        return value.strip()

    for attr in ("fit_markdown", "raw_markdown", "markdown", "markdown_with_citations"):
        nested = getattr(value, attr, None)
        if isinstance(nested, str) and nested.strip():
            return nested.strip()

    return None

def extract_content(result):
    """Return cleaned markdown and raw markdown from a Crawl4AI result."""
    markdown_value = getattr(result, "markdown", None)
    markdown = get_text_value(markdown_value)

    raw_markdown = (
        get_text_value(getattr(result, "markdown_raw", None))
        or get_text_value(getattr(markdown_value, "raw_markdown", None))
        or markdown
    )

    if markdown:
        return markdown, raw_markdown

    for html_attr in ("cleaned_html", "html"):
        html = getattr(result, html_attr, None)
        if isinstance(html, str) and html.strip():
            fallback_text = html_to_text(html)
            if fallback_text:
                return fallback_text, raw_markdown or fallback_text

    return None, raw_markdown

@get_retry_decorator()
async def fetch_url(url: str, request_config: ScrapeRequest) -> ScrapeResultItem:
    """Fetch and extract one URL with Crawl4AI."""
    logger.info(f"Scraping URL -> {url}")
    
    headers = prepare_headers(request_config.custom_headers)
    proxy = format_proxy(request_config.proxy) if request_config.proxy else None
    
    if HAS_CRAWL4AI_V4:
        browser_cfg = BrowserConfig(headless=True, proxy=proxy, headers=headers)
        run_cfg = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS, 
            word_count_threshold=1, 
            excluded_tags=['script', 'style', 'nav', 'footer', 'aside', 'header'],
            remove_overlay_elements=True
        )
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url, config=run_cfg)
    else:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url=url,
                word_count_threshold=1,
                bypass_cache=True,
                remove_overlay_elements=True,
                exclude_tags=['script', 'style', 'nav', 'footer', 'aside', 'header']
            )
    
    if not result.success:
        raise CrawlError(f"Crawl4AI parsing error: {result.error_message}")
        
    clean_content, raw_content = extract_content(result)
    if not clean_content or len(clean_content.strip()) == 0:
        raise EmptyContentError("Scraped content is empty after markdown and HTML fallback extraction.")
    
    summary = None
    if request_config.extract_summary:
        if hasattr(result, "extracted_content") and result.extracted_content:
            summary = result.extracted_content 
        else:
            summary = clean_content[:300] + "..." if len(clean_content) > 300 else clean_content
            
    links = []
    if request_config.extract_links:
        internal_links = result.links.get('internal', []) if hasattr(result, 'links') and isinstance(result.links, dict) else []
        links = [link.get('href') for link in internal_links if isinstance(link, dict) and link.get('href')]
        
    logger.info(f"Successfully scraped URL -> {url}")
    return ScrapeResultItem(
        url=url,
        title=result.metadata.get('title') if result.metadata else None,
        markdown=clean_content,
        markdown_raw=raw_content,
        summary=summary,
        links=links if links else None,
        metadata=result.metadata if result.metadata else None,
        status="success"
    )

async def process_url(url: str, request_config: ScrapeRequest) -> ScrapeResultItem:
    """Validate, scrape, time, persist, and return one URL result."""
    
    if not is_valid_url(url):
        res = ScrapeResultItem(url=url, status="invalid_url", error="Invalid URL format. Use http:// or https://")
        await db_repository.save_result(res)
        return res

    cached_result = await db_repository.get_successful_result_by_url(url)
    if cached_result:
        logger.info(f"Returning cached scrape result for {url}")
        return cached_result

    start_time = asyncio.get_event_loop().time()

    try:
        result = await fetch_url(url, request_config)
    except EmptyContentError as e:
        logger.error(f"No content extracted from {url}: {e}")
        result = ScrapeResultItem(url=url, status="empty_content", error=str(e))
    except CrawlError as e:
        logger.error(f"Crawl failed for {url}: {e}")
        result = ScrapeResultItem(url=url, status="crawl_error", error=str(e))
    except TimeoutError as e:
        logger.error(f"Timed out scraping {url}: {e}")
        result = ScrapeResultItem(url=url, status="timeout", error=str(e))
    except Exception as e:
        logger.error(f"Failed completely on {url}: {e}")
        result = ScrapeResultItem(url=url, status="failed", error=str(e))
        
    elapsed = asyncio.get_event_loop().time() - start_time
    result.duration_ms = int(elapsed * 1000)
    logger.info(f"Request for {url} ended with status: {result.status} in {elapsed:.2f}s")
    
    await db_repository.save_result(result)
    return result
