from sqlalchemy.orm import Session

from app.db.models import UserItemAction, UserPreference
from app.schemas.preferences import FeedbackProfileSummary, RankingWeights, UserPreferencesUpdate
from app.services.feed_actions import LOCAL_USER_ID, build_feed_interest_profile

DEFAULT_RANKING_WEIGHTS = RankingWeights()
FEEDBACK_PROFILE_LIMIT = 12


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
        preferences.language_preferences = normalize_language_preferences(
            getattr(preferences, "language_preferences", [])
        )
        return preferences

    preferences = UserPreference(
        user_id=LOCAL_USER_ID,
        ranking_weights=DEFAULT_RANKING_WEIGHTS.model_dump(),
        preferred_sources=[],
        blocked_sources=[],
        language_preferences=[],
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
    if payload.language_preferences is not None:
        preferences.language_preferences = normalize_language_preferences(
            payload.language_preferences
        )

    db.add(preferences)
    db.commit()
    db.refresh(preferences)
    return preferences


def get_feedback_profile_summary(db: Session) -> FeedbackProfileSummary:
    profile = build_feed_interest_profile(db)
    counts = count_user_item_feedback(db)
    return FeedbackProfileSummary(
        user_id=LOCAL_USER_ID,
        saved_count=counts["saved"],
        hidden_count=counts["hidden"],
        important_count=counts["important"],
        useful_count=counts["useful"],
        not_useful_count=counts["not_useful"],
        watchlist_symbols=limited_sorted_values(profile.symbols),
        watchlist_terms=limited_sorted_values(profile.terms),
        liked_sources=limited_sorted_values(profile.liked_sources),
        disliked_sources=limited_sorted_values(profile.disliked_sources),
        liked_symbols=limited_sorted_values(profile.liked_symbols),
        disliked_symbols=limited_sorted_values(profile.disliked_symbols),
        liked_terms=limited_sorted_values(profile.liked_terms),
        disliked_terms=limited_sorted_values(profile.disliked_terms),
    )


def count_user_item_feedback(db: Session) -> dict[str, int]:
    actions = db.query(UserItemAction).filter(UserItemAction.user_id == LOCAL_USER_ID).all()
    counts = {
        "saved": 0,
        "hidden": 0,
        "important": 0,
        "useful": 0,
        "not_useful": 0,
    }
    for action in actions:
        if action.is_saved:
            counts["saved"] += 1
        if action.is_hidden:
            counts["hidden"] += 1
        if action.is_important:
            counts["important"] += 1
        if action.usefulness_feedback == "useful":
            counts["useful"] += 1
        elif action.usefulness_feedback == "not_useful":
            counts["not_useful"] += 1
    return counts


def limited_sorted_values(values: frozenset[str] | set[str]) -> list[str]:
    return sorted(value for value in values if value)[:FEEDBACK_PROFILE_LIMIT]


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


def normalize_language_preferences(value: list[str] | None) -> list[str]:
    if not value:
        return []
    seen = set()
    normalized_languages = []
    for language in value:
        normalized = str(language).strip().lower()
        if normalized in {"english", "en-us", "en_us"}:
            normalized = "en"
        elif normalized in {"chinese", "zh-cn", "zh_cn", "cn"}:
            normalized = "zh"
        if normalized and normalized not in seen:
            normalized_languages.append(normalized)
            seen.add(normalized)
    return normalized_languages
