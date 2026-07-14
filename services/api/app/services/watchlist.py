import re
from collections import Counter
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import String, case, cast, func, or_
from sqlalchemy.orm import Session

from app.db.models import (
    CompanyWatchlistItem,
    NormalizedItem,
    ProductWatchlistItem,
    StockPricePoint,
    StockWatchlistItem,
    TopicWatchlistItem,
    UserItemAction,
)
from app.schemas.feed import FeedItem
from app.schemas.watchlist import (
    CompanyBriefing,
    CompanyWatchlistItemCreate,
    CompanyWatchlistItemUpdate,
    ProductBriefing,
    ProductWatchlistItemCreate,
    ProductWatchlistItemUpdate,
    StockBriefing,
    StockBriefingTimelineItem,
    StockMarketImpactEvent,
    StockMarketSnapshot,
    StockSignalSummary,
    StockThemeBreakdown,
    StockWatchlistItemCreate,
    StockWatchlistItemUpdate,
    TopicActivityBucket,
    TopicBriefing,
    TopicSourceCount,
    TopicWatchlistItemCreate,
    TopicWatchlistItemUpdate,
)
from app.schemas.watchlist import CompanyWatchlistItem as CompanyWatchlistSchema
from app.schemas.watchlist import ProductWatchlistItem as ProductWatchlistSchema
from app.schemas.watchlist import (
    StockPricePoint as StockPricePointSchema,
)
from app.schemas.watchlist import StockWatchlistItem as StockWatchlistSchema
from app.schemas.watchlist import (
    TopicWatchlistItem as TopicWatchlistSchema,
)
from app.services.feed_actions import LOCAL_USER_ID, normalize_source_names, serialize_feed_item
from app.services.scoring import TICKER_ALIASES, TICKER_COMPANY_NAMES, infer_product_use_case
from app.services.seed_data import (
    initial_company_watchlist,
    initial_product_watchlist,
    initial_stock_watchlist,
    initial_topic_watchlist,
)

HIGH_IMPACT_SIGNAL_THRESHOLD = 0.75
DEFAULT_STOCK_EXCHANGE = "NASDAQ"
DEFAULT_STOCK_SECTOR = "Technology"
DEFAULT_STOCK_INDUSTRY = "Technology"
DEFAULT_STOCK_PRIORITY = "Medium"
DEFAULT_STOCK_GROUP = "Watch Only"

NON_FINANCIAL_ADVICE_DISCLAIMER = (
    "SignalLens links AI-related items to watched stocks for research only and does not "
    "provide investment advice."
)


def apply_blocked_source_filter(query, blocked_sources: list[str] | None):
    blocked_source_names = normalize_source_names(blocked_sources)
    if not blocked_source_names:
        return query
    return query.filter(~NormalizedItem.source_name.in_(blocked_source_names))


def list_stock_watchlist(db: Session) -> list[StockWatchlistItem]:
    return (
        db.query(StockWatchlistItem)
        .order_by(
            StockWatchlistItem.is_pinned.desc(),
            StockWatchlistItem.display_order.asc(),
            stock_priority_sort_expression(),
            StockWatchlistItem.ticker.asc(),
        )
        .all()
    )


def resolve_stock_watchlist_create_payload(
    payload: StockWatchlistItemCreate,
) -> dict[str, object]:
    raw_ticker = (payload.ticker or "").strip()
    company_name = (payload.company_name or "").strip()
    ticker_candidate = normalize_ticker(raw_ticker) if looks_like_ticker(raw_ticker) else ""
    seed = find_stock_seed([ticker_candidate, raw_ticker, company_name])
    alias_ticker = resolve_stock_alias([company_name, raw_ticker])
    known_tickers = set(TICKER_COMPANY_NAMES) | {
        stock.ticker for stock in initial_stock_watchlist()
    }

    if seed:
        ticker = seed.ticker
    elif ticker_candidate in known_tickers:
        ticker = ticker_candidate
    elif alias_ticker:
        ticker = alias_ticker
    else:
        ticker = ticker_candidate

    if not seed and ticker:
        seed = find_stock_seed([ticker])

    resolved_company = (
        company_name
        or (seed.company_name if seed else "")
        or TICKER_COMPANY_NAMES.get(ticker, "")
        or ticker
    )

    return {
        "ticker": ticker,
        "company_name": resolved_company,
        "exchange": resolve_stock_text_field(
            payload,
            "exchange",
            DEFAULT_STOCK_EXCHANGE,
            seed.exchange if seed else None,
        ).upper(),
        "sector": resolve_stock_text_field(
            payload,
            "sector",
            DEFAULT_STOCK_SECTOR,
            seed.sector if seed else None,
        ),
        "industry": resolve_stock_text_field(
            payload,
            "industry",
            DEFAULT_STOCK_INDUSTRY,
            seed.industry if seed else None,
        ),
        "priority": resolve_stock_text_field(
            payload,
            "priority",
            DEFAULT_STOCK_PRIORITY,
            seed.priority if seed else None,
        ),
        "group_name": resolve_stock_text_field(
            payload,
            "group_name",
            DEFAULT_STOCK_GROUP,
            seed.group_name if seed else None,
        ),
        "is_pinned": (
            payload.is_pinned
            if "is_pinned" in payload.model_fields_set
            else seed.is_pinned
            if seed
            else payload.is_pinned
        ),
        "related_keywords": resolve_stock_terms(
            payload.related_keywords,
            seed.related_keywords if seed else [],
        ),
        "related_companies": [
            normalize_ticker(value)
            for value in resolve_stock_terms(
                payload.related_companies,
                seed.related_companies if seed else [],
            )
        ],
        "related_ai_themes": resolve_stock_terms(
            payload.related_ai_themes,
            seed.related_ai_themes if seed else [],
        ),
    }


