from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.manual_submissions import ManualSubmissionRequest, ManualSubmissionResponse
from app.services.manual_submissions import create_manual_submission

router = APIRouter()


@router.post("", response_model=ManualSubmissionResponse)
async def submit_manual_url(
    request: ManualSubmissionRequest,
    db: DbSession,
) -> ManualSubmissionResponse:
    item = create_manual_submission(db=db, request=request)
    return ManualSubmissionResponse(item=item)
