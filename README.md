# MicroScraper Microservice

A modular web scraping service built with FastAPI, Crawl4AI, and PostgreSQL. It renders pages, extracts clean content, falls back when extraction is weak, and stores results for later reuse.

## What It Does

- Scrapes one URL or many URLs in a single request.
- Uses Crawl4AI for the primary scrape path.
- Scrolls and expands pages during scraping to reveal lazy-loaded content.
- Falls back to static HTML extraction when the primary result looks too weak.
- Returns partial results when a batch has some failures or timeouts.
- Caches results in PostgreSQL so repeat requests can reuse prior work.
- Includes a separate React frontend for running scrapes and viewing results.

## Architecture

The project is organized as a small service pipeline:

- `app/main.py`: app startup, CORS, DB connect and disconnect
- `app/api/routes.py`: `/health` and `/scrape`
- `app/scraper/crawl_service.py`: scraping flow, scroll logic, fallback extraction, cache handling
- `app/schemas/scrape_schema.py`: request and response models
- `app/db/*`: PostgreSQL pool, table setup, and repository layer
- `frontend/src/App.jsx` and `frontend/styles.css`: UI for driving the API

## Fallback Behavior

The scraper is designed to fail soft when possible.

The fallback chain is:

1. Crawl4AI rendered scrape
2. Markdown and HTML candidate scoring
3. Static HTML fetch fallback
4. `EmptyContentError` if no usable content remains

A few other safeguards are built in:

- If Crawl4AI reports a problem but the extracted content is still usable, the scraper keeps the result instead of failing immediately.
- If a cached result looks too shallow, the service can ignore it and scrape again.
- If some URLs in a batch time out, the API can still return the successful results.

## Multi-URL Scraping

Yes, the API can scrape multiple websites in the same request.

The `/scrape` endpoint accepts either a single URL or a list of URLs, and the route layer runs them concurrently with `asyncio.create_task(...)`. Concurrency is limited by `MAX_CONCURRENT_SCRAPES`, so the service can scale up while still avoiding uncontrolled browser load.

## Setup & Installation

**1. Install Python dependencies**

From the project root:

```bash
pip install -r requirements.txt
```

**2. Install the browser runtime**

Set up the browser components required by Crawl4AI:

```bash
python -m playwright install chromium
crawl4ai-setup
```

**3. Configure environment variables**

Create a local `.env` file from the example template:

```bash
cp .env.example .env
```

**4. Initialize the database**

Create or update the PostgreSQL tables before starting the API:

```bash
python scripts/init_db.py
```

## Running the API

Start the local development server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- Interactive docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Docker Compose

Start the API and frontend with Docker Compose. PostgreSQL must already be running locally and reachable from Docker through `host.docker.internal`.

```bash
docker compose up --build
```

- Frontend: http://localhost:5174
- API docs: http://localhost:8007/docs
- Health check: http://localhost:8007/health
- PostgreSQL: local database configured in `.env`, for example `localhost:5433`

The compose setup uses these services:

- `api`: FastAPI + Crawl4AI service
- `frontend`: React UI for running scrapes

By default, Docker Compose limits the API to `MAX_CONCURRENT_SCRAPES=10`. Crawl4AI uses browser contexts for extraction, so increasing this value can raise memory usage quickly.

For Docker Compose, keep `API_POSTGRES_HOST=host.docker.internal` and set `API_POSTGRES_PORT` to your local PostgreSQL port.

To inspect saved scrape results from your host machine:

```bash
psql -h localhost -p 5433 -U postgres -d deep_search_results -c "select id, url, status, created_at from scraped_pages order by created_at desc limit 10;"
```

Stop everything:

```bash
docker compose down
```
