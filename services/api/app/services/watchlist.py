from sqlalchemy.orm import Session

from app.db.models import StockWatchlistItem, TopicWatchlistItem
from app.schemas.watchlist import TopicWatchlistItemCreate
from app.services.seed_data import initial_stock_watchlist, initial_topic_watchlist


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


def seed_initial_topic_watchlist(db: Session) -> list[TopicWatchlistItem]:
    existing = {item.topic for item in db.query(TopicWatchlistItem).all()}
    created: list[TopicWatchlistItem] = []

    for seed_item in initial_topic_watchlist():
        if seed_item.topic in existing:
            continue
        item = TopicWatchlistItem(**seed_item.model_dump(), user_id="local")
        db.add(item)
        created.append(item)

    db.commit()

    return list_topic_watchlist(db)


def list_topic_watchlist(db: Session) -> list[TopicWatchlistItem]:
    return (
        db.query(TopicWatchlistItem)
        .order_by(
            TopicWatchlistItem.is_pinned.desc(),
            TopicWatchlistItem.priority.asc(),
            TopicWatchlistItem.label.asc(),
        )
        .all()
    )


def create_topic_watchlist_item(
    db: Session,
    payload: TopicWatchlistItemCreate,
) -> TopicWatchlistItem:
    topic = payload.topic.strip().lower().replace(" ", "-")
    label = payload.label.strip() if payload.label else payload.topic.strip()
    item = TopicWatchlistItem(
        user_id="local",
        topic=topic,
        label=label,
        category=payload.category,
        priority=payload.priority,
        is_pinned=payload.is_pinned,
        include_in_digest=payload.include_in_digest,
        related_terms=payload.related_terms,
        notes=payload.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
