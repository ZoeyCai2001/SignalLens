from sqlalchemy.orm import Session

from app.db.models import NormalizedItem, UserItemAction
from app.schemas.feed import FeedItem

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


def list_visible_feed_items(db: Session, limit: int) -> list[FeedItem]:
    rows = (
        db.query(NormalizedItem, UserItemAction)
        .outerjoin(
            UserItemAction,
            (UserItemAction.item_id == NormalizedItem.id)
            & (UserItemAction.user_id == LOCAL_USER_ID),
        )
        .filter((UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None)))
        .order_by(
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
