import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes import manual_submissions as manual_submission_routes
from app.db.models import Base, NormalizedItem, RawItem, Source
from app.schemas.feed import FeedItem
from app.schemas.manual_submissions import ManualSubmissionRequest
from app.services.classification import ClassificationError
from app.services.manual_submissions import (
    ManualSubmissionSaveResult,
    create_manual_normalized_item,
    create_manual_submission_result,
    create_raw_manual_item,
    enrich_manual_normalized_item,
    first_sentence,
    reset_manual_normalized_item,
    resolve_manual_source_name,
    resolve_manual_title,
)
from app.services.summarization import SummarizationError


def test_manual_fallback_normalization_keeps_user_submission() -> None:
    source = Source(
        id=1,
        name="Manual Submission",
        type="manual",
        access_method="manual_submission",
        enabled=True,
        priority=5,
    )
    raw = RawItem(
        id=1,
        source_id=1,
        external_id="https://example.com/product",
        url="https://example.com/product",
        raw_title="Interesting AI product",
        raw_text="A user-submitted product note.",
        raw_metadata={},
        content_hash="abc",
    )

    item = create_manual_normalized_item(raw=raw, source=source)

    assert item.category == "manual_submission"
    assert item.summary_short == (
        "Manual submission: Interesting AI product - A user-submitted product note."
    )
    assert item.source_name == "Manual Submission"


def test_manual_enrichment_routes_ai_product_submissions() -> None:
    source = make_source()
    raw = make_raw(
        title="AgentDesk: AI agents for product teams",
        text="AgentDesk launches AI workflow agents for product managers.",
    )
    item = create_manual_normalized_item(raw=raw, source=source)

    enrich_manual_normalized_item(item, raw)

    assert item.category == "product"
    assert item.subcategory == "product_business"
    assert item.companies == []
    assert item.products == ["AgentDesk"]
    assert "agent" in item.topics
    assert item.summary_short == (
        "Manual submission: AgentDesk: AI agents for product teams - "
        "AgentDesk launches AI workflow agents for product managers."
    )
    assert item.importance_score > 0.3


def test_manual_enrichment_detects_known_ai_products() -> None:
    source = make_source()
    raw = make_raw(
        title="Claude and Cursor workflow update",
        text="Claude and Cursor improve AI coding agent workflows.",
    )
    item = create_manual_normalized_item(raw=raw, source=source)

    enrich_manual_normalized_item(item, raw)

    assert item.products == ["Claude", "Cursor"]


def test_manual_enrichment_routes_stock_submissions_with_tickers() -> None:
    source = make_source()
    raw = make_raw(
        title="MRVL AI data center demand update",
        text="Marvell discussed AI data center custom silicon revenue and LLM inference demand.",
    )
    item = create_manual_normalized_item(raw=raw, source=source)

    enrich_manual_normalized_item(item, raw)

    assert item.category == "stock_company_event"
    assert item.subcategory == "manual_stock_signal"
    assert item.tickers == ["MRVL"]
    assert item.companies == ["Marvell Technology"]
    assert item.stock_impact_score == 0.35
    assert "MRVL" in item.why_it_matters


def test_manual_enrichment_detects_private_ai_lab_companies() -> None:
    source = make_source()
    raw = make_raw(
        title="OpenAI agent update",
        text="OpenAI and Anthropic both discussed Claude and ChatGPT enterprise agents.",
    )
    item = create_manual_normalized_item(raw=raw, source=source)

    enrich_manual_normalized_item(item, raw)

    assert item.category == "technical_trend"
    assert item.companies == ["Anthropic", "OpenAI"]
    assert item.tickers == []


def test_manual_enrichment_prefers_chinese_social_context() -> None:
    source = make_source()
    raw = make_raw(
        title="小红书 AI写真工具 workflow",
        text="小红书用户讨论人工智能修图和 AI photo tools viral editing workflows.",
    )
    item = create_manual_normalized_item(raw=raw, source=source)

    enrich_manual_normalized_item(item, raw)

    assert item.category == "social_trend"
    assert item.subcategory == "manual_social_signal"
    assert item.language == "zh"
    assert "AI photo tool" in item.products
    assert item.summary_detailed is not None
    assert "English summary:" in item.summary_detailed
    assert "Product/use case: AI photo tool" in item.summary_detailed
    assert "Manual source: user-submitted public URL" in item.summary_detailed


