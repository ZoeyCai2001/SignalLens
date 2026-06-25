from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import NormalizedItem, UserItemAction
from app.schemas.feed import FeedItem, FeedItemDetail
from app.schemas.preferences import RankingWeights

LOCAL_USER_ID = "local"


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
    saved_only: bool = False,
) -> list[FeedItem]:
    query = (
        db.query(NormalizedItem, UserItemAction)
        .outerjoin(
            UserItemAction,
            (UserItemAction.item_id == NormalizedItem.id)
            & (UserItemAction.user_id == LOCAL_USER_ID),
        )
        .filter((UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None)))
    )
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
    return rank_feed_items(items, ranking_weights=ranking_weights)[:limit]


def rank_feed_items(
    items: list[FeedItem],
    ranking_weights: RankingWeights | dict | None = None,
    now: datetime | None = None,
) -> list[FeedItem]:
    weights = resolve_ranking_weights(ranking_weights)
    reference_time = now or datetime.now(UTC)
    return sorted(
        items,
        key=lambda item: (
            item.is_important,
            weighted_feed_score(item, weights, now=reference_time),
            item.published_at or datetime.min.replace(tzinfo=UTC),
        ),
        reverse=True,
    )


def weighted_feed_score(
    item: FeedItem,
    weights: RankingWeights,
    now: datetime | None = None,
) -> float:
    reference_time = now or datetime.now(UTC)
    return round(
        weights.relevance * item.relevance_score
        + weights.importance * item.importance_score
        + weights.novelty * item.novelty_score
        + weights.source_quality * item.source_quality_score
        + weights.stock_impact * item.stock_impact_score
        + weights.freshness * freshness_score(item, now=reference_time),
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
    age_hours = max(0, (reference_time - item.published_at).total_seconds() / 3600)
    return round(max(0, 1 - age_hours / 72), 4)


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