def find_stock_seed(search_terms: list[str]) -> StockWatchlistSchema | None:
    normalized_terms = {
        normalize_lookup_text(term)
        for term in search_terms
        if term and normalize_lookup_text(term)
    }
    ticker_terms = {
        normalize_ticker(term)
        for term in search_terms
        if term and looks_like_ticker(term)
    }
    for stock in initial_stock_watchlist():
        if stock.ticker in ticker_terms:
            return stock
        if normalize_lookup_text(stock.company_name) in normalized_terms:
            return stock
        aliases = TICKER_ALIASES.get(stock.ticker, [])
        if any(normalize_lookup_text(alias) in normalized_terms for alias in aliases):
            return stock
    return None


def resolve_stock_alias(search_terms: list[str]) -> str:
    normalized_terms = {
        normalize_lookup_text(term)
        for term in search_terms
        if term and normalize_lookup_text(term)
    }
    for ticker, aliases in TICKER_ALIASES.items():
        ticker_name = TICKER_COMPANY_NAMES.get(ticker, "")
        lookup_values = [ticker_name, *aliases]
        if any(normalize_lookup_text(value) in normalized_terms for value in lookup_values):
            return ticker
    return ""


def resolve_stock_text_field(
    payload: StockWatchlistItemCreate,
    field_name: str,
    fallback: str,
    seed_value: str | None,
) -> str:
    raw_value = getattr(payload, field_name)
    value = raw_value.strip() if raw_value else ""
    if field_name in payload.model_fields_set and value:
        return value
    return seed_value or value or fallback


def resolve_stock_terms(payload_terms: list[str], seed_terms: list[str]) -> list[str]:
    return clean_terms([*seed_terms, *payload_terms])


def looks_like_ticker(value: str) -> bool:
    return bool(re.fullmatch(r"\$?[A-Za-z][A-Za-z0-9.-]{0,14}", value.strip()))


def normalize_lookup_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.strip().lower()).strip()


