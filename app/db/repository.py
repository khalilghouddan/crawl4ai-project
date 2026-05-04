from app.db.database import db
from app.schemas.scrape_schema import ScrapeResultItem
from app.utils.logger import logger

class DBRepository:
    async def save_result(self, result: ScrapeResultItem):
        if not db.pool:
            return
            
        query = '''
        INSERT INTO scraped_pages (url, title, content, summary, status, error_msg)
        VALUES ($1, $2, $3, $4, $5, $6)
        '''
        try:
            async with db.pool.acquire() as conn:
                await conn.execute(
                    query, 
                    result.url, 
                    result.title, 
                    result.content, 
                    result.summary, 
                    result.status, 
                    result.error
                )
        except Exception as e:
            logger.error(f"Failed to auto-save result for {result.url} into database: {e}")

db_repository = DBRepository()
