from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.schemas.ingestion import IngestionRunResponse
from app.services.ingestion import run_hacker_news_ingestion

router = APIRouter()


@router.post("/hacker-news", response_model=IngestionRunResponse)
async def ingest_hacker_news(
    db: DbSession,
    limit: int = Query(default=30, ge=1, le=100),
) -> IngestionRunResponse:
    result = await run_hacker_news_ingestion(db=db, limit=limit)
    return IngestionRunResponse.model_validate(result)
