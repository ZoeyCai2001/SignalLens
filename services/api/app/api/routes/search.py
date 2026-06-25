from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.schemas.feed import FeedItem
from app.services.search import search_feed_items

router = APIRouter()


@router.get("", response_model=list[FeedItem])
async def search_items(
    db: DbSession,
    q: str | None = Query(default=None, max_length=300),
    source: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, max_length=80),
    ticker: str | None = Query(default=None, max_length=20),
    topic: str | None = Query(default=None, max_length=120),
    language: str | None = Query(default=None, max_length=20),
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    min_importance_score: float | None = Query(default=None, ge=0, le=1),
    saved_only: bool = Query(default=False),
    limit: int = Query(default=30, ge=1, le=100),
) -> list[FeedItem]:
    return search_feed_items(
        db=db,
        query=q,
        source=source,
        category=category,
        ticker=ticker,
        topic=topic,
        language=language,
        date_from=date_from,
        date_to=date_to,
        min_importance_score=min_importance_score,
        saved_only=saved_only,
        limit=limit,
    )
