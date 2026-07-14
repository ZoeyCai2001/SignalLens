import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes import llm as llm_routes
from app.core.config import Settings
from app.db.models import Base, NormalizedItem, UserItemAction
from app.schemas.llm import FeedProcessingRequest, FeedProcessingResponse
from app.services.llm_processing import (
    build_llm_candidate_preview,
    canonical_llm_candidate_url,
    dedupe_llm_processing_candidates,
    list_llm_processing_candidates,
    normalize_llm_candidate_title,
    preview_llm_batch_model_calls,
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


def test_list_llm_processing_candidates_filters_module_before_limit() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_item(1, importance_score=1.0, category="technical_trend"),
                make_item(2, importance_score=0.9, category="research"),
                make_item(3, importance_score=0.8, category="research"),
            ]
        )
        db.commit()

        candidates = list_llm_processing_candidates(
            db=db,
            limit=2,
            summarize=True,
            classify=False,
            skip_summarized=True,
            module="research",
        )

    assert [item.id for item in candidates] == [2, 3]


def test_list_llm_processing_candidates_filters_stock_module_entities() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_item(1, importance_score=1.0, category="technical_trend"),
                make_item(
                    2,
                    importance_score=0.9,
                    category="technical_trend",
                    tickers=["MU"],
                    stock_impact_score=0.6,
                ),
            ]
        )
        db.commit()

        candidates = list_llm_processing_candidates(
            db=db,
            limit=2,
            summarize=True,
            classify=False,
            skip_summarized=True,
            module="stocks",
        )

    assert [item.id for item in candidates] == [2]


def test_list_llm_processing_candidates_deduplicates_before_limit() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_item(
                    1,
                    title="OpenAI releases a new agent workflow for developers",
                    url="https://example.com/agent-workflow?utm_source=newsletter",
                    importance_score=1.0,
                ),
                make_item(
                    2,
                    title="OpenAI releases a new agent workflow for developers",
                    url="https://example.com/agent-workflow?utm_medium=social",
                    importance_score=0.95,
                ),
                make_item(
                    3,
                    title="Anthropic publishes a model routing benchmark",
                    url="https://example.com/model-routing",
                    importance_score=0.8,
                ),
            ]
        )
        db.commit()

        candidates = list_llm_processing_candidates(
            db=db,
            limit=2,
            summarize=True,
            classify=False,
            skip_summarized=True,
        )

    assert [item.id for item in candidates] == [1, 3]


def test_list_llm_processing_candidates_filters_low_signal_items_before_limit() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_item(1, importance_score=0.8, relevance_score=0.2),
                make_item(2, importance_score=0.1, relevance_score=0.8),
                make_item(3, importance_score=0.1, relevance_score=0.1),
                make_item(4, importance_score=0.1, relevance_score=0.1),
                make_item(5, importance_score=0.1, relevance_score=0.1, stock_impact_score=0.7),
            ]
        )
        db.add(UserItemAction(item_id=4, user_id="local", is_important=True))
        db.commit()

        candidates = list_llm_processing_candidates(
            db=db,
            limit=5,
            summarize=True,
            classify=False,
            skip_summarized=True,
        )

    assert [item.id for item in candidates] == [4, 1, 2, 5]


def test_dedupe_llm_processing_candidates_keeps_distinct_related_items() -> None:
    items = [
        make_item(
            1,
            title="OpenAI releases a new agent workflow for developers",
            url="https://example.com/openai-agent",
        ),
        make_item(
            2,
            title="Developers debate OpenAI agent workflows on Hacker News",
            url="https://news.ycombinator.com/item?id=123",
        ),
    ]

    candidates = dedupe_llm_processing_candidates(items, limit=2)

    assert [item.id for item in candidates] == [1, 2]


def test_llm_candidate_deduplication_helpers_normalize_tracking_noise() -> None:
    assert (
        canonical_llm_candidate_url(
            "https://Example.com/path/?utm_source=newsletter&b=2&a=1#section"
        )
        == "https://example.com/path?a=1&b=2"
    )
    assert normalize_llm_candidate_title("  OpenAI   launches   agent workflows  ") == (
        "openai launches agent workflows"
    )
    assert normalize_llm_candidate_title("Short") is None


