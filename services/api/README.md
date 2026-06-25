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

Run one local scheduled ingestion cycle:

```bash
python scripts/run_scheduler.py
```

Run the scheduler continuously with a six-hour interval:

```bash
SIGNALLENS_SCHEDULER_MODE=forever SIGNALLENS_SCHEDULER_INTERVAL_MINUTES=360 python scripts/run_scheduler.py
```

Ingest watched-ticker AI stock news with an optional `ALPHA_VANTAGE_API_KEY`:

```bash
curl -X POST "http://127.0.0.1:8000/api/ingestion/alpha-vantage-news?limit=25"
```

Ingest Hacker News top stories:

```bash
curl -X POST "http://127.0.0.1:8000/api/ingestion/hacker-news?limit=30"
```

Ingest recent arXiv AI papers:

```bash
curl -X POST "http://127.0.0.1:8000/api/ingestion/arxiv?limit=25"
```

Ingest configured Chinese public RSS/Atom feeds:

```bash
curl -X POST "http://127.0.0.1:8000/api/ingestion/chinese-rss?limit=25"
```

Configure feeds with `CHINESE_RSS_FEEDS`, using comma-separated `Name|URL` entries.

Ingest public GitHub AI repositories:

```bash
curl -X POST "http://127.0.0.1:8000/api/ingestion/github?limit=20"
```

Ingest public Hugging Face model metadata:

```bash
curl -X POST "http://127.0.0.1:8000/api/ingestion/hugging-face?limit=25"
```

Ingest Product Hunt launches with an optional `PRODUCT_HUNT_API_TOKEN`:

```bash
curl -X POST "http://127.0.0.1:8000/api/ingestion/product-hunt?limit=25"
```

Ingest selected public RSS feeds:

```bash
curl -X POST "http://127.0.0.1:8000/api/ingestion/rss?limit=25"
```

Summarize a stored feed item with Kimi:

```bash
curl -X POST "http://127.0.0.1:8000/api/feed/1/summarize"
```

Classify a stored feed item with Kimi:

```bash
curl -X POST "http://127.0.0.1:8000/api/feed/1/classify"
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

Generate, read, and dismiss dashboard alerts:

```bash
curl -X POST "http://127.0.0.1:8000/api/alerts/generate"
curl "http://127.0.0.1:8000/api/alerts?limit=10"
curl -X POST "http://127.0.0.1:8000/api/alerts/1/dismiss"
```

Create, update, or delete alert rules:

```bash
curl "http://127.0.0.1:8000/api/alerts/rules"
curl -X POST "http://127.0.0.1:8000/api/alerts/rules" \
  -H "Content-Type: application/json" \
  -d '{"name":"Watch AVGO custom silicon","category":"stock_company_event","tickers":["AVGO"],"topics":["custom silicon"],"min_importance_score":0.65}'
curl -X PATCH "http://127.0.0.1:8000/api/alerts/rules/1" \
  -H "Content-Type: application/json" \
  -d '{"enabled":false}'
curl -X DELETE "http://127.0.0.1:8000/api/alerts/rules/1"
```

Generate the daily digest from stored feed items:

```bash
curl "http://127.0.0.1:8000/api/digest/daily"
curl "http://127.0.0.1:8000/api/digest/daily?date=2026-06-25&limit_per_section=3"
```

Read deterministic event clusters:

```bash
curl "http://127.0.0.1:8000/api/events/clusters?limit=10&min_items=1"
```

Read and seed topic watchlist items:

```bash
curl "http://127.0.0.1:8000/api/watchlist/topics"
curl -X POST "http://127.0.0.1:8000/api/watchlist/topics/seed"
curl -X POST "http://127.0.0.1:8000/api/watchlist/topics" \
  -H "Content-Type: application/json" \
  -d '{"topic":"model-routing","label":"Model routing","priority":"Medium","related_terms":["router","mixture of experts"]}'
curl -X PATCH "http://127.0.0.1:8000/api/watchlist/topics/model-routing" \
  -H "Content-Type: application/json" \
  -d '{"category":"technical_trend","is_pinned":true}'
curl -X DELETE "http://127.0.0.1:8000/api/watchlist/topics/model-routing"
```

Read stock-linked AI signals:

```bash
curl "http://127.0.0.1:8000/api/watchlist/stocks/signals/summary"
curl "http://127.0.0.1:8000/api/watchlist/stocks/MU/signals?limit=10"
```

Create, update, or delete a stock watchlist item:

```bash
curl -X POST "http://127.0.0.1:8000/api/watchlist/stocks" \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AVGO","company_name":"Broadcom","related_ai_themes":["custom silicon"],"related_keywords":["AI ASIC"]}'
curl -X PATCH "http://127.0.0.1:8000/api/watchlist/stocks/AVGO" \
  -H "Content-Type: application/json" \
  -d '{"priority":"High","is_pinned":true}'
curl -X DELETE "http://127.0.0.1:8000/api/watchlist/stocks/AVGO"
```
