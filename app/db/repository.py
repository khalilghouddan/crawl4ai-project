"""Repository functions for storing scrape results in PostgreSQL."""

import json

from app.db.database import db
from app.schemas.scrape_schema import ScrapeResultItem
from app.utils.logger import logger

def to_json(value):
    """Serialize optional Python values for PostgreSQL JSONB columns."""
    return json.dumps(value, default=str) if value else None

def from_json(value):
    """Decode values returned from PostgreSQL JSONB columns."""
    if value is None:
        return None
    if isinstance(value, str):
        return json.loads(value)
    return value

class DBRepository:
    """Persistence layer for scrape result records."""

    async def get_successful_result_by_url(self, url: str):
        """Return the newest successful scrape result for a URL, if one exists."""
        if not db.pool:
            return None

        query = '''
        SELECT
            url,
            title,
            markdown,
            markdown_raw,
            summary,
            links,
            metadata,
            status,
            error_msg,
            duration_ms
        FROM scraped_pages
        WHERE url = $1
          AND status = 'success'
        ORDER BY created_at DESC
        LIMIT 1
        '''

        try:
            async with db.pool.acquire() as conn:
                row = await conn.fetchrow(query, url)
        except Exception as e:
            logger.error(f"Failed to read cached scrape result for {url}: {e}")
            return None

        if not row:
            return None

        return ScrapeResultItem(
            url=row["url"],
            title=row["title"],
            markdown=row["markdown"],
            markdown_raw=row["markdown_raw"],
            summary=row["summary"],
            links=from_json(row["links"]),
            metadata=from_json(row["metadata"]),
            status=row["status"],
            error=row["error_msg"],
            duration_ms=row["duration_ms"],
        )

    async def save_result(self, result: ScrapeResultItem):
        """Insert a single scrape result if the database pool is available."""
        if not db.pool:
            return
            
        query = '''
        INSERT INTO scraped_pages (
            url,
            title,
            markdown,
            markdown_raw,
            summary,
            links,
            metadata,
            status,
            error_msg,
            duration_ms
        )
        VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, $8, $9, $10)
        '''
        try:
            async with db.pool.acquire() as conn:
                await conn.execute(
                    query, 
                    result.url, 
                    result.title, 
                    result.markdown, 
                    result.markdown_raw,
                    result.summary, 
                    to_json(result.links),
                    to_json(result.metadata),
                    result.status, 
                    result.error,
                    result.duration_ms
                )
        except Exception as e:
            logger.error(f"Failed to auto-save result for {result.url} into database: {e}")

db_repository = DBRepository()
