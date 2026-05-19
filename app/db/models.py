"""Database schema initialization for persisted scrape results."""

from app.db.database import db

async def init_db():
    """Create or upgrade the scraped_pages table used by the service."""
    query = '''
    CREATE TABLE IF NOT EXISTS scraped_pages (
        id BIGSERIAL PRIMARY KEY,
        url TEXT NOT NULL,
        title TEXT,
        markdown TEXT,
        markdown_raw TEXT,
        summary TEXT,
        links JSONB,
        metadata JSONB,
        status TEXT NOT NULL,
        error_msg TEXT,
        duration_ms INTEGER,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    ALTER TABLE scraped_pages
        ADD COLUMN IF NOT EXISTS markdown TEXT,
        ADD COLUMN IF NOT EXISTS markdown_raw TEXT,
        ADD COLUMN IF NOT EXISTS links JSONB,
        ADD COLUMN IF NOT EXISTS metadata JSONB,
        ADD COLUMN IF NOT EXISTS duration_ms INTEGER,
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'scraped_pages'
              AND column_name = 'content'
        ) THEN
            EXECUTE 'UPDATE scraped_pages SET markdown = content WHERE markdown IS NULL';
        END IF;
    END $$;

    ALTER TABLE scraped_pages
        DROP COLUMN IF EXISTS success;

    CREATE INDEX IF NOT EXISTS idx_scraped_pages_url
        ON scraped_pages (url);

    CREATE INDEX IF NOT EXISTS idx_scraped_pages_success_cache
        ON scraped_pages (url, created_at DESC)
        WHERE status = 'success';

    CREATE INDEX IF NOT EXISTS idx_scraped_pages_created_at
        ON scraped_pages (created_at);

    CREATE OR REPLACE FUNCTION set_scraped_pages_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    DROP TRIGGER IF EXISTS trg_scraped_pages_updated_at ON scraped_pages;

    CREATE TRIGGER trg_scraped_pages_updated_at
    BEFORE UPDATE ON scraped_pages
    FOR EACH ROW
    EXECUTE FUNCTION set_scraped_pages_updated_at();
    '''
    if db.pool:
        async with db.pool.acquire() as conn:
            await conn.execute(query)
