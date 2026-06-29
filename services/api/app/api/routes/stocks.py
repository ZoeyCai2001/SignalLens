from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession
from app.schemas.watchlist import (
    StockBriefing,
    StockBriefingTimelineItem,
    StockMarketSnapshot,
    StockSignalSummary,
)
from app.services.preferences import get_user_preferences
from app.services.watchlist import (
    build_stock_market_snapshot,
    get_stock_briefing,
    summarize_stock_signals,
)

router = APIRouter()


@router.get("/watchlist-dashboard", response_model=list[StockSignalSummary])
async def get_stock_watchlist_dashboard(
    db: DbSession,
    limit_per_stock: Annotated[int, Query(ge=0, le=10)] = 3,
) -> list[StockSignalSummary]:
    preferences = get_user_preferences(db)
    return summarize_stock_signals(
        db,
        limit_per_stock=limit_per_stock,
        blocked_sources=preferences.blocked_sources,
    )


@router.get("/{ticker}", response_model=StockBriefing)
async def get_stock_detail(
    ticker: str,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> StockBriefing:
    briefing = get_preference_aware_stock_briefing(db=db, ticker=ticker, limit=limit)
    if briefing is None:
        raise HTTPException(status_code=404, detail="Stock ticker not found in watchlist.")
    return briefing


@router.get("/{ticker}/events", response_model=list[StockBriefingTimelineItem])
async def get_stock_events(
    ticker: str,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[StockBriefingTimelineItem]:
    briefing = get_preference_aware_stock_briefing(db=db, ticker=ticker, limit=limit)
    if briefing is None:
        raise HTTPException(status_code=404, detail="Stock ticker not found in watchlist.")
    return briefing.recent_timeline


@router.get("/{ticker}/price-series", response_model=StockMarketSnapshot | None)
async def get_stock_price_series(
    ticker: str,
    db: DbSession,
    limit: Annotated[int, Query(ge=2, le=260)] = 260,
) -> StockMarketSnapshot | None:
    return build_stock_market_snapshot(db=db, ticker=ticker, limit=limit)


def get_preference_aware_stock_briefing(
    db: DbSession,
    ticker: str,
    limit: int,
) -> StockBriefing | None:
    preferences = get_user_preferences(db)
    return get_stock_briefing(
        db,
        ticker=ticker,
        limit=limit,
        blocked_sources=preferences.blocked_sources,
    )