def test_manual_submission_extracts_public_social_engagement_counts() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        result = create_manual_submission_result(
            db=db,
            request=ManualSubmissionRequest(
                title="小红书 AI写真工具 workflow",
                url="https://example.com/xhs-ai-photo",
                source_name="Xiaohongshu Manual Watch",
                text=(
                    "小红书用户讨论人工智能修图。 "
                    "likes: 1,800; collects: 500; comments: 260; "
                    "reposts: 60; views: 88,000."
                ),
            ),
        )

        raw = db.query(RawItem).one()

    assert raw.raw_metadata["likes"] == 1800
    assert raw.raw_metadata["collects"] == 500
    assert raw.raw_metadata["comments_count"] == 260
    assert raw.raw_metadata["reposts"] == 60
    assert raw.raw_metadata["views"] == 88000
    assert result.item.category == "social_trend"
    assert result.item.social_signal_score == 1


def test_manual_submission_structured_engagement_overrides_pasted_counts() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        result = create_manual_submission_result(
            db=db,
            request=ManualSubmissionRequest(
                title="Xiaohongshu AI note",
                url="https://example.com/manual-social-note",
                source_name="Xiaohongshu Manual Watch",
                text="A pasted note with likes: 3 and views: 10.",
                public_engagement={
                    "likes": 1200,
                    "comments_count": 80,
                    "collects": 420,
                    "reposts": 24,
                    "views": 33000,
                },
            ),
        )

        raw = db.query(RawItem).one()

    assert raw.raw_metadata["likes"] == 1200
    assert raw.raw_metadata["comments_count"] == 80
    assert raw.raw_metadata["collects"] == 420
    assert raw.raw_metadata["reposts"] == 24
    assert raw.raw_metadata["views"] == 33000
    assert result.item.category == "social_trend"
    assert result.item.social_signal_score > 0.8


def test_manual_enrichment_keeps_non_ai_submission_as_manual() -> None:
    source = make_source()
    raw = make_raw(
        title="Personal reading list",
        text="A note about weekend reading and travel plans.",
    )
    item = create_manual_normalized_item(raw=raw, source=source)

    enrich_manual_normalized_item(item, raw)

    assert item.category == "manual_submission"
    assert item.tickers == []
    assert item.topics == []


def test_manual_resubmission_resets_stale_ai_metadata() -> None:
    source = make_source()
    raw = make_raw(
        title="MRVL AI data center demand update",
        text="Marvell discussed AI data center custom silicon revenue and LLM inference demand.",
    )
    item = create_manual_normalized_item(raw=raw, source=source)
    enrich_manual_normalized_item(item, raw)

    assert item.category == "stock_company_event"
    assert item.tickers == ["MRVL"]
    assert item.companies == ["Marvell Technology"]

    raw.raw_title = "Personal reading list"
    raw.raw_text = "A note about weekend reading and travel plans."
    item.summary_detailed = "Old LLM-generated summary."

    reset_manual_normalized_item(item, raw, source)
    enrich_manual_normalized_item(item, raw)

    assert item.category == "manual_submission"
    assert item.subcategory == "user_submitted_url"
    assert item.tickers == []
    assert item.companies == []
    assert item.products == []
    assert item.topics == []
    assert item.classification_confidence == 0.5
    assert item.relevance_score == 0.3
    assert item.stock_impact_score == 0
    assert item.summary_short == (
        "Manual submission: Personal reading list - "
        "A note about weekend reading and travel plans."
    )
    assert item.summary_detailed is None


def test_first_sentence_handles_chinese_punctuation() -> None:
    assert first_sentence("国产大模型应用正在升温。第二句。") == "国产大模型应用正在升温。"


