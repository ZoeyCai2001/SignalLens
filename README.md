# SignalLens

SignalLens is a personal AI intelligence dashboard for tracking AI trends, research, products, stock-watchlist events, Chinese social signals, and daily digests.

The initial product requirements are documented in [ai_intelligence_dashboard_prd.md](ai_intelligence_dashboard_prd.md).

## Project Documents

- [Technical Design](docs/technical_design.md)
- [Development Process](docs/development_process.md)
- [Conversation Log](docs/conversation_log.md)

## Status

Current phase: technical design first.

No application code has been scaffolded yet. The recommended MVP stack is:

- Frontend: Next.js, React, TypeScript, Tailwind CSS
- Backend: Python FastAPI
- Database: PostgreSQL with pgvector
- Scheduler: APScheduler for MVP, Celery/RQ later if needed
- Cache/queue: Redis
- LLM providers: configurable API-based providers
