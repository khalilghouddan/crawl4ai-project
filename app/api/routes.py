"""HTTP routes for health checks and scrape requests."""

import asyncio
from fastapi import APIRouter, HTTPException

from app.schemas.scrape_schema import ScrapeRequest, ScrapeResponse, ScrapeResultItem
from app.scraper.crawl_service import process_url
from app.core.settings import settings
from app.utils.logger import logger
from app.db.database import db
from app.db.repository import db_repository

router = APIRouter()
scrape_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_SCRAPES)

@router.get("/health")
async def health_check():
    """Return API health and database connection status."""
    return {
        "status": "ok", 
        "database": "connected" if db.pool else "disconnected"
    }

@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_endpoint(request: ScrapeRequest):
    """Scrape one or more URLs concurrently and return normalized results."""
    urls = request.urls if isinstance(request.urls, list) else [request.urls]
    if not urls:
        raise HTTPException(status_code=400, detail="No URLs provided")
        
    logger.info(f"Initiating pool scrape operation for {len(urls)} concurrent URLs.")
    
    async def _safe_scrape(u):
        """Run one scrape while respecting the API-wide concurrency limit."""
        async with scrape_semaphore:
            return await process_url(u, request)

    batch_timeout = request.batch_timeout_seconds or settings.SCRAPE_BATCH_TIMEOUT_SECONDS
    tasks = {
        asyncio.create_task(_safe_scrape(url)): (index, url)
        for index, url in enumerate(urls)
    }
    done, pending = await asyncio.wait(tasks, timeout=batch_timeout)

    results_by_index: dict[int, ScrapeResultItem] = {}
    for task in done:
        index, url = tasks[task]
        try:
            results_by_index[index] = task.result()
        except Exception as exc:
            logger.error(f"Unexpected scrape task failure for {url}: {exc}")
            results_by_index[index] = ScrapeResultItem(
                url=url,
                status="failed",
                error=str(exc),
            )

    if pending:
        logger.warning(
            f"Batch scrape timed out after {batch_timeout}s; "
            f"returning {len(done)} completed and {len(pending)} timed out result(s)."
        )
    for task in pending:
        index, url = tasks[task]
        task.cancel()
        result = ScrapeResultItem(
            url=url,
            status="timeout",
            error=f"Batch timeout after {batch_timeout} seconds before this URL completed.",
        )
        results_by_index[index] = result
        await db_repository.save_result(result)

    if pending:
        await asyncio.gather(*pending, return_exceptions=True)

    results = [results_by_index[index] for index in range(len(urls))]
    
    return ScrapeResponse(results=results)
