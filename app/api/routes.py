"""HTTP routes for health checks and scrape requests."""

import asyncio
from fastapi import APIRouter, HTTPException

from app.schemas.scrape_schema import ScrapeRequest, ScrapeResponse
from app.scraper.crawl_service import process_url
from app.core.settings import settings
from app.utils.logger import logger
from app.db.database import db

router = APIRouter()

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
    
    semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_SCRAPES)
    
    async def _safe_scrape(u):
        """Run one scrape while respecting the endpoint concurrency limit."""
        async with semaphore:
            return await process_url(u, request)
            
    tasks = [_safe_scrape(u) for u in urls]
    results = await asyncio.gather(*tasks)
    
    return ScrapeResponse(results=results)
