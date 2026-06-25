from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession
from app.core.config import get_settings
from app.db.models import NormalizedItem
from app.schemas.feed import FeedItem
from app.services.summarization import SummarizationError, summarize_feed_item

router = APIRouter()


@router.get("", response_model=list[FeedItem])
async def list_feed_items(
    db: DbSession,
    limit: int = Query(default=25, ge=1, le=100),
) -> list[FeedItem]:
    items = (
        db.query(NormalizedItem)
        .order_by(
            NormalizedItem.importance_score.desc(),
            NormalizedItem.relevance_score.desc(),
            NormalizedItem.published_at.desc().nullslast(),
            NormalizedItem.created_at.desc(),
        )
        .limit(limit)
        .all()
    )
    return [FeedItem.model_validate(item) for item in items]


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

    return FeedItem.model_validate(summarized_item)
