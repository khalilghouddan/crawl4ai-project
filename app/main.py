import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from app.api.routes import router
from app.db.database import db
from app.db.models import init_db
from app.config import PROJECT_NAME, PROJECT_DESCRIPTION, PROJECT_VERSION

app = FastAPI(
    title=PROJECT_NAME, 
    description=PROJECT_DESCRIPTION,
    version=PROJECT_VERSION
)

app.include_router(router)

@app.on_event("startup")
async def startup_event():
    await db.connect()
    if db.pool:
        await init_db()

@app.on_event("shutdown")
async def shutdown_event():
    await db.disconnect()

if __name__ == "__main__":
    import uvicorn
    # Make sure to run this via standard terminal usage or module `-m app.main`
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
