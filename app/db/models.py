from app.db.database import db

async def init_db():
    query = '''
    CREATE TABLE IF NOT EXISTS scraped_pages (
        id SERIAL PRIMARY KEY,
        url TEXT NOT NULL,
        title TEXT,
        content TEXT,
        summary TEXT,
        status TEXT NOT NULL,
        error_msg TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    '''
    if db.pool:
        async with db.pool.acquire() as conn:
            await conn.execute(query)
