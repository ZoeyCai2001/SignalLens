from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession
from app.schemas.watchlist import (
    StockSignalSummary,
    StockWatchlistItem,
    TopicWatchlistItem,
    TopicWatchlistItemCreate,
)
from app.services.seed_data import initial_stock_watchlist, initial_topic_watchlist
from app.services.watchlist import (
    create_topic_watchlist_item,
    get_stock_signals,
    list_topic_watchlist,
    seed_initial_stock_watchlist,
    seed_initial_topic_watchlist,
    summarize_stock_signals,
)
from app.services.watchlist import (
    list_stock_watchlist as list_stock_watchlist_items,
)

router = APIRouter()


@router.get("/stocks", response_model=list[StockWatchlistItem])
async def list_stock_watchlist(db: DbSession) -> list[StockWatchlistItem]:
    items = list_stock_watchlist_items(db)
    if not items:
        return initial_stock_watchlist()
    return [StockWatchlistItem.model_validate(item) for item in items]


@router.post("/stocks/seed", response_model=list[StockWatchlistItem])
async def seed_stock_watchlist(db: DbSession) -> list[StockWatchlistItem]:
    items = seed_initial_stock_watchlist(db)
    return [StockWatchlistItem.model_validate(item) for item in items]


@router.get("/stocks/signals/summary", response_model=list[StockSignalSummary])
async def list_stock_signal_summary(
    db: DbSession,
    limit_per_stock: Annotated[int, Query(ge=0, le=10)] = 3,
) -> list[StockSignalSummary]:
    return summarize_stock_signals(db, limit_per_stock=limit_per_stock)


@router.get("/stocks/{ticker}/signals", response_model=StockSignalSummary)
async def list_stock_signals(
    ticker: str,
    db: DbSession,
    limit: Annotated[int, Query(ge=0, le=100)] = 20,
) -> StockSignalSummary:
    result = get_stock_signals(db, ticker=ticker, limit=limit)
    if result is None:
        raise HTTPException(status_code=404, detail="Stock ticker not found in watchlist.")
    return result


@router.get("/topics", response_model=list[TopicWatchlistItem])
async def list_topics(db: DbSession) -> list[TopicWatchlistItem]:
    items = list_topic_watchlist(db)
    if not items:
        return initial_topic_watchlist()
    return [TopicWatchlistItem.model_validate(item) for item in items]


@router.post("/topics", response_model=TopicWatchlistItem)
async def create_topic(
    payload: TopicWatchlistItemCreate,
    db: DbSession,
) -> TopicWatchlistItem:
    item = create_topic_watchlist_item(db, payload)
    return TopicWatchlistItem.model_validate(item)


@router.post("/topics/seed", response_model=list[TopicWatchlistItem])
async def seed_topics(db: DbSession) -> list[TopicWatchlistItem]:
    items = seed_initial_topic_watchlist(db)
    return [TopicWatchlistItem.model_validate(item) for item in items]
