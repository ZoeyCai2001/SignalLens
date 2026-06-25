import pytest

from app.db.models import NormalizedItem
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
          "importance_score": 1.2,
          "stock_impact_score": -0.2,
          "why_it_matters": "The source links AI infrastructure demand to a chip supplier."
        }
        """,
        item,
    )

    assert classification.category == "stock_company_event"
    assert classification.tickers == ["AVGO"]
    assert classification.importance_score == 1.0
    assert classification.stock_impact_score == 0.0


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