def test_manual_submission_title_can_be_inferred_from_text() -> None:
    request = ManualSubmissionRequest(
        url="https://example.com/agent-note",
        text="OpenAI released a new agent workflow. More context follows.",
    )

    assert resolve_manual_title(request) == "OpenAI released a new agent workflow."


def test_manual_submission_title_can_be_inferred_from_url() -> None:
    request = ManualSubmissionRequest(url="https://example.com/posts/ai-agent-workflow")

    assert resolve_manual_title(request) == "example.com: ai agent workflow"


def test_manual_submission_blank_title_is_treated_as_missing() -> None:
    request = ManualSubmissionRequest(
        title="  ",
        url="https://example.com/launch",
        text="Claude workflow update.",
    )

    assert request.title is None
    assert resolve_manual_title(request) == "Claude workflow update."


def test_manual_submission_source_name_can_be_inferred_from_known_url() -> None:
    assert (
        resolve_manual_source_name(
            ManualSubmissionRequest(url="https://github.com/modelcontextprotocol/servers")
        )
        == "GitHub"
    )
    assert (
        resolve_manual_source_name(
            ManualSubmissionRequest(url="https://huggingface.co/spaces/example/demo")
        )
        == "Hugging Face"
    )
    assert (
        resolve_manual_source_name(
            ManualSubmissionRequest(url="https://news.ycombinator.com/item?id=123")
        )
        == "Hacker News"
    )


def test_manual_submission_source_name_can_be_inferred_from_generic_domain() -> None:
    request = ManualSubmissionRequest(url="https://blog.example-ai.com/posts/agent-workflow")

    assert resolve_manual_source_name(request) == "Example AI"


def test_manual_submission_preserves_custom_source_name() -> None:
    request = ManualSubmissionRequest(
        url="https://example.com/posts/agent-workflow",
        source_name="My Research Inbox",
    )

    assert resolve_manual_source_name(request) == "My Research Inbox"


def test_manual_submission_result_uses_inferred_source_name() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        result = create_manual_submission_result(
            db=db,
            request=ManualSubmissionRequest(
                title="MCP server repository",
                url="https://github.com/modelcontextprotocol/servers",
                text="GitHub repository for MCP server integrations.",
            ),
        )

        source = db.query(Source).one()

    assert result.item.source_name == "GitHub"
    assert source.name == "GitHub"
    assert source.base_url == "https://github.com"


def test_manual_resubmission_updates_existing_url_item() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        source = make_source()
        db.add(source)
        db.flush()

        first = create_raw_manual_item(
            db=db,
            source=source,
            request=ManualSubmissionRequest(
                title="Old title",
                url="https://example.com/agent-note",
                text="Old note.",
            ),
        )
        db.add(
            NormalizedItem(
                raw_item_id=first.id,
                title=first.raw_title,
                url=first.url,
                source_name=source.name,
                text=first.raw_text,
            )
        )
        db.commit()

        second = create_raw_manual_item(
            db=db,
            source=source,
            request=ManualSubmissionRequest(
                title="Updated agent note",
                url="https://example.com/agent-note",
                text="Updated note about OpenAI agents.",
            ),
        )
        db.commit()

        raw_items = db.query(RawItem).all()
        assert second.id == first.id
        assert len(raw_items) == 1
        assert raw_items[0].raw_title == "Updated agent note"
        assert raw_items[0].raw_text == "Updated note about OpenAI agents."
        assert raw_items[0].normalized_item.title == "Updated agent note"
        assert raw_items[0].normalized_item.text == "Updated note about OpenAI agents."


