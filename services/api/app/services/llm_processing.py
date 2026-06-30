import re
from collections.abc import Awaitable, Callable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import NormalizedItem, UserItemAction
from app.schemas.llm import FeedProcessingError, FeedProcessingResponse
from app.services.feed_actions import (
    LOCAL_USER_ID,
    build_feed_module_conditions,
    normalize_feed_module_filter,
    normalize_source_names,
)
from app.services.preferences import get_user_preferences

LlmItemProcessor = Callable[[Session, NormalizedItem, Settings], Awaitable[NormalizedItem]]

LLM_CANDIDATE_OVERFETCH_MULTIPLIER = 4
MAX_LLM_CANDIDATE_PREFETCH = 80
MIN_LLM_CANDIDATE_RELEVANCE = 0.35
MIN_LLM_CANDIDATE_IMPORTANCE = 0.5
MIN_LLM_CANDIDATE_STOCK_IMPACT = 0.5
TRACKING_QUERY_PARAMS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


async def process_feed_with_llm(
    db: Session,
    settings: Settings,
    limit: int,
    summarize: bool = True,
    classify: bool = False,
    skip_summarized: bool = True,
    skip_classified: bool = True,
    min_classification_confidence: float = 0.7,
    blocked_sources: list[str] | None = None,
    module: str | None = None,
) -> FeedProcessingResponse:
    if blocked_sources is None:
        blocked_sources = get_user_preferences(db).blocked_sources
    candidates = list_llm_processing_candidates(
        db=db,
        limit=limit,
        summarize=summarize,
        classify=classify,
        skip_summarized=skip_summarized,
        skip_classified=skip_classified,
        min_classification_confidence=min_classification_confidence,
        blocked_sources=blocked_sources,
        module=module,
    )
    return await process_llm_batch_items(
        db=db,
        settings=settings,
        items=candidates,
        requested_limit=limit,
        summarize=summarize,
        classify=classify,
        skip_summarized=skip_summarized,
        skip_classified=skip_classified,
        min_classification_confidence=min_classification_confidence,
    )


def list_llm_processing_candidates(
    db: Session,
    limit: int,
    summarize: bool = True,
    classify: bool = False,
    skip_summarized: bool = True,
    skip_classified: bool = True,
    min_classification_confidence: float = 0.7,
    blocked_sources: list[str] | None = None,
    module: str | None = None,
) -> list[NormalizedItem]:
    blocked_source_names = normalize_source_names(blocked_sources)
    module_filter = normalize_feed_module_filter(module)
    query = db.query(NormalizedItem).outerjoin(
        UserItemAction,
        (UserItemAction.item_id == NormalizedItem.id)
        & (UserItemAction.user_id == LOCAL_USER_ID),
    )
    query = query.filter((UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None)))
    if blocked_source_names:
        query = query.filter(~NormalizedItem.source_name.in_(blocked_source_names))
    module_conditions = build_feed_module_conditions(module_filter)
    if module_conditions:
        query = query.filter(or_(*module_conditions))
    query = query.filter(
        or_(
            NormalizedItem.relevance_score >= MIN_LLM_CANDIDATE_RELEVANCE,
            NormalizedItem.importance_score >= MIN_LLM_CANDIDATE_IMPORTANCE,
            NormalizedItem.stock_impact_score >= MIN_LLM_CANDIDATE_STOCK_IMPACT,
            UserItemAction.is_important.is_(True),
        )
    )

    candidate_filters = []
    if summarize and skip_summarized:
        candidate_filters.append(
            or_(
                NormalizedItem.summary_detailed.is_(None),
                NormalizedItem.summary_detailed == "",
            )
        )
    if classify and skip_classified:
        candidate_filters.append(
            NormalizedItem.classification_confidence < min_classification_confidence
        )

    if candidate_filters:
        query = query.filter(or_(*candidate_filters))

    prefetch_limit = min(
        MAX_LLM_CANDIDATE_PREFETCH,
        max(limit, limit * LLM_CANDIDATE_OVERFETCH_MULTIPLIER),
    )
    rows = query.order_by(
        UserItemAction.is_important.desc().nullslast(),
        NormalizedItem.importance_score.desc(),
        NormalizedItem.relevance_score.desc(),
        NormalizedItem.stock_impact_score.desc(),
        NormalizedItem.published_at.desc().nullslast(),
        NormalizedItem.created_at.desc(),
    ).limit(prefetch_limit).all()
    return dedupe_llm_processing_candidates(list(rows), limit=limit)


