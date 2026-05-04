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
crawl4ai-setup
```

**3. Set Environment Variables**
Configure the DB in `.env`.

---

## ⚡ Running the API
**Start the local Uvicorn development server as a module:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- **Interactive Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
