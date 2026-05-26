"""Crawl4AI integration and scrape result normalization."""

import asyncio
import inspect
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib import request as url_request

from app.utils.logger import logger
from app.schemas.scrape_schema import ScrapeRequest, ScrapeResultItem
from app.scraper.headers import prepare_headers
from app.scraper.proxy import format_proxy
from app.scraper.retry import CrawlError, EmptyContentError, get_retry_decorator
from app.utils.cleaner import clean_markdown
from app.utils.validators import is_valid_url
from app.db.repository import db_repository
from app.core.settings import settings

from crawl4ai import AsyncWebCrawler
try:
    from crawl4ai import BrowserConfig, CrawlerRunConfig, CacheMode
    HAS_CRAWL4AI_V4 = True
except ImportError:
    HAS_CRAWL4AI_V4 = False
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


MIN_CONTENT_CHARS = 120
MIN_CONTENT_WORDS = 30
SUSPICIOUS_CONTENT_WORDS = 350
ARTICLE_SELECTORS = (
    "article",
    "main",
    "[role='main']",
    ".entry-content",
    ".post-content",
    ".article-content",
    ".article__content",
    ".blog-post-content",
    ".post-body",
    ".content-area",
    "#content",
)
READ_MORE_TERMS = (
    "accept",
    "agree",
    "allow",
    "continuer",
    "accepter",
    "j'accepte",
    "lire la suite",
    "read more",
    "show more",
    "load more",
    "voir plus",
)
SCROLL_AND_EXPAND_JS = """
async () => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const terms = %s;
  const isVisible = (el) => {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style && style.visibility !== "hidden" && style.display !== "none" && rect.width > 0 && rect.height > 0;
  };
  for (const el of Array.from(document.querySelectorAll("button, a, [role='button']"))) {
    const text = (el.innerText || el.textContent || el.getAttribute("aria-label") || "").trim().toLowerCase();
    if (text && terms.some((term) => text.includes(term)) && isVisible(el)) {
      try { el.click(); await sleep(400); } catch (_) {}
    }
  }
  let previousHeight = 0;
  for (let i = 0; i < 10; i += 1) {
    window.scrollTo(0, document.body.scrollHeight);
    await sleep(650);
    const currentHeight = document.body.scrollHeight;
    if (currentHeight === previousHeight && i > 2) break;
    previousHeight = currentHeight;
  }
  window.scrollTo(0, 0);
}
""" % json.dumps(list(READ_MORE_TERMS))


@dataclass(frozen=True)
class ContentCandidate:
    """A candidate text extracted from one source."""

    source: str
    text: str
    raw_text: str | None = None

    @property
    def words(self) -> int:
        return word_count(self.text)

    @property
    def complete(self) -> bool:
        return is_complete_enough(self.text)

    @property
    def score(self) -> float:
        return self.words * source_weight(self.source)


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
    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        lines = [
            line.strip()
            for line in soup.get_text(separator="\n").splitlines()
            if line.strip()
        ]
        return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()

    parser = TextExtractor()
    parser.feed(html)
    return parser.get_text()


