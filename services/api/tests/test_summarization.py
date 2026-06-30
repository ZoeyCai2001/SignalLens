import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.models import Base, LlmUsageEvent, NormalizedItem
from app.llm.kimi_coding import KimiMessageResult
from app.services import summarization
from app.services.summarization import (
    format_detailed_summary,
    format_short_summary,
    parse_summary,
)


def test_parse_summary_extracts_expected_json() -> None:
    summary = parse_summary(
        """
        {
          "one_line_summary": "A paper evaluates AI agents.",
          "bullet_summary": ["It studies tool use.", "It reports benchmark results."],
          "why_it_matters": "Agent evaluation is a watched technical topic.",
          "technical_relevance": "Useful for agent benchmark tracking.",
          "market_relevance": "",
          "uncertainties": ["The result needs source review."]
        }
        """
    )

    assert summary.one_line_summary == "A paper evaluates AI agents."
    assert summary.bullet_summary == ["It studies tool use.", "It reports benchmark results."]
    assert summary.market_relevance is None
    assert summary.uncertainties == ["The result needs source review."]


def test_parse_summary_extracts_research_and_product_context() -> None:
    summary = parse_summary(
        """
        {
          "one_line_summary": "A launch introduces an AI coding workspace.",
          "bullet_summary": ["It targets coding workflows.", "It reports strong launch interest."],
          "why_it_matters": "Coding tools are a watched product category.",
          "research_contribution": "It contributes an agent evaluation dataset.",
          "research_method": "It compares tool-use agents on multi-step tasks.",
          "product_use_case": "It helps developers coordinate coding agents.",
          "product_audience": "software teams",
          "traction_signal": "The source reports launch upvotes.",
          "uncertainties": []
        }
        """
    )

    detailed = format_detailed_summary(summary)

    assert summary.research_contribution == "It contributes an agent evaluation dataset."
    assert summary.research_method == "It compares tool-use agents on multi-step tasks."
    assert summary.product_use_case == "It helps developers coordinate coding agents."
    assert summary.product_audience == "software teams"
    assert summary.traction_signal == "The source reports launch upvotes."
    assert "Research contribution: It contributes an agent evaluation dataset." in detailed
    assert "Product use case: It helps developers coordinate coding agents." in detailed
    assert "Traction signal: The source reports launch upvotes." in detailed


def test_format_short_summary_includes_bullets() -> None:
    summary = parse_summary(
        """
        {
          "one_line_summary": "An AI infrastructure item appeared.",
          "bullet_summary": ["It mentions inference.", "It may matter for developers."],
          "why_it_matters": "Inference is a watched topic."
        }
        """
    )

    assert "- It mentions inference." in format_short_summary(summary)


@pytest.mark.anyio
async def test_summarize_feed_item_records_llm_usage(monkeypatch) -> None:
    class FakeKimiClient:
        def __init__(self, settings: Settings) -> None:
            self.settings = settings

        async def create_message(self, prompt: str, max_tokens: int = 64) -> KimiMessageResult:
            return KimiMessageResult(
                model="kimi-for-coding",
                text="""
                {
                  "one_line_summary": "A source describes a useful AI agent update.",
                  "bullet_summary": ["It improves tool use.", "It matters to developers."],
                  "why_it_matters": "Agent workflow updates are relevant to SignalLens.",
                  "technical_relevance": "It mentions tool orchestration.",
                  "market_relevance": "",
                  "uncertainties": []
                }
                """,
                input_tokens=120,
                output_tokens=40,
                total_tokens=160,
            )

    monkeypatch.setattr(summarization, "KimiCodingClient", FakeKimiClient)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        item = make_item()
        db.add(item)
        db.commit()
        summarized = await summarization.summarize_feed_item(
            db=db,
            item=item,
            settings=Settings(MOONSHOT_API_KEY="test-key"),
        )
        usage = db.query(LlmUsageEvent).one()

    assert "A source describes" in summarized.summary_short
    assert usage.operation == "summarize_item"
    assert usage.provider == "kimi_coding"
    assert usage.model == "kimi-for-coding"
    assert usage.item_id == 1
    assert usage.input_tokens == 120
    assert usage.output_tokens == 40
    assert usage.total_tokens == 160


def make_item() -> NormalizedItem:
    return NormalizedItem(
        id=1,
        raw_item_id=1,
        title="New AI agent workflow ships",
        url="https://example.com/agent",
        source_name="Test Source",
        language="en",
        text="The source describes a new AI agent workflow for developers.",
        category="technical_trend",
        tickers=[],
        companies=[],
        products=[],
        topics=["agents"],
        sentiment="neutral",
        relevance_score=0.8,
        classification_confidence=0.8,
        importance_score=0.7,
        novelty_score=0.6,
        source_quality_score=0.7,
        stock_impact_score=0.0,
    )
