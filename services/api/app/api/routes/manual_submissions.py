from fastapi import APIRouter

from app.api.deps import DbSession
from app.core.config import get_settings
from app.db.models import NormalizedItem
from app.schemas.manual_submissions import ManualSubmissionRequest, ManualSubmissionResponse
from app.services.feed_actions import get_action, serialize_feed_item
from app.services.manual_submissions import create_manual_submission
from app.services.summarization import SummarizationError, summarize_feed_item

router = APIRouter()


@router.post("", response_model=ManualSubmissionResponse)
async def submit_manual_url(
    request: ManualSubmissionRequest,
    db: DbSession,
) -> ManualSubmissionResponse:
    item = create_manual_submission(db=db, request=request)
    if not request.summarize_with_llm:
        return ManualSubmissionResponse(item=item)

    stored_item = db.get(NormalizedItem, item.id)
    if stored_item is None:
        return ManualSubmissionResponse(
            item=item,
            summary_status="failed",
            summary_error="Manual item was stored but could not be reloaded for summarization.",
        )

    try:
        summarized_item = await summarize_feed_item(
            db=db,
            item=stored_item,
            settings=get_settings(),
        )
    except SummarizationError as exc:
        return ManualSubmissionResponse(
            item=item,
            summary_status="failed",
            summary_error=str(exc),
        )

    return ManualSubmissionResponse(
        item=serialize_feed_item(summarized_item, get_action(db, summarized_item.id)),
        summary_status="succeeded",
    )