def dedupe_llm_processing_candidates(
    items: list[NormalizedItem],
    limit: int,
) -> list[NormalizedItem]:
    selected: list[NormalizedItem] = []
    seen_keys: set[str] = set()

    for item in items:
        keys = llm_candidate_deduplication_keys(item)
        if keys and seen_keys.intersection(keys):
            continue
        selected.append(item)
        seen_keys.update(keys)
        if len(selected) >= limit:
            break

    return selected


def llm_candidate_deduplication_keys(item: NormalizedItem) -> set[str]:
    keys: set[str] = set()
    normalized_url = canonical_llm_candidate_url(item.url)
    if normalized_url:
        keys.add(f"url:{normalized_url}")
    normalized_title = normalize_llm_candidate_title(item.title)
    if normalized_title:
        keys.add(f"title:{normalized_title}")
    return keys


def canonical_llm_candidate_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parsed = urlsplit(url.strip())
    except ValueError:
        return url.strip().casefold() or None
    if not parsed.scheme and not parsed.netloc:
        return url.strip().casefold() or None
    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.casefold() not in TRACKING_QUERY_PARAMS
    ]
    normalized = urlunsplit(
        (
            parsed.scheme.casefold(),
            parsed.netloc.casefold(),
            parsed.path.rstrip("/"),
            urlencode(sorted(filtered_query)),
            "",
        )
    )
    return normalized or None


def normalize_llm_candidate_title(title: str | None) -> str | None:
    normalized = re.sub(r"\s+", " ", title or "").strip().casefold()
    return normalized if len(normalized) >= 20 else None


async def process_llm_batch_items(
    db: Session,
    settings: Settings,
    items: list[NormalizedItem],
    requested_limit: int,
    summarize: bool = True,
    classify: bool = False,
    skip_summarized: bool = True,
    skip_classified: bool = True,
    min_classification_confidence: float = 0.7,
    summarizer: LlmItemProcessor | None = None,
    classifier: LlmItemProcessor | None = None,
) -> FeedProcessingResponse:
    if summarize and summarizer is None:
        from app.services.summarization import summarize_feed_item

        summarizer = summarize_feed_item
    if classify and classifier is None:
        from app.services.classification import classify_feed_item

        classifier = classify_feed_item

    summarized_count = 0
    classified_count = 0
    skipped_count = 0
    model_calls_attempted = 0
    processed_item_ids: list[int] = []
    errors: list[FeedProcessingError] = []

    for item in items:
        touched = False
        if classify and should_classify_item(
            item,
            skip_classified=skip_classified,
            min_classification_confidence=min_classification_confidence,
        ):
            assert classifier is not None
            try:
                model_calls_attempted += 1
                item = await classifier(db, item, settings)
                classified_count += 1
                touched = True
            except Exception as exc:
                errors.append(
                    FeedProcessingError(item_id=item.id, stage="classify", error=str(exc))
                )
        elif classify:
            skipped_count += 1

        if summarize and should_summarize_item(item, skip_summarized=skip_summarized):
            assert summarizer is not None
            try:
                model_calls_attempted += 1
                item = await summarizer(db, item, settings)
                summarized_count += 1
                touched = True
            except Exception as exc:
                errors.append(
                    FeedProcessingError(item_id=item.id, stage="summarize", error=str(exc))
                )
        elif summarize:
            skipped_count += 1

        if touched:
            processed_item_ids.append(item.id)

    enabled_operation_count = int(summarize) + int(classify)
    model_call_budget = requested_limit * enabled_operation_count
    model_calls_succeeded = summarized_count + classified_count
    model_calls_failed = len(errors)
    model_calls_unused = max(0, model_call_budget - model_calls_attempted - skipped_count)

    return FeedProcessingResponse(
        requested_limit=requested_limit,
        candidates_seen=len(items),
        summarized_count=summarized_count,
        classified_count=classified_count,
        skipped_count=skipped_count,
        model_call_budget=model_call_budget,
        model_calls_attempted=model_calls_attempted,
        model_calls_succeeded=model_calls_succeeded,
        model_calls_failed=model_calls_failed,
        model_calls_skipped=skipped_count,
        model_calls_unused=model_calls_unused,
        item_ids=processed_item_ids,
        errors=errors,
    )


def should_summarize_item(item: NormalizedItem, skip_summarized: bool) -> bool:
    return not skip_summarized or not bool(item.summary_detailed)


def should_classify_item(
    item: NormalizedItem,
    skip_classified: bool,
    min_classification_confidence: float,
) -> bool:
    return (
        not skip_classified
        or item.classification_confidence < min_classification_confidence
    )