def test_manual_submission_resubmits_old_generic_source_as_inferred_update() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        old_source = make_source()
        db.add(old_source)
        db.flush()

        first = create_raw_manual_item(
            db=db,
            source=old_source,
            request=ManualSubmissionRequest(
                title="Old GitHub note",
                url="https://github.com/example/agent",
                text="Old note.",
            ),
        )
        db.add(
            NormalizedItem(
                raw_item_id=first.id,
                title=first.raw_title,
                url=first.url,
                source_name=old_source.name,
                text=first.raw_text,
            )
        )
        db.commit()

        result = create_manual_submission_result(
            db=db,
            request=ManualSubmissionRequest(
                title="Updated GitHub note",
                url="https://github.com/example/agent?utm_source=newsletter",
                text="Updated note about AI agents.",
            ),
        )

        raw_items = db.query(RawItem).all()
        sources = {source.name for source in db.query(Source).all()}

    assert result.created is False
    assert result.updated_existing is True
    assert result.item.id == first.normalized_item.id
    assert result.item.source_name == "GitHub"
    assert len(raw_items) == 1
    assert sources == {"Manual Submission", "GitHub"}


def test_manual_submission_result_reports_created_and_updated_existing() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        first = create_manual_submission_result(
            db=db,
            request=ManualSubmissionRequest(
                title="Original agent note",
                url="https://example.com/agent-note",
                text="OpenAI released a new agent workflow.",
            ),
        )
        second = create_manual_submission_result(
            db=db,
            request=ManualSubmissionRequest(
                title="Updated agent note",
                url="https://example.com/agent-note",
                text="OpenAI released a new agent workflow with more context.",
            ),
        )

        assert first.created is True
        assert first.updated_existing is False
        assert second.created is False
        assert second.updated_existing is True
        assert second.item.id == first.item.id
        assert second.item.title == "Updated agent note"


def test_manual_submission_resubmits_tracking_url_variant_as_update() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        first = create_manual_submission_result(
            db=db,
            request=ManualSubmissionRequest(
                title="Original agent note",
                url="https://example.com/agent-note?utm_source=newsletter",
                text="OpenAI released a new agent workflow.",
            ),
        )
        second = create_manual_submission_result(
            db=db,
            request=ManualSubmissionRequest(
                title="Updated agent note",
                url="https://example.com/agent-note?utm_medium=social",
                text="OpenAI released a new agent workflow with more context.",
            ),
        )

        assert first.created is True
        assert first.updated_existing is False
        assert second.created is False
        assert second.updated_existing is True
        assert second.item.id == first.item.id
        assert db.query(RawItem).count() == 1


def test_manual_submission_can_save_item_on_submit() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        result = create_manual_submission_result(
            db=db,
            request=ManualSubmissionRequest(
                title="Saved agent note",
                url="https://example.com/saved-agent-note",
                text="OpenAI released a new agent workflow.",
                save_item=True,
            ),
        )

        assert result.created is True
        assert result.item.is_saved is True
        assert result.item.title == "Saved agent note"


def test_manual_submission_can_save_note_and_tags_on_submit() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        result = create_manual_submission_result(
            db=db,
            request=ManualSubmissionRequest(
                title="Tagged agent note",
                url="https://example.com/tagged-agent-note",
                text="OpenAI released a new agent workflow.",
                save_item=True,
                personal_note="  Read before weekend digest.  ",
                manual_tags=[" Agent ", "agent", "market impact", ""],
            ),
        )

        assert result.created is True
        assert result.item.is_saved is True
        assert result.item.personal_note == "Read before weekend digest."
        assert result.item.manual_tags == ["Agent", "market impact"]


@pytest.mark.anyio
async def test_manual_submission_route_skips_llm_enrichment_by_default(monkeypatch) -> None:
    calls: list[str] = []

    async def fake_classify_feed_item(**_kwargs) -> NormalizedItem:
        calls.append("classify")
        return make_normalized_manual_item()

    async def fake_summarize_feed_item(**_kwargs) -> NormalizedItem:
        calls.append("summarize")
        return make_normalized_manual_item()

    monkeypatch.setattr(
        manual_submission_routes,
        "create_manual_submission_result",
        lambda **_kwargs: ManualSubmissionSaveResult(
            item=make_manual_feed_item(summary_short="Manual summary"),
            created=True,
            updated_existing=False,
        ),
    )
    monkeypatch.setattr(manual_submission_routes, "classify_feed_item", fake_classify_feed_item)
    monkeypatch.setattr(manual_submission_routes, "summarize_feed_item", fake_summarize_feed_item)

    response = await manual_submission_routes.submit_manual_url(
        request=ManualSubmissionRequest(url="https://example.com/manual"),
        db=FakeManualSubmissionDb(make_normalized_manual_item()),
    )

    assert response.item.summary_short == "Manual summary"
    assert response.created is True
    assert response.updated_existing is False
    assert response.classification_status == "not_requested"
    assert response.classification_error is None
    assert response.summary_status == "not_requested"
    assert response.summary_error is None
    assert calls == []