def create_stock_watchlist_item(
    db: Session,
    payload: StockWatchlistItemCreate,
) -> StockWatchlistItem:
    resolved = resolve_stock_watchlist_create_payload(payload)
    ticker = resolved["ticker"]
    if not ticker:
        raise ValueError("Stock ticker or known company name is required.")
    existing = get_stock_watchlist_item(db, ticker)
    if existing:
        raise ValueError(f"{ticker} is already in the stock watchlist.")

    item = StockWatchlistItem(
        user_id=LOCAL_USER_ID,
        ticker=ticker,
        company_name=resolved["company_name"],
        exchange=resolved["exchange"],
        sector=resolved["sector"],
        industry=resolved["industry"],
        priority=resolved["priority"],
        group_name=resolved["group_name"],
        display_order=(
            payload.display_order
            if payload.display_order is not None
            else next_stock_display_order(db)
        ),
        is_pinned=resolved["is_pinned"],
        is_holding=payload.is_holding,
        shares=payload.shares,
        average_cost=payload.average_cost,
        related_keywords=resolved["related_keywords"],
        related_companies=resolved["related_companies"],
        related_ai_themes=resolved["related_ai_themes"],
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
        if field_name == "display_order" and value is None:
            continue
        if field_name in {"related_keywords", "related_ai_themes"} and value is not None:
            value = clean_terms(value)
        elif field_name == "related_companies" and value is not None:
            value = [normalize_ticker(term) for term in clean_terms(value)]
        elif field_name in {
            "company_name",
            "exchange",
            "sector",
            "industry",
            "priority",
            "group_name",
        } and isinstance(value, str):
            normalized_text = value.strip()
            if not normalized_text:
                continue
            value = normalized_text
        elif field_name == "notes" and isinstance(value, str):
            value = value.strip() or None
        elif isinstance(value, str):
            value = value.strip()
        setattr(item, field_name, value)

    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def move_stock_watchlist_item(
    db: Session,
    ticker: str,
    direction: str,
) -> list[StockWatchlistItem] | None:
    item = get_stock_watchlist_item(db, ticker)
    if item is None:
        return None
    normalized_direction = direction.strip().lower()
    if normalized_direction not in {"up", "down"}:
        raise ValueError("Stock move direction must be up or down.")

    normalize_stock_display_orders(db=db, is_pinned=item.is_pinned)
    db.flush()
    db.refresh(item)
    peers = list_stock_watchlist_peers(db=db, is_pinned=item.is_pinned)
    index = next((idx for idx, peer in enumerate(peers) if peer.ticker == item.ticker), -1)
    neighbor_index = index + (-1 if normalized_direction == "up" else 1)
    if index < 0 or neighbor_index < 0 or neighbor_index >= len(peers):
        db.commit()
        return list_stock_watchlist(db)

    neighbor = peers[neighbor_index]
    item.display_order, neighbor.display_order = neighbor.display_order, item.display_order
    db.add_all([item, neighbor])
    db.commit()
    return list_stock_watchlist(db)


def list_stock_watchlist_peers(db: Session, is_pinned: bool) -> list[StockWatchlistItem]:
    return (
        db.query(StockWatchlistItem)
        .filter(
            StockWatchlistItem.user_id == LOCAL_USER_ID,
            StockWatchlistItem.is_pinned.is_(is_pinned),
        )
        .order_by(
            StockWatchlistItem.display_order.asc(),
            stock_priority_sort_expression(),
            StockWatchlistItem.ticker.asc(),
        )
        .all()
    )


def normalize_stock_display_orders(db: Session, is_pinned: bool) -> None:
    for index, item in enumerate(list_stock_watchlist_peers(db=db, is_pinned=is_pinned), start=1):
        item.display_order = index * 10
        db.add(item)


def next_stock_display_order(db: Session) -> int:
    current_max = (
        db.query(func.max(StockWatchlistItem.display_order))
        .filter(StockWatchlistItem.user_id == LOCAL_USER_ID)
        .scalar()
    )
    return int(current_max or 0) + 10


def stock_priority_sort_expression():
    return case(
        (StockWatchlistItem.priority == "High", 0),
        (StockWatchlistItem.priority == "Medium", 1),
        (StockWatchlistItem.priority == "Low", 2),
        else_=3,
    )


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


def seed_initial_company_watchlist(db: Session) -> list[CompanyWatchlistItem]:
    existing = {item.company_key for item in db.query(CompanyWatchlistItem).all()}

    for seed_item in initial_company_watchlist():
        if seed_item.company_key in existing:
            continue
        item = CompanyWatchlistItem(**seed_item.model_dump(), user_id="local")
        db.add(item)

    db.commit()

    return list_company_watchlist(db)


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


def list_company_watchlist(db: Session) -> list[CompanyWatchlistItem]:
    return (
        db.query(CompanyWatchlistItem)
        .order_by(
            CompanyWatchlistItem.is_pinned.desc(),
            CompanyWatchlistItem.priority.asc(),
            CompanyWatchlistItem.company_name.asc(),
        )
        .all()
    )


def create_company_watchlist_item(
    db: Session,
    payload: CompanyWatchlistItemCreate,
) -> CompanyWatchlistItem:
    company_name = payload.company_name.strip()
    if not company_name:
        raise ValueError("Company name is required.")
    company_key = normalize_company_key(payload.company_key or company_name)
    if not company_key:
        raise ValueError("Company key is required.")
    if get_company_watchlist_item(db, company_key):
        raise ValueError(f"{company_key} is already in the company watchlist.")
    item = CompanyWatchlistItem(
        user_id=LOCAL_USER_ID,
        company_key=company_key,
        company_name=company_name,
        ticker=normalize_optional_ticker(payload.ticker),
        category=payload.category.strip() or "ai_company",
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


def update_company_watchlist_item(
    db: Session,
    company_key: str,
    payload: CompanyWatchlistItemUpdate,
) -> CompanyWatchlistItem | None:
    item = get_company_watchlist_item(db, company_key)
    if item is None:
        return None

    updates = payload.model_dump(exclude_unset=True)
    for field_name, value in updates.items():
        if field_name == "related_terms" and value is not None:
            value = clean_terms(value)
        elif field_name == "ticker":
            value = normalize_optional_ticker(value)
        elif field_name in {"company_name", "category", "priority"} and isinstance(value, str):
            normalized_text = value.strip()
            if not normalized_text:
                continue
            value = normalized_text
        elif field_name == "notes" and isinstance(value, str):
            value = value.strip() or None
        elif isinstance(value, str):
            value = value.strip()
        setattr(item, field_name, value)

    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_company_watchlist_item(db: Session, company_key: str) -> bool:
    item = get_company_watchlist_item(db, company_key)
    if item is None:
        return False
    db.delete(item)
    db.commit()
    return True


def get_company_watchlist_item(db: Session, company_key: str) -> CompanyWatchlistItem | None:
    return (
        db.query(CompanyWatchlistItem)
        .filter(
            CompanyWatchlistItem.user_id == LOCAL_USER_ID,
            CompanyWatchlistItem.company_key == normalize_company_key(company_key),
        )
        .one_or_none()
    )


def get_company_briefing(
    db: Session,
    company_key: str,
    limit: int = 20,
    blocked_sources: list[str] | None = None,
) -> CompanyBriefing | None:
    watch_company = get_company_watchlist_item(db, company_key)
    if watch_company is None:
        normalized_key = normalize_company_key(company_key)
        watch_company = next(
            (item for item in initial_company_watchlist() if item.company_key == normalized_key),
            None,
        )
    if watch_company is None:
        return None

    rows = query_company_rows(
        db=db,
        company=watch_company,
        limit=limit,
        blocked_sources=blocked_sources,
    )
    items = [serialize_feed_item(item, action) for item, action in rows]
    company_schema = (
        watch_company
        if isinstance(watch_company, CompanyWatchlistSchema)
        else CompanyWatchlistSchema.model_validate(watch_company)
    )
    return build_company_briefing(company=company_schema, items=items)


def build_company_briefing(
    company: CompanyWatchlistSchema,
    items: list[FeedItem],
) -> CompanyBriefing:
    source_counts = Counter(item.source_name for item in items)
    topic_counts: Counter[str] = Counter()
    product_counts: Counter[str] = Counter()
    ticker_counts: Counter[str] = Counter()
    activity_counts: Counter = Counter()

    for item in items:
        for value in item.topics:
            normalized = value.strip()
            if normalized:
                topic_counts[normalized] += 1
        for value in item.products:
            normalized = value.strip()
            if normalized:
                product_counts[normalized] += 1
        for value in item.tickers:
            normalized = value.strip().upper()
            if normalized:
                ticker_counts[normalized] += 1
        if item.published_at:
            activity_counts[item.published_at.date()] += 1

    return CompanyBriefing(
        company=company,
        item_count=len(items),
        high_impact_count=count_high_impact_feed_items(items),
        average_importance_score=average_importance_score(items),
        trending_sources=[
            TopicSourceCount(source_name=source_name, item_count=count)
            for source_name, count in source_counts.most_common(8)
        ],
        related_topics=[topic for topic, _count in topic_counts.most_common(10)],
        related_products=[product for product, _count in product_counts.most_common(10)],
        related_tickers=[ticker for ticker, _count in ticker_counts.most_common(10)],
        recent_timeline=items[:12],
        activity_timeline=[
            TopicActivityBucket(activity_date=activity_date, item_count=count)
            for activity_date, count in sorted(activity_counts.items(), reverse=True)[:14]
        ],
    )


def query_company_rows(
    db: Session,
    company: CompanyWatchlistItem | CompanyWatchlistSchema,
    limit: int,
    blocked_sources: list[str] | None = None,
) -> list[tuple[NormalizedItem, UserItemAction | None]]:
    return (
        company_signal_query(db=db, company=company, blocked_sources=blocked_sources)
        .limit(limit)
        .all()
    )


def company_signal_query(
    db: Session,
    company: CompanyWatchlistItem | CompanyWatchlistSchema,
    blocked_sources: list[str] | None = None,
):
    conditions = []
    for term in build_company_match_terms(company):
        pattern = f"%{term}%"
        json_pattern = f'%"{term}"%'
        conditions.extend(
            [
                cast(NormalizedItem.companies, String).ilike(json_pattern),
                cast(NormalizedItem.companies, String).ilike(pattern),
                cast(NormalizedItem.tickers, String).ilike(json_pattern),
                cast(NormalizedItem.tickers, String).ilike(pattern),
                cast(NormalizedItem.products, String).ilike(pattern),
                cast(NormalizedItem.topics, String).ilike(pattern),
                NormalizedItem.title.ilike(pattern),
                NormalizedItem.text.ilike(pattern),
                NormalizedItem.summary_short.ilike(pattern),
                NormalizedItem.summary_detailed.ilike(pattern),
                NormalizedItem.why_it_matters.ilike(pattern),
            ]
        )

    query = (
        db.query(NormalizedItem, UserItemAction)
        .outerjoin(
            UserItemAction,
            (UserItemAction.item_id == NormalizedItem.id)
            & (UserItemAction.user_id == LOCAL_USER_ID),
        )
        .filter((UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None)))
        .filter(or_(*conditions))
    )
    return apply_blocked_source_filter(query, blocked_sources).order_by(
        UserItemAction.is_important.desc().nullslast(),
        NormalizedItem.importance_score.desc(),
        NormalizedItem.relevance_score.desc(),
        NormalizedItem.published_at.desc().nullslast(),
        NormalizedItem.created_at.desc(),
    )


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
        elif field_name in {"label", "priority"} and isinstance(value, str):
            normalized_text = value.strip()
            if not normalized_text:
                continue
            value = normalized_text
        elif field_name == "notes" and isinstance(value, str):
            value = value.strip() or None
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


def get_product_briefing(
    db: Session,
    category: str,
    limit: int = 20,
    blocked_sources: list[str] | None = None,
) -> ProductBriefing | None:
    watch_product = get_product_watchlist_item(db, category)
    if watch_product is None:
        normalized_category = normalize_product_category(category)
        watch_product = next(
            (item for item in initial_product_watchlist() if item.category == normalized_category),
            None,
        )
    if watch_product is None:
        return None

    rows = query_product_rows(
        db=db,
        product=watch_product,
        limit=limit,
        blocked_sources=blocked_sources,
    )
    items = [serialize_feed_item(item, action) for item, action in rows]
    product_schema = (
        watch_product
        if isinstance(watch_product, ProductWatchlistSchema)
        else ProductWatchlistSchema.model_validate(watch_product)
    )
    return build_product_briefing(product=product_schema, items=items)


def build_product_briefing(
    product: ProductWatchlistSchema,
    items: list[FeedItem],
) -> ProductBriefing:
    source_counts = Counter(item.source_name for item in items)
    use_case_counts = Counter(
        format_product_use_case_label(item.subcategory)
        for item in items
        if item.category == "product" and item.subcategory
    )
    product_counts: Counter[str] = Counter()
    company_counts: Counter[str] = Counter()
    activity_counts: Counter = Counter()

    for item in items:
        for value in item.products:
            normalized = value.strip()
            if normalized:
                product_counts[normalized] += 1
        for value in [*item.companies, *item.tickers]:
            normalized = value.strip()
            if normalized:
                company_counts[normalized] += 1
        if item.published_at:
            activity_counts[item.published_at.date()] += 1

    return ProductBriefing(
        product=product,
        item_count=len(items),
        high_impact_count=count_high_impact_feed_items(items),
        average_importance_score=average_importance_score(items),
        average_novelty_score=average_novelty_score(items),
        trending_sources=[
            TopicSourceCount(source_name=source_name, item_count=count)
            for source_name, count in source_counts.most_common(8)
        ],
        use_case_counts=[
            TopicSourceCount(source_name=use_case, item_count=count)
            for use_case, count in use_case_counts.most_common(8)
        ],
        matched_products=[
            product_name for product_name, _count in product_counts.most_common(10)
        ],
        related_companies=[
            company for company, _count in company_counts.most_common(10)
        ],
        traction_signals=build_product_traction_signals(items),
        recent_timeline=rank_product_discovery_items(items)[:12],
        activity_timeline=[
            TopicActivityBucket(activity_date=activity_date, item_count=count)
            for activity_date, count in sorted(activity_counts.items(), reverse=True)[:14]
        ],
    )


def format_product_use_case_label(subcategory: str | None) -> str:
    labels = {
        "product_coding": "Coding",
        "product_media": "Media",
        "product_search": "Search",
        "product_education": "Education",
        "product_business": "Business",
        "product_productivity": "Productivity",
        "product_entertainment": "Entertainment",
        "product_general": "General",
    }
    return labels.get(subcategory or "", (subcategory or "General").replace("_", " ").title())


def query_product_rows(
    db: Session,
    product: ProductWatchlistItem | ProductWatchlistSchema,
    limit: int,
    blocked_sources: list[str] | None = None,
) -> list[tuple[NormalizedItem, UserItemAction | None]]:
    return (
        product_signal_query(db=db, product=product, blocked_sources=blocked_sources)
        .limit(limit)
        .all()
    )


def product_signal_query(
    db: Session,
    product: ProductWatchlistItem | ProductWatchlistSchema,
    blocked_sources: list[str] | None = None,
):
    conditions = []
    use_case_terms = build_product_use_case_terms(product)
    if use_case_terms:
        conditions.append(NormalizedItem.subcategory.in_(use_case_terms))
    for term in build_product_match_terms(product):
        pattern = f"%{term}%"
        json_pattern = f'%"{term}"%'
        conditions.extend(
            [
                cast(NormalizedItem.products, String).ilike(json_pattern),
                cast(NormalizedItem.products, String).ilike(pattern),
                cast(NormalizedItem.topics, String).ilike(pattern),
                NormalizedItem.title.ilike(pattern),
                NormalizedItem.text.ilike(pattern),
                NormalizedItem.summary_short.ilike(pattern),
                NormalizedItem.summary_detailed.ilike(pattern),
                NormalizedItem.why_it_matters.ilike(pattern),
            ]
        )

    query = (
        db.query(NormalizedItem, UserItemAction)
        .outerjoin(
            UserItemAction,
            (UserItemAction.item_id == NormalizedItem.id)
            & (UserItemAction.user_id == LOCAL_USER_ID),
        )
        .filter((UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None)))
        .filter(or_(*conditions))
    )
    return apply_blocked_source_filter(query, blocked_sources).order_by(
        UserItemAction.is_important.desc().nullslast(),
        NormalizedItem.novelty_score.desc(),
        NormalizedItem.importance_score.desc(),
        NormalizedItem.relevance_score.desc(),
        NormalizedItem.published_at.desc().nullslast(),
        NormalizedItem.created_at.desc(),
    )


