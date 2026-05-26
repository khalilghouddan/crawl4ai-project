# MicroScraper Microservice

A production-ready, modular API built with FastAPI and Crawl4AI. It performs scalable, concurrent web scraping to extract clean, AI-ready data, storing the results directly into PostgreSQL.

## Features

- **Modular Architecture**: Cleanly separated logic with repositories, services, and schemas.
- **FastAPI**: Fully asynchronous endpoints and concurrent processing.
- **Crawl4AI Integration**: Headless page rendering strictly for extraction.
- **Auto DB Persist**: Automatically creates PostgreSQL schemas and logs results cleanly.
- **Anti-Bot Basics**: Rotates browser dummy user-agents and supports proxies.

---

## 🚀 Setup & Installation

**1. Install Python Dependencies**
Navigate to the `scraper-service` directory:
```bash
cd C:\emsi\stage_nttdta\code\scraping\scraper-service
pip install -r requirements.txt
```

**2. Initialize Crawl4AI**
Setup the required internal headless browsers:
```bash
python -m playwright install chromium
crawl4ai-setup
```

**3. Set Environment Variables**
Configure the DB in `.env`.
```bash
cp .env.example .env
```

**4. Initialize the Database**
Create or update the PostgreSQL tables before starting the API:
```bash
python scripts/init_db.py
```

---

## ⚡ Running the API
**Start the local Uvicorn development server as a module:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- **Interactive Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

---

## 🐳 Docker Compose

Start the API and serve the frontend. PostgreSQL must already be running locally and reachable from Docker through `host.docker.internal`.

```bash
docker compose up --build
```

- **Frontend:** http://localhost:5174
- **API Docs:** http://localhost:8007/docs
- **Health Check:** http://localhost:8007/health
- **PostgreSQL:** local database configured in `.env`, for example `localhost:5433`

The compose setup uses these services:

- `api`: FastAPI + Crawl4AI service
- `frontend`: static React test UI

By default, Docker Compose limits the API to `MAX_CONCURRENT_SCRAPES=10`. Crawl4AI uses browser contexts for extraction, so raising this value can increase memory use quickly.

For Docker Compose, keep `API_POSTGRES_HOST=host.docker.internal` and set `API_POSTGRES_PORT` to your local PostgreSQL port.

To inspect saved scrape results from your host machine:

```bash
psql -h localhost -p 5433 -U postgres -d deep_search_results -c "select id, url, status, created_at from scraped_pages order by created_at desc limit 10;"
```

Stop everything:

```bash
docker compose down
```
