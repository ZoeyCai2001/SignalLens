from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, NormalizedItem
from app.db.models import RawItem, Source
from app.schemas.manual_submissions import ManualSubmissionRequest
from app.services.manual_submissions import (
    create_raw_manual_item,
    create_manual_normalized_item,
    enrich_manual_normalized_item,
    first_sentence,
    reset_manual_normalized_item,
    resolve_manual_title,
)


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
    assert item.subcategory == "manual_product"
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
        title="小红书 AI photo tool workflow",
        text="小红书用户讨论 AI photo tools and viral editing workflows.",
    )
    item = create_manual_normalized_item(raw=raw, source=source)

    enrich_manual_normalized_item(item, raw)

    assert item.category == "social_trend"
    assert item.subcategory == "manual_social_signal"
    assert item.language == "zh"


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