def build_product_match_terms(
    product: ProductWatchlistItem | ProductWatchlistSchema,
) -> list[str]:
    label_words = product.label.replace("-", " ")
    category_words = product.category.replace("-", " ")
    return unique_normalized_terms(
        [product.category, label_words, category_words, *product.related_terms]
    )


def build_product_use_case_terms(
    product: ProductWatchlistItem | ProductWatchlistSchema,
) -> list[str]:
    combined_text = " ".join(
        [product.category.replace("-", " "), product.label, *product.related_terms]
    )
    use_case = infer_product_use_case(combined_text)
    return [] if use_case == "product_general" else [use_case]


def rank_product_discovery_items(items: list[FeedItem]) -> list[FeedItem]:
    return sorted(
        items,
        key=lambda item: (
            product_discovery_score(item),
            item.published_at or datetime.min.replace(tzinfo=UTC),
            item.id,
        ),
        reverse=True,
    )


def product_discovery_score(item: FeedItem) -> float:
    return round(
        0.40 * item.novelty_score
        + 0.25 * item.importance_score
        + 0.20 * item.relevance_score
        + 0.15 * product_traction_score(item),
        3,
    )


def product_traction_score(item: FeedItem) -> float:
    total = 0.0
    text = product_signal_text(item)
    for match in re.finditer(
        r"(\d+(?:\.\d+)?)([kKmM]?)\s*"
        r"(?:[A-Za-z][A-Za-z-]*\s+){0,3}"
        r"(stars/day|stars|votes|upvotes|comments|forks|downloads|users)",
        text,
    ):
        value = float(match.group(1))
        suffix = match.group(2).lower()
        unit = match.group(3).lower()
        if suffix == "k":
            value *= 1_000
        elif suffix == "m":
            value *= 1_000_000
        weight = {
            "stars/day": 4.0,
            "stars": 1.0,
            "votes": 0.8,
            "upvotes": 0.8,
            "comments": 0.5,
            "forks": 0.7,
            "downloads": 0.6,
            "users": 0.7,
        }.get(unit, 0.0)
        total += value * weight
    return min(total / 1_200, 1.0)


