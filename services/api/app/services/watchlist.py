from collections import Counter

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from app.db.models import (
    NormalizedItem,
    ProductWatchlistItem,
    StockPricePoint,
    StockWatchlistItem,
    TopicWatchlistItem,
    UserItemAction,
)
from app.schemas.feed import FeedItem
from app.schemas.watchlist import (
    ProductWatchlistItemCreate,
    ProductWatchlistItemUpdate,
    StockBriefing,
    StockBriefingTimelineItem,
    StockMarketSnapshot,
    StockMarketImpactEvent,
    StockSignalSummary,
    StockThemeBreakdown,
    TopicActivityBucket,
    TopicBriefing,
    TopicSourceCount,
    StockWatchlistItemCreate,
    StockWatchlistItemUpdate,
    TopicWatchlistItemCreate,
    TopicWatchlistItemUpdate,
)
from app.schemas.watchlist import (
    StockPricePoint as StockPricePointSchema,
)
from app.schemas.watchlist import StockWatchlistItem as StockWatchlistSchema
from app.schemas.watchlist import (
    TopicWatchlistItem as TopicWatchlistSchema,
)
from app.services.feed_actions import LOCAL_USER_ID, serialize_feed_item
from app.services.scoring import TICKER_ALIASES
from app.services.seed_data import (
    initial_product_watchlist,
    initial_stock_watchlist,
    initial_topic_watchlist,
)

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


def seed_initial_product_watchlist(db: Session) -> list[ProductWatchlistItem]:
    existing = {item.category for item in db.query(ProductWatchlistItem).all()}
    created: list[ProductWatchlistItem] = []

    for seed_item in initial_product_watchlist():
        if seed_item.category in existing:
            continue
        item = ProductWatchlistItem(**seed_item.model_dump(), user_id="local")
        db.add(item)
        created.append(item)

    db.commit()

    return list_product_watchlist(db)


def list_product_watchlist(db: Session) -> list[ProductWatchlistItem]:
    return (
        db.query(ProductWatchlistItem)
        .order_by(
            ProductWatchlistItem.is_pinned.desc(),
            ProductWatchlistItem.priority.asc(),
            ProductWatchlistItem.label.asc(),
        )
        .all()
    )


