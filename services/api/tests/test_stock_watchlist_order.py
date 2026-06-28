from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, StockWatchlistItem
from app.schemas.watchlist import StockWatchlistItemCreate
from app.services.watchlist import create_stock_watchlist_item, list_stock_watchlist


def test_list_stock_watchlist_uses_pin_then_display_order_then_priority() -> None:
    db = make_db()
    db.add_all(
        [
            make_stock("SNDK", display_order=10, priority="Low", is_pinned=False),
            make_stock("MRVL", display_order=20, priority="High", is_pinned=True),
            make_stock("MU", display_order=10, priority="High", is_pinned=True),
            make_stock("AVGO", display_order=10, priority="Medium", is_pinned=False),
        ]
    )
    db.commit()

    stocks = list_stock_watchlist(db)

    assert [stock.ticker for stock in stocks] == ["MU", "MRVL", "AVGO", "SNDK"]


def test_create_stock_watchlist_item_assigns_next_display_order() -> None:
    db = make_db()
    db.add(make_stock("MU", display_order=30))
    db.commit()

    created = create_stock_watchlist_item(
        db,
        StockWatchlistItemCreate(
            ticker="MRVL",
            company_name="Marvell Technology",
            related_ai_themes=["custom silicon"],
        ),
    )

    assert created.display_order == 40


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    return session_factory()


def make_stock(
    ticker: str,
    display_order: int,
    priority: str = "Medium",
    is_pinned: bool = False,
) -> StockWatchlistItem:
    return StockWatchlistItem(
        user_id="local",
        ticker=ticker,
        company_name=ticker,
        exchange="NASDAQ",
        sector="Technology",
        industry="Semiconductors",
        priority=priority,
        group_name="Watch Only",
        display_order=display_order,
        is_pinned=is_pinned,
        related_keywords=[],
        related_companies=[],
        related_ai_themes=[],
    )
