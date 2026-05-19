"""Initialize or upgrade the PostgreSQL schema for MicroScraper."""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.database import db
from app.db.models import init_db
from app.utils.logger import logger


async def main() -> None:
    """Connect to PostgreSQL, apply schema changes, and close the pool."""
    await db.connect()
    if not db.pool:
        raise SystemExit("Could not connect to PostgreSQL. Check your .env settings.")

    try:
        await init_db()
        logger.info("Database schema is ready.")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
