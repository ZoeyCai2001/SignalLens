import json
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import NormalizedItem
from app.llm.kimi_coding import KimiCodingClient, KimiCodingError


class SummarizationError(RuntimeError):
    """Raised when an item cannot be summarized reliably."""


@dataclass(frozen=True)
class ItemSummary:
    one_line_summary: str
    bullet_summary: list[str]
    why_it_matters: str
    technical_relevance: str | None = None
    market_relevance: str | None = None
    uncertainties: list[str] | None = None


async def summarize_feed_item(
    db: Session,
    item: NormalizedItem,
    settings: Settings,
) -> NormalizedItem:
    client = KimiCodingClient(settings=settings)
    prompt = build_summary_prompt(item)
    try:
        result = await client.create_message(prompt=prompt, max_tokens=700)
    except KimiCodingError as exc:
        raise SummarizationError(str(exc)) from exc

    summary = parse_summary(result.text)
    item.summary_short = format_short_summary(summary)
    item.summary_detailed = format_detailed_summary(summary)
    item.why_it_matters = summary.why_it_matters
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def build_summary_prompt(item: NormalizedItem) -> str:
    source_text = item.text or ""
    trimmed_text = source_text[:4000]
    topics = ", ".join(item.topics or [])
    tickers = ", ".join(item.tickers or [])
    return f"""
You are summarizing an item for SignalLens, a personal AI intelligence dashboard.
Return only valid compact JSON. Do not include markdown fences.

Required JSON shape:
{{
  "one_line_summary": "one sentence",
  "bullet_summary": ["2 to 4 concise bullets"],
  "why_it_matters": "short explanation of technical, product, or market relevance",
  "technical_relevance": "short optional text or empty string",
  "market_relevance": "short optional text or empty string",
  "uncertainties": ["0 to 3 uncertainty notes"]
}}

Rules:
- Keep everything in English.
- Do not give investment advice.
- Use conservative wording for market impact.
- Preserve source attribution by referring to the item as source material, not verified fact.

Item:
Title: {item.title}
Source: {item.source_name}
Category: {item.category}
Topics: {topics or "none"}
Tickers: {tickers or "none"}
URL: {item.url}
Text: {trimmed_text or item.title}
""".strip()


def parse_summary(text: str) -> ItemSummary:
    data = parse_json_object(text)
    try:
        one_line = str(data["one_line_summary"]).strip()
        bullets = [str(bullet).strip() for bullet in data["bullet_summary"] if str(bullet).strip()]
        why = str(data["why_it_matters"]).strip()
    except (KeyError, TypeError) as exc:
        raise SummarizationError(
            "Kimi summary response did not match the expected schema."
        ) from exc

    if not one_line or not bullets or not why:
        raise SummarizationError("Kimi summary response contained empty required fields.")

    return ItemSummary(
        one_line_summary=one_line,
        bullet_summary=bullets[:4],
        why_it_matters=why,
        technical_relevance=optional_string(data.get("technical_relevance")),
        market_relevance=optional_string(data.get("market_relevance")),
        uncertainties=optional_string_list(data.get("uncertainties")),
    )


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return json.loads(stripped)

    match = re.search(r"\{.*\}", stripped, flags=re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise SummarizationError("Kimi summary response did not include a JSON object.")


def optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def optional_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def format_short_summary(summary: ItemSummary) -> str:
    bullets = " ".join(f"- {bullet}" for bullet in summary.bullet_summary)
    return f"{summary.one_line_summary}\n{bullets}"


def format_detailed_summary(summary: ItemSummary) -> str:
    parts = [summary.one_line_summary, *summary.bullet_summary]
    if summary.technical_relevance:
        parts.append(f"Technical relevance: {summary.technical_relevance}")
    if summary.market_relevance:
        parts.append(f"Market relevance: {summary.market_relevance}")
    if summary.uncertainties:
        parts.append("Uncertainties: " + "; ".join(summary.uncertainties))
    return "\n".join(parts)
