# MicroScraper Frontend

Small React test console for the FastAPI scraper API.

## Run

Start the backend first:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8007 --reload
```

Then serve this folder:

```bash
cd frontend
python3 -m http.server 5174
```

Open:

```text
http://127.0.0.1:5174
```
