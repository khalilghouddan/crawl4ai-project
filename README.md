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

Run PostgreSQL, start the API, and serve the frontend:

```bash
docker compose up --build
```

- **Frontend:** http://localhost:5174
- **API Docs:** http://localhost:8007/docs
- **Health Check:** http://localhost:8007/health
- **PostgreSQL:** `localhost:5433`, database `deep_search_results`, user `postgres`, password `change_me`

The compose setup uses these services:

- `db`: PostgreSQL database
- `api`: FastAPI + Crawl4AI service
- `frontend`: static React test UI

To inspect saved scrape results from your host machine:

```bash
docker compose exec -T db psql -U postgres -d deep_search_results -c "select id, url, status, created_at from scraped_pages order by created_at desc limit 10;"
```

Stop everything:

```bash
docker compose down
```

Stop and delete the PostgreSQL volume:

```bash
docker compose down -v
```