def make_item(
    item_id: int,
    title: str | None = None,
    url: str | None = None,
    summary_detailed: str | None = None,
    importance_score: float = 0,
    relevance_score: float = 0.8,
    classification_confidence: float = 0.5,
    source_name: str = "Test",
    category: str = "technical_trend",
    tickers: list[str] | None = None,
    products: list[str] | None = None,
    stock_impact_score: float = 0,
) -> NormalizedItem:
    return NormalizedItem(
        id=item_id,
        raw_item_id=item_id,
        title=title or f"Item {item_id}",
        url=url or f"https://example.com/{item_id}",
        source_name=source_name,
        text="A relevant AI intelligence item.",
        category=category,
        tickers=tickers or [],
        products=products or [],
        importance_score=importance_score,
        relevance_score=relevance_score,
        classification_confidence=classification_confidence,
        stock_impact_score=stock_impact_score,
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


def test_preview_llm_batch_model_calls_counts_planned_and_skipped_calls() -> None:
    items = [
        make_item(1, classification_confidence=0.85, summary_detailed="Existing"),
        make_item(2, classification_confidence=0.62),
    ]

    planned_model_calls, skipped_count = preview_llm_batch_model_calls(
        items=items,
        summarize=True,
        classify=True,
        skip_summarized=True,
        skip_classified=True,
        min_classification_confidence=0.7,
    )

    assert planned_model_calls == 2
    assert skipped_count == 2


def test_build_llm_candidate_preview_lists_planned_and_skipped_operations() -> None:
    item = make_item(
        1,
        title="Existing high-confidence summary",
        summary_detailed="Existing summary",
        classification_confidence=0.9,
        source_name="Curated Source",
        category="research",
    )

    preview = build_llm_candidate_preview(
        item=item,
        summarize=True,
        classify=True,
        skip_summarized=True,
        skip_classified=True,
        min_classification_confidence=0.7,
    )

    assert preview.item_id == 1
    assert preview.title == "Existing high-confidence summary"
    assert preview.source_name == "Curated Source"
    assert preview.category == "research"
    assert preview.planned_operations == []
    assert preview.skipped_operations == ["classify", "summarize"]


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
async def test_process_llm_batch_items_dry_run_reports_plan_without_model_calls() -> None:
    items = [
        make_item(1, classification_confidence=0.85, summary_detailed="Existing"),
        make_item(2, classification_confidence=0.62),
    ]
    called_processors: list[int] = []

    async def fake_processor(db, item: NormalizedItem, settings: Settings) -> NormalizedItem:
        called_processors.append(item.id)
        return item

    result = await process_llm_batch_items(
        db=None,
        settings=Settings(),
        items=items,
        requested_limit=2,
        summarize=True,
        classify=True,
        dry_run=True,
        skip_summarized=True,
        skip_classified=True,
        min_classification_confidence=0.7,
        summarizer=fake_processor,
        classifier=fake_processor,
    )

    assert called_processors == []
    assert result.dry_run is True
    assert result.candidates_seen == 2
    assert result.planned_model_calls == 2
    assert result.summarized_count == 0
    assert result.classified_count == 0
    assert result.skipped_count == 2
    assert result.model_call_budget == 4
    assert result.model_calls_attempted == 0
    assert result.model_calls_succeeded == 0
    assert result.model_calls_failed == 0
    assert result.model_calls_skipped == 2
    assert result.model_calls_unused == 0
    assert result.item_ids == [1, 2]
    assert [preview.item_id for preview in result.candidate_previews] == [1, 2]
    assert result.candidate_previews[0].planned_operations == []
    assert result.candidate_previews[0].skipped_operations == ["classify", "summarize"]
    assert result.candidate_previews[1].planned_operations == ["classify", "summarize"]
    assert result.candidate_previews[1].skipped_operations == []
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
        assert kwargs["module"] is None
        assert kwargs["dry_run"] is False
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


@pytest.mark.anyio
async def test_process_feed_route_passes_module_filter(monkeypatch) -> None:
    monkeypatch.setattr(
        llm_routes,
        "get_settings",
        lambda: Settings(moonshot_api_key="test-key"),
    )
    monkeypatch.setattr(
        llm_routes,
        "get_user_preferences",
        lambda db: type("Preferences", (), {"blocked_sources": []})(),
    )

    async def fake_process_feed_with_llm(**kwargs) -> FeedProcessingResponse:
        assert kwargs["module"] == "research"
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
        request=FeedProcessingRequest(limit=3, summarize=True, classify=False, module="research"),
        db=object(),
    )

    assert result.requested_limit == 3


@pytest.mark.anyio
async def test_process_feed_route_passes_dry_run(monkeypatch) -> None:
    monkeypatch.setattr(
        llm_routes,
        "get_settings",
        lambda: Settings(moonshot_api_key=None),
    )
    monkeypatch.setattr(
        llm_routes,
        "get_user_preferences",
        lambda db: type("Preferences", (), {"blocked_sources": []})(),
    )

    async def fake_process_feed_with_llm(**kwargs) -> FeedProcessingResponse:
        assert kwargs["dry_run"] is True
        return FeedProcessingResponse(
            requested_limit=kwargs["limit"],
            dry_run=True,
            candidates_seen=0,
            summarized_count=0,
            classified_count=0,
            skipped_count=0,
            item_ids=[],
            errors=[],
        )

    monkeypatch.setattr(llm_routes, "process_feed_with_llm", fake_process_feed_with_llm)

    result = await llm_routes.process_feed_items(
        request=FeedProcessingRequest(
            limit=3,
            summarize=True,
            classify=False,
            dry_run=True,
        ),
        db=object(),
    )

    assert result.dry_run is True


@pytest.mark.anyio
async def test_process_feed_route_requires_key_for_real_model_calls(monkeypatch) -> None:
    monkeypatch.setattr(
        llm_routes,
        "get_settings",
        lambda: Settings(moonshot_api_key=None),
    )

    with pytest.raises(llm_routes.HTTPException) as exc_info:
        await llm_routes.process_feed_items(
            request=FeedProcessingRequest(
                limit=3,
                summarize=True,
                classify=False,
                dry_run=False,
            ),
            db=object(),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "MOONSHOT_API_KEY is not configured."
