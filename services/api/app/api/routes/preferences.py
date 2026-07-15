from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.preferences import FeedbackProfileSummary, UserPreferences, UserPreferencesUpdate
from app.services.preferences import (
    get_feedback_profile_summary,
    get_user_preferences,
    update_user_preferences,
)

router = APIRouter()


@router.get("", response_model=UserPreferences)
async def read_preferences(db: DbSession) -> UserPreferences:
    return UserPreferences.model_validate(get_user_preferences(db))


@router.get("/feedback-profile", response_model=FeedbackProfileSummary)
async def read_feedback_profile(db: DbSession) -> FeedbackProfileSummary:
    return get_feedback_profile_summary(db)


@router.patch("", response_model=UserPreferences)
async def patch_preferences(
    payload: UserPreferencesUpdate,
    db: DbSession,
) -> UserPreferences:
    return UserPreferences.model_validate(update_user_preferences(db, payload))
