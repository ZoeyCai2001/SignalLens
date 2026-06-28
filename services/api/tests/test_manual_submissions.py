from app.db.models import RawItem, Source
from app.services.manual_submissions import (
    create_manual_normalized_item,
    enrich_manual_normalized_item,
    first_sentence,
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
    assert item.summary_short == "Manual submission: Interesting AI product"
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


def test_first_sentence_handles_chinese_punctuation() -> None:
    assert first_sentence("国产大模型应用正在升温。第二句。") == "国产大模型应用正在升温。"


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