@pytest.mark.anyio
async def test_manual_submission_route_can_classify_and_summarize_saved_item(monkeypatch) -> None:
    async def fake_classify_feed_item(**kwargs) -> NormalizedItem:
        item = kwargs["item"]
        item.category = "product"
        item.subcategory = "manual_product"
        item.topics = ["agent"]
        item.products = ["AgentDesk"]
        item.classification_confidence = 0.91
        return item

    async def fake_summarize_feed_item(**kwargs) -> NormalizedItem:
        item = kwargs["item"]
        item.summary_short = "Kimi summary"
        item.summary_detailed = "Kimi detailed summary"
        item.why_it_matters = "Kimi why it matters"
        return item

    monkeypatch.setattr(
        manual_submission_routes,
        "create_manual_submission_result",
        lambda **_kwargs: ManualSubmissionSaveResult(
            item=make_manual_feed_item(summary_short="Manual summary"),
            created=False,
            updated_existing=True,
        ),
    )
    monkeypatch.setattr(manual_submission_routes, "classify_feed_item", fake_classify_feed_item)
    monkeypatch.setattr(manual_submission_routes, "summarize_feed_item", fake_summarize_feed_item)
    monkeypatch.setattr(manual_submission_routes, "get_settings", lambda: object())
    monkeypatch.setattr(manual_submission_routes, "get_action", lambda *_args: None)

    response = await manual_submission_routes.submit_manual_url(
        request=ManualSubmissionRequest(
            url="https://example.com/manual",
            classify_with_llm=True,
            summarize_with_llm=True,
        ),
        db=FakeManualSubmissionDb(make_normalized_manual_item()),
    )

    assert response.item.category == "product"
    assert response.item.products == ["AgentDesk"]
    assert response.item.summary_short == "Kimi summary"
    assert response.created is False
    assert response.updated_existing is True
    assert response.item.summary_detailed == "Kimi detailed summary"
    assert response.item.why_it_matters == "Kimi why it matters"
    assert response.classification_status == "succeeded"
    assert response.classification_error is None
    assert response.summary_status == "succeeded"
    assert response.summary_error is None


@pytest.mark.anyio
async def test_manual_submission_route_keeps_item_when_llm_summary_fails(monkeypatch) -> None:
    async def fake_summarize_feed_item(**_kwargs) -> NormalizedItem:
        raise SummarizationError("Kimi unavailable")

    monkeypatch.setattr(
        manual_submission_routes,
        "create_manual_submission_result",
        lambda **_kwargs: ManualSubmissionSaveResult(
            item=make_manual_feed_item(summary_short="Manual summary"),
            created=True,
            updated_existing=False,
        ),
    )
    monkeypatch.setattr(manual_submission_routes, "summarize_feed_item", fake_summarize_feed_item)
    monkeypatch.setattr(manual_submission_routes, "get_settings", lambda: object())
    monkeypatch.setattr(manual_submission_routes, "get_action", lambda *_args: None)

    response = await manual_submission_routes.submit_manual_url(
        request=ManualSubmissionRequest(
            url="https://example.com/manual",
            summarize_with_llm=True,
        ),
        db=FakeManualSubmissionDb(make_normalized_manual_item()),
    )

    assert response.item.summary_short == "Manual summary"
    assert response.classification_status == "not_requested"
    assert response.classification_error is None
    assert response.summary_status == "failed"
    assert response.summary_error == "Kimi unavailable"


