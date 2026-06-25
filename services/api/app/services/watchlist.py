from collections import Counter

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from app.db.models import (
    NormalizedItem,
    StockPricePoint,
    StockWatchlistItem,
    TopicWatchlistItem,
    UserItemAction,
)
from app.schemas.feed import FeedItem
from app.schemas.watchlist import (
    StockBriefing,
    StockBriefingTimelineItem,
    StockMarketSnapshot,
    StockSignalSummary,
    StockWatchlistItemCreate,
    StockWatchlistItemUpdate,
    TopicWatchlistItemCreate,
    TopicWatchlistItemUpdate,
)
from app.schemas.watchlist import (
    StockPricePoint as StockPricePointSchema,
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


def create_stock_watchlist_item(
    db: Session,
    payload: StockWatchlistItemCreate,
) -> StockWatchlistItem:
    ticker = normalize_ticker(payload.ticker)
    if not ticker:
        raise ValueError("Stock ticker is required.")
    if not payload.company_name.strip():
        raise ValueError("Company name is required.")
    existing = get_stock_watchlist_item(db, ticker)
    if existing:
        raise ValueError(f"{ticker} is already in the stock watchlist.")

    item = StockWatchlistItem(
        user_id=LOCAL_USER_ID,
        ticker=ticker,
        company_name=payload.company_name.strip(),
        exchange=payload.exchange.strip().upper(),
        sector=payload.sector.strip(),
        industry=payload.industry.strip(),
        priority=payload.priority.strip() or "Medium",
        group_name=payload.group_name.strip() or "Watch Only",
        is_pinned=payload.is_pinned,
        is_holding=payload.is_holding,
        shares=payload.shares,
        average_cost=payload.average_cost,
        related_keywords=clean_terms(payload.related_keywords),
        related_companies=[
            normalize_ticker(value)
            for value in clean_terms(payload.related_companies)
        ],
        related_ai_themes=clean_terms(payload.related_ai_themes),
        notes=payload.notes.strip() if payload.notes else None,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_stock_watchlist_item(
    db: Session,
    ticker: str,
    payload: StockWatchlistItemUpdate,
) -> StockWatchlistItem | None:
    item = get_stock_watchlist_item(db, ticker)
    if item is None:
        return None

    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        if field_name in {"related_keywords", "related_ai_themes"} and value is not None:
            value = clean_terms(value)
        elif field_name == "related_companies" and value is not None:
            value = [normalize_ticker(term) for term in clean_terms(value)]
        elif isinstance(value, str):
            value = value.strip()
        setattr(item, field_name, value)

    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_stock_watchlist_item(db: Session, ticker: str) -> bool:
    item = get_stock_watchlist_item(db, ticker)
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True


def get_stock_watchlist_item(db: Session, ticker: str) -> StockWatchlistItem | None:
    return (
        db.query(StockWatchlistItem)
        .filter(
            StockWatchlistItem.user_id == LOCAL_USER_ID,
            StockWatchlistItem.ticker == normalize_ticker(ticker),
        )
        .one_or_none()
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
    topic = normalize_topic(payload.topic)
    if not topic:
        raise ValueError("Topic is required.")
    if get_topic_watchlist_item(db, topic):
        raise ValueError(f"{topic} is already in the topic watchlist.")
    label = payload.label.strip() if payload.label else payload.topic.strip()
    if not label:
        raise ValueError("Topic label is required.")
    item = TopicWatchlistItem(
        user_id=LOCAL_USER_ID,
        topic=topic,
        label=label,
        category=payload.category.strip() or "technical_trend",
        priority=payload.priority.strip() or "Medium",
        is_pinned=payload.is_pinned,
        include_in_digest=payload.include_in_digest,
        related_terms=clean_terms(payload.related_terms),
        notes=payload.notes.strip() if payload.notes else None,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_topic_watchlist_item(
    db: Session,
    topic: str,
    payload: TopicWatchlistItemUpdate,
) -> TopicWatchlistItem | None:
    item = get_topic_watchlist_item(db, topic)
    if item is None:
        return None

    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        if field_name == "related_terms" and value is not None:
            value = clean_terms(value)
        elif isinstance(value, str):
            value = value.strip()
        setattr(item, field_name, value)

    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_topic_watchlist_item(db: Session, topic: str) -> bool:
    item = get_topic_watchlist_item(db, topic)
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True


def get_topic_watchlist_item(db: Session, topic: str) -> TopicWatchlistItem | None:
    return (
        db.query(TopicWatchlistItem)
        .filter(
            TopicWatchlistItem.user_id == LOCAL_USER_ID,
            TopicWatchlistItem.topic == normalize_topic(topic),
        )
        .one_or_none()
    )


def summarize_stock_signals(
    db: Session,
    limit_per_stock: int = 3,
) -> list[StockSignalSummary]:
    stocks = list_stock_watchlist(db)
    if not stocks:
        summaries = [
            build_stock_signal_summary(db, stock, limit=limit_per_stock)
            for stock in initial_stock_watchlist()
        ]
    else:
        summaries = [
            build_stock_signal_summary(db, stock, limit=limit_per_stock) for stock in stocks
        ]
    return sorted(summaries, key=lambda summary: summary.attention_score, reverse=True)


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


def get_stock_briefing(
    db: Session,
    ticker: str,
    limit: int = 10,
) -> StockBriefing | None:
    summary = get_stock_signals(db, ticker=ticker, limit=limit)
    if summary is None:
        return None
    return build_stock_briefing(summary)


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
        attention_score=compute_stock_attention_score(
            stock=stock_schema,
            top_signals=top_signals,
            signal_count=signal_count,
        ),
        market=build_stock_market_snapshot(db=db, ticker=stock_schema.ticker),
        top_signals=top_signals,
        disclaimer=NON_FINANCIAL_ADVICE_DISCLAIMER,
    )


def build_stock_briefing(summary: StockSignalSummary) -> StockBriefing:
    latest_signal_at = max(
        (item.published_at for item in summary.top_signals if item.published_at is not None),
        default=None,
    )
    sentiment_counts = Counter(item.sentiment or "neutral" for item in summary.top_signals)
    return StockBriefing(
        stock=summary.stock,
        signal_count=summary.signal_count,
        attention_score=summary.attention_score,
        market=summary.market,
        urgency=classify_stock_urgency(summary),
        latest_signal_at=latest_signal_at,
        sentiment_counts=dict(sentiment_counts),
        key_themes=build_stock_briefing_themes(summary.top_signals),
        recent_timeline=[
            StockBriefingTimelineItem(
                item=item,
                signal_score=compute_stock_signal_score(item),
                reason=build_stock_signal_reason(item),
            )
            for item in summary.top_signals
        ],
        disclaimer=summary.disclaimer,
    )


def build_stock_market_snapshot(
    db: Session,
    ticker: str,
    limit: int = 30,
) -> StockMarketSnapshot | None:
    rows = (
        db.query(StockPricePoint)
        .filter(StockPricePoint.ticker == normalize_ticker(ticker))
        .order_by(StockPricePoint.price_date.desc())
        .limit(limit)
        .all()
    )
    if not rows:
        return None

    history = [StockPricePointSchema.model_validate(row) for row in reversed(rows)]
    latest = StockPricePointSchema.model_validate(rows[0])
    previous = rows[1] if len(rows) > 1 else None
    change = latest.close_price - previous.close_price if previous else None
    change_percent = (
        round((change / previous.close_price) * 100, 2)
        if previous and previous.close_price
        else None
    )
    return StockMarketSnapshot(
        latest=latest,
        previous_close=previous.close_price if previous else None,
        change=round(change, 4) if change is not None else None,
        change_percent=change_percent,
        history=history,
    )


def classify_stock_urgency(summary: StockSignalSummary) -> str:
    if not summary.top_signals:
        return "low"
    top_score = max(compute_stock_signal_score(item) for item in summary.top_signals)
    if top_score >= 0.75:
        return "high"
    if top_score >= 0.45 or summary.signal_count >= 3:
        return "medium"
    return "low"


def compute_stock_signal_score(item: FeedItem) -> float:
    return round(
        max(
            item.stock_impact_score,
            item.importance_score * 0.85,
            item.relevance_score * 0.65,
        ),
        3,
    )


def compute_stock_attention_score(
    stock: StockWatchlistSchema,
    top_signals: list[FeedItem],
    signal_count: int,
) -> float:
    strongest_signal = max(
        (compute_stock_signal_score(item) for item in top_signals),
        default=0,
    )
    signal_volume = min(signal_count / 10, 1)
    priority = priority_score(stock.priority)
    pinned_bonus = 1 if stock.is_pinned else 0
    return round(
        min(
            1,
            0.55 * strongest_signal
            + 0.25 * signal_volume
            + 0.15 * priority
            + 0.05 * pinned_bonus,
        ),
        3,
    )


def priority_score(value: str) -> float:
    normalized = value.strip().lower()
    if normalized == "high":
        return 1
    if normalized == "medium":
        return 0.6
    if normalized == "low":
        return 0.25
    return 0.4


def build_stock_briefing_themes(items: list[FeedItem], limit: int = 8) -> list[str]:
    counts: Counter[str] = Counter()
    display_terms: dict[str, str] = {}
    for item in items:
        for term in [*item.topics, *item.products, *item.companies]:
            normalized = term.strip().lower()
            if not normalized:
                continue
            counts[normalized] += 1
            display_terms.setdefault(normalized, term.strip())

    ranked_terms = sorted(counts.items(), key=lambda row: (-row[1], row[0]))
    return [display_terms[key] for key, _count in ranked_terms[:limit]]


def build_stock_signal_reason(item: FeedItem) -> str:
    if item.why_it_matters:
        return item.why_it_matters
    if item.summary_short:
        return item.summary_short
    if item.stock_impact_score >= 0.75:
        return "High stock-impact score from an AI-related source item."
    if item.importance_score >= 0.75:
        return "High importance score from an AI-related source item."
    return "Matched the ticker, company, related companies, keywords, or AI themes."


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


def normalize_ticker(value: str) -> str:
    return value.strip().upper().removeprefix("$")


def normalize_topic(value: str) -> str:
    return "-".join(value.strip().lower().split())


def clean_terms(values: list[str]) -> list[str]:
    return unique_normalized_terms(values)
