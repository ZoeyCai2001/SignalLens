import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes import llm as llm_routes
from app.core.config import Settings
from app.db.models import Base, NormalizedItem, UserItemAction
from app.schemas.llm import FeedProcessingRequest, FeedProcessingResponse
from app.services.llm_processing import (
    list_llm_processing_candidates,
    process_llm_batch_items,
    should_classify_item,
    should_summarize_item,
)


def test_list_llm_processing_candidates_skips_summarized_items_before_limit() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_item(1, summary_detailed="Already summarized", importance_score=1.0),
                make_item(2, importance_score=0.9),
                make_item(3, importance_score=0.8),
                make_item(4, importance_score=0.7),
            ]
        )
        db.add(UserItemAction(item_id=4, user_id="local", is_hidden=True))
        db.commit()

        candidates = list_llm_processing_candidates(
            db=db,
            limit=2,
            summarize=True,
            classify=False,
            skip_summarized=True,
        )

    assert [item.id for item in candidates] == [2, 3]


def test_list_llm_processing_candidates_skips_high_confidence_items_before_limit() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_item(1, importance_score=1.0, classification_confidence=0.92),
                make_item(2, importance_score=0.9, classification_confidence=0.62),
                make_item(3, importance_score=0.8, classification_confidence=0.55),
                make_item(4, importance_score=0.7, classification_confidence=0.45),
            ]
        )
        db.add(UserItemAction(item_id=4, user_id="local", is_hidden=True))
        db.commit()

        candidates = list_llm_processing_candidates(
            db=db,
            limit=2,
            summarize=False,
            classify=True,
            skip_classified=True,
            min_classification_confidence=0.7,
        )

    assert [item.id for item in candidates] == [2, 3]


def test_list_llm_processing_candidates_excludes_blocked_sources_before_limit() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_item(1, importance_score=1.0, source_name="Noisy Blog"),
                make_item(2, importance_score=0.9, source_name="Trusted Blog"),
                make_item(3, importance_score=0.8, source_name="Trusted Blog"),
            ]
        )
        db.commit()

        candidates = list_llm_processing_candidates(
            db=db,
            limit=2,
            summarize=True,
            classify=False,
            skip_summarized=True,
            blocked_sources=["Noisy Blog"],
        )

    assert [item.id for item in candidates] == [2, 3]


def make_item(
    item_id: int,
    summary_detailed: str | None = None,
    importance_score: float = 0,
    classification_confidence: float = 0.5,
    source_name: str = "Test",
) -> NormalizedItem:
    return NormalizedItem(
        id=item_id,
        raw_item_id=item_id,
        title=f"Item {item_id}",
        url=f"https://example.com/{item_id}",
        source_name=source_name,
        text="A relevant AI intelligence item.",
        importance_score=importance_score,
        classification_confidence=classification_confidence,
        summary_detailed=summary_detailed,
    )


def test_should_summarize_item_respects_existing_summary() -> None:
    item = make_item(1, summary_detailed="Already summarized")

    assert not should_summarize_item(item, skip_summarized=True)
    assert should_summarize_item(item, skip_summarized=False)


def test_should_classify_item_respects_confidence_threshold() -> None:
    confident = make_item(1, classification_confidence=0.85)
    uncertain = make_item(2, classification_confidence=0.62)

    assert not should_classify_item(
        confident,
        skip_classified=True,
        min_classification_confidence=0.7,
    )
    assert should_classify_item(
        uncertain,
        skip_classified=True,
        min_classification_confidence=0.7,
    )
    assert should_classify_item(
        confident,
        skip_classified=False,
        min_classification_confidence=0.7,
    )