def average_novelty_score(items: list[FeedItem]) -> float:
    if not items:
        return 0
    return sum(item.novelty_score for item in items) / len(items)


def build_product_traction_signals(items: list[FeedItem], limit: int = 6) -> list[str]:
    signals: list[str] = []
    seen: set[str] = set()
    for item in rank_product_discovery_items(items):
        signal = extract_product_traction_signal(item)
        if signal is None:
            continue
        dedupe_key = signal.lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        signals.append(signal)
        if len(signals) >= limit:
            break
    return signals


def extract_product_traction_signal(item: FeedItem) -> str | None:
    text = product_signal_text(item)
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("traction signal:"):
            signal = stripped.split(":", 1)[1].strip()
            if signal:
                return f"{item.title}: {signal}"
    if item.source_name.lower() == "github" and "stars" in text.lower():
        return f"{item.title}: GitHub repository traction mentioned by the source"
    return None


def product_signal_text(item: FeedItem) -> str:
    return "\n".join(
        part
        for part in [
            item.summary_detailed or "",
            item.summary_short or "",
            item.why_it_matters or "",
        ]
        if part
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
        elif field_name in {"label", "category", "priority"} and isinstance(value, str):
            normalized_text = value.strip()
            if not normalized_text:
                continue
            value = normalized_text
        elif field_name == "notes" and isinstance(value, str):
            value = value.strip() or None
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
    blocked_sources: list[str] | None = None,
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

    rows = query_topic_rows(
        db=db,
        topic=watch_topic,
        limit=limit,
        blocked_sources=blocked_sources,
    )
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
        definition=build_topic_definition(topic),
        item_count=len(items),
        high_impact_count=count_high_impact_feed_items(items),
        average_importance_score=average_importance_score(items),
        trending_sources=[
            TopicSourceCount(source_name=source_name, item_count=count)
            for source_name, count in source_counts.most_common(8)
        ],
        related_papers=rank_topic_research_items(topic, items)[:6],
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


def build_topic_definition(topic: TopicWatchlistSchema) -> str:
    if topic.notes:
        return topic.notes.strip()

    category = topic.category.replace("_", " ").replace("-", " ").strip() or "AI"
    if topic.related_terms:
        focus = ", ".join(topic.related_terms[:4])
        return f"{topic.label} is a {category} watch topic focused on {focus}."
    return f"{topic.label} is a {category} watch topic."


def rank_topic_research_items(
    topic: TopicWatchlistItem | TopicWatchlistSchema,
    items: list[FeedItem],
) -> list[FeedItem]:
    return sorted(
        [item for item in items if item.category == "research"],
        key=lambda item: (
            topic_research_score(topic, item),
            item.published_at or datetime.min.replace(tzinfo=UTC),
            item.id,
        ),
        reverse=True,
    )


def topic_research_score(
    topic: TopicWatchlistItem | TopicWatchlistSchema,
    item: FeedItem,
) -> float:
    topic_match = topic_research_match_score(topic, item)
    potential_impact = (
        0.45 * item.importance_score
        + 0.30 * item.relevance_score
        + 0.15 * item.source_quality_score
        + 0.10 * item.novelty_score
    )
    return round(0.55 * topic_match + 0.45 * potential_impact, 3)


def topic_research_match_score(
    topic: TopicWatchlistItem | TopicWatchlistSchema,
    item: FeedItem,
) -> float:
    terms = build_topic_match_terms(topic)
    if not terms:
        return 0

    text = " ".join(
        [
            item.title,
            " ".join(item.topics),
            item.summary_short or "",
            item.summary_detailed or "",
            item.why_it_matters or "",
        ]
    ).lower()
    matches = sum(1 for term in terms if term.lower() in text)
    return min(matches / min(len(terms), 4), 1.0)


def query_topic_rows(
    db: Session,
    topic: TopicWatchlistItem | TopicWatchlistSchema,
    limit: int,
    blocked_sources: list[str] | None = None,
) -> list[tuple[NormalizedItem, UserItemAction | None]]:
    return (
        topic_signal_query(db=db, topic=topic, blocked_sources=blocked_sources)
        .limit(limit)
        .all()
    )


def topic_signal_query(
    db: Session,
    topic: TopicWatchlistItem | TopicWatchlistSchema,
    blocked_sources: list[str] | None = None,
):
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

    query = (
        db.query(NormalizedItem, UserItemAction)
        .outerjoin(
            UserItemAction,
            (UserItemAction.item_id == NormalizedItem.id)
            & (UserItemAction.user_id == LOCAL_USER_ID),
        )
        .filter((UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None)))
        .filter(or_(*conditions))
    )
    return apply_blocked_source_filter(query, blocked_sources).order_by(
        UserItemAction.is_important.desc().nullslast(),
        NormalizedItem.importance_score.desc(),
        NormalizedItem.relevance_score.desc(),
        NormalizedItem.published_at.desc().nullslast(),
        NormalizedItem.created_at.desc(),
    )


