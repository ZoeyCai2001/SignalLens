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
    "policy_regulation",
    "infrastructure",
    "funding_mna",
    "benchmark_evaluation",
    "open_source_release",
    "tutorial_opinion",
    "noise_irrelevant",
}

ALLOWED_SENTIMENTS = {"positive", "neutral", "negative", "mixed"}
MARKET_IMPACT_SENTIMENT_FALLBACKS = {
    "positive": "positive",
    "negative": "negative",
    "mixed": "mixed",
}
MARKET_IMPACT_SCORE_FALLBACKS = {
    "positive": 0.55,
    "negative": 0.55,
    "mixed": 0.4,
    "uncertain": 0.25,
    "none": 0.0,
}

CATEGORY_ALIASES = {
    "technical_trend": "technical_trend",
    "technical_trends": "technical_trend",
    "research": "research",
    "product": "product",
    "products": "product",
    "stock_company": "stock_company_event",
    "stock_company_event": "stock_company_event",
    "manual_submission": "manual_submission",
    "manual": "manual_submission",
    "social_trend": "social_trend",
    "social_trends": "social_trend",
    "policy_regulation": "policy_regulation",
    "policy_regulations": "policy_regulation",
    "infrastructure": "infrastructure",
    "funding_m_a": "funding_mna",
    "funding_m_and_a": "funding_mna",
    "funding_ma": "funding_mna",
    "funding_mna": "funding_mna",
    "funding_merger_acquisition": "funding_mna",
    "funding_mergers_and_acquisitions": "funding_mna",
    "funding_mergers_acquisitions": "funding_mna",
    "benchmark": "benchmark_evaluation",
    "benchmarks": "benchmark_evaluation",
    "benchmark_evaluation": "benchmark_evaluation",
    "benchmark_evaluations": "benchmark_evaluation",
    "open_source": "open_source_release",
    "open_source_release": "open_source_release",
    "open_source_releases": "open_source_release",
    "tutorial": "tutorial_opinion",
    "opinion": "tutorial_opinion",
    "tutorial_opinion": "tutorial_opinion",
    "tutorial_opinions": "tutorial_opinion",
    "noise": "noise_irrelevant",
    "irrelevant": "noise_irrelevant",
    "noise_irrelevant": "noise_irrelevant",
}

CATEGORY_PROMPT_VALUES = [
    "technical_trend",
    "research",
    "product",
    "stock_company_event",
    "manual_submission",
    "social_trend",
    "policy_regulation",
    "infrastructure",
    "funding_mna",
    "benchmark_evaluation",
    "open_source_release",
    "tutorial_opinion",
    "noise_irrelevant",
]


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
    allowed_values = "\n".join(f"- {category}" for category in CATEGORY_PROMPT_VALUES)
    return f"""
You are classifying an item for SignalLens, a personal AI intelligence dashboard.
Return only valid compact JSON. Do not include markdown fences.

Allowed category values:
{allowed_values}

Required JSON shape:
{{
  "category": "one allowed category",
  "subcategory": "short snake_case label or empty string",
  "related_topics": ["2 to 8 lowercase AI topic tags"],
  "technologies": ["related AI technologies if directly relevant"],
  "related_tickers": ["stock tickers if directly relevant"],
  "related_companies": ["company names if directly relevant"],
  "related_products": ["product/model/tool names if directly relevant"],
  "sentiment": "positive, neutral, negative, or mixed",
  "market_impact": "none, positive, negative, mixed, or uncertain",
  "relevance_score": 0.0,
  "confidence": 0.0,
  "importance_score": 0.0,
  "stock_impact_score": 0.0,
  "why_it_matters": "one concise English explanation"
}}

Rules:
- Keep everything in English.
- Use the exact snake_case category values from the allowed list.
- Do not give investment advice.
- Use stock_company_event only for company, market, earnings, chip, cloud capex,
  partnership, supply-chain, or analyst events.
- Use policy_regulation for policy, regulation, export control, safety governance,
  or legal changes that are not primarily about one public company.
- Use infrastructure for AI compute, data center, cloud, networking, serving, or
  deployment infrastructure signals that are not primarily public-company stock events.
- Use funding_mna for funding rounds, acquisitions, mergers, or venture activity.
- Use benchmark_evaluation for benchmark, eval, leaderboard, or measurement news.
- Use open_source_release for open-source model, repo, dataset, or tool releases.
- Use tutorial_opinion for practical guides, tutorials, essays, or opinion pieces.
- Use noise_irrelevant only when the item is not useful AI intelligence.
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
    market_impact = normalize_market_impact(
        data.get("market_impact", data.get("market_impact_type"))
    )
    sentiment = normalize_sentiment(
        data.get("sentiment")
        or MARKET_IMPACT_SENTIMENT_FALLBACKS.get(market_impact)
        or item.sentiment
    )
    topics = merge_string_lists(
        normalized_string_list(data.get("topics")),
        normalized_string_list(data.get("related_topics")),
        normalized_string_list(data.get("technologies")),
    ) or detect_topics(item.title)
    tickers = normalized_tickers(
        data.get("tickers", data.get("related_tickers")),
        fallback_text=item.title,
    )
    companies = merge_string_lists(
        normalized_string_list(data.get("companies")),
        normalized_string_list(data.get("related_companies")),
    )
    products = merge_string_lists(
        normalized_string_list(data.get("products")),
        normalized_string_list(data.get("related_products")),
    )
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
            data.get(
                "confidence_score",
                data.get("classification_confidence", data.get("confidence", 0.7)),
            )
        ),
        importance_score=clamp_score(data.get("importance_score")),
        stock_impact_score=classification_stock_impact_score(data, market_impact),
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
    category = normalize_category_key(value)
    category = CATEGORY_ALIASES.get(category, category)
    if category not in ALLOWED_CATEGORIES:
        raise ClassificationError(f"Unsupported category from Kimi classification: {category}")
    return category


def normalize_category_key(value: Any) -> str:
    category = str(value or "").strip().lower()
    category = category.replace("&", " and ")
    category = re.sub(r"[^a-z0-9]+", "_", category)
    return re.sub(r"_+", "_", category).strip("_")


def normalize_sentiment(value: Any) -> str:
    sentiment = str(value or "neutral").strip().lower()
    return sentiment if sentiment in ALLOWED_SENTIMENTS else "neutral"


def normalize_market_impact(value: Any) -> str:
    key = normalize_category_key(value)
    if key in {
        "positive",
        "potentially_positive",
        "potential_positive",
        "market_positive",
        "positive_signal",
        "potentially_positive_market_impact",
    }:
        return "positive"
    if key in {
        "negative",
        "potentially_negative",
        "potential_negative",
        "market_negative",
        "negative_signal",
        "potentially_negative_market_impact",
    }:
        return "negative"
    if key in {"mixed", "unclear", "ambiguous"}:
        return "mixed"
    if key in {"uncertain", "possible", "indirect"}:
        return "uncertain"
    if key in {"none", "no", "no_market_impact", "not_applicable", "na", ""}:
        return "none"
    return "uncertain"


def classification_stock_impact_score(data: dict[str, Any], market_impact: str) -> float:
    if data.get("stock_impact_score") is not None:
        return clamp_score(data.get("stock_impact_score"))
    return MARKET_IMPACT_SCORE_FALLBACKS.get(market_impact, 0.0)


def normalized_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def merge_string_lists(*values: list[str]) -> list[str]:
    merged = []
    seen = set()
    for value_list in values:
        for value in value_list:
            key = value.casefold()
            if key not in seen:
                merged.append(value)
                seen.add(key)
    return merged


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
