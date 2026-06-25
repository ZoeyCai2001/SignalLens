from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from app.db.models import NormalizedItem, StockWatchlistItem, TopicWatchlistItem, UserItemAction
from app.schemas.watchlist import (
    StockSignalSummary,
    TopicWatchlistItemCreate,
)
from app.schemas.watchlist import (
    StockWatchlistItem as StockWatchlistSchema,
)
from app.services.feed_actions import LOCAL_USER_ID, serialize_feed_item
from app.services.scoring import TICKER_ALIASES
from app.services.seed_data import initial_stock_watchlist, initial_topic_watchlist

NON_FINANCIAL_ADVICE_DISCLAIMER = (
    "SignalLens links AI-related items to watched stocks for research only and does not "
    "provide investment advice."
)


def list_stock_watchlist(db: Session) -> list[StockWatchlistItem]:
    return (
        db.query(StockWatchlistItem)
        .order_by(
            StockWatchlistItem.is_pinned.desc(),
            StockWatchlistItem.priority.asc(),
            StockWatchlistItem.ticker.asc(),
        )
        .all()
    )


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

    return list_stock_watchlist(db)


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


def summarize_stock_signals(
    db: Session,
    limit_per_stock: int = 3,
) -> list[StockSignalSummary]:
    stocks = list_stock_watchlist(db)
    if not stocks:
        return [
            build_stock_signal_summary(db, stock, limit=limit_per_stock)
            for stock in initial_stock_watchlist()
        ]
    return [build_stock_signal_summary(db, stock, limit=limit_per_stock) for stock in stocks]


def get_stock_signals(
    db: Session,
    ticker: str,
    limit: int = 20,
) -> StockSignalSummary | None:
    normalized_ticker = ticker.strip().upper()
    stock = (
        db.query(StockWatchlistItem)
        .filter(
            StockWatchlistItem.user_id == LOCAL_USER_ID,
            StockWatchlistItem.ticker == normalized_ticker,
        )
        .one_or_none()
    )
    if stock is None:
        stock = next(
            (item for item in initial_stock_watchlist() if item.ticker == normalized_ticker),
            None,
        )
    if stock is None:
        return None
    return build_stock_signal_summary(db, stock, limit=limit)


def build_stock_signal_summary(
    db: Session,
    stock: StockWatchlistItem | StockWatchlistSchema,
    limit: int,
) -> StockSignalSummary:
    rows = query_stock_signal_rows(db, stock=stock, limit=limit)
    top_signals = [serialize_feed_item(item, action) for item, action in rows]
    signal_count = count_stock_signal_rows(db, stock=stock)
    stock_schema = stock if isinstance(stock, StockWatchlistSchema) else (
        StockWatchlistSchema.model_validate(stock)
    )
    return StockSignalSummary(
        stock=stock_schema,
        signal_count=signal_count,
        top_signals=top_signals,
        disclaimer=NON_FINANCIAL_ADVICE_DISCLAIMER,
    )


def query_stock_signal_rows(
    db: Session,
    stock: StockWatchlistItem | StockWatchlistSchema,
    limit: int,
) -> list[tuple[NormalizedItem, UserItemAction | None]]:
    return stock_signal_query(db, stock=stock).limit(limit).all()


def count_stock_signal_rows(
    db: Session,
    stock: StockWatchlistItem | StockWatchlistSchema,
) -> int:
    return stock_signal_query(db, stock=stock).count()


def stock_signal_query(db: Session, stock: StockWatchlistItem | StockWatchlistSchema):
    conditions = []
    for symbol in build_stock_symbol_terms(stock):
        pattern = f'%"{symbol}"%'
        conditions.extend(
            [
                cast(NormalizedItem.tickers, String).ilike(pattern),
                cast(NormalizedItem.companies, String).ilike(pattern),
            ]
        )

    for term in build_stock_text_terms(stock):
        pattern = f"%{term}%"
        conditions.extend(
            [
                NormalizedItem.title.ilike(pattern),
                NormalizedItem.text.ilike(pattern),
                NormalizedItem.summary_short.ilike(pattern),
                NormalizedItem.summary_detailed.ilike(pattern),
                NormalizedItem.why_it_matters.ilike(pattern),
                cast(NormalizedItem.companies, String).ilike(pattern),
                cast(NormalizedItem.topics, String).ilike(pattern),
            ]
        )

    return (
        db.query(NormalizedItem, UserItemAction)
        .outerjoin(
            UserItemAction,
            (UserItemAction.item_id == NormalizedItem.id)
            & (UserItemAction.user_id == LOCAL_USER_ID),
        )
        .filter((UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None)))
        .filter(or_(*conditions))
        .order_by(
            UserItemAction.is_important.desc().nullslast(),
            NormalizedItem.stock_impact_score.desc(),
            NormalizedItem.importance_score.desc(),
            NormalizedItem.relevance_score.desc(),
            NormalizedItem.published_at.desc().nullslast(),
            NormalizedItem.created_at.desc(),
        )
    )


def build_stock_match_terms(stock: StockWatchlistItem | StockWatchlistSchema) -> list[str]:
    terms = [*build_stock_symbol_terms(stock), *build_stock_text_terms(stock)]
    return unique_normalized_terms(terms)


def build_stock_symbol_terms(stock: StockWatchlistItem | StockWatchlistSchema) -> list[str]:
    terms = [stock.ticker, *stock.related_companies]
    return [term.upper() for term in unique_normalized_terms(terms)]


def build_stock_text_terms(stock: StockWatchlistItem | StockWatchlistSchema) -> list[str]:
    alias_terms = []
    for ticker in [stock.ticker, *stock.related_companies]:
        alias_terms.extend(TICKER_ALIASES.get(ticker.upper(), []))

    terms = [
        stock.company_name,
        *alias_terms,
        *stock.related_keywords,
        *stock.related_ai_themes,
    ]
    return unique_normalized_terms(terms)


def unique_normalized_terms(values: list[str]) -> list[str]:
    seen: set[str] = set()
    terms: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        terms.append(normalized)
    return terms