def create_product_watchlist_item(
    db: Session,
    payload: ProductWatchlistItemCreate,
) -> ProductWatchlistItem:
    category = normalize_product_category(payload.category)
    if not category:
        raise ValueError("Product category is required.")
    if get_product_watchlist_item(db, category):
        raise ValueError(f"{category} is already in the product watchlist.")
    label = payload.label.strip() if payload.label else payload.category.strip()
    if not label:
        raise ValueError("Product category label is required.")
    item = ProductWatchlistItem(
        user_id=LOCAL_USER_ID,
        category=category,
        label=label,
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


def update_product_watchlist_item(
    db: Session,
    category: str,
    payload: ProductWatchlistItemUpdate,
) -> ProductWatchlistItem | None:
    item = get_product_watchlist_item(db, category)
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


def delete_product_watchlist_item(db: Session, category: str) -> bool:
    item = get_product_watchlist_item(db, category)
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True


def get_product_watchlist_item(db: Session, category: str) -> ProductWatchlistItem | None:
    return (
        db.query(ProductWatchlistItem)
        .filter(
            ProductWatchlistItem.user_id == LOCAL_USER_ID,
            ProductWatchlistItem.category == normalize_product_category(category),
        )
        .one_or_none()
    )


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


def get_topic_briefing(
    db: Session,
    topic: str,
    limit: int = 20,
) -> TopicBriefing | None:
    watch_topic = get_topic_watchlist_item(db, topic)
    if watch_topic is None:
        normalized_topic = normalize_topic(topic)
        watch_topic = next(
            (item for item in initial_topic_watchlist() if item.topic == normalized_topic),
            None,
        )
    if watch_topic is None:
        return None

    rows = query_topic_rows(db=db, topic=watch_topic, limit=limit)
    items = [serialize_feed_item(item, action) for item, action in rows]
    topic_schema = (
        watch_topic
        if isinstance(watch_topic, TopicWatchlistSchema)
        else TopicWatchlistSchema.model_validate(watch_topic)
    )
    return build_topic_briefing(topic=topic_schema, items=items)


def build_topic_briefing(
    topic: TopicWatchlistSchema,
    items: list[FeedItem],
) -> TopicBriefing:
    source_counts = Counter(item.source_name for item in items)
    company_counts: Counter[str] = Counter()
    activity_counts: Counter = Counter()

    for item in items:
        for value in [*item.companies, *item.tickers]:
            normalized = value.strip()
            if normalized:
                company_counts[normalized] += 1
        if item.published_at:
            activity_counts[item.published_at.date()] += 1

    return TopicBriefing(
        topic=topic,
        item_count=len(items),
        trending_sources=[
            TopicSourceCount(source_name=source_name, item_count=count)
            for source_name, count in source_counts.most_common(8)
        ],
        related_papers=[item for item in items if item.category == "research"][:6],
        related_products=[
            item for item in items if item.category == "product" or item.products
        ][:6],
        related_companies=[
            company for company, _count in company_counts.most_common(10)
        ],
        recent_timeline=items[:12],
        activity_timeline=[
            TopicActivityBucket(activity_date=activity_date, item_count=count)
            for activity_date, count in sorted(activity_counts.items(), reverse=True)[:14]
        ],
    )

def query_topic_rows(
    db: Session,
    topic: TopicWatchlistItem | TopicWatchlistSchema,
    limit: int,
) -> list[tuple[NormalizedItem, UserItemAction | None]]:
    return topic_signal_query(db=db, topic=topic).limit(limit).all()


def topic_signal_query(db: Session, topic: TopicWatchlistItem | TopicWatchlistSchema):
    conditions = []
    for term in build_topic_match_terms(topic):
        pattern = f"%{term}%"
        topic_pattern = f'%"{term}"%'
        conditions.extend(
            [
                cast(NormalizedItem.topics, String).ilike(topic_pattern),
                cast(NormalizedItem.products, String).ilike(pattern),
                cast(NormalizedItem.companies, String).ilike(pattern),
                NormalizedItem.title.ilike(pattern),
                NormalizedItem.text.ilike(pattern),
                NormalizedItem.summary_short.ilike(pattern),
                NormalizedItem.summary_detailed.ilike(pattern),
                NormalizedItem.why_it_matters.ilike(pattern),
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
            NormalizedItem.importance_score.desc(),
            NormalizedItem.relevance_score.desc(),
            NormalizedItem.published_at.desc().nullslast(),
            NormalizedItem.created_at.desc(),
        )
    )


def build_topic_match_terms(topic: TopicWatchlistItem | TopicWatchlistSchema) -> list[str]:
    label_words = topic.label.replace("-", " ")
    slug_words = topic.topic.replace("-", " ")
    return unique_normalized_terms([topic.topic, label_words, slug_words, *topic.related_terms])


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
    latest_signal = top_signals[0] if top_signals else None
    stock_schema = stock if isinstance(stock, StockWatchlistSchema) else (
        StockWatchlistSchema.model_validate(stock)
    )
    return StockSignalSummary(
        stock=stock_schema,
        signal_count=signal_count,
        high_impact_count=count_high_impact_stock_signal_rows(db, stock=stock),
        attention_score=compute_stock_attention_score(
            stock=stock_schema,
            top_signals=top_signals,
            signal_count=signal_count,
        ),
        market=build_stock_market_snapshot(db=db, ticker=stock_schema.ticker),
        latest_event_title=latest_signal.title if latest_signal else None,
        latest_event_at=latest_signal.published_at if latest_signal else None,
        sentiment_counts=build_sentiment_counts(top_signals),
        top_signals=top_signals,
        disclaimer=NON_FINANCIAL_ADVICE_DISCLAIMER,
    )


def build_stock_briefing(summary: StockSignalSummary) -> StockBriefing:
    latest_signal_at = max(
        (item.published_at for item in summary.top_signals if item.published_at is not None),
        default=None,
    )
    return StockBriefing(
        stock=summary.stock,
        signal_count=summary.signal_count,
        attention_score=summary.attention_score,
        market=summary.market,
        urgency=classify_stock_urgency(summary),
        latest_signal_at=latest_signal_at,
        sentiment_counts=summary.sentiment_counts,
        key_themes=build_stock_briefing_themes(summary.top_signals),
        ai_relevance_summary=build_stock_ai_relevance_summary(summary),
        theme_breakdown=build_stock_theme_breakdown(summary),
        market_impact_events=build_stock_market_impact_events(summary.top_signals),
        recent_timeline=[
            StockBriefingTimelineItem(
                item=item,
                signal_score=compute_stock_signal_score(item),
                reason=build_stock_signal_reason(item),
                event_type=infer_stock_event_type(item),
                possible_market_impact=infer_possible_market_impact(item),
                confidence=compute_stock_event_confidence(item),
                time_sensitivity=infer_stock_event_time_sensitivity(item),
                event_summary=build_stock_event_summary(item),
                uncertainties=build_stock_event_uncertainties(item),
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


def build_stock_ai_relevance_summary(summary: StockSignalSummary) -> str:
    stock = summary.stock
    themes = stock.related_ai_themes[:4] or build_stock_briefing_themes(summary.top_signals, limit=4)
    theme_text = ", ".join(themes) if themes else "AI-related company and technology signals"
    signal_text = (
        f"{summary.signal_count} recent AI-linked item"
        f"{'' if summary.signal_count == 1 else 's'}"
    )
    high_impact_text = (
        f"{summary.high_impact_count} high-impact signal"
        f"{'' if summary.high_impact_count == 1 else 's'}"
    )
    latest_text = (
        f" Latest event: {summary.latest_event_title}."
        if summary.latest_event_title
        else " No recent event headline is available yet."
    )
    return (
        f"{stock.company_name} ({stock.ticker}) is watched for {theme_text}. "
        f"SignalLens found {signal_text}, including {high_impact_text}.{latest_text} "
        "Review the linked sources and uncertainties before drawing conclusions."
    )


def build_stock_theme_breakdown(
    summary: StockSignalSummary,
    limit: int = 8,
) -> list[StockThemeBreakdown]:
    counts: Counter[str] = Counter()
    display_terms: dict[str, str] = {}

    for theme in summary.stock.related_ai_themes:
        normalized = theme.strip().lower()
        if normalized:
            counts[normalized] += 0
            display_terms.setdefault(normalized, theme.strip())

    for item in summary.top_signals:
        for term in [*item.topics, *item.products, *item.companies]:
            normalized = term.strip().lower()
            if not normalized:
                continue
            counts[normalized] += 1
            display_terms.setdefault(normalized, term.strip())

    ranked_terms = sorted(counts.items(), key=lambda row: (-row[1], row[0]))
    return [
        StockThemeBreakdown(theme=display_terms[key], item_count=count)
        for key, count in ranked_terms[:limit]
        if count > 0
    ]


def build_stock_market_impact_events(
    items: list[FeedItem],
    limit: int = 8,
) -> list[StockMarketImpactEvent]:
    counts: Counter[str] = Counter()
    latest_by_type: dict[str, FeedItem] = {}

    for item in items:
        event_type = infer_stock_event_type(item)
        counts[event_type] += 1
        current_latest = latest_by_type.get(event_type)
        if current_latest is None or compare_feed_item_recency(item, current_latest) > 0:
            latest_by_type[event_type] = item

    ranked_events = sorted(counts.items(), key=lambda row: (-row[1], row[0]))
    return [
        StockMarketImpactEvent(
            event_type=event_type,
            item_count=count,
            latest_title=latest_by_type[event_type].title,
            latest_at=latest_by_type[event_type].published_at,
        )
        for event_type, count in ranked_events[:limit]
    ]


def infer_stock_event_type(item: FeedItem) -> str:
    text = " ".join(
        part
        for part in [
            item.title,
            item.summary_short or "",
            item.why_it_matters or "",
            " ".join(item.topics),
        ]
        if part
    ).lower()
    if any(term in text for term in ["earnings", "guidance", "revenue", "margin"]):
        return "earnings_guidance"
    if any(term in text for term in ["analyst", "rating", "upgrade", "downgrade", "price target"]):
        return "analyst_action"
    if any(term in text for term in ["partnership", "customer win", "customer", "contract"]):
        return "partnership_customer"
    if any(term in text for term in ["supply chain", "supplier", "export", "regulation"]):
        return "supply_chain_regulation"
    if any(term in text for term in ["launch", "product", "release"]):
        return "product_launch"
    if any(
        term in text
        for term in [
            "demand",
            "capex",
            "data center",
            "hbm",
            "custom silicon",
            "storage",
            "nand",
        ]
    ):
        return "demand_signal"
    return "stock_signal"


def infer_possible_market_impact(item: FeedItem) -> str:
    if item.sentiment == "positive" and item.stock_impact_score >= 0.45:
        return "positive"
    if item.sentiment == "negative" and item.stock_impact_score >= 0.45:
        return "negative"
    if item.sentiment == "mixed" or item.stock_impact_score >= 0.35:
        return "mixed"
    return "uncertain"


def compute_stock_event_confidence(item: FeedItem) -> float:
    return round(
        min(
            1,
            max(
                item.classification_confidence,
                item.relevance_score * 0.7,
                item.stock_impact_score * 0.85,
            ),
        ),
        3,
    )


def infer_stock_event_time_sensitivity(item: FeedItem) -> str:
    event_type = infer_stock_event_type(item)
    if event_type in {"earnings_guidance", "analyst_action", "supply_chain_regulation"}:
        return "high"
    if item.stock_impact_score >= 0.75 or item.importance_score >= 0.8:
        return "high"
    if item.stock_impact_score >= 0.45 or item.importance_score >= 0.6:
        return "medium"
    return "low"


def build_stock_event_summary(item: FeedItem) -> str:
    return (
        item.summary_short
        or item.why_it_matters
        or f"{item.title} may be relevant to watched AI stock themes."
    )


def build_stock_event_uncertainties(item: FeedItem) -> list[str]:
    uncertainties: list[str] = []
    if item.stock_impact_score < 0.75:
        uncertainties.append("Stock impact is inferred from source text and may be indirect.")
    if not item.tickers:
        uncertainties.append("No explicit watched ticker was extracted from the item.")
    if item.sentiment in {"neutral", "mixed"}:
        uncertainties.append("Market direction is not clear from the available signal.")
    if not uncertainties:
        uncertainties.append("Review the original source before drawing market conclusions.")
    return uncertainties[:3]


def compare_feed_item_recency(left: FeedItem, right: FeedItem) -> int:
    if left.published_at and right.published_at:
        return (left.published_at > right.published_at) - (left.published_at < right.published_at)
    if left.published_at and not right.published_at:
        return 1
    if right.published_at and not left.published_at:
        return -1
    return left.id - right.id


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


def count_high_impact_stock_signal_rows(
    db: Session,
    stock: StockWatchlistItem | StockWatchlistSchema,
) -> int:
    return (
        stock_signal_query(db, stock=stock)
        .filter(
            or_(
                NormalizedItem.stock_impact_score >= 0.75,
                NormalizedItem.importance_score >= 0.75,
            )
        )
        .count()
    )


def build_sentiment_counts(items: list[FeedItem]) -> dict[str, int]:
    return dict(Counter(item.sentiment or "neutral" for item in items))


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


def normalize_product_category(value: str) -> str:
    return "-".join(value.strip().lower().split())


def clean_terms(values: list[str]) -> list[str]:
    return unique_normalized_terms(values)
