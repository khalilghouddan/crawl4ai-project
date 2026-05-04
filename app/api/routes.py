#run multiple tasks at the same time
import asyncio
#fastapi router to define routes
from fastapi import APIRouter, HTTPException
#schemas for request in the folder shemat 
from app.schemas.scrape_schema import ScrapeRequest, ScrapeResponse
#process url in the folder scraper
from app.scraper.crawl_service import process_url
#control how many requests run at once
from app.core.settings import settings
#logger in the folder utils
from app.utils.logger import logger
#database 
from app.db.database import db
from app.db.repository import db_repository
from app.utils.validators import is_valid_url

#router object
router = APIRouter()

#health check endpoint
@router.get("/health")
async def health_check():
    return {
        "status": "ok", 
        "database": "connected" if db.pool else "disconnected"
    }

#scrape endpoint
@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_endpoint(request: ScrapeRequest):
    #Normalize Input (single or list)
    urls = request.urls if isinstance(request.urls, list) else [request.urls]
    #If empty → return error
    if not urls:
        raise HTTPException(status_code=400, detail="No URLs provided")
        
    logger.info(f"Initiating pool scrape operation for {len(urls)} concurrent URLs.")
    
    #A limit on how many tasks run at the same time
    semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_SCRAPES)
    
    async def _safe_scrape(u):
        async with semaphore:
            if not is_valid_url(u):
                res = ScrapeResultItem(url=u, status="failed", error="Invalid URL format. Use http:// or https://")
                await db_repository.save_result(res)
                return res
            
            result = await process_url(u, request)
            await db_repository.save_result(result)
            return result
            
    tasks = [_safe_scrape(u) for u in urls]
    results = await asyncio.gather(*tasks)
    
    return ScrapeResponse(results=results)
