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
from app.services.feed_actions import normalize_feed_module_filter
from app.services.preferences import get_user_preferences
from app.services.search import (
    build_search_summary,
    infer_search_intent,
    latest_stored_item_date,
    search_feed_items,
)

router = APIRouter()


@router.get("", response_model=list[FeedItem])
async def search_items(
    db: DbSession,
    q: str | None = Query(default=None, max_length=300),
    source: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, max_length=80),
    subcategory: str | None = Query(default=None, max_length=120),
    ticker: str | None = Query(default=None, max_length=20),
    company: str | None = Query(default=None, max_length=120),
    topic: str | None = Query(default=None, max_length=120),
    manual_tag: str | None = Query(default=None, max_length=60),
    language: str | None = Query(default=None, max_length=20),
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    min_importance_score: float | None = Query(default=None, ge=0, le=1),
    min_social_signal_score: float | None = Query(default=None, ge=0, le=1),
    ai_related: bool | None = Query(default=None),
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
        subcategory=subcategory,
        ticker=ticker,
        company=company,
        topic=topic,
        manual_tag=manual_tag,
        language=language,
        date_from=date_from,
        date_to=date_to,
        min_importance_score=min_importance_score,
        min_social_signal_score=min_social_signal_score,
        ai_related=ai_related,
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
    intent = infer_search_intent(
        payload.query,
        recent_anchor_date=latest_stored_item_date(db),
    )
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
        summary=build_search_summary(payload.query, intent, items),
    )
