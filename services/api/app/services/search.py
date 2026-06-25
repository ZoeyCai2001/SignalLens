from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from app.db.models import NormalizedItem, UserItemAction
from app.schemas.feed import FeedItem
from app.services.feed_actions import LOCAL_USER_ID, serialize_feed_item


def search_feed_items(
    db: Session,
    query: str | None = None,
    source: str | None = None,
    category: str | None = None,
    ticker: str | None = None,
    topic: str | None = None,
    language: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    min_importance_score: float | None = None,
    saved_only: bool = False,
    limit: int = 30,
) -> list[FeedItem]:
    statement = db.query(NormalizedItem, UserItemAction).outerjoin(
        UserItemAction,
        (UserItemAction.item_id == NormalizedItem.id)
        & (UserItemAction.user_id == LOCAL_USER_ID),
    )

    statement = statement.filter(
        (UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None))
    )

    normalized_query = normalize_filter_value(query)
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
            )
        )

    normalized_source = normalize_filter_value(source)
    if normalized_source:
        statement = statement.filter(NormalizedItem.source_name.ilike(f"%{normalized_source}%"))

    normalized_category = normalize_filter_value(category)
    if normalized_category:
        statement = statement.filter(NormalizedItem.category == normalized_category)

    normalized_ticker = normalize_filter_value(ticker)
    if normalized_ticker:
        statement = statement.filter(
            cast(NormalizedItem.tickers, String).ilike(f"%{normalized_ticker}%")
        )

    normalized_topic = normalize_filter_value(topic)
    if normalized_topic:
        statement = statement.filter(
            cast(NormalizedItem.topics, String).ilike(f"%{normalized_topic}%")
        )

    normalized_language = normalize_filter_value(language)
    if normalized_language:
        statement = statement.filter(NormalizedItem.language == normalized_language.lower())

    if date_from:
        statement = statement.filter(
            or_(
                NormalizedItem.published_at >= start_of_day(date_from),
                (
                    (NormalizedItem.published_at.is_(None))
                    & (NormalizedItem.created_at >= start_of_day(date_from))
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

    normalized_min_importance = normalize_score(min_importance_score)
    if normalized_min_importance is not None:
        statement = statement.filter(NormalizedItem.importance_score >= normalized_min_importance)

    if saved_only:
        statement = statement.filter(UserItemAction.is_saved.is_(True))

    rows = (
        statement.order_by(
            UserItemAction.is_important.desc().nullslast(),
            NormalizedItem.importance_score.desc(),
            NormalizedItem.relevance_score.desc(),
            NormalizedItem.published_at.desc().nullslast(),
            NormalizedItem.created_at.desc(),
        )
        .limit(limit)
        .all()
    )

    return [serialize_feed_item(item, action) for item, action in rows]


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