@pytest.mark.anyio
async def test_manual_submission_route_can_summarize_after_llm_classification_fails(
    monkeypatch,
) -> None:
    async def fake_classify_feed_item(**_kwargs) -> NormalizedItem:
        raise ClassificationError("Kimi classification unavailable")

    async def fake_summarize_feed_item(**kwargs) -> NormalizedItem:
        item = kwargs["item"]
        item.summary_short = "Kimi summary"
        return item

    monkeypatch.setattr(
        manual_submission_routes,
        "create_manual_submission_result",
        lambda **_kwargs: ManualSubmissionSaveResult(
            item=make_manual_feed_item(summary_short="Manual summary"),
            created=True,
            updated_existing=False,
        ),
    )
    monkeypatch.setattr(manual_submission_routes, "classify_feed_item", fake_classify_feed_item)
    monkeypatch.setattr(manual_submission_routes, "summarize_feed_item", fake_summarize_feed_item)
    monkeypatch.setattr(manual_submission_routes, "get_settings", lambda: object())
    monkeypatch.setattr(manual_submission_routes, "get_action", lambda *_args: None)

    response = await manual_submission_routes.submit_manual_url(
        request=ManualSubmissionRequest(
            url="https://example.com/manual",
            classify_with_llm=True,
            summarize_with_llm=True,
        ),
        db=FakeManualSubmissionDb(make_normalized_manual_item()),
    )

    assert response.item.summary_short == "Kimi summary"
    assert response.classification_status == "failed"
    assert response.classification_error == "Kimi classification unavailable"
    assert response.summary_status == "succeeded"
    assert response.summary_error is None


def make_source() -> Source:
    return Source(
        id=1,
        name="Manual Submission",
        type="manual",
        access_method="manual_submission",
        enabled=True,
        priority=5,
    )


def make_raw(title: str, text: str) -> RawItem:
    return RawItem(
        id=1,
        source_id=1,
        external_id="https://example.com/manual",
        url="https://example.com/manual",
        raw_title=title,
        raw_text=text,
        raw_metadata={},
        content_hash="abc",
    )


class FakeManualSubmissionDb:
    def __init__(self, item: NormalizedItem) -> None:
        self.item = item

    def get(self, model: type[NormalizedItem], item_id: int) -> NormalizedItem | None:
        if model is NormalizedItem and item_id == self.item.id:
            return self.item
        return None


def make_manual_feed_item(summary_short: str) -> FeedItem:
    return FeedItem(
        id=1,
        title="Manual AI item",
        url="https://example.com/manual",
        source_name="Manual Submission",
        author=None,
        language="en",
        published_at=None,
        category="technical_trend",
        subcategory="manual_ai_signal",
        tickers=[],
        companies=[],
        products=[],
        topics=["agent"],
        sentiment="neutral",
        relevance_score=0.7,
        classification_confidence=0.65,
        importance_score=0.5,
        novelty_score=1.0,
        source_quality_score=0.65,
        social_signal_score=0,
        stock_impact_score=0,
        summary_short=summary_short,
        summary_detailed=None,
        why_it_matters="This user-submitted item matched AI relevance signals.",
        is_saved=False,
        is_hidden=False,
        is_important=False,
        personal_note=None,
        manual_tags=[],
    )


def make_normalized_manual_item() -> NormalizedItem:
    return NormalizedItem(
        id=1,
        raw_item_id=1,
        title="Manual AI item",
        url="https://example.com/manual",
        source_name="Manual Submission",
        author=None,
        language="en",
        published_at=None,
        text="Manual AI item",
        category="technical_trend",
        subcategory="manual_ai_signal",
        tickers=[],
        companies=[],
        products=[],
        topics=["agent"],
        sentiment="neutral",
        relevance_score=0.7,
        classification_confidence=0.65,
        importance_score=0.5,
        novelty_score=1.0,
        source_quality_score=0.65,
        stock_impact_score=0,
        summary_short="Manual summary",
        summary_detailed=None,
        why_it_matters="This user-submitted item matched AI relevance signals.",
    )
