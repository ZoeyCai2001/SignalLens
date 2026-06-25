from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.schemas.ingestion import IngestionRunResponse
from app.services.ingestion import (
    run_arxiv_ingestion,
    run_github_ingestion,
    run_hacker_news_ingestion,
    run_hugging_face_ingestion,
)

router = APIRouter()


@router.post("/hacker-news", response_model=IngestionRunResponse)
async def ingest_hacker_news(
    db: DbSession,
    limit: int = Query(default=30, ge=1, le=100),
) -> IngestionRunResponse:
    result = await run_hacker_news_ingestion(db=db, limit=limit)
    return IngestionRunResponse.model_validate(result)


@router.post("/arxiv", response_model=IngestionRunResponse)
async def ingest_arxiv(
    db: DbSession,
    limit: int = Query(default=25, ge=1, le=100),
) -> IngestionRunResponse:
    result = await run_arxiv_ingestion(db=db, limit=limit)
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
