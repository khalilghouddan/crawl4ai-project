"""FastAPI application entrypoint for the MicroScraper service."""

import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.db.database import db
from app.config import PROJECT_NAME, PROJECT_DESCRIPTION, PROJECT_VERSION

app = FastAPI(
    title=PROJECT_NAME, 
    description=PROJECT_DESCRIPTION,
    version=PROJECT_VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.on_event("startup")
async def startup_event():
    """Connect to PostgreSQL when the API starts."""
    await db.connect()

@app.on_event("shutdown")
async def shutdown_event():
    """Close the PostgreSQL connection pool when the API stops."""
    await db.disconnect()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
