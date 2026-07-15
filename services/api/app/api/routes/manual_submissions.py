from fastapi import APIRouter

from app.api.deps import DbSession
from app.core.config import get_settings
from app.db.models import NormalizedItem
from app.schemas.manual_submissions import ManualSubmissionRequest, ManualSubmissionResponse
from app.services.classification import ClassificationError, classify_feed_item
from app.services.feed_actions import get_action, serialize_feed_item
from app.services.manual_submissions import (
    create_manual_submission_result,
    enrich_manual_request_with_public_metadata,
)
from app.services.summarization import SummarizationError, summarize_feed_item

router = APIRouter()


@router.post("", response_model=ManualSubmissionResponse)
async def submit_manual_url(
    request: ManualSubmissionRequest,
    db: DbSession,
) -> ManualSubmissionResponse:
    request = await enrich_manual_request_with_public_metadata(request)
    save_result = create_manual_submission_result(db=db, request=request)
    item = save_result.item
    if not request.classify_with_llm and not request.summarize_with_llm:
        return ManualSubmissionResponse(
            item=item,
            created=save_result.created,
            updated_existing=save_result.updated_existing,
        )

    stored_item = db.get(NormalizedItem, item.id)
    if stored_item is None:
        return ManualSubmissionResponse(
            item=item,
            created=save_result.created,
            updated_existing=save_result.updated_existing,
            classification_status="failed" if request.classify_with_llm else "not_requested",
            classification_error=(
                "Manual item was stored but could not be reloaded for classification."
                if request.classify_with_llm
                else None
            ),
            summary_status="failed" if request.summarize_with_llm else "not_requested",
            summary_error=(
                "Manual item was stored but could not be reloaded for summarization."
                if request.summarize_with_llm
                else None
            ),
        )

    settings = get_settings()
    current_item = stored_item
    classification_status = "not_requested"
    classification_error = None
    summary_status = "not_requested"
    summary_error = None

    if request.classify_with_llm:
        try:
            current_item = await classify_feed_item(
                db=db,
                item=current_item,
                settings=settings,
            )
            classification_status = "succeeded"
        except ClassificationError as exc:
            classification_status = "failed"
            classification_error = str(exc)

    if request.summarize_with_llm:
        try:
            current_item = await summarize_feed_item(
                db=db,
                item=current_item,
                settings=settings,
            )
            summary_status = "succeeded"
        except SummarizationError as exc:
            summary_status = "failed"
            summary_error = str(exc)

    return ManualSubmissionResponse(
        item=serialize_feed_item(current_item, get_action(db, current_item.id)),
        created=save_result.created,
        updated_existing=save_result.updated_existing,
        classification_status=classification_status,
        classification_error=classification_error,
        summary_status=summary_status,
        summary_error=summary_error,
    )
