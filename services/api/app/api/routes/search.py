from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession
from app.schemas.feed import FeedItem
from app.schemas.search import (
    NaturalLanguageSearchRequest,
    NaturalLanguageSearchResponse,
    SearchIntentResponse,
)
from app.services.preferences import get_user_preferences
from app.services.search import infer_search_intent, search_feed_items
from app.services.feed_actions import normalize_feed_module_filter

router = APIRouter()


@router.get("", response_model=list[FeedItem])
async def search_items(
    db: DbSession,
    q: str | None = Query(default=None, max_length=300),
    source: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, max_length=80),
    ticker: str | None = Query(default=None, max_length=20),
    company: str | None = Query(default=None, max_length=120),
    topic: str | None = Query(default=None, max_length=120),
    manual_tag: str | None = Query(default=None, max_length=60),
    language: str | None = Query(default=None, max_length=20),
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    min_importance_score: float | None = Query(default=None, ge=0, le=1),
    saved_only: bool = Query(default=False),
    read_status: str | None = Query(default=None, max_length=20),
    module: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=30, ge=1, le=100),
) -> list[FeedItem]:
    if module and not normalize_feed_module_filter(module):
        raise HTTPException(
            status_code=400,
            detail="Unsupported feed module. Use trends, research, products, stocks, or chinese.",
        )
    preferences = get_user_preferences(db)
    return search_feed_items(
        db=db,
        query=q,
        source=source,
        category=category,
        ticker=ticker,
        company=company,
        topic=topic,
        manual_tag=manual_tag,
        language=language,
        date_from=date_from,
        date_to=date_to,
        min_importance_score=min_importance_score,
        saved_only=saved_only,
        read_status=read_status,
        ranking_weights=preferences.ranking_weights,
        preferred_sources=preferences.preferred_sources,
        blocked_sources=preferences.blocked_sources,
        language_preferences=preferences.language_preferences,
        module=module,
        limit=limit,
    )


@router.post("/natural-language", response_model=NaturalLanguageSearchResponse)
async def search_items_with_natural_language(
    payload: NaturalLanguageSearchRequest,
    db: DbSession,
) -> NaturalLanguageSearchResponse:
    if payload.module and not normalize_feed_module_filter(payload.module):
        raise HTTPException(
            status_code=400,
            detail="Unsupported feed module. Use trends, research, products, stocks, or chinese.",
        )
    preferences = get_user_preferences(db)
    intent = infer_search_intent(payload.query)
    items = search_feed_items(
        db=db,
        query=payload.query,
        ranking_weights=preferences.ranking_weights,
        preferred_sources=preferences.preferred_sources,
        blocked_sources=preferences.blocked_sources,
        language_preferences=preferences.language_preferences,
        module=payload.module,
        limit=payload.limit,
    )
    return NaturalLanguageSearchResponse(
        intent=SearchIntentResponse.model_validate(intent),
        items=items,
    )
