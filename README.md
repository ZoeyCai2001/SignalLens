# SignalLens

SignalLens is a personal AI intelligence dashboard for tracking AI trends, research, products, stock-watchlist events, Chinese social signals, and daily digests.

The initial product requirements are documented in [ai_intelligence_dashboard_prd.md](ai_intelligence_dashboard_prd.md).

## Project Documents

- [Technical Design](docs/technical_design.md)
- [Development Process](docs/development_process.md)
- [Conversation Log](docs/conversation_log.md)

## Status

Current phase: backend MVP scaffold.

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
- `GET http://127.0.0.1:8000/api/feed`
- `GET http://127.0.0.1:8000/api/sources/health`
- `POST http://127.0.0.1:8000/api/ingestion/hacker-news`
- `POST http://127.0.0.1:8000/api/ingestion/arxiv`
- `POST http://127.0.0.1:8000/api/feed/{item_id}/summarize`
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
