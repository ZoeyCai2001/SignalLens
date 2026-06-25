from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.db.models import NormalizedItem
from app.schemas.feed import FeedItem

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