@pytest.mark.anyio
async def test_process_llm_batch_items_summarizes_unsummarized_items() -> None:
    items = [make_item(1), make_item(2, summary_detailed="Existing")]
    summarized_ids: list[int] = []

    async def fake_summarizer(db, item: NormalizedItem, settings: Settings) -> NormalizedItem:
        summarized_ids.append(item.id)
        item.summary_detailed = "Generated summary"
        return item

    result = await process_llm_batch_items(
        db=None,
        settings=Settings(),
        items=items,
        requested_limit=2,
        summarize=True,
        classify=False,
        skip_summarized=True,
        summarizer=fake_summarizer,
    )

    assert summarized_ids == [1]
    assert result.candidates_seen == 2
    assert result.summarized_count == 1
    assert result.skipped_count == 1
    assert result.model_call_budget == 2
    assert result.model_calls_attempted == 1
    assert result.model_calls_succeeded == 1
    assert result.model_calls_failed == 0
    assert result.model_calls_skipped == 1
    assert result.model_calls_unused == 0
    assert result.item_ids == [1]
    assert result.errors == []


@pytest.mark.anyio
async def test_process_llm_batch_items_skips_high_confidence_classification() -> None:
    items = [
        make_item(1, classification_confidence=0.85),
        make_item(2, classification_confidence=0.62),
    ]
    classified_ids: list[int] = []

    async def fake_classifier(db, item: NormalizedItem, settings: Settings) -> NormalizedItem:
        classified_ids.append(item.id)
        item.classification_confidence = 0.9
        return item

    result = await process_llm_batch_items(
        db=None,
        settings=Settings(),
        items=items,
        requested_limit=2,
        summarize=False,
        classify=True,
        skip_classified=True,
        min_classification_confidence=0.7,
        classifier=fake_classifier,
    )

    assert classified_ids == [2]
    assert result.classified_count == 1
    assert result.skipped_count == 1
    assert result.model_call_budget == 2
    assert result.model_calls_attempted == 1
    assert result.model_calls_succeeded == 1
    assert result.model_calls_failed == 0
    assert result.model_calls_skipped == 1
    assert result.model_calls_unused == 0
    assert result.item_ids == [2]


@pytest.mark.anyio
async def test_process_llm_batch_items_captures_classification_errors() -> None:
    items = [make_item(1), make_item(2)]
    summarized_ids: list[int] = []

    async def fake_classifier(db, item: NormalizedItem, settings: Settings) -> NormalizedItem:
        if item.id == 1:
            raise RuntimeError("classification failed")
        item.category = "social_trend"
        return item

    async def fake_summarizer(db, item: NormalizedItem, settings: Settings) -> NormalizedItem:
        summarized_ids.append(item.id)
        item.summary_detailed = "Generated summary"
        return item

    result = await process_llm_batch_items(
        db=None,
        settings=Settings(),
        items=items,
        requested_limit=2,
        summarize=True,
        classify=True,
        skip_summarized=True,
        summarizer=fake_summarizer,
        classifier=fake_classifier,
    )

    assert summarized_ids == [1, 2]
    assert result.summarized_count == 2
    assert result.classified_count == 1
    assert result.model_call_budget == 4
    assert result.model_calls_attempted == 4
    assert result.model_calls_succeeded == 3
    assert result.model_calls_failed == 1
    assert result.model_calls_skipped == 0
    assert result.model_calls_unused == 0
    assert result.item_ids == [1, 2]
    assert len(result.errors) == 1
    assert result.errors[0].item_id == 1
    assert result.errors[0].stage == "classify"


@pytest.mark.anyio
async def test_process_feed_route_passes_blocked_sources(monkeypatch) -> None:
    monkeypatch.setattr(
        llm_routes,
        "get_settings",
        lambda: Settings(moonshot_api_key="test-key"),
    )
    monkeypatch.setattr(
        llm_routes,
        "get_user_preferences",
        lambda db: type("Preferences", (), {"blocked_sources": ["Noisy Blog"]})(),
    )

    async def fake_process_feed_with_llm(**kwargs) -> FeedProcessingResponse:
        assert kwargs["blocked_sources"] == ["Noisy Blog"]
        return FeedProcessingResponse(
            requested_limit=kwargs["limit"],
            candidates_seen=0,
            summarized_count=0,
            classified_count=0,
            skipped_count=0,
            item_ids=[],
            errors=[],
        )

    monkeypatch.setattr(llm_routes, "process_feed_with_llm", fake_process_feed_with_llm)

    result = await llm_routes.process_feed_items(
        request=FeedProcessingRequest(limit=3, summarize=True, classify=False),
        db=object(),
    )

    assert result.requested_limit == 3