def soup_text(node) -> str | None:
    """Extract normalized text from a BeautifulSoup node."""
    if not BeautifulSoup or not node:
        return None

    clone = BeautifulSoup(str(node), "html.parser")
    for tag in clone(["script", "style", "noscript", "svg", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()

    lines = [
        line.strip()
        for line in clone.get_text(separator="\n").splitlines()
        if line.strip()
    ]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return text or None


def iter_jsonld_values(value):
    """Yield nested JSON-LD dictionaries."""
    if isinstance(value, dict):
        yield value
        graph = value.get("@graph")
        if graph:
            yield from iter_jsonld_values(graph)
    elif isinstance(value, list):
        for item in value:
            yield from iter_jsonld_values(item)


def jsonld_article_bodies(soup) -> list[str]:
    """Extract articleBody values from JSON-LD metadata."""
    bodies: list[str] = []
    for script in soup.find_all("script", type=lambda value: value and "ld+json" in value):
        raw = script.string or script.get_text()
        if not raw or not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue

        for item in iter_jsonld_values(payload):
            article_body = item.get("articleBody")
            if isinstance(article_body, str) and article_body.strip():
                bodies.append(article_body.strip())

    return bodies


def html_text_candidates(html: str, source_prefix: str) -> list[ContentCandidate]:
    """Return article-aware text candidates from HTML."""
    candidates: list[ContentCandidate] = []
    if not isinstance(html, str) or not html.strip():
        return candidates

    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        for body in jsonld_article_bodies(soup):
            add_candidate(candidates, f"{source_prefix}.jsonld.articleBody", body)

        for selector in ARTICLE_SELECTORS:
            for index, node in enumerate(soup.select(selector)[:4]):
                add_candidate(candidates, f"{source_prefix}.{selector}:{index}", soup_text(node))

    add_candidate(candidates, f"{source_prefix}.body", html_to_text(html))
    return candidates


def source_weight(source: str) -> float:
    """Prefer article-specific sources without ignoring much richer generic text."""
    if "jsonld.articleBody" in source:
        return 1.45
    if any(token in source for token in ("article", "main", "entry-content", "post-content", "article-content", "post-body")):
        return 1.25
    if "markdown.raw_markdown" in source or "result.markdown_raw" in source:
        return 1.15
    if "fit_markdown" in source:
        return 0.55
    if source.endswith(".body"):
        return 0.85
    return 1.0


def supported_config(config_cls, **kwargs):
    """Build a Crawl4AI config using only kwargs supported by the installed version."""
    try:
        signature = inspect.signature(config_cls)
    except (TypeError, ValueError):
        return config_cls(**kwargs)

    if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values()):
        return config_cls(**kwargs)

    supported = {
        key: value
        for key, value in kwargs.items()
        if key in signature.parameters and value is not None
    }
    return config_cls(**supported)


async def fetch_static_html(url: str, headers: dict) -> str:
    """Fetch HTML without Playwright as a fallback for structural false positives."""
    def _read_url():
        req = url_request.Request(url, headers=headers or {})
        with url_request.urlopen(req, timeout=settings.SCRAPE_STATIC_FETCH_TIMEOUT_SECONDS) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")

    return await asyncio.to_thread(_read_url)


def normalize_text(value):
    """Return stripped text when a value contains usable text."""
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def word_count(text: str | None) -> int:
    """Count human-readable words in extracted text."""
    return len(re.findall(r"\w+", text or ""))


def is_complete_enough(text: str | None) -> bool:
    """Detect title-only/snippet extractions without rejecting normal short pages."""
    return len(text or "") >= MIN_CONTENT_CHARS or word_count(text) >= MIN_CONTENT_WORDS


def add_candidate(candidates: list[ContentCandidate], source: str, text: str | None, clean: bool = False):
    """Normalize and append one extraction candidate."""
    normalized = normalize_text(text)
    if not normalized:
        return

    raw_text = normalized
    if clean:
        normalized = clean_markdown(normalized)
        if not normalized:
            return

    if normalized not in {candidate.text for candidate in candidates}:
        candidates.append(ContentCandidate(source=source, text=normalized, raw_text=raw_text))


def best_candidate(candidates: list[ContentCandidate]) -> ContentCandidate | None:
    """Choose the richest candidate, keeping fit_markdown as the last resort."""
    if not candidates:
        return None

    non_fit = [candidate for candidate in candidates if candidate.source != "markdown.fit_markdown"]
    pool = non_fit or candidates
    complete = [candidate for candidate in pool if candidate.complete]
    return max(complete or pool, key=lambda candidate: (candidate.score, candidate.words, len(candidate.text)))


def markdown_candidates(result) -> list[ContentCandidate]:
    """Collect markdown candidates from Crawl4AI in safest priority order."""
    candidates: list[ContentCandidate] = []
    markdown_value = getattr(result, "markdown", None)

    add_candidate(candidates, "result.markdown_raw", getattr(result, "markdown_raw", None), clean=True)
    for attr in ("raw_markdown", "markdown", "markdown_with_citations", "fit_markdown"):
        add_candidate(candidates, f"markdown.{attr}", getattr(markdown_value, attr, None), clean=True)
    if isinstance(markdown_value, str):
        add_candidate(candidates, "result.markdown", markdown_value, clean=True)

    return candidates


def html_candidates(result) -> list[ContentCandidate]:
    """Collect text candidates from rendered HTML returned by Crawl4AI."""
    candidates: list[ContentCandidate] = []
    for attr, source in (("cleaned_html", "html.cleaned"), ("html", "html.rendered")):
        html = getattr(result, attr, None)
        candidates.extend(html_text_candidates(html, source))
    return candidates


async def static_html_candidate(url: str, headers: dict) -> ContentCandidate | None:
    """Fetch the original HTML when Crawl4AI returns only a weak snippet."""
    return best_candidate(html_text_candidates(await fetch_static_html(url, headers), "html.static"))


def should_replace_content(current: ContentCandidate | None, fallback: ContentCandidate | None) -> bool:
    """Return whether fallback is clearly better than the current candidate."""
    if not fallback:
        return False
    if not current:
        return True
    if fallback.complete and not current.complete:
        return True
    return fallback.words > current.words and len(fallback.text) > len(current.text)


def page_timeout_for_request(request_config: ScrapeRequest) -> int:
    """Return Crawl4AI page timeout for one URL."""
    return request_config.page_timeout_ms or settings.SCRAPE_PAGE_TIMEOUT_MS


def extract_content(result):
    """Return the best Crawl4AI content candidate before external fallback."""
    return best_candidate(markdown_candidates(result) + html_candidates(result))


@get_retry_decorator()
async def fetch_url(url: str, request_config: ScrapeRequest) -> ScrapeResultItem:
    """Fetch and extract one URL with Crawl4AI."""
    logger.info(f"Scraping URL -> {url}")
    
    headers = prepare_headers(request_config.custom_headers)
    proxy = format_proxy(request_config.proxy) if request_config.proxy else None
    
    if HAS_CRAWL4AI_V4:
        user_agent = headers.get("User-Agent")
        browser_cfg = supported_config(
            BrowserConfig,
            headless=True,
            proxy=proxy,
            headers=headers,
            user_agent=user_agent,
            enable_stealth=True,
            viewport={"width": 1366, "height": 900},
        )
        run_cfg = supported_config(
            CrawlerRunConfig,
            cache_mode=CacheMode.BYPASS,
            word_count_threshold=1,
            excluded_tags=["script", "style"],
            remove_overlay_elements=True,
            remove_consent_popups=True,
            wait_until="networkidle",
            js_code=SCROLL_AND_EXPAND_JS,
            page_timeout=page_timeout_for_request(request_config),
            delay_before_return_html=2.0,
            scan_full_page=True,
            max_scroll_steps=10,
            scroll_delay=0.65,
            process_iframes=True,
            flatten_shadow_dom=True,
            simulate_user=True,
            override_navigator=True,
            magic=True,
            max_retries=1,
            fallback_fetch_function=lambda fallback_url: fetch_static_html(
                fallback_url,
                headers,
            ),
        )
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url, config=run_cfg)
    else:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url=url,
                word_count_threshold=1,
                bypass_cache=True,
                js_code=SCROLL_AND_EXPAND_JS,
                remove_overlay_elements=True,
                exclude_tags=["script", "style"]
            )
    
    content = extract_content(result)
    if not content or not content.complete or content.words < SUSPICIOUS_CONTENT_WORDS:
        try:
            fallback = await static_html_candidate(url, headers)
            if should_replace_content(content, fallback):
                content = fallback
        except Exception as e:
            logger.warning(f"Static HTML fallback failed for {url}: {e}")

    if not result.success:
        if content:
            logger.warning(
                f"Crawl4AI reported failure for {url}, but usable content was extracted: {result.error_message}"
            )
        else:
            raise CrawlError(f"Crawl4AI parsing error: {result.error_message}")

    if not content or not content.text.strip():
        raise EmptyContentError("Scraped content is empty after markdown and HTML fallback extraction.")
    
    summary = None
    if request_config.extract_summary:
        if hasattr(result, "extracted_content") and result.extracted_content:
            summary = result.extracted_content
        else:
            summary = content.text[:300] + "..." if len(content.text) > 300 else content.text
            
    links = []
    if request_config.extract_links:
        internal_links = (
            result.links.get("internal", [])
            if hasattr(result, "links") and isinstance(result.links, dict)
            else []
        )
        links = [
            link.get("href")
            for link in internal_links
            if isinstance(link, dict) and link.get("href")
        ]
        
    metadata = dict(result.metadata or {})
    metadata.update(
        {
            "content_source": content.source,
            "content_length": len(content.text),
            "content_words": content.words,
            "content_complete": content.complete,
        }
    )

    logger.info(f"Successfully scraped URL -> {url} using {content.source}")
    return ScrapeResultItem(
        url=url,
        title=result.metadata.get("title") if result.metadata else None,
        markdown=content.text,
        markdown_raw=content.raw_text or content.text,
        summary=summary,
        links=links if links else None,
        metadata=metadata if metadata else None,
        status="success"
    )


