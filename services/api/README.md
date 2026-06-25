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
