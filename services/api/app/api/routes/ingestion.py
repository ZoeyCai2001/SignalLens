from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.schemas.ingestion import IngestionRunResponse
from app.services.ingestion import (
    run_alpha_vantage_news_ingestion,
    run_arxiv_ingestion,
    run_chinese_rss_ingestion,
    run_github_ingestion,
    run_hacker_news_ingestion,
    run_hugging_face_ingestion,
    run_product_hunt_ingestion,
    run_rss_ingestion,
)

router = APIRouter()


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
