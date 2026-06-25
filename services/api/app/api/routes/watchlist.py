from fastapi import APIRouter

from app.schemas.watchlist import StockWatchlistItem
from app.services.seed_data import initial_stock_watchlist

router = APIRouter()


@router.get("/stocks", response_model=list[StockWatchlistItem])
async def list_stock_watchlist() -> list[StockWatchlistItem]:
    return initial_stock_watchlist()
