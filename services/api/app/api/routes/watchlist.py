from fastapi import APIRouter

from app.api.deps import DbSession
from app.db.models import StockWatchlistItem as StockWatchlistItemModel
from app.schemas.watchlist import StockWatchlistItem, TopicWatchlistItem, TopicWatchlistItemCreate
from app.services.seed_data import initial_stock_watchlist, initial_topic_watchlist
from app.services.watchlist import (
    create_topic_watchlist_item,
    list_topic_watchlist,
    seed_initial_stock_watchlist,
    seed_initial_topic_watchlist,
)

router = APIRouter()


@router.get("/stocks", response_model=list[StockWatchlistItem])
async def list_stock_watchlist(db: DbSession) -> list[StockWatchlistItem]:
    items = (
        db.query(StockWatchlistItemModel)
        .order_by(
            StockWatchlistItemModel.is_pinned.desc(),
            StockWatchlistItemModel.priority.asc(),
            StockWatchlistItemModel.ticker.asc(),
        )
        .all()
    )
    if not items:
        return initial_stock_watchlist()
    return [StockWatchlistItem.model_validate(item) for item in items]


@router.post("/stocks/seed", response_model=list[StockWatchlistItem])
async def seed_stock_watchlist(db: DbSession) -> list[StockWatchlistItem]:
    items = seed_initial_stock_watchlist(db)
    return [StockWatchlistItem.model_validate(item) for item in items]


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
