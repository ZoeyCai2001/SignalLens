from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import String, cast, or_
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
SAVED_ITEM_RANKING_BONUS = 0.05
PREFERRED_SOURCE_RANKING_BONUS = 0.08


@dataclass(frozen=True)
class FeedInterestProfile:
    symbols: frozenset[str]
    terms: frozenset[str]


def serialize_feed_item(
    item: NormalizedItem,
    action: UserItemAction | None = None,
) -> FeedItem:
    data = FeedItem.model_validate(item)
    data.social_signal_score = social_signal_score_for_item(item)
    if action:
        data.is_saved = action.is_saved
        data.is_hidden = action.is_hidden
        data.is_important = action.is_important
        data.is_read = action.is_read
        data.read_at = action.read_at
        data.personal_note = action.personal_note
        data.manual_tags = normalize_manual_tags(action.manual_tags)
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
        uncertainty_notes=build_feed_uncertainty_notes(base),
        action_state={
            "is_saved": base.is_saved,
            "is_hidden": base.is_hidden,
            "is_important": base.is_important,
            "is_read": base.is_read,
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
    if item.social_signal_score >= 0.65:
        reasons.append("strong source engagement signal")
    if item.classification_confidence < 0.6:
        reasons.append("lower classifier confidence")
    if item.importance_score >= 0.75:
        reasons.append("high importance score")
    if item.stock_impact_score >= 0.75:
        reasons.append("high stock-impact score")
    if item.is_saved:
        reasons.append("saved by you")
    if item.is_important:
        reasons.append("marked important by you")
    if not reasons:
        reasons.append("matched the AI relevance prefilter")
    return "Shown because it " + "; ".join(reasons) + "."


def build_feed_uncertainty_notes(item: FeedItem) -> list[str]:
    notes: list[str] = []
    if item.classification_confidence < 0.6:
        notes.append("Classifier confidence is low, so category and entity labels may need review.")
    if item.source_quality_score < 0.6:
        notes.append("Source credibility is lower than the preferred-source threshold.")
    if item.stock_impact_score >= 0.35 and not item.tickers:
        notes.append("Stock impact was inferred, but no explicit ticker was extracted.")
    if item.stock_impact_score >= 0.35 and item.sentiment == "neutral":
        notes.append("Market direction is unclear from the available signal.")
    if not item.summary_short and not item.summary_detailed:
        notes.append("No generated summary is stored yet; review the original source text.")
    if item.source_name == "Manual Submission":
        notes.append("Manual submissions depend on the supplied URL and note context.")
    return notes or ["No major uncertainty flags from the stored item signals."]


def list_visible_feed_items(
    db: Session,
    limit: int,
    ranking_weights: RankingWeights | dict | None = None,
    preferred_sources: list[str] | None = None,
    blocked_sources: list[str] | None = None,
    language_preferences: list[str] | None = None,
    saved_only: bool = False,
    hidden_only: bool = False,
    topic: str | None = None,
) -> list[FeedItem]:
    blocked_source_names = normalize_source_names(blocked_sources)
    preferred_languages = normalize_language_codes(language_preferences)
    topic_terms = build_feed_topic_filter_terms(topic)
    query = (
        db.query(NormalizedItem, UserItemAction)
        .outerjoin(
            UserItemAction,
            (UserItemAction.item_id == NormalizedItem.id)
            & (UserItemAction.user_id == LOCAL_USER_ID),
        )
    )
    if hidden_only:
        query = query.filter(UserItemAction.is_hidden.is_(True))
    else:
        query = query.filter((UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None)))
    if blocked_source_names:
        query = query.filter(~NormalizedItem.source_name.in_(blocked_source_names))
    if preferred_languages:
        query = query.filter(NormalizedItem.language.in_(preferred_languages))
    if saved_only:
        query = query.filter(UserItemAction.is_saved.is_(True))
    if topic_terms:
        topic_conditions = []
        for topic_term in topic_terms:
            pattern = f"%{topic_term}%"
            json_pattern = f'%"{topic_term}"%'
            topic_conditions.extend(
                [
                    cast(NormalizedItem.topics, String).ilike(json_pattern),
                    cast(NormalizedItem.topics, String).ilike(pattern),
                    cast(NormalizedItem.products, String).ilike(pattern),
                    cast(NormalizedItem.companies, String).ilike(pattern),
                    NormalizedItem.title.ilike(pattern),
                    NormalizedItem.summary_short.ilike(pattern),
                    NormalizedItem.summary_detailed.ilike(pattern),
                    NormalizedItem.why_it_matters.ilike(pattern),
                ]
            )
        query = query.filter(or_(*topic_conditions))

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
    source_bonus = (
        PREFERRED_SOURCE_RANKING_BONUS
        if preferred_sources and item.source_name in preferred_sources
        else 0
    )
    saved_bonus = SAVED_ITEM_RANKING_BONUS if item.is_saved else 0
    interest_bonus = feed_interest_bonus(item=item, interest_profile=interest_profile)
    return round(
        weights.relevance * item.relevance_score
        + weights.importance * item.importance_score
        + weights.novelty * item.novelty_score
        + weights.source_quality * item.source_quality_score
        + weights.social_signal * item.social_signal_score
        + weights.stock_impact * item.stock_impact_score
        + weights.freshness * freshness_score(item, now=reference_time)
        + source_bonus
        + saved_bonus
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


def social_signal_score_for_item(item: NormalizedItem) -> float:
    raw_metadata = item.raw_item.raw_metadata if item.raw_item else {}
    source_name = item.source_name.lower()

    if "github" in source_name:
        return bounded_social_score(
            0.45 * scaled_metric(raw_metadata.get("stars"), 5000)
            + 0.35 * scaled_metric(raw_metadata.get("stars_per_day"), 50)
            + 0.20 * scaled_metric(raw_metadata.get("forks"), 1000)
        )
    if "hacker news" in source_name:
        return bounded_social_score(
            0.60 * scaled_metric(raw_metadata.get("score"), 500)
            + 0.30 * scaled_metric(raw_metadata.get("descendants"), 200)
            + 0.10 * scaled_metric(raw_metadata.get("top_comment_count"), 10)
        )
    if "product hunt" in source_name:
        return bounded_social_score(
            0.70 * scaled_metric(raw_metadata.get("votes_count"), 1000)
            + 0.30 * scaled_metric(raw_metadata.get("comments_count"), 100)
        )

    return bounded_social_score(
        0.45 * scaled_metric(raw_metadata.get("likes"), 1000)
        + 0.30 * scaled_metric(raw_metadata.get("comments"), 200)
        + 0.25 * scaled_metric(raw_metadata.get("views"), 50000)
    )


def scaled_metric(value: object, denominator: float) -> float:
    if denominator <= 0:
        return 0
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0
    return min(max(parsed, 0) / denominator, 1)


def bounded_social_score(value: float) -> float:
    return round(min(max(value, 0), 1), 3)


def normalize_source_names(values: list[str] | None) -> set[str]:
    return {str(value).strip() for value in values or [] if str(value).strip()}


def normalize_language_codes(values: list[str] | None) -> set[str]:
    normalized_values = set()
    for value in values or []:
        normalized = str(value).strip().lower()
        if normalized in {"english", "en-us", "en_us"}:
            normalized = "en"
        elif normalized in {"chinese", "zh-cn", "zh_cn", "cn"}:
            normalized = "zh"
        if normalized:
            normalized_values.add(normalized)
    return normalized_values


def normalize_feed_topic_filter(value: str | None) -> str | None:
    normalized = " ".join(str(value or "").strip().replace("-", " ").split())
    return normalized.lower() or None


def build_feed_topic_filter_terms(value: str | None) -> set[str]:
    normalized = normalize_feed_topic_filter(value)
    raw = str(value or "").strip().lower()
    terms = {term for term in [normalized, raw] if term}
    if normalized and normalized.startswith("ai "):
        terms.add(normalized.removeprefix("ai ").strip())
    for term in list(terms):
        words = term.split()
        if len(words) > 1 and words[-1].endswith("s") and len(words[-1]) > 3:
            terms.add(" ".join([*words[:-1], words[-1][:-1]]))
    return {term for term in terms if term}


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
    elif action_name == "unhide":
        action.is_hidden = False
    elif action_name == "mark-important":
        action.is_important = True
    elif action_name == "mark-read":
        action.is_read = True
        action.read_at = datetime.now(UTC)
    elif action_name == "mark-unread":
        action.is_read = False
        action.read_at = None
    else:
        raise ValueError(f"Unsupported action: {action_name}")

    db.add(action)
    db.commit()
    db.refresh(action)
    return serialize_feed_item(item, action)


def update_item_personal_metadata(
    db: Session,
    item: NormalizedItem,
    personal_note: str | None,
    manual_tags: list[str],
) -> FeedItemDetail:
    action = get_or_create_action(db, item.id)
    normalized_note = str(personal_note or "").strip()
    action.personal_note = normalized_note or None
    action.manual_tags = normalize_manual_tags(manual_tags)

    db.add(action)
    db.commit()
    db.refresh(action)
    return serialize_feed_item_detail(item, action)


def normalize_manual_tags(values: list[str] | None) -> list[str]:
    seen = set()
    tags = []
    for value in values or []:
        normalized = " ".join(str(value).strip().split())
        key = normalized.lower()
        if normalized and key not in seen:
            tags.append(normalized[:60])
            seen.add(key)
    return tags[:12]