def build_topic_match_terms(topic: TopicWatchlistItem | TopicWatchlistSchema) -> list[str]:
    label_words = topic.label.replace("-", " ")
    slug_words = topic.topic.replace("-", " ")
    return unique_normalized_terms([topic.topic, label_words, slug_words, *topic.related_terms])


def build_company_match_terms(company: CompanyWatchlistItem | CompanyWatchlistSchema) -> list[str]:
    terms = [
        company.company_name,
        company.company_key.replace("-", " "),
        company.ticker or "",
        *company.related_terms,
    ]
    return unique_normalized_terms(terms)


def summarize_stock_signals(
    db: Session,
    limit_per_stock: int = 3,
    blocked_sources: list[str] | None = None,
) -> list[StockSignalSummary]:
    stocks = list_stock_watchlist(db)
    if not stocks:
        summaries = [
            build_stock_signal_summary(
                db,
                stock,
                limit=limit_per_stock,
                blocked_sources=blocked_sources,
            )
            for stock in initial_stock_watchlist()
        ]
    else:
        summaries = [
            build_stock_signal_summary(
                db,
                stock,
                limit=limit_per_stock,
                blocked_sources=blocked_sources,
            )
            for stock in stocks
        ]
    return sorted(summaries, key=lambda summary: summary.attention_score, reverse=True)


