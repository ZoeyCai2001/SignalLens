from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, StockWatchlistItem
from app.schemas.watchlist import StockWatchlistItemCreate, StockWatchlistItemUpdate
from app.services.watchlist import (
    create_stock_watchlist_item,
    list_stock_watchlist,
    move_stock_watchlist_item,
    update_stock_watchlist_item,
)


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


def test_create_stock_watchlist_item_resolves_seed_metadata_from_ticker() -> None:
    db = make_db()

    created = create_stock_watchlist_item(
        db,
        StockWatchlistItemCreate(ticker="mu"),
    )

    assert created.ticker == "MU"
    assert created.company_name == "Micron Technology"
    assert created.priority == "High"
    assert created.group_name == "Memory / Storage"
    assert created.industry == "Semiconductors"
    assert created.is_pinned is True
    assert "HBM memory" in created.related_ai_themes


def test_create_stock_watchlist_item_resolves_seed_metadata_from_company() -> None:
    db = make_db()

    created = create_stock_watchlist_item(
        db,
        StockWatchlistItemCreate(company_name="Marvell Technology"),
    )

    assert created.ticker == "MRVL"
    assert created.company_name == "Marvell Technology"
    assert created.group_name == "AI Chips"
    assert "custom silicon" in created.related_ai_themes


def test_create_stock_watchlist_item_resolves_alias_company_to_ticker() -> None:
    db = make_db()

    created = create_stock_watchlist_item(
        db,
        StockWatchlistItemCreate(company_name="Broadcom"),
    )

    assert created.ticker == "AVGO"
    assert created.company_name == "Broadcom"
    assert created.exchange == "NASDAQ"
    assert created.group_name == "Watch Only"


def test_create_stock_watchlist_item_requires_ticker_or_known_company() -> None:
    db = make_db()

    try:
        create_stock_watchlist_item(db, StockWatchlistItemCreate())
    except ValueError as exc:
        assert "ticker or known company name" in str(exc)
    else:
        raise AssertionError("Expected empty stock watchlist create payload to fail")


def test_update_stock_watchlist_item_can_change_display_name_without_blank_overwrite() -> None:
    db = make_db()
    db.add(make_stock("MU", display_order=10))
    db.commit()

    updated = update_stock_watchlist_item(
        db,
        "MU",
        StockWatchlistItemUpdate(company_name="  Micron AI Memory  "),
    )
    blank_update = update_stock_watchlist_item(
        db,
        "MU",
        StockWatchlistItemUpdate(company_name="   "),
    )

    assert updated is not None
    assert updated.company_name == "Micron AI Memory"
    assert blank_update is not None
    assert blank_update.company_name == "Micron AI Memory"


def test_update_stock_watchlist_item_ignores_blank_required_metadata() -> None:
    db = make_db()
    db.add(make_stock("MRVL", display_order=10, priority="High"))
    db.commit()

    updated = update_stock_watchlist_item(
        db,
        "MRVL",
        StockWatchlistItemUpdate(
            exchange="   ",
            sector="   ",
            industry="   ",
            priority="   ",
            group_name="   ",
        ),
    )

    assert updated is not None
    assert updated.exchange == "NASDAQ"
    assert updated.sector == "Technology"
    assert updated.industry == "Semiconductors"
    assert updated.priority == "High"
    assert updated.group_name == "Watch Only"


def test_update_stock_watchlist_item_can_clear_notes() -> None:
    db = make_db()
    db.add(make_stock("SNDK", display_order=10, notes="Monitor storage cycle"))
    db.commit()

    updated = update_stock_watchlist_item(
        db,
        "SNDK",
        StockWatchlistItemUpdate(notes="   "),
    )

    assert updated is not None
    assert updated.notes is None


def test_move_stock_watchlist_item_swaps_with_neighbor_after_normalizing_order() -> None:
    db = make_db()
    db.add_all(
        [
            make_stock("MU", display_order=10, priority="High", is_pinned=True),
            make_stock("MRVL", display_order=10, priority="Medium", is_pinned=True),
            make_stock("SNDK", display_order=10, priority="High", is_pinned=False),
        ]
    )
    db.commit()

    moved = move_stock_watchlist_item(db, "MRVL", "up")

    assert moved is not None
    assert [stock.ticker for stock in moved] == ["MRVL", "MU", "SNDK"]
    assert [(stock.ticker, stock.display_order) for stock in moved[:2]] == [
        ("MRVL", 10),
        ("MU", 20),
    ]


def test_move_stock_watchlist_item_stays_within_pin_group() -> None:
    db = make_db()
    db.add_all(
        [
            make_stock("MU", display_order=10, priority="High", is_pinned=True),
            make_stock("MRVL", display_order=10, priority="High", is_pinned=False),
            make_stock("SNDK", display_order=20, priority="Medium", is_pinned=False),
        ]
    )
    db.commit()

    moved = move_stock_watchlist_item(db, "MRVL", "up")

    assert moved is not None
    assert [stock.ticker for stock in moved] == ["MU", "MRVL", "SNDK"]
    assert [(stock.ticker, stock.display_order) for stock in moved[1:]] == [
        ("MRVL", 10),
        ("SNDK", 20),
    ]


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
    notes: str | None = None,
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
        notes=notes,
    )
