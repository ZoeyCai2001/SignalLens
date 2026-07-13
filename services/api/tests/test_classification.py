import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.models import Base, LlmUsageEvent, NormalizedItem
from app.llm.kimi_coding import KimiMessageResult
from app.services import classification
from app.services.classification import ClassificationError, parse_classification


def test_parse_classification_validates_and_clamps_scores() -> None:
    item = make_item()

    classification = parse_classification(
        """
        {
          "category": "stock_company_event",
          "subcategory": "chip_partnership",
          "topics": ["ai", "inference", "custom silicon"],
          "tickers": ["avgo"],
          "companies": ["Broadcom", "OpenAI"],
          "products": ["inference chip"],
          "sentiment": "mixed",
          "relevance_score": 0.92,
          "confidence_score": 1.4,
          "importance_score": 1.2,
          "stock_impact_score": -0.2,
          "why_it_matters": "The source links AI infrastructure demand to a chip supplier."
        }
        """,
        item,
    )

    assert classification.category == "stock_company_event"
    assert classification.tickers == ["AVGO"]
    assert classification.classification_confidence == 1.0
    assert classification.importance_score == 1.0
    assert classification.stock_impact_score == 0.0


@pytest.mark.parametrize(
    ("raw_category", "expected_category"),
    [
        ("policy/regulation", "policy_regulation"),
        ("funding/M&A", "funding_mna"),
        ("open-source release", "open_source_release"),
        ("benchmark/evaluation", "benchmark_evaluation"),
    ],
)
def test_parse_classification_normalizes_prd_secondary_categories(
    raw_category: str,
    expected_category: str,
) -> None:
    classification = parse_classification(
        f"""
        {{
          "category": "{raw_category}",
          "subcategory": "",
          "topics": ["ai"],
          "tickers": [],
          "companies": [],
          "products": [],
          "sentiment": "neutral",
          "relevance_score": 0.7,
          "confidence_score": 0.8,
          "importance_score": 0.6,
          "stock_impact_score": 0.0,
          "why_it_matters": "This item matches a PRD secondary intelligence category."
        }}
        """,
        make_item(),
    )

    assert classification.category == expected_category


def test_parse_classification_rejects_unknown_category() -> None:
    with pytest.raises(ClassificationError):
        parse_classification(
            """
            {
              "category": "investment_advice",
              "topics": ["ai"],
              "tickers": [],
              "companies": [],
              "products": [],
              "sentiment": "neutral",
              "relevance_score": 0.5,
              "importance_score": 0.5,
              "stock_impact_score": 0.0,
              "why_it_matters": "Nope."
            }
            """,
            make_item(),
        )


@pytest.mark.anyio
async def test_classify_feed_item_records_llm_usage(monkeypatch) -> None:
    class FakeKimiClient:
        def __init__(self, settings: Settings) -> None:
            self.settings = settings

        async def create_message(self, prompt: str, max_tokens: int = 64) -> KimiMessageResult:
            return KimiMessageResult(
                model="kimi-for-coding",
                text="""
                {
                  "category": "stock_company_event",
                  "subcategory": "chip_partnership",
                  "topics": ["ai", "inference"],
                  "tickers": ["mrvl"],
                  "companies": ["Marvell"],
                  "products": ["AI accelerator"],
                  "sentiment": "mixed",
                  "relevance_score": 0.9,
                  "confidence_score": 0.8,
                  "importance_score": 0.75,
                  "stock_impact_score": 0.6,
                  "why_it_matters": "The source links AI infrastructure demand to a watched chip name."
                }
                """,
                input_tokens=90,
                output_tokens=30,
                total_tokens=120,
            )

    monkeypatch.setattr(classification, "KimiCodingClient", FakeKimiClient)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        item = make_item()
        db.add(item)
        db.commit()
        classified = await classification.classify_feed_item(
            db=db,
            item=item,
            settings=Settings(MOONSHOT_API_KEY="test-key"),
        )
        usage = db.query(LlmUsageEvent).one()

    assert classified.category == "stock_company_event"
    assert classified.tickers == ["MRVL"]
    assert usage.operation == "classify_item"
    assert usage.provider == "kimi_coding"
    assert usage.model == "kimi-for-coding"
    assert usage.item_id == 1
    assert usage.input_tokens == 90
    assert usage.output_tokens == 30
    assert usage.total_tokens == 120


def make_item() -> NormalizedItem:
    return NormalizedItem(
        id=1,
        raw_item_id=1,
        title="OpenAI and Broadcom unveil LLM inference chip",
        url="https://example.com",
        source_name="Test Source",
        language="en",
        category="technical_trend",
        tickers=[],
        companies=[],
        products=[],
        topics=["ai"],
        sentiment="neutral",
        relevance_score=0.5,
        importance_score=0.5,
        novelty_score=1.0,
        source_quality_score=0.75,
        stock_impact_score=0.0,
    )
