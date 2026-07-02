from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.core.config import get_settings
from app.schemas.ingestion import (
    DemoDataSeedResponse,
    IngestionRunResponse,
    IngestionScheduleStatus,
    ScheduledCycleResponse,
)
from app.services.demo_data import seed_demo_data
from app.services.ingestion import (
    run_alpha_vantage_news_ingestion,
    run_alpha_vantage_price_ingestion,
    run_arxiv_ingestion,
    run_chinese_rss_ingestion,
    run_github_ingestion,
    run_hacker_news_ingestion,
    run_hugging_face_ingestion,
    run_product_hunt_ingestion,
    run_rss_ingestion,
    run_sec_filings_ingestion,
)
from app.services.scheduled_jobs import build_ingestion_schedule_status, run_ingestion_cycle
from app.services.watchlist import (
    seed_initial_company_watchlist,
    seed_initial_product_watchlist,
    seed_initial_stock_watchlist,
    seed_initial_topic_watchlist,
)

router = APIRouter()


@router.post("/cycle", response_model=ScheduledCycleResponse)
async def run_scheduled_ingestion_cycle(db: DbSession) -> ScheduledCycleResponse:
    result = await run_ingestion_cycle(db)
    return ScheduledCycleResponse.model_validate(result)


@router.get("/schedule", response_model=IngestionScheduleStatus)
async def read_ingestion_schedule(db: DbSession) -> IngestionScheduleStatus:
    settings = get_settings()
    return build_ingestion_schedule_status(
        db=db,
        mode=settings.signallens_scheduler_mode,
        interval_minutes=settings.signallens_scheduler_interval_minutes,
        digest_target_hour_utc=settings.digest_target_hour_utc,
    )


@router.post("/demo-data", response_model=DemoDataSeedResponse)
async def seed_local_demo_data(db: DbSession) -> DemoDataSeedResponse:
    result = {
        "seeded_stock_watchlist_count": len(seed_initial_stock_watchlist(db)),
        "seeded_company_watchlist_count": len(seed_initial_company_watchlist(db)),
        "seeded_topic_watchlist_count": len(seed_initial_topic_watchlist(db)),
        "seeded_product_watchlist_count": len(seed_initial_product_watchlist(db)),
    }
    result.update(seed_demo_data(db))
    return DemoDataSeedResponse.model_validate(result)


@router.post("/hacker-news", response_model=IngestionRunResponse)
async def ingest_hacker_news(
    db: DbSession,
    limit: int = Query(default=30, ge=1, le=100),
) -> IngestionRunResponse:
    result = await run_hacker_news_ingestion(db=db, limit=limit)
    return IngestionRunResponse.model_validate(result)


@router.post("/alpha-vantage-news", response_model=IngestionRunResponse)
async def ingest_alpha_vantage_news(
    db: DbSession,
    limit: int = Query(default=25, ge=1, le=100),
) -> IngestionRunResponse:
    result = await run_alpha_vantage_news_ingestion(db=db, limit=limit)
    return IngestionRunResponse.model_validate(result)


@router.post("/alpha-vantage-prices", response_model=IngestionRunResponse)
async def ingest_alpha_vantage_prices(
    db: DbSession,
    limit: int = Query(default=30, ge=1, le=100),
) -> IngestionRunResponse:
    result = await run_alpha_vantage_price_ingestion(db=db, limit=limit)
    return IngestionRunResponse.model_validate(result)


@router.post("/sec-filings", response_model=IngestionRunResponse)
async def ingest_sec_filings(
    db: DbSession,
    limit: int = Query(default=25, ge=1, le=100),
) -> IngestionRunResponse:
    result = await run_sec_filings_ingestion(db=db, limit=limit)
    return IngestionRunResponse.model_validate(result)


@router.post("/arxiv", response_model=IngestionRunResponse)
async def ingest_arxiv(
    db: DbSession,
    limit: int = Query(default=25, ge=1, le=100),
) -> IngestionRunResponse:
    result = await run_arxiv_ingestion(db=db, limit=limit)
    return IngestionRunResponse.model_validate(result)


@router.post("/chinese-rss", response_model=IngestionRunResponse)
async def ingest_chinese_rss(
    db: DbSession,
    limit: int = Query(default=25, ge=1, le=100),
) -> IngestionRunResponse:
    result = await run_chinese_rss_ingestion(db=db, limit=limit)
    return IngestionRunResponse.model_validate(result)


@router.post("/github", response_model=IngestionRunResponse)
async def ingest_github(
    db: DbSession,
    limit: int = Query(default=25, ge=1, le=100),
) -> IngestionRunResponse:
    result = await run_github_ingestion(db=db, limit=limit)
    return IngestionRunResponse.model_validate(result)


@router.post("/hugging-face", response_model=IngestionRunResponse)
async def ingest_hugging_face(
    db: DbSession,
    limit: int = Query(default=25, ge=1, le=100),
) -> IngestionRunResponse:
    result = await run_hugging_face_ingestion(db=db, limit=limit)
    return IngestionRunResponse.model_validate(result)


@router.post("/product-hunt", response_model=IngestionRunResponse)
async def ingest_product_hunt(
    db: DbSession,
    limit: int = Query(default=25, ge=1, le=100),
) -> IngestionRunResponse:
    result = await run_product_hunt_ingestion(db=db, limit=limit)
    return IngestionRunResponse.model_validate(result)


@router.post("/rss", response_model=IngestionRunResponse)
async def ingest_rss(
    db: DbSession,
    limit: int = Query(default=25, ge=1, le=100),
) -> IngestionRunResponse:
    result = await run_rss_ingestion(db=db, limit=limit)
    return IngestionRunResponse.model_validate(result)
