from collections.abc import Awaitable, Callable

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import NormalizedItem, UserItemAction
from app.schemas.llm import FeedProcessingError, FeedProcessingResponse
from app.services.classification import classify_feed_item
from app.services.feed_actions import (
    LOCAL_USER_ID,
    build_feed_module_conditions,
    normalize_feed_module_filter,
    normalize_source_names,
)
from app.services.preferences import get_user_preferences
from app.services.summarization import summarize_feed_item

LlmItemProcessor = Callable[[Session, NormalizedItem, Settings], Awaitable[NormalizedItem]]


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

    rows = query.order_by(
        UserItemAction.is_important.desc().nullslast(),
        NormalizedItem.importance_score.desc(),
        NormalizedItem.relevance_score.desc(),
        NormalizedItem.stock_impact_score.desc(),
        NormalizedItem.published_at.desc().nullslast(),
        NormalizedItem.created_at.desc(),
    ).limit(limit).all()
    return list(rows)


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
    summarizer: LlmItemProcessor = summarize_feed_item,
    classifier: LlmItemProcessor = classify_feed_item,
) -> FeedProcessingResponse:
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
