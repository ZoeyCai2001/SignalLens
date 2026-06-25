from sqlalchemy.orm import Session

from app.db.models import StockWatchlistItem
from app.services.seed_data import initial_stock_watchlist


def seed_initial_stock_watchlist(db: Session) -> list[StockWatchlistItem]:
    existing = {item.ticker for item in db.query(StockWatchlistItem).all()}
    created: list[StockWatchlistItem] = []

    for seed_item in initial_stock_watchlist():
        if seed_item.ticker in existing:
            continue
        item = StockWatchlistItem(**seed_item.model_dump(), user_id="local")
        db.add(item)
        created.append(item)

    db.commit()

    return (
        db.query(StockWatchlistItem)
        .order_by(
            StockWatchlistItem.is_pinned.desc(),
            StockWatchlistItem.priority.asc(),
            StockWatchlistItem.ticker.asc(),
        )
        .all()
    )
