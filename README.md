# SignalLens

SignalLens is a personal AI intelligence dashboard for tracking AI trends, research, products, stock-watchlist events, Chinese social signals, and daily digests.

The initial product requirements are documented in [ai_intelligence_dashboard_prd.md](ai_intelligence_dashboard_prd.md).

## Project Documents

- [Technical Design](docs/technical_design.md)
- [Source Feasibility](docs/source_feasibility.md)
- [Development Process](docs/development_process.md)
- [Conversation Log](docs/conversation_log.md)

## Status

Current phase: MVP implementation in progress.

The initial backend scaffold lives in [services/api](services/api). The recommended MVP stack is:

- Frontend: Next.js, React, TypeScript, Tailwind CSS
- Backend: Python FastAPI
- Database: PostgreSQL with pgvector
- Scheduler: APScheduler for MVP, Celery/RQ later if needed
- Cache/queue: Redis
- LLM providers: configurable API-based providers

## Local Backend Setup

Create a virtual environment and install the API service:

```bash
cd services/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

From the repository root, start local infrastructure:

```bash
docker compose -f infra/docker-compose.yml up -d
```

The Docker PostgreSQL service maps to host port `55432` to avoid conflicts with a local
Postgres running on the default `5432`.

Run the API:

```bash
cd services/api
uvicorn app.main:app --reload
```

Useful endpoints:

- `GET http://127.0.0.1:8000/api/health`
- `GET http://127.0.0.1:8000/api/watchlist/stocks`
- `GET http://127.0.0.1:8000/api/watchlist/stocks/signals/summary`
- `GET http://127.0.0.1:8000/api/watchlist/stocks/MU/signals`
- `GET http://127.0.0.1:8000/api/watchlist/stocks/MU/briefing`
- `GET http://127.0.0.1:8000/api/watchlist/stocks/MU/prices`
- `GET http://127.0.0.1:8000/api/watchlist/topics`
- `GET http://127.0.0.1:8000/api/feed`
- `GET http://127.0.0.1:8000/api/feed?saved_only=true`
- `GET http://127.0.0.1:8000/api/feed/{item_id}`
- `GET http://127.0.0.1:8000/api/search`
- `POST http://127.0.0.1:8000/api/search/natural-language`
- `GET http://127.0.0.1:8000/api/preferences`
- `PATCH http://127.0.0.1:8000/api/preferences`
- `GET http://127.0.0.1:8000/api/alerts`
- `GET http://127.0.0.1:8000/api/alerts/rules`
- `GET http://127.0.0.1:8000/api/digest/daily`
- `GET http://127.0.0.1:8000/api/digest/daily/markdown`
- `GET http://127.0.0.1:8000/api/digest/daily/snapshots`
- `POST http://127.0.0.1:8000/api/digest/daily/snapshots`
- `GET http://127.0.0.1:8000/api/events/clusters`
- `GET http://127.0.0.1:8000/api/sources/health`
- `GET http://127.0.0.1:8000/api/sources/runs`
- `PATCH http://127.0.0.1:8000/api/sources/{source_id}`
- `POST http://127.0.0.1:8000/api/sources/{source_id}/run`
- `POST http://127.0.0.1:8000/api/ingestion/hacker-news`
- `POST http://127.0.0.1:8000/api/ingestion/alpha-vantage-news`
- `POST http://127.0.0.1:8000/api/ingestion/alpha-vantage-prices`
- `POST http://127.0.0.1:8000/api/ingestion/arxiv`
- `POST http://127.0.0.1:8000/api/ingestion/chinese-rss`
- `POST http://127.0.0.1:8000/api/ingestion/github`
- `POST http://127.0.0.1:8000/api/ingestion/hugging-face`
- `POST http://127.0.0.1:8000/api/ingestion/product-hunt`
- `POST http://127.0.0.1:8000/api/ingestion/rss`
- `POST http://127.0.0.1:8000/api/manual-submissions`
- `POST http://127.0.0.1:8000/api/watchlist/stocks`
- `PATCH http://127.0.0.1:8000/api/watchlist/stocks/{ticker}`
- `DELETE http://127.0.0.1:8000/api/watchlist/stocks/{ticker}`
- `POST http://127.0.0.1:8000/api/watchlist/topics`
- `PATCH http://127.0.0.1:8000/api/watchlist/topics/{topic}`
- `DELETE http://127.0.0.1:8000/api/watchlist/topics/{topic}`
- `POST http://127.0.0.1:8000/api/feed/{item_id}/save`
- `POST http://127.0.0.1:8000/api/feed/{item_id}/unsave`
- `POST http://127.0.0.1:8000/api/feed/{item_id}/hide`
- `POST http://127.0.0.1:8000/api/feed/{item_id}/mark-important`
- `POST http://127.0.0.1:8000/api/feed/{item_id}/classify`
- `POST http://127.0.0.1:8000/api/feed/{item_id}/summarize`
- `POST http://127.0.0.1:8000/api/llm/process-feed`
- `POST http://127.0.0.1:8000/api/alerts/generate`
- `POST http://127.0.0.1:8000/api/alerts/rules`
- `PATCH http://127.0.0.1:8000/api/alerts/rules/{rule_id}`
- `DELETE http://127.0.0.1:8000/api/alerts/rules/{rule_id}`
- `POST http://127.0.0.1:8000/api/alerts/{alert_id}/dismiss`
- `POST http://127.0.0.1:8000/api/llm/smoke-test`

Run database migrations and seed the initial stock watchlist:

```bash
cd services/api
alembic upgrade head
python scripts/seed_database.py
```

Run the Kimi API smoke test:

```bash
cd services/api
python scripts/smoke_test_kimi.py
```

Product Hunt ingestion is optional and uses the official GraphQL API. Set
`PRODUCT_HUNT_API_TOKEN` in `.env` to enable it; without a token the source run is
recorded as `skipped`.

Alpha Vantage stock news ingestion is optional. Set `ALPHA_VANTAGE_API_KEY` in
`.env` to enable watched-ticker news; without a key the source run is recorded as
`skipped`.

Chinese social trend ingestion is configurable through public RSS/Atom feeds. Set
`CHINESE_RSS_FEEDS` in `.env` as comma-separated `Name|URL` entries; without feeds
the source run is recorded as `skipped`.

Run one scheduled ingestion cycle from the command line:

```bash
cd services/api
python scripts/run_scheduler.py
```

Run the local scheduler continuously:

```bash
cd services/api
SIGNALLENS_SCHEDULER_MODE=forever SIGNALLENS_SCHEDULER_INTERVAL_MINUTES=360 python scripts/run_scheduler.py
```

## Local Web Setup

Install frontend dependencies from the repository root:

```bash
pnpm install
```

Run the dashboard:

```bash
pnpm web:dev
```

Open:

```text
http://127.0.0.1:3000
```

The web app expects the API at:

```text
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

The dashboard System Readiness panel reads `/api/health` and shows which optional
integration environment variables are configured without exposing secret values.
