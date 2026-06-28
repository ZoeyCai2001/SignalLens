from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import (
    CompanyWatchlistItem,
    NormalizedItem,
    ProductWatchlistItem,
    StockWatchlistItem,
    TopicWatchlistItem,
    UserItemAction,
)
from app.schemas.feed import FeedItem, FeedItemDetail
from app.schemas.preferences import RankingWeights
from app.services.seed_data import (
    initial_company_watchlist,
    initial_product_watchlist,
    initial_stock_watchlist,
    initial_topic_watchlist,
)

LOCAL_USER_ID = "local"


@dataclass(frozen=True)
class FeedInterestProfile:
    symbols: frozenset[str]
    terms: frozenset[str]


def serialize_feed_item(
    item: NormalizedItem,
    action: UserItemAction | None = None,
) -> FeedItem:
    data = FeedItem.model_validate(item)
    if action:
        data.is_saved = action.is_saved
        data.is_hidden = action.is_hidden
        data.is_important = action.is_important
    return data


def serialize_feed_item_detail(
    item: NormalizedItem,
    action: UserItemAction | None = None,
) -> FeedItemDetail:
    base = serialize_feed_item(item, action)
    return FeedItemDetail(
        **base.model_dump(),
        text=item.text,
        score_explanation=build_score_explanation(base),
        action_state={
            "is_saved": base.is_saved,
            "is_hidden": base.is_hidden,
            "is_important": base.is_important,
        },
    )


def build_score_explanation(item: FeedItem) -> str:
    reasons: list[str] = []
    if item.tickers:
        reasons.append(f"matched tickers {', '.join(item.tickers[:3])}")
    if item.topics:
        reasons.append(f"matched topics {', '.join(item.topics[:3])}")
    if item.category:
        reasons.append(f"classified as {item.category.replace('_', ' ')}")
    if item.source_quality_score >= 0.8:
        reasons.append("high source credibility")
    elif item.source_quality_score < 0.6:
        reasons.append("lower source credibility; review the original source")
    if item.classification_confidence < 0.6:
        reasons.append("lower classifier confidence")
    if item.importance_score >= 0.75:
        reasons.append("high importance score")
    if item.stock_impact_score >= 0.75:
        reasons.append("high stock-impact score")
    if not reasons:
        reasons.append("matched the AI relevance prefilter")
    return "Shown because it " + "; ".join(reasons) + "."


def list_visible_feed_items(
    db: Session,
    limit: int,
    ranking_weights: RankingWeights | dict | None = None,
    preferred_sources: list[str] | None = None,
    blocked_sources: list[str] | None = None,
    saved_only: bool = False,
) -> list[FeedItem]:
    blocked_source_names = normalize_source_names(blocked_sources)
    query = (
        db.query(NormalizedItem, UserItemAction)
        .outerjoin(
            UserItemAction,
            (UserItemAction.item_id == NormalizedItem.id)
            & (UserItemAction.user_id == LOCAL_USER_ID),
        )
        .filter((UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None)))
    )
    if blocked_source_names:
        query = query.filter(~NormalizedItem.source_name.in_(blocked_source_names))
    if saved_only:
        query = query.filter(UserItemAction.is_saved.is_(True))

    rows = (
        query
        .order_by(
            UserItemAction.is_important.desc().nullslast(),
            NormalizedItem.importance_score.desc(),
            NormalizedItem.relevance_score.desc(),
            NormalizedItem.published_at.desc().nullslast(),
            NormalizedItem.created_at.desc(),
        )
        .limit(max(limit, 100))
        .all()
    )
    items = [serialize_feed_item(item, action) for item, action in rows]
    return rank_feed_items(
        items,
        ranking_weights=ranking_weights,
        preferred_sources=preferred_sources,
        interest_profile=build_feed_interest_profile(db),
    )[:limit]


def rank_feed_items(
    items: list[FeedItem],
    ranking_weights: RankingWeights | dict | None = None,
    preferred_sources: list[str] | None = None,
    interest_profile: FeedInterestProfile | None = None,
    now: datetime | None = None,
) -> list[FeedItem]:
    weights = resolve_ranking_weights(ranking_weights)
    reference_time = now or datetime.now(UTC)
    preferred_source_names = normalize_source_names(preferred_sources)
    return sorted(
        items,
        key=lambda item: (
            item.is_important,
            weighted_feed_score(
                item,
                weights,
                now=reference_time,
                preferred_sources=preferred_source_names,
                interest_profile=interest_profile,
            ),
            item.published_at or datetime.min.replace(tzinfo=UTC),
        ),
        reverse=True,
    )


def weighted_feed_score(
    item: FeedItem,
    weights: RankingWeights,
    now: datetime | None = None,
    preferred_sources: set[str] | None = None,
    interest_profile: FeedInterestProfile | None = None,
) -> float:
    reference_time = now or datetime.now(UTC)
    source_bonus = 0.08 if preferred_sources and item.source_name in preferred_sources else 0
    interest_bonus = feed_interest_bonus(item=item, interest_profile=interest_profile)
    return round(
        weights.relevance * item.relevance_score
        + weights.importance * item.importance_score
        + weights.novelty * item.novelty_score
        + weights.source_quality * item.source_quality_score
        + weights.stock_impact * item.stock_impact_score
        + weights.freshness * freshness_score(item, now=reference_time)
        + source_bonus
        + interest_bonus,
        4,
    )


