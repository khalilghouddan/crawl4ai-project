import asyncpg
from typing import Optional
from app.utils.logger import logger
from app.core.settings import settings

class DatabaseManager:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        logger.info("Connecting to PostgreSQL...")
        try:
            self.pool = await asyncpg.create_pool(dsn=settings.DATABASE_URL)
            logger.info("Successfully connected to PostgreSQL.")
        except Exception as e:
            logger.error(f"Failed to connect to database. {e}")

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            logger.info("Disconnected from PostgreSQL.")

db = DatabaseManager()
