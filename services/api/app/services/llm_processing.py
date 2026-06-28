from collections.abc import Awaitable, Callable

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import NormalizedItem, UserItemAction
from app.schemas.llm import FeedProcessingError, FeedProcessingResponse
from app.services.classification import classify_feed_item
from app.services.feed_actions import LOCAL_USER_ID
from app.services.summarization import summarize_feed_item

LlmItemProcessor = Callable[[Session, NormalizedItem, Settings], Awaitable[NormalizedItem]]


async def process_feed_with_llm(
    db: Session,
    settings: Settings,
    limit: int,
    summarize: bool = True,
    classify: bool = False,
    skip_summarized: bool = True,
) -> FeedProcessingResponse:
    candidates = list_llm_processing_candidates(
        db=db,
        limit=limit,
        summarize=summarize,
        classify=classify,
        skip_summarized=skip_summarized,
    )
    return await process_llm_batch_items(
        db=db,
        settings=settings,
        items=candidates,
        requested_limit=limit,
        summarize=summarize,
        classify=classify,
        skip_summarized=skip_summarized,
    )


def list_llm_processing_candidates(
    db: Session,
    limit: int,
    summarize: bool = True,
    classify: bool = False,
    skip_summarized: bool = True,
) -> list[NormalizedItem]:
    query = db.query(NormalizedItem).outerjoin(
        UserItemAction,
        (UserItemAction.item_id == NormalizedItem.id)
        & (UserItemAction.user_id == LOCAL_USER_ID),
    )
    query = query.filter((UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None)))
    if summarize and skip_summarized and not classify:
        query = query.filter(
            or_(
                NormalizedItem.summary_detailed.is_(None),
                NormalizedItem.summary_detailed == "",
            )
        )

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
    summarizer: LlmItemProcessor = summarize_feed_item,
    classifier: LlmItemProcessor = classify_feed_item,
) -> FeedProcessingResponse:
    summarized_count = 0
    classified_count = 0
    skipped_count = 0
    processed_item_ids: list[int] = []
    errors: list[FeedProcessingError] = []

    for item in items:
        touched = False
        if classify:
            try:
                item = await classifier(db, item, settings)
                classified_count += 1
                touched = True
            except Exception as exc:
                errors.append(
                    FeedProcessingError(item_id=item.id, stage="classify", error=str(exc))
                )

        if summarize and should_summarize_item(item, skip_summarized=skip_summarized):
            try:
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

    return FeedProcessingResponse(
        requested_limit=requested_limit,
        candidates_seen=len(items),
        summarized_count=summarized_count,
        classified_count=classified_count,
        skipped_count=skipped_count,
        item_ids=processed_item_ids,
        errors=errors,
    )


def should_summarize_item(item: NormalizedItem, skip_summarized: bool) -> bool:
    return not skip_summarized or not bool(item.summary_detailed)