def resolve_ranking_weights(value: RankingWeights | dict | None) -> RankingWeights:
    if isinstance(value, RankingWeights):
        return value
    if isinstance(value, dict):
        return RankingWeights(**value)
    return RankingWeights()


def freshness_score(item: FeedItem, now: datetime | None = None) -> float:
    if item.published_at is None:
        return 0
    reference_time = now or datetime.now(UTC)
    published_at = item.published_at
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)
    age_hours = max(0, (reference_time - published_at).total_seconds() / 3600)
    return round(max(0, 1 - age_hours / 72), 4)


def normalize_source_names(values: list[str] | None) -> set[str]:
    return {str(value).strip() for value in values or [] if str(value).strip()}


def build_feed_interest_profile(db: Session) -> FeedInterestProfile:
    symbols: set[str] = set()
    terms: set[str] = set()

    stocks = db.query(StockWatchlistItem).filter(StockWatchlistItem.user_id == LOCAL_USER_ID).all()
    stock_items = stocks or initial_stock_watchlist()
    for stock in stock_items:
        symbols.update(
            normalize_interest_symbol(value)
            for value in [stock.ticker, *stock.related_companies]
        )
        terms.update(
            normalize_interest_term(value)
            for value in [
                stock.company_name,
                *stock.related_keywords,
                *stock.related_ai_themes,
            ]
        )

    topics = db.query(TopicWatchlistItem).filter(TopicWatchlistItem.user_id == LOCAL_USER_ID).all()
    topic_items = topics or initial_topic_watchlist()
    for topic in topic_items:
        terms.update(
            normalize_interest_term(value)
            for value in [topic.topic, topic.label, topic.category, *topic.related_terms]
        )

    products = (
        db.query(ProductWatchlistItem)
        .filter(ProductWatchlistItem.user_id == LOCAL_USER_ID)
        .all()
    )
    product_items = products or initial_product_watchlist()
    for product in product_items:
        terms.update(
            normalize_interest_term(value)
            for value in [product.category, product.label, *product.related_terms]
        )

    companies = (
        db.query(CompanyWatchlistItem)
        .filter(CompanyWatchlistItem.user_id == LOCAL_USER_ID)
        .all()
    )
    company_items = companies or initial_company_watchlist()
    for company in company_items:
        if company.ticker:
            symbols.add(normalize_interest_symbol(company.ticker))
        terms.update(
            normalize_interest_term(value)
            for value in [
                company.company_key,
                company.company_name,
                company.category,
                *company.related_terms,
            ]
        )

    return FeedInterestProfile(
        symbols=frozenset(symbol for symbol in symbols if symbol),
        terms=frozenset(term for term in terms if term),
    )


def feed_interest_bonus(
    item: FeedItem,
    interest_profile: FeedInterestProfile | None,
) -> float:
    if not interest_profile:
        return 0

    matches = 0
    item_symbols = {
        normalize_interest_symbol(value)
        for value in [*item.tickers, *item.companies]
        if normalize_interest_symbol(value)
    }
    if item_symbols & interest_profile.symbols:
        matches += 1

    searchable_text = build_interest_search_text(item)
    for term in interest_profile.terms:
        if term in searchable_text:
            matches += 1
            if matches >= 3:
                break

    return round(min(0.12, matches * 0.04), 4)


def build_interest_search_text(item: FeedItem) -> str:
    parts = [
        item.title,
        item.source_name,
        item.category,
        item.subcategory or "",
        item.summary_short or "",
        item.summary_detailed or "",
        item.why_it_matters or "",
        *item.topics,
        *item.products,
        *item.companies,
    ]
    return "\n".join(part.lower() for part in parts if part)


def normalize_interest_symbol(value: str) -> str:
    return value.strip().upper().removeprefix("$")


def normalize_interest_term(value: str) -> str:
    normalized = " ".join(value.strip().lower().replace("-", " ").split())
    generic_terms = {
        "ai",
        "app",
        "apps",
        "tool",
        "tools",
        "launch",
        "technology",
        "nasdaq",
    }
    if len(normalized) < 3 or normalized in generic_terms:
        return ""
    return normalized


def get_action(db: Session, item_id: int) -> UserItemAction | None:
    return (
        db.query(UserItemAction)
        .filter(UserItemAction.user_id == LOCAL_USER_ID, UserItemAction.item_id == item_id)
        .one_or_none()
    )


def get_or_create_action(db: Session, item_id: int) -> UserItemAction:
    action = get_action(db, item_id)
    if action:
        return action

    action = UserItemAction(user_id=LOCAL_USER_ID, item_id=item_id)
    db.add(action)
    db.flush()
    return action


def update_item_action(
    db: Session,
    item: NormalizedItem,
    action_name: str,
) -> FeedItem:
    action = get_or_create_action(db, item.id)
    if action_name == "save":
        action.is_saved = True
    elif action_name == "unsave":
        action.is_saved = False
    elif action_name == "hide":
        action.is_hidden = True
    elif action_name == "mark-important":
        action.is_important = True
    else:
        raise ValueError(f"Unsupported action: {action_name}")

    db.add(action)
    db.commit()
    db.refresh(action)
    return serialize_feed_item(item, action)
