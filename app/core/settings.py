"""Application settings loaded from environment variables and .env."""

import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)


class Settings:
    """Runtime configuration for PostgreSQL and scraper concurrency."""

    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "deep_search_results")

    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        (
            f"postgresql://{quote_plus(POSTGRES_USER)}:"
            f"{quote_plus(POSTGRES_PASSWORD)}@"
            f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
        ),
    )
    MAX_CONCURRENT_SCRAPES = int(os.getenv("MAX_CONCURRENT_SCRAPES", "10"))
    SCRAPE_CACHE_TTL_SECONDS = int(os.getenv("SCRAPE_CACHE_TTL_SECONDS", "0"))
    SCRAPE_BATCH_TIMEOUT_SECONDS = int(os.getenv("SCRAPE_BATCH_TIMEOUT_SECONDS", "240"))
    SCRAPE_PAGE_TIMEOUT_MS = int(os.getenv("SCRAPE_PAGE_TIMEOUT_MS", "60000"))
    SCRAPE_STATIC_FETCH_TIMEOUT_SECONDS = int(os.getenv("SCRAPE_STATIC_FETCH_TIMEOUT_SECONDS", "20"))

settings = Settings()
