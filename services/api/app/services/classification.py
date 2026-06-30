import json
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import NormalizedItem
from app.llm.kimi_coding import KimiCodingClient, KimiCodingError
from app.services.llm_usage import record_llm_usage
from app.services.scoring import detect_tickers, detect_topics


class ClassificationError(RuntimeError):
    """Raised when an item cannot be classified reliably."""


ALLOWED_CATEGORIES = {
    "technical_trend",
    "research",
    "product",
    "stock_company_event",
    "manual_submission",
    "social_trend",
}

ALLOWED_SENTIMENTS = {"positive", "neutral", "negative", "mixed"}


@dataclass(frozen=True)
class ItemClassification:
    category: str
    subcategory: str | None
    topics: list[str]
    tickers: list[str]
    companies: list[str]
    products: list[str]
    sentiment: str
    relevance_score: float
    classification_confidence: float
    importance_score: float
    stock_impact_score: float
    why_it_matters: str


async def classify_feed_item(
    db: Session,
    item: NormalizedItem,
    settings: Settings,
) -> NormalizedItem:
    client = KimiCodingClient(settings=settings)
    prompt = build_classification_prompt(item)
    try:
        result = await client.create_message(prompt=prompt, max_tokens=500)
    except KimiCodingError as exc:
        raise ClassificationError(str(exc)) from exc

    classification = parse_classification(result.text, item)
    item.category = classification.category
    item.subcategory = classification.subcategory
    item.topics = classification.topics
    item.tickers = classification.tickers
    item.companies = classification.companies
    item.products = classification.products
    item.sentiment = classification.sentiment
    item.relevance_score = classification.relevance_score
    item.classification_confidence = classification.classification_confidence
    item.importance_score = classification.importance_score
    item.stock_impact_score = classification.stock_impact_score
    item.why_it_matters = classification.why_it_matters
    db.add(item)
    record_llm_usage(
        db=db,
        operation="classify_item",
        provider=settings.llm_provider,
        result=result,
        item_id=item.id,
    )
    db.commit()
    db.refresh(item)
    return item


def build_classification_prompt(item: NormalizedItem) -> str:
    source_text = item.text or ""
    trimmed_text = source_text[:3500]
    return f"""
You are classifying an item for SignalLens, a personal AI intelligence dashboard.
Return only valid compact JSON. Do not include markdown fences.

Allowed category values:
- technical_trend
- research
- product
- stock_company_event
- manual_submission
- social_trend

Required JSON shape:
{{
  "category": "one allowed category",
  "subcategory": "short snake_case label or empty string",
  "topics": ["2 to 8 lowercase AI topic tags"],
  "tickers": ["stock tickers if directly relevant"],
  "companies": ["company names if directly relevant"],
  "products": ["product/model/tool names if directly relevant"],
  "sentiment": "positive, neutral, negative, or mixed",
  "relevance_score": 0.0,
  "confidence_score": 0.0,
  "importance_score": 0.0,
  "stock_impact_score": 0.0,
  "why_it_matters": "one concise English explanation"
}}

Rules:
- Keep everything in English.
- Do not give investment advice.
- Use stock_company_event only for company, market, earnings, chip, cloud capex,
  regulation, partnership, supply-chain, or analyst events.
- Scores must be numbers from 0 to 1.
- confidence_score is how certain you are about the category and extracted entities.
- Preserve source uncertainty. Describe what the source item says, not verified fact.

Item:
Title: {item.title}
Source: {item.source_name}
Current category: {item.category}
URL: {item.url}
Text: {trimmed_text or item.title}
""".strip()


def parse_classification(text: str, item: NormalizedItem) -> ItemClassification:
    data = parse_json_object(text)
    category = normalize_category(data.get("category"))
    sentiment = normalize_sentiment(data.get("sentiment"))
    topics = normalized_string_list(data.get("topics")) or detect_topics(item.title)
    tickers = normalized_tickers(data.get("tickers"), fallback_text=item.title)
    companies = normalized_string_list(data.get("companies"))
    products = normalized_string_list(data.get("products"))
    why = str(data.get("why_it_matters") or "").strip()

    if not why:
        raise ClassificationError("Kimi classification response omitted why_it_matters.")

    return ItemClassification(
        category=category,
        subcategory=optional_string(data.get("subcategory")),
        topics=topics[:12],
        tickers=tickers[:12],
        companies=companies[:12],
        products=products[:12],
        sentiment=sentiment,
        relevance_score=clamp_score(data.get("relevance_score")),
        classification_confidence=clamp_score(
            data.get("confidence_score", data.get("classification_confidence", 0.7))
        ),
        importance_score=clamp_score(data.get("importance_score")),
        stock_impact_score=clamp_score(data.get("stock_impact_score")),
        why_it_matters=why,
    )


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return json.loads(stripped)

    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ClassificationError("Kimi classification response did not include a JSON object.")


def normalize_category(value: Any) -> str:
    category = str(value or "").strip()
    if category not in ALLOWED_CATEGORIES:
        raise ClassificationError(f"Unsupported category from Kimi classification: {category}")
    return category


def normalize_sentiment(value: Any) -> str:
    sentiment = str(value or "neutral").strip().lower()
    return sentiment if sentiment in ALLOWED_SENTIMENTS else "neutral"


def normalized_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def normalized_tickers(value: Any, fallback_text: str) -> list[str]:
    tickers = [ticker.upper() for ticker in normalized_string_list(value)]
    if tickers:
        return tickers
    return detect_tickers(fallback_text)


def optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def clamp_score(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ClassificationError(
            "Kimi classification response included a non-numeric score."
        ) from exc
    return round(max(0.0, min(1.0, number)), 3)
