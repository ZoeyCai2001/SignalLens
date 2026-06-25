# SignalLens API

This service contains the FastAPI backend for SignalLens.

## Responsibilities

- Expose dashboard, watchlist, source health, and LLM processing APIs.
- Coordinate source connectors and ingestion jobs.
- Store normalized intelligence items in PostgreSQL.
- Keep the LLM provider swappable.

## Local Development

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run the server:

```bash
uvicorn app.main:app --reload
```

Run migrations:

```bash
alembic upgrade head
```

Seed the initial stock watchlist:

```bash
python scripts/seed_database.py
```

Run the Kimi smoke test:

```bash
python scripts/smoke_test_kimi.py
```

Ingest Hacker News top stories:

```bash
curl -X POST "http://127.0.0.1:8000/api/ingestion/hacker-news?limit=30"
```

Ingest recent arXiv AI papers:

```bash
curl -X POST "http://127.0.0.1:8000/api/ingestion/arxiv?limit=25"
```

Summarize a stored feed item with Kimi:

```bash
curl -X POST "http://127.0.0.1:8000/api/feed/1/summarize"
```

Submit a manual URL:

```bash
curl -X POST "http://127.0.0.1:8000/api/manual-submissions" \
  -H "Content-Type: application/json" \
  -d '{"title":"Manual AI note","url":"https://example.com","text":"Optional context"}'
```

Save, hide, or mark a feed item:

```bash
curl -X POST "http://127.0.0.1:8000/api/feed/1/save"
curl -X POST "http://127.0.0.1:8000/api/feed/1/hide"
curl -X POST "http://127.0.0.1:8000/api/feed/1/mark-important"
```

Search stored feed items:

```bash
curl "http://127.0.0.1:8000/api/search?q=agent&category=research&limit=10"
curl "http://127.0.0.1:8000/api/search?topic=inference&saved_only=true"
```

Generate the daily digest from stored feed items:

```bash
curl "http://127.0.0.1:8000/api/digest/daily"
curl "http://127.0.0.1:8000/api/digest/daily?date=2026-06-25&limit_per_section=3"
```
