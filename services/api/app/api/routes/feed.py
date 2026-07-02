from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession
from app.core.config import get_settings
from app.db.models import NormalizedItem
from app.schemas.feed import (
    FeedItem,
    FeedItemDetail,
    FeedItemPersonalMetadataUpdate,
    SavedItemsMarkdownExport,
)
from app.services.classification import ClassificationError, classify_feed_item
from app.services.feed_actions import (
    build_feed_interest_profile,
    delete_feed_item,
    export_saved_items_markdown,
    get_action,
    list_visible_feed_items,
    normalize_feed_module_filter,
    serialize_feed_item,
    serialize_feed_item_detail,
    update_item_action,
    update_item_personal_metadata,
)
from app.services.preferences import get_user_preferences
from app.services.summarization import SummarizationError, summarize_feed_item

router = APIRouter()


@router.get("", response_model=list[FeedItem])
async def list_feed_items(
    db: DbSession,
    limit: int = Query(default=25, ge=1, le=100),
    saved_only: bool = Query(default=False),
    hidden_only: bool = Query(default=False),
    topic: str | None = Query(default=None, max_length=120),
    module: str | None = Query(default=None, max_length=80),
) -> list[FeedItem]:
    if module and not normalize_feed_module_filter(module):
        raise HTTPException(
            status_code=400,
            detail="Unsupported feed module. Use trends, research, products, stocks, or chinese.",
        )
    preferences = get_user_preferences(db)
    return list_visible_feed_items(
        db=db,
        limit=limit,
        ranking_weights=preferences.ranking_weights,
        preferred_sources=preferences.preferred_sources,
        blocked_sources=preferences.blocked_sources,
        language_preferences=preferences.language_preferences,
        saved_only=saved_only,
        hidden_only=hidden_only,
        topic=topic,
        module=module,
    )


@router.get("/saved/export/markdown", response_model=SavedItemsMarkdownExport)
async def export_saved_items_markdown_route(
    db: DbSession,
    include_read: bool = Query(default=True),
    limit: int = Query(default=100, ge=1, le=200),
) -> SavedItemsMarkdownExport:
    return export_saved_items_markdown(
        db=db,
        include_read=include_read,
        limit=limit,
    )


@router.get("/{item_id}", response_model=FeedItemDetail)
async def get_feed_item_detail(item_id: int, db: DbSession) -> FeedItemDetail:
    item = get_feed_item_or_404(db, item_id)
    return serialize_feed_item_detail(
        item,
        get_action(db, item_id),
        interest_profile=build_feed_interest_profile(db),
    )


@router.post("/{item_id}/summarize", response_model=FeedItem)
async def summarize_item(item_id: int, db: DbSession) -> FeedItem:
    item = db.get(NormalizedItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Feed item not found.")

    try:
        summarized_item = await summarize_feed_item(
            db=db,
            item=item,
            settings=get_settings(),
        )
    except SummarizationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return serialize_feed_item(summarized_item, get_action(db, item_id))


@router.post("/{item_id}/classify", response_model=FeedItem)
async def classify_item(item_id: int, db: DbSession) -> FeedItem:
    item = db.get(NormalizedItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Feed item not found.")

    try:
        classified_item = await classify_feed_item(
            db=db,
            item=item,
            settings=get_settings(),
        )
    except ClassificationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return serialize_feed_item(classified_item, get_action(db, item_id))


@router.post("/{item_id}/save", response_model=FeedItem)
async def save_item(item_id: int, db: DbSession) -> FeedItem:
    item = get_feed_item_or_404(db, item_id)
    return update_item_action(db=db, item=item, action_name="save")


@router.post("/{item_id}/unsave", response_model=FeedItem)
async def unsave_item(item_id: int, db: DbSession) -> FeedItem:
    item = get_feed_item_or_404(db, item_id)
    return update_item_action(db=db, item=item, action_name="unsave")


@router.post("/{item_id}/hide", response_model=FeedItem)
async def hide_item(item_id: int, db: DbSession) -> FeedItem:
    item = get_feed_item_or_404(db, item_id)
    return update_item_action(db=db, item=item, action_name="hide")


@router.post("/{item_id}/unhide", response_model=FeedItem)
async def unhide_item(item_id: int, db: DbSession) -> FeedItem:
    item = get_feed_item_or_404(db, item_id)
    return update_item_action(db=db, item=item, action_name="unhide")


@router.post("/{item_id}/mark-important", response_model=FeedItem)
async def mark_item_important(item_id: int, db: DbSession) -> FeedItem:
    item = get_feed_item_or_404(db, item_id)
    return update_item_action(db=db, item=item, action_name="mark-important")


@router.post("/{item_id}/unmark-important", response_model=FeedItem)
async def unmark_item_important(item_id: int, db: DbSession) -> FeedItem:
    item = get_feed_item_or_404(db, item_id)
    return update_item_action(db=db, item=item, action_name="unmark-important")


@router.post("/{item_id}/mark-read", response_model=FeedItem)
async def mark_item_read(item_id: int, db: DbSession) -> FeedItem:
    item = get_feed_item_or_404(db, item_id)
    return update_item_action(db=db, item=item, action_name="mark-read")


@router.post("/{item_id}/mark-unread", response_model=FeedItem)
async def mark_item_unread(item_id: int, db: DbSession) -> FeedItem:
    item = get_feed_item_or_404(db, item_id)
    return update_item_action(db=db, item=item, action_name="mark-unread")


@router.patch("/{item_id}/personal-metadata", response_model=FeedItemDetail)
async def update_item_personal_metadata_route(
    item_id: int,
    payload: FeedItemPersonalMetadataUpdate,
    db: DbSession,
) -> FeedItemDetail:
    item = get_feed_item_or_404(db, item_id)
    return update_item_personal_metadata(
        db=db,
        item=item,
        personal_note=payload.personal_note,
        manual_tags=payload.manual_tags,
    )


@router.delete("/{item_id}", status_code=204)
async def delete_feed_item_route(item_id: int, db: DbSession) -> None:
    item = get_feed_item_or_404(db, item_id)
    delete_feed_item(db=db, item=item)


def get_feed_item_or_404(db: DbSession, item_id: int) -> NormalizedItem:
    item = db.get(NormalizedItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Feed item not found.")
    return item