def get_stock_signals(
    db: Session,
    ticker: str,
    limit: int = 20,
    blocked_sources: list[str] | None = None,
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
    return build_stock_signal_summary(
        db,
        stock,
        limit=limit,
        blocked_sources=blocked_sources,
    )


def get_stock_briefing(
    db: Session,
    ticker: str,
    limit: int = 10,
    blocked_sources: list[str] | None = None,
) -> StockBriefing | None:
    summary = get_stock_signals(
        db,
        ticker=ticker,
        limit=limit,
        blocked_sources=blocked_sources,
    )
    if summary is None:
        return None
    return build_stock_briefing(summary)


def build_stock_signal_summary(
    db: Session,
    stock: StockWatchlistItem | StockWatchlistSchema,
    limit: int,
    blocked_sources: list[str] | None = None,
) -> StockSignalSummary:
    rows = query_stock_signal_rows(
        db,
        stock=stock,
        limit=limit,
        blocked_sources=blocked_sources,
    )
    top_signals = [serialize_feed_item(item, action) for item, action in rows]
    signal_count = count_stock_signal_rows(db, stock=stock, blocked_sources=blocked_sources)
    latest_signal = top_signals[0] if top_signals else None
    stock_schema = stock if isinstance(stock, StockWatchlistSchema) else (
        StockWatchlistSchema.model_validate(stock)
    )
    market = build_stock_market_snapshot(db=db, ticker=stock_schema.ticker)
    latest_event_at = latest_signal.published_at if latest_signal else None
    today_signal_count = count_stock_signal_rows_for_date(
        db,
        stock=stock,
        signal_date=datetime.now(UTC).date(),
        blocked_sources=blocked_sources,
    )
    high_impact_count = count_high_impact_stock_signal_rows(
        db,
        stock=stock,
        blocked_sources=blocked_sources,
    )
    return StockSignalSummary(
        stock=stock_schema,
        signal_count=signal_count,
        today_signal_count=today_signal_count,
        high_impact_count=high_impact_count,
        attention_score=compute_stock_attention_score(
            stock=stock_schema,
            top_signals=top_signals,
            signal_count=signal_count,
        ),
        attention_reasons=build_stock_attention_reasons(
            stock=stock_schema,
            top_signals=top_signals,
            signal_count=signal_count,
            today_signal_count=today_signal_count,
            high_impact_count=high_impact_count,
        ),
        market=market,
        latest_event_title=latest_signal.title if latest_signal else None,
        latest_event_at=latest_event_at,
        last_updated_at=compute_stock_summary_last_updated_at(
            latest_event_at=latest_event_at,
            market=market,
        ),
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
        attention_reasons=summary.attention_reasons,
        market=summary.market,
        urgency=classify_stock_urgency(summary),
        latest_signal_at=latest_signal_at,
        sentiment_counts=summary.sentiment_counts,
        key_themes=build_stock_briefing_themes(summary.top_signals),
        ai_relevance_summary=build_stock_ai_relevance_summary(summary),
        theme_breakdown=build_stock_theme_breakdown(summary),
        market_impact_events=build_stock_market_impact_events(summary.top_signals),
        recent_timeline=[
            build_stock_briefing_timeline_item(item=item, market=summary.market)
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
    volume_change_percent = (
        round(((latest.volume - previous.volume) / previous.volume) * 100, 2)
        if previous and latest.volume is not None and previous.volume
        else None
    )
    return StockMarketSnapshot(
        latest=latest,
        previous_close=previous.close_price if previous else None,
        change=round(change, 4) if change is not None else None,
        change_percent=change_percent,
        volume_change_percent=volume_change_percent,
        history=history,
    )


def compute_stock_summary_last_updated_at(
    latest_event_at: datetime | None,
    market: StockMarketSnapshot | None,
) -> datetime | None:
    candidates = []
    if latest_event_at is not None:
        candidates.append(
            latest_event_at if latest_event_at.tzinfo else latest_event_at.replace(tzinfo=UTC)
        )
    if market and market.latest:
        candidates.append(datetime.combine(market.latest.price_date, time.min, tzinfo=UTC))
    return max(candidates) if candidates else None


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


def build_stock_attention_reasons(
    stock: StockWatchlistSchema,
    top_signals: list[FeedItem],
    signal_count: int,
    today_signal_count: int,
    high_impact_count: int,
) -> list[str]:
    reasons: list[str] = []
    strongest_signal = max(
        (compute_stock_signal_score(item) for item in top_signals),
        default=0,
    )
    if strongest_signal >= 0.7:
        reasons.append(f"Strongest signal scored {round(strongest_signal * 100)}")
    if signal_count > 0:
        reasons.append(f"{signal_count} matched signal{'' if signal_count == 1 else 's'}")
    if today_signal_count > 0:
        reasons.append(
            f"{today_signal_count} signal{'' if today_signal_count == 1 else 's'} today"
        )
    if high_impact_count > 0:
        reasons.append(
            f"{high_impact_count} high-impact signal{'' if high_impact_count == 1 else 's'}"
        )
    if stock.priority.strip().lower() == "high":
        reasons.append("High watchlist priority")
    elif stock.priority.strip().lower() == "medium":
        reasons.append("Medium watchlist priority")
    if stock.is_pinned:
        reasons.append("Pinned ticker boost")
    if not reasons:
        reasons.append("No AI-related signals matched yet")
    return reasons[:4]


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
    themes = stock.related_ai_themes[:4] or build_stock_briefing_themes(
        summary.top_signals,
        limit=4,
    )
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


def build_stock_briefing_llm_prompt(briefing: StockBriefing) -> str:
    stock = briefing.stock
    market_lines = ["No recent price context is available."]
    if briefing.market and briefing.market.latest:
        latest = briefing.market.latest
        market_lines = [
            f"Latest close: {latest.close_price} on {latest.price_date.isoformat()}",
            f"Previous close: {briefing.market.previous_close}",
            f"Change: {briefing.market.change} ({briefing.market.change_percent}%)",
            f"Volume: {latest.volume}",
        ]
        if briefing.market.volume_change_percent is not None:
            market_lines.append(f"Volume change: {briefing.market.volume_change_percent}%")

    themes = ", ".join(briefing.key_themes[:8]) or "None extracted"
    sentiment = ", ".join(
        f"{label}: {count}" for label, count in sorted(briefing.sentiment_counts.items())
    ) or "None"
    event_lines = [
        (
            f"- {event.event_type}: {event.item_count} item(s); "
            f"latest={event.latest_title or 'unknown'}"
        )
        for event in briefing.market_impact_events[:6]
    ] or ["- None"]
    timeline_lines = []
    for item in briefing.recent_timeline[:8]:
        published = item.item.published_at.isoformat() if item.item.published_at else "unknown"
        uncertainties = "; ".join(item.uncertainties) or "none"
        timeline_lines.append(
            f"- {item.item.title} | source={item.item.source_name} | "
            f"published={published} | event={item.event_type} | "
            f"impact={item.possible_market_impact} | price_reaction={item.price_reaction} | "
            f"confidence={item.confidence} | summary={item.event_summary} | "
            f"uncertainties={uncertainties}"
        )
    if not timeline_lines:
        timeline_lines = ["- No recent timeline items."]

    return "\n".join(
        [
            "You are SignalLens, a research assistant for AI market intelligence.",
            "Use only the supplied evidence. Do not provide investment advice.",
            "If evidence is thin or uncertain, say so directly.",
            "Return four short sections with these exact headings:",
            "What happened",
            "Why it matters",
            "Possible market relevance",
            "Uncertainties",
            "",
            "Stock:",
            f"- Ticker: {stock.ticker}",
            f"- Company: {stock.company_name}",
            f"- Exchange: {stock.exchange}",
            f"- Sector: {stock.sector}",
            f"- Industry: {stock.industry}",
            f"- Watchlist priority: {stock.priority}",
            f"- Watched AI themes: {', '.join(stock.related_ai_themes) or 'None configured'}",
            "",
            "Signal state:",
            f"- Signal count: {briefing.signal_count}",
            f"- Attention score: {briefing.attention_score}",
            f"- Urgency: {briefing.urgency}",
            f"- Sentiment counts: {sentiment}",
            f"- Key themes: {themes}",
            f"- Existing deterministic summary: {briefing.ai_relevance_summary}",
            "",
            "Market context:",
            *market_lines,
            "",
            "Market-impact event groups:",
            *event_lines,
            "",
            "Recent timeline evidence:",
            *timeline_lines,
            "",
            f"Disclaimer to respect: {briefing.disclaimer}",
        ]
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


def build_stock_briefing_timeline_item(
    item: FeedItem,
    market: StockMarketSnapshot | None,
) -> StockBriefingTimelineItem:
    possible_market_impact = infer_possible_market_impact(item)
    event_price_date, event_price_change_percent = infer_event_price_move(
        market=market,
        item=item,
    )
    return StockBriefingTimelineItem(
        item=item,
        signal_score=compute_stock_signal_score(item),
        reason=build_stock_signal_reason(item),
        event_type=infer_stock_event_type(item),
        possible_market_impact=possible_market_impact,
        price_reaction=infer_stock_price_reaction_from_change(
            change_percent=(
                event_price_change_percent
                if event_price_change_percent is not None
                else market.change_percent if market else None
            ),
            possible_market_impact=possible_market_impact,
        ),
        event_price_date=event_price_date,
        event_price_change_percent=event_price_change_percent,
        confidence=compute_stock_event_confidence(item),
        time_sensitivity=infer_stock_event_time_sensitivity(item),
        event_summary=build_stock_event_summary(item),
        uncertainties=build_stock_event_uncertainties(item),
    )


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


def infer_stock_price_reaction(
    market: StockMarketSnapshot | None,
    possible_market_impact: str,
) -> str:
    return infer_stock_price_reaction_from_change(
        change_percent=market.change_percent if market else None,
        possible_market_impact=possible_market_impact,
    )


def infer_stock_price_reaction_from_change(
    change_percent: float | None,
    possible_market_impact: str,
) -> str:
    if change_percent is None:
        return "no_price_data"

    if abs(change_percent) < 0.75:
        return "muted_or_unclear"

    if possible_market_impact == "positive":
        return "aligned_up" if change_percent > 0 else "opposite_move"
    if possible_market_impact == "negative":
        return "aligned_down" if change_percent < 0 else "opposite_move"
    return "muted_or_unclear"


def infer_event_price_move(
    market: StockMarketSnapshot | None,
    item: FeedItem,
) -> tuple[date | None, float | None]:
    if market is None or not market.history or item.published_at is None:
        return None, None

    event_date = item.published_at.date()
    history = sorted(market.history, key=lambda point: point.price_date)
    for index, point in enumerate(history):
        if point.price_date < event_date:
            continue
        if index == 0:
            return point.price_date, None
        previous = history[index - 1]
        if not previous.close_price:
            return point.price_date, None
        change_percent = round(
            ((point.close_price - previous.close_price) / previous.close_price) * 100,
            2,
        )
        return point.price_date, change_percent
    return None, None


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
    blocked_sources: list[str] | None = None,
) -> list[tuple[NormalizedItem, UserItemAction | None]]:
    return (
        stock_signal_query(db, stock=stock, blocked_sources=blocked_sources)
        .limit(limit)
        .all()
    )


def count_stock_signal_rows(
    db: Session,
    stock: StockWatchlistItem | StockWatchlistSchema,
    blocked_sources: list[str] | None = None,
) -> int:
    return stock_signal_query(db, stock=stock, blocked_sources=blocked_sources).count()


def count_stock_signal_rows_for_date(
    db: Session,
    stock: StockWatchlistItem | StockWatchlistSchema,
    signal_date: date,
    blocked_sources: list[str] | None = None,
) -> int:
    start = datetime.combine(signal_date, time.min, tzinfo=UTC)
    end = start + timedelta(days=1)
    return (
        stock_signal_query(db, stock=stock, blocked_sources=blocked_sources)
        .filter(
            NormalizedItem.published_at >= start,
            NormalizedItem.published_at < end,
        )
        .count()
    )


def count_high_impact_stock_signal_rows(
    db: Session,
    stock: StockWatchlistItem | StockWatchlistSchema,
    blocked_sources: list[str] | None = None,
) -> int:
    return (
        stock_signal_query(db, stock=stock, blocked_sources=blocked_sources)
        .filter(
            or_(
                NormalizedItem.stock_impact_score >= HIGH_IMPACT_SIGNAL_THRESHOLD,
                NormalizedItem.importance_score >= HIGH_IMPACT_SIGNAL_THRESHOLD,
            )
        )
        .count()
    )


def count_high_impact_feed_items(items: list[FeedItem]) -> int:
    return sum(
        1
        for item in items
        if item.stock_impact_score >= HIGH_IMPACT_SIGNAL_THRESHOLD
        or item.importance_score >= HIGH_IMPACT_SIGNAL_THRESHOLD
    )


def average_importance_score(items: list[FeedItem]) -> float:
    if not items:
        return 0
    return sum(item.importance_score for item in items) / len(items)


def build_sentiment_counts(items: list[FeedItem]) -> dict[str, int]:
    return dict(Counter(item.sentiment or "neutral" for item in items))


def stock_signal_query(
    db: Session,
    stock: StockWatchlistItem | StockWatchlistSchema,
    blocked_sources: list[str] | None = None,
):
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

    query = (
        db.query(NormalizedItem, UserItemAction)
        .outerjoin(
            UserItemAction,
            (UserItemAction.item_id == NormalizedItem.id)
            & (UserItemAction.user_id == LOCAL_USER_ID),
        )
        .filter((UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None)))
        .filter(or_(*conditions))
    )
    return apply_blocked_source_filter(query, blocked_sources).order_by(
        UserItemAction.is_important.desc().nullslast(),
        NormalizedItem.stock_impact_score.desc(),
        NormalizedItem.importance_score.desc(),
        NormalizedItem.relevance_score.desc(),
        NormalizedItem.published_at.desc().nullslast(),
        NormalizedItem.created_at.desc(),
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


def normalize_optional_ticker(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = normalize_ticker(value)
    return normalized or None


def normalize_company_key(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return normalized.strip("-")


def normalize_topic(value: str) -> str:
    return "-".join(value.strip().lower().split())


def normalize_product_category(value: str) -> str:
    return "-".join(value.strip().lower().split())


def clean_terms(values: list[str]) -> list[str]:
    return unique_normalized_terms(values)