def cached_result_is_usable(result: ScrapeResultItem) -> bool:
    """Avoid serving old title-only cached rows forever."""
    if not is_complete_enough(result.markdown):
        return False

    words = word_count(result.markdown)
    metadata = result.metadata or {}
    source = str(metadata.get("content_source") or "")
    if words < SUSPICIOUS_CONTENT_WORDS and "fit_markdown" in source:
        return False
    if words < SUSPICIOUS_CONTENT_WORDS and metadata.get("content_complete") is False:
        return False

    return True


def cache_ttl_for_request(request_config: ScrapeRequest) -> int | None:
    """Return cache max-age in seconds; None means cache never expires."""
    ttl = (
        request_config.cache_ttl_seconds
        if request_config.cache_ttl_seconds is not None
        else settings.SCRAPE_CACHE_TTL_SECONDS
    )
    return ttl or None


async def process_url(url: str, request_config: ScrapeRequest) -> ScrapeResultItem:
    """Validate, scrape, time, persist, and return one URL result."""
    
    if not is_valid_url(url):
        res = ScrapeResultItem(
            url=url,
            status="invalid_url",
            error="Invalid URL format. Use http:// or https://",
        )
        await db_repository.save_result(res)
        return res

    if not request_config.bypass_cache:
        cached_result = await db_repository.get_successful_result_by_url(
            url,
            max_age_seconds=cache_ttl_for_request(request_config),
        )
        if cached_result and cached_result_is_usable(cached_result):
            logger.info(f"Returning cached scrape result for {url}")
            return cached_result
        if cached_result:
            logger.info(f"Ignoring incomplete cached scrape result for {url}")

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
