from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import feed, health, ingestion, llm, manual_submissions, sources, watchlist
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SignalLens API",
        version="0.1.0",
        description="Backend API for the SignalLens personal AI intelligence dashboard.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(feed.router, prefix="/api/feed", tags=["feed"])
    app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
    app.include_router(watchlist.router, prefix="/api/watchlist", tags=["watchlist"])
    app.include_router(ingestion.router, prefix="/api/ingestion", tags=["ingestion"])
    app.include_router(
        manual_submissions.router,
        prefix="/api/manual-submissions",
        tags=["manual-submissions"],
    )
    app.include_router(llm.router, prefix="/api/llm", tags=["llm"])
    return app


app = create_app()
