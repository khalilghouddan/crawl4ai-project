#asyncronous program buid in python 
import asyncio
#instead of print (logger.info .error )
from app.utils.logger import logger
#just the input output data
from app.schemas.scrape_schema import ScrapeRequest, ScrapeResultItem
#fuction to to preper HTTP header
from app.scraper.headers import prepare_headers
#for proxi this is nothing right now 
from app.scraper.proxy import format_proxy
#the rtey file i build ealier 
from app.scraper.retry import get_retry_decorator, ScrapeError
#url
from app.utils.validators import is_valid_url
#db
from app.db.repository import db_repository

#i will call crawl for ai and them i will verfy if the user hve v4
#vesrion consediration 
from crawl4ai import AsyncWebCrawler
try:
    #controles the browser env(procy,network,mode,identity ),cleaning and filtring,
    from crawl4ai import BrowserConfig, CrawlerRunConfig, CacheMode
    HAS_CRAWL4AI_V4 = True
except ImportError:
    HAS_CRAWL4AI_V4 = False

#repete the fuction if it fais
@get_retry_decorator()
#ayc def
async def fetch_url(url: str, request_config: ScrapeRequest) -> ScrapeResultItem:
    #bdina loggs
    logger.info(f"Scraping URL -> {url}")
    
    #cosum heder b fonctrion le 3adelna 
    headers = prepare_headers(request_config.custom_headers)
    proxy = format_proxy(request_config.proxy) if request_config.proxy else None
    
    #if we have v4
    if HAS_CRAWL4AI_V4:
        #CONFIG OBJECTS → clean + reusable + organized
        #configuring the browser no ui 
        browser_cfg = BrowserConfig(headless=True, proxy=proxy, headers=headers)
        #i will controle crawilng behibre
        run_cfg = CrawlerRunConfig(
            #no cache
            cache_mode=CacheMode.BYPASS, 
            #ignor empty pages
            word_count_threshold=10, 
            #remove usless html
            excluded_tags=['script', 'style', 'nav', 'footer', 'aside', 'header'],
            #popops
            remove_overlay_elements=True
        )
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url, config=run_cfg)
    else:
        #INLINE PARAMETERS → messy + less flexible
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url=url,
                word_count_threshold=10,
                bypass_cache=True,
                remove_overlay_elements=True,
                exclude_tags=['script', 'style', 'nav', 'footer', 'aside', 'header']
            )
    
    #cheking if scrap worked or faild 
    #pasting the error
    if not result.success:
        raise ScrapeError(f"Crawl4AI parsing error: {result.error_message}")
        
    #copy the content and make sure is not empty 
    clean_content = result.markdown
    if not clean_content or len(clean_content.strip()) == 0:
        raise ScrapeError("Scraped content is conceptually empty or JavaScript failed to mount fully.")
    
    #sart with no somry
    summary = None
    #cheking if will use the summury 
    if request_config.extract_summary:
        #cheking if it exeist 
        if hasattr(result, "extracted_content") and result.extracted_content:
            summary = result.extracted_content 
        else:
            #use the first 300 caracter as summry
            summary = clean_content[:300] + "..." if len(clean_content) > 300 else clean_content
            
    #link init
    links = []
    #ckeking if the user want links 
    if request_config.extract_links:
        internal_links = result.links.get('internal', []) if hasattr(result, 'links') and isinstance(result.links, dict) else []
        links = [link.get('href') for link in internal_links if isinstance(link, dict) and link.get('href')]
        
    logger.info(f"Successfully scraped URL -> {url}")
    return ScrapeResultItem(
        url=url,
        title=result.metadata.get('title') if result.metadata else None,
        content=clean_content,
        summary=summary,
        links=links if links else None,
        status="success"
    )

async def process_url(url: str, request_config: ScrapeRequest) -> ScrapeResultItem:
    if not is_valid_url(url):
        res = ScrapeResultItem(url=url, status="failed", error="Invalid URL format. Use http:// or https://")
        await db_repository.save_result(res)
        return res
    if not is_valid_url(url):
        res = ScrapeResultItem(url=url, status="failed", error="Invalid URL format. Use http:// or https://")
        await db_repository.save_result(res)
        return res
        
    start_time = asyncio.get_event_loop().time()
    try:
        result = await fetch_url(url, request_config)
    except Exception as e:
        logger.error(f"Failed completely on {url}: {e}")
        result = ScrapeResultItem(url=url, status="failed", error=str(e))
        
    elapsed = asyncio.get_event_loop().time() - start_time
    logger.info(f"Request for {url} ended with status: {result.status} in {elapsed:.2f}s")
    
    await db_repository.save_result(result)
    return result
