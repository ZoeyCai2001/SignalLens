import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from app.db.models import NormalizedItem, UserItemAction
from app.schemas.feed import FeedItem
from app.schemas.preferences import RankingWeights
from app.services.feed_actions import (
    LOCAL_USER_ID,
    build_feed_interest_profile,
    normalize_language_codes,
    normalize_source_names,
    rank_feed_items,
    serialize_feed_item,
)
from app.services.scoring import detect_tickers


@dataclass(frozen=True)
class SearchIntent:
    query: str | None = None
    category: str | None = None
    ticker: str | None = None
    company: str | None = None
    topic: str | None = None
    language: str | None = None
    date_from: date | None = None
    min_importance_score: float | None = None
    saved_only: bool = False


def search_feed_items(
    db: Session,
    query: str | None = None,
    source: str | None = None,
    category: str | None = None,
    ticker: str | None = None,
    company: str | None = None,
    topic: str | None = None,
    language: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    min_importance_score: float | None = None,
    saved_only: bool = False,
    ranking_weights: RankingWeights | dict | None = None,
    preferred_sources: list[str] | None = None,
    blocked_sources: list[str] | None = None,
    language_preferences: list[str] | None = None,
    limit: int = 30,
) -> list[FeedItem]:
    intent = infer_search_intent(query)
    effective_query = intent.query if query and intent.query is not None else query
    effective_category = category or intent.category
    effective_ticker = ticker or intent.ticker
    effective_company = company or intent.company
    effective_topic = topic or intent.topic
    effective_language = language or intent.language
    effective_date_from = date_from or intent.date_from
    effective_min_importance = (
        min_importance_score
        if min_importance_score is not None
        else intent.min_importance_score
    )
    effective_saved_only = saved_only or intent.saved_only

    statement = db.query(NormalizedItem, UserItemAction).outerjoin(
        UserItemAction,
        (UserItemAction.item_id == NormalizedItem.id)
        & (UserItemAction.user_id == LOCAL_USER_ID),
    )

    statement = statement.filter(
        (UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None))
    )

    blocked_source_names = normalize_source_names(blocked_sources)
    if blocked_source_names:
        statement = statement.filter(~NormalizedItem.source_name.in_(blocked_source_names))

    normalized_query = normalize_filter_value(effective_query)
    if normalized_query:
        pattern = f"%{normalized_query}%"
        statement = statement.filter(
            or_(
                NormalizedItem.title.ilike(pattern),
                NormalizedItem.text.ilike(pattern),
                NormalizedItem.summary_short.ilike(pattern),
                NormalizedItem.summary_detailed.ilike(pattern),
                NormalizedItem.why_it_matters.ilike(pattern),
                NormalizedItem.source_name.ilike(pattern),
                cast(NormalizedItem.tickers, String).ilike(pattern),
                cast(NormalizedItem.companies, String).ilike(pattern),
                cast(NormalizedItem.products, String).ilike(pattern),
                cast(NormalizedItem.topics, String).ilike(pattern),
            )
        )

    normalized_source = normalize_filter_value(source)
    if normalized_source:
        statement = statement.filter(NormalizedItem.source_name.ilike(f"%{normalized_source}%"))

    normalized_category = normalize_filter_value(effective_category)
    if normalized_category:
        statement = statement.filter(NormalizedItem.category == normalized_category)

    normalized_ticker = normalize_filter_value(effective_ticker)
    if normalized_ticker:
        statement = statement.filter(
            cast(NormalizedItem.tickers, String).ilike(f"%{normalized_ticker}%")
        )

    normalized_company = normalize_filter_value(effective_company)
    if normalized_company:
        statement = statement.filter(
            cast(NormalizedItem.companies, String).ilike(f"%{normalized_company}%")
        )

    normalized_topic = normalize_filter_value(effective_topic)
    if normalized_topic:
        statement = statement.filter(
            cast(NormalizedItem.topics, String).ilike(f"%{normalized_topic}%")
        )

    normalized_language = normalize_filter_value(effective_language)
    if normalized_language:
        statement = statement.filter(NormalizedItem.language == normalized_language.lower())
    else:
        preferred_languages = normalize_language_codes(language_preferences)
        if preferred_languages:
            statement = statement.filter(NormalizedItem.language.in_(preferred_languages))

    if effective_date_from:
        statement = statement.filter(
            or_(
                NormalizedItem.published_at >= start_of_day(effective_date_from),
                (
                    (NormalizedItem.published_at.is_(None))
                    & (NormalizedItem.created_at >= start_of_day(effective_date_from))
                ),
            )
        )

    if date_to:
        next_day = start_of_day(date_to) + timedelta(days=1)
        statement = statement.filter(
            or_(
                NormalizedItem.published_at < next_day,
                (
                    (NormalizedItem.published_at.is_(None))
                    & (NormalizedItem.created_at < next_day)
                ),
            )
        )

    normalized_min_importance = normalize_score(effective_min_importance)
    if normalized_min_importance is not None:
        statement = statement.filter(NormalizedItem.importance_score >= normalized_min_importance)

    if effective_saved_only:
        statement = statement.filter(UserItemAction.is_saved.is_(True))

    rows = (
        statement.order_by(
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


def infer_search_intent(query: str | None, today: date | None = None) -> SearchIntent:
    normalized = normalize_filter_value(query)
    if normalized is None:
        return SearchIntent()

    lowered = normalized.lower()
    today = today or datetime.now(UTC).date()
    category = infer_category(lowered)
    language = infer_language(lowered)
    ticker = next(iter(detect_tickers(normalized)), None)
    company = infer_company(lowered)
    min_importance_score = (
        0.7
        if re.search(
            r"\b(high impact|important|most important|urgent|market[- ]moving)\b",
            lowered,
        )
        else None
    )
    date_from = (
        today - timedelta(days=7)
        if re.search(r"\b(recent|latest|this week|past week)\b", lowered)
        else None
    )
    saved_only = bool(re.search(r"\b(saved|bookmarked)\b", lowered))
    topic = infer_topic(lowered)

    return SearchIntent(
        query=extract_search_keywords(normalized),
        category=category,
        ticker=ticker,
        company=company,
        topic=topic,
        language=language,
        date_from=date_from,
        min_importance_score=min_importance_score,
        saved_only=saved_only,
    )


def infer_category(lowered_query: str) -> str | None:
    if has_chinese_signal(lowered_query) or re.search(
        r"\b(social media|social posts?)\b",
        lowered_query,
    ):
        return "social_trend"
    if re.search(
        r"\b(stock|stocks|semiconductor|chip|earnings|market|data centers?|capex)\b",
        lowered_query,
    ):
        return "stock_company_event"
    if re.search(
        r"\b(product|products|app|apps|tool|tools|launch|photo|browser)\b",
        lowered_query,
    ):
        return "product"
    if re.search(r"\b(paper|papers|research|arxiv|benchmark|benchmarks)\b", lowered_query):
        return "research"
    if re.search(
        r"\b(agent harness|coding agent|model routing|inference|rag|mcp)\b",
        lowered_query,
    ):
        return "technical_trend"
    return None


def infer_language(lowered_query: str) -> str | None:
    if has_chinese_signal(lowered_query):
        return "zh"
    return None


def has_chinese_signal(lowered_query: str) -> bool:
    return bool(
        re.search(r"\b(chinese|xiaohongshu|wechat|zh)\b", lowered_query)
        or any(term in lowered_query for term in ["中文", "小红书", "微信"])
    )


def infer_topic(lowered_query: str) -> str | None:
    topic_phrases = [
        "agent harness",
        "ai data center",
        "data center",
        "ai coding",
        "coding agent",
        "model routing",
        "open-source llm",
        "open source llm",
        "ai photo",
        "semiconductor",
    ]
    return next((phrase for phrase in topic_phrases if phrase in lowered_query), None)


def infer_company(lowered_query: str) -> str | None:
    company_aliases = [
        ("openai", "OpenAI"),
        ("anthropic", "Anthropic"),
        ("deepmind", "Google DeepMind"),
        ("google deepmind", "Google DeepMind"),
        ("nvidia", "NVIDIA"),
        ("nvda", "NVIDIA"),
        ("micron", "Micron"),
        ("marvell", "Marvell"),
        ("mrvl", "Marvell"),
        ("sandisk", "SanDisk"),
        ("sndk", "SanDisk"),
        ("amd", "AMD"),
        ("broadcom", "Broadcom"),
        ("avgo", "Broadcom"),
        ("tsmc", "TSMC"),
        ("microsoft", "Microsoft"),
        ("msft", "Microsoft"),
        ("google", "Google"),
        ("googl", "Google"),
        ("amazon", "Amazon"),
        ("amzn", "Amazon"),
        ("meta", "Meta"),
        ("oracle", "Oracle"),
        ("orcl", "Oracle"),
    ]
    return next((company for alias, company in company_aliases if alias in lowered_query), None)


def extract_search_keywords(query: str) -> str | None:
    lowered = query.lower()
    phrase_matches = [
        ("ai data center", "AI data center"),
        ("data centers", "data center"),
        ("data center", "data center"),
        ("ai coding products", "AI coding"),
        ("coding products", "coding"),
        ("agent harness", "agent harness"),
        ("ai photo tools", "AI photo"),
        ("photo tools", "photo"),
        ("semiconductor ai", "semiconductor AI"),
        ("open-source llms", "open-source LLM"),
        ("open source llms", "open source LLM"),
    ]
    for needle, replacement in phrase_matches:
        if needle in lowered:
            return replacement

    cleaned = re.sub(r"\$?[A-Z]{1,5}\b", " ", query)
    cleaned = re.sub(
        r"\b(show|me|what|are|the|latest|recent|find|about|posts|post|news|discussion|"
        r"discussions|summarize|most|important|this|week|saved|bookmarked|chinese|social|media)\b",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ?.")
    return cleaned or None


def normalize_filter_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def normalize_score(value: float | None) -> float | None:
    if value is None:
        return None
    return min(1, max(0, value))


def start_of_day(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)
