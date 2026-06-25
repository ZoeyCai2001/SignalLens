from fastapi import APIRouter

from app.api.deps import DbSession
from app.db.models import StockWatchlistItem as StockWatchlistItemModel
from app.schemas.watchlist import StockWatchlistItem
from app.services.seed_data import initial_stock_watchlist
from app.services.watchlist import seed_initial_stock_watchlist

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
