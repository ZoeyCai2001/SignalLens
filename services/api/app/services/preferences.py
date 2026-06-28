from sqlalchemy.orm import Session

from app.db.models import UserPreference
from app.schemas.preferences import RankingWeights, UserPreferencesUpdate
from app.services.feed_actions import LOCAL_USER_ID

DEFAULT_RANKING_WEIGHTS = RankingWeights()


def get_user_preferences(db: Session) -> UserPreference:
    preferences = (
        db.query(UserPreference)
        .filter(UserPreference.user_id == LOCAL_USER_ID)
        .one_or_none()
    )
    if preferences is not None:
        preferences.ranking_weights = normalize_ranking_weights(preferences.ranking_weights)
        preferences.preferred_sources = normalize_source_preferences(preferences.preferred_sources)
        preferences.blocked_sources = normalize_source_preferences(preferences.blocked_sources)
        return preferences

    preferences = UserPreference(
        user_id=LOCAL_USER_ID,
        ranking_weights=DEFAULT_RANKING_WEIGHTS.model_dump(),
        preferred_sources=[],
        blocked_sources=[],
    )
    db.add(preferences)
    db.commit()
    db.refresh(preferences)
    return preferences


def update_user_preferences(
    db: Session,
    payload: UserPreferencesUpdate,
) -> UserPreference:
    preferences = get_user_preferences(db)
    if payload.ranking_weights is not None:
        preferences.ranking_weights = normalize_ranking_weights(
            payload.ranking_weights.model_dump()
        )
    if payload.preferred_sources is not None:
        preferences.preferred_sources = normalize_source_preferences(payload.preferred_sources)
    if payload.blocked_sources is not None:
        preferences.blocked_sources = normalize_source_preferences(payload.blocked_sources)

    db.add(preferences)
    db.commit()
    db.refresh(preferences)
    return preferences


def normalize_ranking_weights(value: dict | None) -> dict[str, float]:
    if not value:
        return DEFAULT_RANKING_WEIGHTS.model_dump()
    return RankingWeights(**value).model_dump()


def normalize_source_preferences(value: list[str] | None) -> list[str]:
    if not value:
        return []
    seen = set()
    normalized_sources = []
    for source_name in value:
        normalized = str(source_name).strip()
        key = normalized.lower()
        if normalized and key not in seen:
            normalized_sources.append(normalized)
            seen.add(key)
    return normalized_sources
