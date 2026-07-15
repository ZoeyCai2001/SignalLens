import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from app.db.models import (
    Alert,
    CompanyWatchlistItem,
    DailyDigestSnapshot,
    LlmUsageEvent,
    NormalizedItem,
    ProductWatchlistItem,
    RawItem,
    StockPricePoint,
    StockWatchlistItem,
    TopicWatchlistItem,
    UserItemAction,
)
from app.schemas.feed import (
    FeedItem,
    FeedItemDetail,
    FeedPublicEngagementMetric,
    FeedStockReactionSummary,
    SavedItemsMarkdownExport,
)
from app.schemas.preferences import RankingWeights
from app.services.seed_data import (
    initial_company_watchlist,
    initial_product_watchlist,
    initial_stock_watchlist,
    initial_topic_watchlist,
)

LOCAL_USER_ID = "local"
SAVED_ITEM_RANKING_BONUS = 0.05
PREFERRED_SOURCE_RANKING_BONUS = 0.08
CROSS_SOURCE_CONFIRMATION_RANKING_BONUS = 0.08
CROSS_SOURCE_CONFIRMATION_SOFT_BONUS = 0.06
REPEATED_EVENT_RANKING_BONUS = 0.03
FEEDBACK_INTEREST_MATCH_BONUS = 0.035
FEEDBACK_INTEREST_MATCH_PENALTY = 0.04
MAX_FEEDBACK_INTEREST_BONUS = 0.10
MAX_FEEDBACK_INTEREST_PENALTY = 0.12

CONFIRMATION_STOP_WORDS = {
    "about",
    "after",
    "from",
    "into",
    "more",
    "news",
    "over",
    "that",
    "their",
    "this",
    "with",
    "using",
}

CONFIRMATION_SIGNATURE_TERMS = [
    "earnings",
    "guidance",
    "upgrade",
    "downgrade",
    "analyst",
    "partnership",
    "deal",
    "chip",
    "gpu",
    "memory",
    "hbm",
    "datacenter",
    "capex",
    "launch",
    "release",
    "model",
    "benchmark",
    "agent",
    "inference",
    "training",
    "supply",
    "export",
]

TECHNOLOGY_TOPIC_LABELS = {
    "agent": "AI agents",
    "agents": "AI agents",
    "artificial intelligence": "AI",
    "benchmark": "Benchmarks",
    "coding agent": "Coding agents",
    "diffusion": "Diffusion models",
    "embedding": "Embeddings",
    "gpu": "GPUs",
    "inference": "Inference",
    "llama": "Llama",
    "llm": "LLMs",
    "machine learning": "Machine learning",
    "mcp": "MCP",
    "model": "AI models",
    "multimodal": "Multimodal AI",
    "rag": "RAG",
    "reasoning": "Reasoning models",
    "retrieval": "Retrieval",
    "transformer": "Transformers",
}


@dataclass(frozen=True)
class FeedInterestProfile:
    symbols: frozenset[str] = field(default_factory=frozenset)
    terms: frozenset[str] = field(default_factory=frozenset)
    liked_symbols: frozenset[str] = field(default_factory=frozenset)
    liked_terms: frozenset[str] = field(default_factory=frozenset)
    liked_sources: frozenset[str] = field(default_factory=frozenset)
    disliked_symbols: frozenset[str] = field(default_factory=frozenset)
    disliked_terms: frozenset[str] = field(default_factory=frozenset)
    disliked_sources: frozenset[str] = field(default_factory=frozenset)


def serialize_feed_item(
    item: NormalizedItem,
    action: UserItemAction | None = None,
) -> FeedItem:
    data = FeedItem.model_validate(item)
    data.is_ai_related = infer_is_ai_related(data)
    data.technologies = infer_related_technologies(data)
    data.social_signal_score = social_signal_score_for_item(item)
    data.market_impact_type = infer_market_impact_type(data)
    data.why_it_matters = build_feed_why_it_matters(data)
    if action:
        data.is_saved = action.is_saved
        data.is_hidden = action.is_hidden
        data.is_important = action.is_important
        data.is_read = action.is_read
        data.read_at = action.read_at
        data.personal_note = action.personal_note
        data.manual_tags = normalize_manual_tags(action.manual_tags)
        data.usefulness_feedback = normalize_usefulness_feedback(action.usefulness_feedback)
        data.usefulness_feedback_at = action.usefulness_feedback_at
    return data


def infer_is_ai_related(item: FeedItem) -> bool:
    if item.category == "noise_irrelevant":
        return False
    if item.relevance_score >= 0.35:
        return True
    if item.topics or item.products or item.tickers or item.companies:
        return True
    return item.category not in {"manual_submission", "noise_irrelevant"}


def infer_related_technologies(item: FeedItem) -> list[str]:
    technologies: list[str] = []
    seen: set[str] = set()
    for topic in item.topics:
        label = TECHNOLOGY_TOPIC_LABELS.get(topic.strip().casefold())
        if label and label.casefold() not in seen:
            technologies.append(label)
            seen.add(label.casefold())
    return technologies[:8]


def infer_market_impact_type(item: FeedItem) -> str:
    if item.stock_impact_score < 0.25 and not item.tickers:
        return "none"

    text = " ".join(
        part
        for part in [
            item.title,
            item.summary_short or "",
            item.why_it_matters or "",
            " ".join(item.topics),
        ]
        if part
    ).lower()
    if any(term in text for term in ["earnings", "guidance", "revenue", "margin"]):
        return "earnings_guidance"
    if any(
        term in text
        for term in ["analyst", "rating", "upgrade", "downgrade", "price target"]
    ):
        return "analyst_action"
    if any(term in text for term in ["partnership", "customer win", "customer", "contract"]):
        return "partnership_customer"
    if any(term in text for term in ["supply chain", "supplier", "export", "regulation"]):
        return "supply_chain_regulation"
    if any(term in text for term in ["funding", "acquisition", "merger", "m&a", "venture"]):
        return "funding_mna"
    if any(
        term in text
        for term in [
            "demand",
            "capex",
            "data center",
            "hbm",
            "custom silicon",
            "storage",
            "nand",
        ]
    ):
        return "demand_signal"
    if item.sentiment == "positive" and item.stock_impact_score >= 0.45:
        return "positive_signal"
    if item.sentiment == "negative" and item.stock_impact_score >= 0.45:
        return "negative_signal"
    if item.stock_impact_score >= 0.35 or item.category in {"stock_company_event", "funding_mna"}:
        return "stock_signal"
    return "none"


def build_feed_why_it_matters(item: FeedItem) -> str | None:
    if item.why_it_matters and item.why_it_matters.strip():
        return item.why_it_matters.strip()

    focus = primary_item_focus(item)
    context = category_context(item.category)
    signal_parts = []
    if item.importance_score >= 0.75:
        signal_parts.append("high importance")
    if item.relevance_score >= 0.72:
        signal_parts.append("strong AI relevance")
    if item.stock_impact_score >= 0.45:
        signal_parts.append("possible stock-watchlist impact")
    if item.social_signal_score >= 0.65:
        signal_parts.append("strong public traction")
    if item.source_quality_score >= 0.8:
        signal_parts.append("high source credibility")
    elif item.source_quality_score < 0.6:
        signal_parts.append("lower source credibility")
    if item.classification_confidence < 0.6:
        signal_parts.append("lower classifier confidence")

    signal_text = ", ".join(signal_parts[:3])
    if focus and signal_text:
        return f"{context} It is linked to {focus} and shows {signal_text}."
    if focus:
        return f"{context} It is linked to {focus}."
    if signal_text:
        return f"{context} It shows {signal_text}."
    return context


def primary_item_focus(item: FeedItem) -> str:
    technology_topic_keys = {
        topic.strip().casefold()
        for topic in item.topics
        if TECHNOLOGY_TOPIC_LABELS.get(topic.strip().casefold()) in item.technologies
    }
    labels = [
        *item.tickers,
        *item.products,
        product_use_case_label(item.subcategory) if item.category == "product" else "",
        *item.companies,
        *item.technologies,
        *[
            topic
            for topic in item.topics
            if topic.strip().casefold() not in technology_topic_keys
        ],
    ]
    unique_labels = []
    seen = set()
    for label in labels:
        normalized = label.strip()
        key = normalized.casefold()
        if normalized and key not in seen:
            unique_labels.append(normalized)
            seen.add(key)
    if not unique_labels:
        return ""
    return ", ".join(unique_labels[:3])


def category_context(category: str) -> str:
    contexts = {
        "technical_trend": "This may affect the AI technical trend watchlist.",
        "research": "This may inform AI research tracking and related paper discovery.",
        "product": "This may help identify AI products gaining traction.",
        "stock_company_event": "This may matter for AI-linked company and stock monitoring.",
        "social_trend": "This may indicate an emerging AI social or Chinese-language trend.",
        "manual_submission": (
            "This user-submitted link may need review for the personal intelligence archive."
        ),
    }
    return contexts.get(category, "This item matched the SignalLens AI relevance filters.")


def serialize_feed_item_detail(
    item: NormalizedItem,
    action: UserItemAction | None = None,
    interest_profile: FeedInterestProfile | None = None,
    db: Session | None = None,
) -> FeedItemDetail:
    base = serialize_feed_item(item, action)
    if db is not None:
        annotate_item_cross_source_confirmation(db=db, item=base)
    summary_profile = build_feed_summary_profile(base)
    return FeedItemDetail(
        **base.model_dump(),
        text=item.text,
        **summary_profile,
        stock_reaction_summary=build_feed_stock_reaction_summary(db=db, item=base),
        public_engagement=build_public_engagement_metrics(item),
        score_explanation=build_score_explanation(base),
        uncertainty_notes=build_feed_uncertainty_notes(base),
        personalization_notes=build_personalization_notes(base, interest_profile),
        action_state={
            "is_saved": base.is_saved,
            "is_hidden": base.is_hidden,
            "is_important": base.is_important,
            "is_read": base.is_read,
            "has_usefulness_feedback": base.usefulness_feedback is not None,
        },
    )


def build_feed_summary_profile(item: FeedItem) -> dict[str, str | list[str] | None]:
    one_line = extract_one_line_summary(item)
    card_summary = extract_card_summary(item)
    return {
        "one_line_summary": one_line,
        "card_summary": card_summary,
        "technical_summary": extract_technical_summary(item),
        "market_watch_summary": extract_market_watch_summary(item),
        "summary_source": summary_source_label(item),
    }


def extract_one_line_summary(item: FeedItem) -> str | None:
    for line in split_summary_lines(item.summary_short):
        if not is_bullet_line(line):
            return line
    for candidate in [item.summary_detailed, item.why_it_matters, item.title]:
        sentence = first_sentence(candidate)
        if sentence:
            return sentence
    return None


def extract_card_summary(item: FeedItem) -> list[str]:
    bullets = [
        strip_bullet_prefix(line)
        for line in split_summary_lines(item.summary_short)
        if is_bullet_line(line)
    ]
    if bullets:
        return bullets[:4]

    candidates = [
        first_sentence(item.why_it_matters),
        first_sentence(item.summary_detailed),
    ]
    return [candidate for candidate in candidates if candidate][:4]


def extract_technical_summary(item: FeedItem) -> str | None:
    labeled_parts = extract_labeled_summary_parts(
        item.summary_detailed,
        [
            "Technical relevance",
            "Research contribution",
            "Research method",
        ],
    )
    if labeled_parts:
        return " ".join(labeled_parts)
    if item.category not in {
        "research",
        "technical_trend",
        "infrastructure",
        "benchmark_evaluation",
        "open_source_release",
    }:
        return None
    return first_sentence(item.why_it_matters)


def extract_market_watch_summary(item: FeedItem) -> str | None:
    has_market_context = (
        bool(item.tickers)
        or item.category == "stock_company_event"
        or item.stock_impact_score >= 0.25
    )
    if not has_market_context:
        return None
    labeled_parts = extract_labeled_summary_parts(item.summary_detailed, ["Market relevance"])
    if labeled_parts:
        return " ".join(labeled_parts)
    ticker_text = f" for {', '.join(item.tickers[:3])}" if item.tickers else ""
    direction = "possible market context"
    if item.sentiment in {"positive", "negative", "mixed"}:
        direction = f"{item.sentiment} market context"
    return (
        f"Watch{ticker_text} as {direction}; SignalLens does not provide financial advice."
    )


def build_feed_stock_reaction_summary(
    db: Session | None,
    item: FeedItem,
) -> FeedStockReactionSummary | None:
    ticker = first_stock_reaction_ticker(item)
    if db is None or ticker is None:
        return None

    possible_market_impact = infer_feed_possible_market_impact(item)
    rows = (
        db.query(StockPricePoint)
        .filter(StockPricePoint.ticker == ticker)
        .order_by(StockPricePoint.price_date.desc())
        .limit(60)
        .all()
    )
    if not rows:
        return FeedStockReactionSummary(
            ticker=ticker,
            possible_market_impact=possible_market_impact,
            price_reaction="no_price_data",
            summary=(
                f"No stored price data is available for {ticker}; refresh stock prices before "
                "reviewing whether the market reacted."
            ),
        )

    event_price_date, event_price_change_percent = infer_feed_event_price_move(
        sorted(rows, key=lambda row: row.price_date),
        item,
    )
    price_reaction = infer_feed_stock_price_reaction_from_change(
        change_percent=event_price_change_percent,
        possible_market_impact=possible_market_impact,
    )
    return FeedStockReactionSummary(
        ticker=ticker,
        possible_market_impact=possible_market_impact,
        price_reaction=price_reaction,
        event_price_date=event_price_date,
        event_price_change_percent=event_price_change_percent,
        summary=format_feed_stock_reaction_summary(
            ticker=ticker,
            possible_market_impact=possible_market_impact,
            price_reaction=price_reaction,
            event_price_date=event_price_date,
            event_price_change_percent=event_price_change_percent,
        ),
    )


def first_stock_reaction_ticker(item: FeedItem) -> str | None:
    if item.category != "stock_company_event" and item.stock_impact_score < 0.25:
        return None
    for ticker in item.tickers:
        normalized = str(ticker).strip().upper()
        if normalized:
            return normalized
    return None


def infer_feed_possible_market_impact(item: FeedItem) -> str:
    if item.sentiment == "positive" and item.stock_impact_score >= 0.45:
        return "positive"
    if item.sentiment == "negative" and item.stock_impact_score >= 0.45:
        return "negative"
    if item.sentiment == "mixed" or item.stock_impact_score >= 0.35:
        return "mixed"
    return "uncertain"


def infer_feed_stock_price_reaction_from_change(
    change_percent: float | None,
    possible_market_impact: str,
) -> str:
    if change_percent is None:
        return "no_price_data"
    if abs(change_percent) < 0.75:
        return "muted_or_unclear"
    if possible_market_impact == "positive":
        return "aligned_up" if change_percent > 0 else "opposite_move"
    if possible_market_impact == "negative":
        return "aligned_down" if change_percent < 0 else "opposite_move"
    return "muted_or_unclear"


def infer_feed_event_price_move(
    rows: list[StockPricePoint],
    item: FeedItem,
) -> tuple[date | None, float | None]:
    if not rows or item.published_at is None:
        return None, None

    event_date = item.published_at.date()
    for index, point in enumerate(rows):
        if point.price_date < event_date:
            continue
        if index == 0:
            return point.price_date, None
        previous = rows[index - 1]
        if not previous.close_price:
            return point.price_date, None
        change_percent = round(
            ((point.close_price - previous.close_price) / previous.close_price) * 100,
            2,
        )
        return point.price_date, change_percent
    return None, None


def format_feed_stock_reaction_summary(
    ticker: str,
    possible_market_impact: str,
    price_reaction: str,
    event_price_date: date | None,
    event_price_change_percent: float | None,
) -> str:
    if event_price_date is None or event_price_change_percent is None:
        return (
            f"Stored prices do not yet show a comparable close for {ticker} around this item."
        )
    direction = "+" if event_price_change_percent > 0 else ""
    reaction_label = price_reaction.replace("_", " ")
    impact_label = possible_market_impact.replace("_", " ")
    return (
        f"{ticker} moved {direction}{event_price_change_percent:.2f}% on "
        f"{event_price_date.isoformat()}; price reaction is {reaction_label} "
        f"for a {impact_label} market-impact read."
    )


def extract_labeled_summary_parts(text: str | None, labels: list[str]) -> list[str]:
    parts = []
    label_prefixes = tuple(f"{label.lower()}:" for label in labels)
    for line in split_summary_lines(text):
        lowered = line.lower()
        if not lowered.startswith(label_prefixes):
            continue
        _label, value = line.split(":", 1)
        cleaned = value.strip()
        if cleaned:
            parts.append(cleaned)
    return parts


def extract_summary_uncertainties(text: str | None) -> list[str]:
    notes: list[str] = []
    for value in extract_labeled_summary_parts(text, ["Uncertainties"]):
        for note in value.split(";"):
            cleaned = note.strip()
            if cleaned:
                notes.append(cleaned)
    return notes[:3]


def split_summary_lines(text: str | None) -> list[str]:
    if not text:
        return []
    return [line.strip() for line in text.splitlines() if line.strip()]


def is_bullet_line(line: str) -> bool:
    return line.startswith(("- ", "* "))


def strip_bullet_prefix(line: str) -> str:
    return line[2:].strip() if is_bullet_line(line) else line.strip()


def first_sentence(text: str | None) -> str | None:
    if not text:
        return None
    normalized = " ".join(line.strip() for line in text.splitlines() if line.strip())
    if not normalized:
        return None
    for marker in [". ", "? ", "! "]:
        if marker in normalized:
            end = normalized.index(marker) + 1
            return normalized[:end].strip()
    return normalized.strip()


def summary_source_label(item: FeedItem) -> str:
    if item.summary_short or item.summary_detailed:
        return "stored_summary"
    if item.why_it_matters:
        return "why_it_matters"
    return "deterministic"


def delete_feed_item(db: Session, item: NormalizedItem) -> None:
    raw_item_id = item.raw_item_id
    delete_digest_snapshots_containing_item(db=db, item=item)
    db.query(Alert).filter(Alert.item_id == item.id).delete(synchronize_session=False)
    db.query(UserItemAction).filter(UserItemAction.item_id == item.id).delete(
        synchronize_session=False
    )
    db.query(LlmUsageEvent).filter(LlmUsageEvent.item_id == item.id).update(
        {LlmUsageEvent.item_id: None},
        synchronize_session=False,
    )
    db.delete(item)
    db.flush()

    raw_item = db.get(RawItem, raw_item_id)
    raw_item_still_referenced = (
        db.query(NormalizedItem.id).filter(NormalizedItem.raw_item_id == raw_item_id).first()
        is not None
    )
    if raw_item is not None and not raw_item_still_referenced:
        db.delete(raw_item)
    db.commit()


def delete_digest_snapshots_containing_item(db: Session, item: NormalizedItem) -> int:
    item_markers = {
        item.url,
        item.title,
        f'"id": {item.id}',
        f'"item_id": {item.id}',
    }
    snapshots = db.query(DailyDigestSnapshot).all()
    deleted_count = 0
    for snapshot in snapshots:
        searchable_text = "\n".join(
            [
                snapshot.markdown or "",
                json.dumps(snapshot.payload or {}, ensure_ascii=False, sort_keys=True),
            ]
        )
        if any(marker and marker in searchable_text for marker in item_markers):
            db.delete(snapshot)
            deleted_count += 1
    return deleted_count


def build_score_explanation(item: FeedItem) -> str:
    reasons: list[str] = []
    if item.tickers:
        reasons.append(f"matched tickers {', '.join(item.tickers[:3])}")
    if item.topics:
        reasons.append(f"matched topics {', '.join(item.topics[:3])}")
    if item.category:
        category_label = item.category.replace("_", " ")
        if item.category == "product" and item.subcategory:
            category_label = f"{category_label} / {product_use_case_label(item.subcategory)}"
        reasons.append(f"classified as {category_label}")
    if item.source_quality_score >= 0.8:
        reasons.append("high source credibility")
    elif item.source_quality_score < 0.6:
        reasons.append("lower source credibility; review the original source")
    if item.social_signal_score >= 0.65:
        reasons.append("strong source engagement signal")
    if item.cross_source_confirmation_score >= CROSS_SOURCE_CONFIRMATION_SOFT_BONUS:
        reasons.append(
            item.cross_source_confirmation_label or "cross-source confirmation"
        )
    elif item.cross_source_confirmation_score > 0:
        reasons.append(item.cross_source_confirmation_label or "repeated event coverage")
    if item.classification_confidence < 0.6:
        reasons.append("lower classifier confidence")
    if item.importance_score >= 0.75:
        reasons.append("high importance score")
    if item.stock_impact_score >= 0.75:
        reasons.append("high stock-impact score")
    if item.is_saved:
        reasons.append("saved by you")
    if item.is_important:
        reasons.append("marked important by you")
    if item.usefulness_feedback == "useful":
        reasons.append("marked useful by you")
    elif item.usefulness_feedback == "not_useful":
        reasons.append("marked not useful by you")
    if not reasons:
        reasons.append("matched the AI relevance prefilter")
    return "Shown because it " + "; ".join(reasons) + "."


def product_use_case_label(subcategory: str | None) -> str:
    labels = {
        "product_coding": "Coding",
        "product_media": "Media",
        "product_search": "Search",
        "product_education": "Education",
        "product_business": "Business",
        "product_productivity": "Productivity",
        "product_entertainment": "Entertainment",
        "product_general": "General",
    }
    return labels.get(subcategory or "", (subcategory or "General").replace("_", " ").title())


def build_feed_uncertainty_notes(item: FeedItem) -> list[str]:
    notes = extract_summary_uncertainties(item.summary_detailed)
    if item.classification_confidence < 0.6:
        notes.append("Classifier confidence is low, so category and entity labels may need review.")
    if item.source_quality_score < 0.6:
        notes.append("Source credibility is lower than the preferred-source threshold.")
    if item.stock_impact_score >= 0.35 and not item.tickers:
        notes.append("Stock impact was inferred, but no explicit ticker was extracted.")
    if item.stock_impact_score >= 0.35 and item.sentiment == "neutral":
        notes.append("Market direction is unclear from the available signal.")
    if not item.summary_short and not item.summary_detailed:
        notes.append("No generated summary is stored yet; review the original source text.")
    if item.source_name == "Manual Submission":
        notes.append("Manual submissions depend on the supplied URL and note context.")
    unique_notes: list[str] = []
    seen_notes: set[str] = set()
    for note in notes:
        normalized = note.casefold()
        if normalized in seen_notes:
            continue
        seen_notes.add(normalized)
        unique_notes.append(note)
    return unique_notes or ["No major uncertainty flags from the stored item signals."]


def build_personalization_notes(
    item: FeedItem,
    interest_profile: FeedInterestProfile | None,
) -> list[str]:
    if not interest_profile:
        return []

    notes: list[str] = []
    item_source = normalize_interest_source(item.source_name)
    item_symbols = {
        normalize_interest_symbol(value)
        for value in [*item.tickers, *item.companies]
        if normalize_interest_symbol(value)
    }
    searchable_text = build_interest_search_text(item)
    positive_terms = matching_terms(searchable_text, interest_profile.liked_terms)
    negative_terms = matching_terms(searchable_text, interest_profile.disliked_terms)
    positive_symbols = sorted(item_symbols & interest_profile.liked_symbols)
    negative_symbols = sorted(item_symbols & interest_profile.disliked_symbols)

    if item_source and item_source in interest_profile.liked_sources:
        notes.append(f"Source matches items you saved or marked important: {item.source_name}.")
    if positive_symbols:
        notes.append(
            "Entity matches items you saved or marked important: "
            + ", ".join(positive_symbols[:4])
            + "."
        )
    if positive_terms:
        notes.append(
            "Topic/product matches items you saved or marked important: "
            + ", ".join(positive_terms[:4])
            + "."
        )
    if item_source and item_source in interest_profile.disliked_sources:
        notes.append(f"Source matches items you previously hid: {item.source_name}.")
    if negative_symbols:
        notes.append(
            "Entity matches items you previously hid: "
            + ", ".join(negative_symbols[:4])
            + "."
        )
    if negative_terms:
        notes.append(
            "Topic/product matches items you previously hid: "
            + ", ".join(negative_terms[:4])
            + "."
        )
    return notes[:4]


def list_visible_feed_items(
    db: Session,
    limit: int,
    ranking_weights: RankingWeights | dict | None = None,
    preferred_sources: list[str] | None = None,
    blocked_sources: list[str] | None = None,
    language_preferences: list[str] | None = None,
    saved_only: bool = False,
    hidden_only: bool = False,
    topic: str | None = None,
    module: str | None = None,
) -> list[FeedItem]:
    blocked_source_names = normalize_source_names(blocked_sources)
    preferred_languages = normalize_language_codes(language_preferences)
    topic_terms = build_feed_topic_filter_terms(topic)
    module_filter = normalize_feed_module_filter(module)
    query = (
        db.query(NormalizedItem, UserItemAction)
        .outerjoin(
            UserItemAction,
            (UserItemAction.item_id == NormalizedItem.id)
            & (UserItemAction.user_id == LOCAL_USER_ID),
        )
    )
    module_conditions = build_feed_module_conditions(module_filter)
    if module_conditions:
        query = query.filter(or_(*module_conditions))
    if hidden_only:
        query = query.filter(UserItemAction.is_hidden.is_(True))
    else:
        query = query.filter((UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None)))
    if blocked_source_names:
        query = query.filter(~NormalizedItem.source_name.in_(blocked_source_names))
    if preferred_languages:
        query = query.filter(NormalizedItem.language.in_(preferred_languages))
    if saved_only:
        query = query.filter(UserItemAction.is_saved.is_(True))
    if topic_terms:
        topic_conditions = []
        for topic_term in topic_terms:
            pattern = f"%{topic_term}%"
            json_pattern = f'%"{topic_term}"%'
            topic_conditions.extend(
                [
                    cast(NormalizedItem.topics, String).ilike(json_pattern),
                    cast(NormalizedItem.topics, String).ilike(pattern),
                    cast(NormalizedItem.products, String).ilike(pattern),
                    cast(NormalizedItem.companies, String).ilike(pattern),
                    NormalizedItem.title.ilike(pattern),
                    NormalizedItem.summary_short.ilike(pattern),
                    NormalizedItem.summary_detailed.ilike(pattern),
                    NormalizedItem.why_it_matters.ilike(pattern),
                ]
            )
        query = query.filter(or_(*topic_conditions))

    rows = (
        query
        .order_by(
            UserItemAction.is_important.desc().nullslast(),
            NormalizedItem.importance_score.desc(),
            NormalizedItem.relevance_score.desc(),
            NormalizedItem.published_at.desc().nullslast(),
            NormalizedItem.created_at.desc(),
        )
        .limit(max(limit, 100))
        .all()
    )
    items = [serialize_feed_item(item, action) for item, action in rows]
    return rank_feed_items(
        items,
        ranking_weights=ranking_weights,
        preferred_sources=preferred_sources,
        interest_profile=build_feed_interest_profile(db),
    )[:limit]


def export_saved_items_markdown(
    db: Session,
    include_read: bool = True,
    limit: int = 100,
) -> SavedItemsMarkdownExport:
    items = list_visible_feed_items(
        db=db,
        limit=limit,
        saved_only=True,
    )
    if not include_read:
        items = [item for item in items if not item.is_read]

    generated_at = datetime.now(UTC)
    lines = [
        "# SignalLens Saved Items",
        "",
        f"Generated: {generated_at.isoformat()}",
        f"Items: {len(items)}",
        "",
    ]
    if not items:
        lines.append("_No saved items matched this export._")
    for index, item in enumerate(order_saved_items_for_export(items), start=1):
        summary = item.summary_short or item.why_it_matters or item.summary_detailed
        status = "read" if item.is_read else "read later"
        metadata = [
            item.source_name,
            format_export_datetime(item.published_at),
            status,
        ]
        metadata = [value for value in metadata if value]
        labels = export_item_labels(item)
        audit_labels = export_item_audit_labels(item)

        lines.extend(
            [
                f"## {index}. [{item.title}]({item.url})",
                "",
                f"- Source: {' | '.join(metadata)}",
            ]
        )
        if labels:
            lines.append(f"- Labels: {', '.join(labels)}")
        if audit_labels:
            lines.append(f"- Signals: {', '.join(audit_labels)}")
        if item.manual_tags:
            lines.append(f"- Manual tags: {', '.join(item.manual_tags)}")
        if item.personal_note:
            lines.append(f"- Personal note: {item.personal_note}")
        if item.is_read and item.read_at:
            lines.append(f"- Read at: {format_export_datetime(item.read_at)}")
        if summary:
            lines.append(f"- Summary: {summary}")
        lines.append("")

    return SavedItemsMarkdownExport(
        generated_at=generated_at,
        item_count=len(items),
        markdown="\n".join(lines).rstrip() + "\n",
    )


def order_saved_items_for_export(items: list[FeedItem]) -> list[FeedItem]:
    return sorted(
        items,
        key=lambda item: (
            item.is_read,
            export_sort_timestamp(item.published_at or item.read_at),
        ),
        reverse=False,
    )


def export_item_labels(item: FeedItem) -> list[str]:
    labels = [
        *item.tickers,
        *item.companies,
        *item.products,
        *item.technologies,
        *item.topics,
    ]
    seen = set()
    result = []
    for label in labels:
        normalized = " ".join(str(label).strip().split())
        key = normalized.lower()
        if normalized and key not in seen:
            result.append(normalized)
            seen.add(key)
    return result[:12]


def export_item_audit_labels(item: FeedItem) -> list[str]:
    labels: list[str] = []
    labels.append("AI-related" if item.is_ai_related else "not AI-related")
    if item.market_impact_type != "none":
        labels.append(f"market impact: {format_export_label(item.market_impact_type)}")
    if item.social_signal_score >= 0.05:
        labels.append(f"social signal {round(item.social_signal_score * 100)}%")
    if item.stock_impact_score >= 0.05:
        labels.append(f"stock impact {round(item.stock_impact_score * 100)}%")
    if item.classification_confidence < 0.7:
        labels.append(f"classifier confidence {round(item.classification_confidence * 100)}%")
    return labels


def format_export_label(value: str) -> str:
    return value.replace("_", " ").replace("-", " ")


def format_export_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


def export_sort_timestamp(value: datetime | None) -> datetime:
    if value is None:
        return datetime.min.replace(tzinfo=UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def rank_feed_items(
    items: list[FeedItem],
    ranking_weights: RankingWeights | dict | None = None,
    preferred_sources: list[str] | None = None,
    interest_profile: FeedInterestProfile | None = None,
    now: datetime | None = None,
) -> list[FeedItem]:
    weights = resolve_ranking_weights(ranking_weights)
    reference_time = now or datetime.now(UTC)
    preferred_source_names = normalize_source_names(preferred_sources)
    confirmation_scores = annotate_cross_source_confirmation(items)
    return sorted(
        items,
        key=lambda item: (
            item.is_important,
            weighted_feed_score(
                item,
                weights,
                now=reference_time,
                preferred_sources=preferred_source_names,
                interest_profile=interest_profile,
                confirmation_scores=confirmation_scores,
            ),
            item.published_at or datetime.min.replace(tzinfo=UTC),
        ),
        reverse=True,
    )


def weighted_feed_score(
    item: FeedItem,
    weights: RankingWeights,
    now: datetime | None = None,
    preferred_sources: set[str] | None = None,
    interest_profile: FeedInterestProfile | None = None,
    confirmation_scores: dict[int, float] | None = None,
) -> float:
    reference_time = now or datetime.now(UTC)
    source_bonus = (
        PREFERRED_SOURCE_RANKING_BONUS
        if preferred_sources and item.source_name in preferred_sources
        else 0
    )
    saved_bonus = SAVED_ITEM_RANKING_BONUS if item.is_saved else 0
    interest_bonus = feed_interest_bonus(item=item, interest_profile=interest_profile)
    feedback_adjustment = feedback_interest_adjustment(
        item=item,
        interest_profile=interest_profile,
    )
    confirmation_bonus = confirmation_scores.get(item.id, 0) if confirmation_scores else 0
    return round(
        weights.relevance * item.relevance_score
        + weights.importance * item.importance_score
        + weights.novelty * item.novelty_score
        + weights.source_quality * item.source_quality_score
        + weights.social_signal * item.social_signal_score
        + weights.stock_impact * item.stock_impact_score
        + weights.freshness * freshness_score(item, now=reference_time)
        + source_bonus
        + saved_bonus
        + interest_bonus
        + feedback_adjustment
        + confirmation_bonus,
        4,
    )


def build_cross_source_confirmation_scores(items: list[FeedItem]) -> dict[int, float]:
    return {
        item_id: context["score"]
        for item_id, context in build_cross_source_confirmation_context(items).items()
    }


def annotate_cross_source_confirmation(items: list[FeedItem]) -> dict[int, float]:
    context = build_cross_source_confirmation_context(items)
    for item in items:
        item_context = context.get(item.id)
        if item_context is None:
            item.cross_source_confirmation_score = 0
            item.cross_source_confirmation_label = None
            continue
        item.cross_source_confirmation_score = item_context["score"]
        item.cross_source_confirmation_label = item_context["label"]
    return {item_id: item_context["score"] for item_id, item_context in context.items()}


def annotate_item_cross_source_confirmation(db: Session, item: FeedItem) -> None:
    nearby_items = list_visible_feed_items(db=db, limit=200)
    match = next((candidate for candidate in nearby_items if candidate.id == item.id), None)
    if match is None:
        item.cross_source_confirmation_score = 0
        item.cross_source_confirmation_label = None
        return
    item.cross_source_confirmation_score = match.cross_source_confirmation_score
    item.cross_source_confirmation_label = match.cross_source_confirmation_label


def build_cross_source_confirmation_context(
    items: list[FeedItem],
) -> dict[int, dict[str, float | str]]:
    grouped: dict[str, list[FeedItem]] = defaultdict(list)
    for item in items:
        grouped[confirmation_group_key(item)].append(item)

    context: dict[int, dict[str, float | str]] = {}
    for group_items in grouped.values():
        if len(group_items) <= 1:
            continue
        source_count = len({item.source_name for item in group_items if item.source_name})
        if source_count >= 3 or (source_count >= 2 and len(group_items) >= 3):
            bonus = CROSS_SOURCE_CONFIRMATION_RANKING_BONUS
            label = "strong cross-source confirmation"
        elif source_count >= 2:
            bonus = CROSS_SOURCE_CONFIRMATION_SOFT_BONUS
            label = "cross-source confirmation"
        else:
            bonus = REPEATED_EVENT_RANKING_BONUS
            label = "repeated event coverage"
        for item in group_items:
            context[item.id] = {"score": bonus, "label": label}
    return context


def confirmation_group_key(item: FeedItem) -> str:
    strong_terms = [*item.tickers, *item.products]
    if strong_terms:
        key_parts = ["strong", item.category, *sorted(term.lower() for term in strong_terms)]
        signature = confirmation_signature_term(item)
        if signature:
            key_parts.append(f"event:{signature}")
        return "|".join(key_parts)

    title_terms = extract_confirmation_title_terms(item.title)
    topic_terms = [topic.lower() for topic in item.topics[:4]]
    key_terms = sorted(set([*topic_terms, *title_terms[:4]]))
    return "|".join([item.category, *key_terms]) if key_terms else f"item:{item.id}"


def confirmation_signature_term(item: FeedItem) -> str | None:
    text = " ".join(
        part
        for part in [
            item.title,
            item.summary_short or "",
            item.why_it_matters or "",
            " ".join(item.topics[:4]),
        ]
        if part
    ).lower()
    for term in CONFIRMATION_SIGNATURE_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", text):
            return term
    for term in extract_confirmation_title_terms(item.title):
        return term
    return None


def extract_confirmation_title_terms(title: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9-]{2,}", title.lower())
    return [word for word in words if word not in CONFIRMATION_STOP_WORDS]


def resolve_ranking_weights(value: RankingWeights | dict | None) -> RankingWeights:
    if isinstance(value, RankingWeights):
        return value
    if isinstance(value, dict):
        return RankingWeights(**value)
    return RankingWeights()


def freshness_score(item: FeedItem, now: datetime | None = None) -> float:
    if item.published_at is None:
        return 0
    reference_time = now or datetime.now(UTC)
    published_at = item.published_at
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)
    age_hours = max(0, (reference_time - published_at).total_seconds() / 3600)
    return round(max(0, 1 - age_hours / 72), 4)


def social_signal_score_for_item(item: NormalizedItem) -> float:
    raw_metadata = item.raw_item.raw_metadata if item.raw_item else {}
    source_name = item.source_name.lower()

    if "github" in source_name:
        return bounded_social_score(
            0.45 * scaled_metric(raw_metadata.get("stars"), 5000)
            + 0.35 * scaled_metric(raw_metadata.get("stars_per_day"), 50)
            + 0.20 * scaled_metric(raw_metadata.get("forks"), 1000)
        )
    if "hacker news" in source_name:
        return bounded_social_score(
            0.60 * scaled_metric(raw_metadata.get("score"), 500)
            + 0.30 * scaled_metric(raw_metadata.get("descendants"), 200)
            + 0.10 * scaled_metric(raw_metadata.get("top_comment_count"), 10)
        )
    if "reddit" in source_name:
        return bounded_social_score(
            0.62 * scaled_metric(raw_metadata.get("score"), 1000)
            + 0.38 * scaled_metric(raw_metadata.get("comments_count"), 300)
        )
    if "product hunt" in source_name:
        return bounded_social_score(
            0.70 * scaled_metric(raw_metadata.get("votes_count"), 1000)
            + 0.30 * scaled_metric(raw_metadata.get("comments_count"), 100)
        )
    if "hugging face" in source_name:
        if raw_metadata.get("hf_kind") == "space":
            return bounded_social_score(0.70 * scaled_metric(raw_metadata.get("likes"), 1000))
        return bounded_social_score(
            0.55 * scaled_metric(raw_metadata.get("downloads"), 100000)
            + 0.45 * scaled_metric(raw_metadata.get("likes"), 3000)
        )

    return bounded_social_score(
        0.45 * scaled_metric(first_metadata_value(raw_metadata, "likes", "like_count"), 1000)
        + 0.30
        * scaled_metric(
            first_metadata_value(raw_metadata, "comments", "comments_count", "reply_count"),
            200,
        )
        + 0.25 * scaled_metric(first_metadata_value(raw_metadata, "views", "view_count"), 50000)
        + 0.20
        * scaled_metric(
            first_metadata_value(
                raw_metadata,
                "collects",
                "collects_count",
                "saves",
                "save_count",
                "favorites",
                "bookmarks",
            ),
            500,
        )
        + 0.10
        * scaled_metric(
            first_metadata_value(
                raw_metadata,
                "reposts",
                "reposts_count",
                "shares",
                "share_count",
                "retweets",
            ),
            300,
        )
    )


def build_public_engagement_metrics(item: NormalizedItem) -> list[FeedPublicEngagementMetric]:
    raw_metadata = item.raw_item.raw_metadata if item.raw_item else {}
    if "reddit" in item.source_name.lower():
        return build_reddit_public_engagement_metrics(raw_metadata)
    metric_defs = [
        ("likes", "Likes", ("likes", "like_count")),
        ("comments", "Comments", ("comments", "comments_count", "reply_count")),
        ("views", "Views", ("views", "view_count")),
        (
            "collects",
            "Collects",
            ("collects", "collects_count", "saves", "save_count", "favorites", "bookmarks"),
        ),
        ("reposts", "Reposts", ("reposts", "reposts_count", "shares", "share_count", "retweets")),
    ]
    metrics: list[FeedPublicEngagementMetric] = []
    for key, label, metadata_keys in metric_defs:
        value = first_metadata_value(raw_metadata, *metadata_keys)
        parsed = parse_public_engagement_value(value)
        if parsed is not None:
            metrics.append(FeedPublicEngagementMetric(key=key, label=label, value=parsed))
    return metrics


def build_reddit_public_engagement_metrics(
    raw_metadata: dict,
) -> list[FeedPublicEngagementMetric]:
    metric_defs = [
        ("upvotes", "Upvotes", ("score",)),
        ("comments", "Comments", ("comments_count",)),
    ]
    metrics: list[FeedPublicEngagementMetric] = []
    for key, label, metadata_keys in metric_defs:
        value = first_metadata_value(raw_metadata, *metadata_keys)
        parsed = parse_public_engagement_value(value)
        if parsed is not None:
            metrics.append(FeedPublicEngagementMetric(key=key, label=label, value=parsed))
    return metrics


def parse_public_engagement_value(value: object | None) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(str(value).replace(",", ""))
    except ValueError:
        return None
    if parsed < 0:
        return None
    return int(parsed)


def first_metadata_value(metadata: dict, *keys: str) -> object | None:
    for key in keys:
        value = metadata.get(key)
        if value not in (None, ""):
            return value
    return None


def scaled_metric(value: object, denominator: float) -> float:
    if denominator <= 0:
        return 0
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0
    return min(max(parsed, 0) / denominator, 1)


def bounded_social_score(value: float) -> float:
    return round(min(max(value, 0), 1), 3)


def normalize_source_names(values: list[str] | None) -> set[str]:
    return {str(value).strip() for value in values or [] if str(value).strip()}


def normalize_language_codes(values: list[str] | None) -> set[str]:
    normalized_values = set()
    for value in values or []:
        normalized = str(value).strip().lower()
        if normalized in {"english", "en-us", "en_us"}:
            normalized = "en"
        elif normalized in {"chinese", "zh-cn", "zh_cn", "cn"}:
            normalized = "zh"
        if normalized:
            normalized_values.add(normalized)
    return normalized_values


def normalize_feed_topic_filter(value: str | None) -> str | None:
    normalized = " ".join(str(value or "").strip().replace("-", " ").split())
    return normalized.lower() or None


def build_feed_topic_filter_terms(value: str | None) -> set[str]:
    normalized = normalize_feed_topic_filter(value)
    raw = str(value or "").strip().lower()
    terms = {term for term in [normalized, raw] if term}
    if normalized and normalized.startswith("ai "):
        terms.add(normalized.removeprefix("ai ").strip())
    for term in list(terms):
        words = term.split()
        if len(words) > 1 and words[-1].endswith("s") and len(words[-1]) > 3:
            terms.add(" ".join([*words[:-1], words[-1][:-1]]))
    return {term for term in terms if term}


def normalize_feed_module_filter(value: str | None) -> str | None:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "ai_trends": "trends",
        "benchmark_evaluation": "research",
        "funding_mna": "stocks",
        "infrastructure": "trends",
        "open_source_release": "trends",
        "policy_regulation": "trends",
        "technical_trend": "trends",
        "technical_trends": "trends",
        "ai_research": "research",
        "ai_products": "products",
        "product": "products",
        "ai_stocks": "stocks",
        "stock": "stocks",
        "stock_company_event": "stocks",
        "chinese_social": "chinese",
        "chinese_social_trends": "chinese",
        "tutorial_opinion": "trends",
        "social_trend": "chinese",
    }
    normalized = aliases.get(normalized, normalized)
    return (
        normalized
        if normalized in {"trends", "research", "products", "stocks", "chinese"}
        else None
    )


def build_feed_module_conditions(module: str | None) -> list:
    if module == "trends":
        return [
            NormalizedItem.category.in_(
                [
                    "technical_trend",
                    "policy_regulation",
                    "infrastructure",
                    "open_source_release",
                    "tutorial_opinion",
                ]
            )
        ]
    if module == "research":
        return [NormalizedItem.category.in_(["research", "benchmark_evaluation"])]
    if module == "products":
        return [
            NormalizedItem.category == "product",
            cast(NormalizedItem.products, String) != "[]",
            NormalizedItem.source_name.ilike("%Product Hunt%"),
        ]
    if module == "stocks":
        return [
            NormalizedItem.category.in_(["stock_company_event", "funding_mna"]),
            cast(NormalizedItem.tickers, String) != "[]",
            NormalizedItem.stock_impact_score >= 0.35,
        ]
    if module == "chinese":
        return [
            NormalizedItem.category == "social_trend",
            NormalizedItem.language == "zh",
            NormalizedItem.source_name.ilike("%Chinese%"),
        ]
    return []


def build_feed_interest_profile(db: Session) -> FeedInterestProfile:
    symbols: set[str] = set()
    terms: set[str] = set()
    liked_symbols: set[str] = set()
    liked_terms: set[str] = set()
    liked_sources: set[str] = set()
    disliked_symbols: set[str] = set()
    disliked_terms: set[str] = set()
    disliked_sources: set[str] = set()

    stocks = db.query(StockWatchlistItem).filter(StockWatchlistItem.user_id == LOCAL_USER_ID).all()
    stock_items = stocks or initial_stock_watchlist()
    for stock in stock_items:
        symbols.update(
            normalize_interest_symbol(value)
            for value in [stock.ticker, *stock.related_companies]
        )
        terms.update(
            normalize_interest_term(value)
            for value in [
                stock.company_name,
                *stock.related_keywords,
                *stock.related_ai_themes,
            ]
        )

    topics = db.query(TopicWatchlistItem).filter(TopicWatchlistItem.user_id == LOCAL_USER_ID).all()
    topic_items = topics or initial_topic_watchlist()
    for topic in topic_items:
        terms.update(
            normalize_interest_term(value)
            for value in [topic.topic, topic.label, topic.category, *topic.related_terms]
        )

    products = (
        db.query(ProductWatchlistItem)
        .filter(ProductWatchlistItem.user_id == LOCAL_USER_ID)
        .all()
    )
    product_items = products or initial_product_watchlist()
    for product in product_items:
        terms.update(
            normalize_interest_term(value)
            for value in [product.category, product.label, *product.related_terms]
        )

    companies = (
        db.query(CompanyWatchlistItem)
        .filter(CompanyWatchlistItem.user_id == LOCAL_USER_ID)
        .all()
    )
    company_items = companies or initial_company_watchlist()
    for company in company_items:
        if company.ticker:
            symbols.add(normalize_interest_symbol(company.ticker))
        terms.update(
            normalize_interest_term(value)
            for value in [
                company.company_key,
                company.company_name,
                company.category,
                *company.related_terms,
            ]
        )

    feedback_rows = (
        db.query(NormalizedItem, UserItemAction)
        .join(
            UserItemAction,
            (UserItemAction.item_id == NormalizedItem.id)
            & (UserItemAction.user_id == LOCAL_USER_ID),
        )
        .filter(
            (UserItemAction.is_saved.is_(True))
            | (UserItemAction.is_important.is_(True))
            | (UserItemAction.is_hidden.is_(True))
            | (UserItemAction.usefulness_feedback.in_(("useful", "not_useful")))
        )
        .all()
    )
    for item, action in feedback_rows:
        feedback_symbols = feedback_symbols_for_item(item)
        feedback_terms = feedback_terms_for_item(item)
        source_name = normalize_interest_source(item.source_name)
        feedback = normalize_usefulness_feedback(action.usefulness_feedback)
        if action.is_saved or action.is_important or feedback == "useful":
            liked_symbols.update(feedback_symbols)
            liked_terms.update(feedback_terms)
            if source_name:
                liked_sources.add(source_name)
        if action.is_hidden or feedback == "not_useful":
            disliked_symbols.update(feedback_symbols)
            disliked_terms.update(feedback_terms)
            if source_name:
                disliked_sources.add(source_name)

    return FeedInterestProfile(
        symbols=frozenset(symbol for symbol in symbols if symbol),
        terms=frozenset(term for term in terms if term),
        liked_symbols=frozenset(symbol for symbol in liked_symbols if symbol),
        liked_terms=frozenset(term for term in liked_terms if term),
        liked_sources=frozenset(source for source in liked_sources if source),
        disliked_symbols=frozenset(symbol for symbol in disliked_symbols if symbol),
        disliked_terms=frozenset(term for term in disliked_terms if term),
        disliked_sources=frozenset(source for source in disliked_sources if source),
    )


def feed_interest_bonus(
    item: FeedItem,
    interest_profile: FeedInterestProfile | None,
) -> float:
    if not interest_profile:
        return 0

    matches = 0
    item_symbols = {
        normalize_interest_symbol(value)
        for value in [*item.tickers, *item.companies]
        if normalize_interest_symbol(value)
    }
    if item_symbols & interest_profile.symbols:
        matches += 1

    searchable_text = build_interest_search_text(item)
    for term in interest_profile.terms:
        if term in searchable_text:
            matches += 1
            if matches >= 3:
                break

    return round(min(0.12, matches * 0.04), 4)


def feedback_interest_adjustment(
    item: FeedItem,
    interest_profile: FeedInterestProfile | None,
) -> float:
    if not interest_profile:
        return 0

    item_source = normalize_interest_source(item.source_name)
    item_symbols = {
        normalize_interest_symbol(value)
        for value in [*item.tickers, *item.companies]
        if normalize_interest_symbol(value)
    }
    searchable_text = build_interest_search_text(item)
    positive_matches = count_feedback_matches(
        source=item_source,
        symbols=item_symbols,
        text=searchable_text,
        profile_sources=interest_profile.liked_sources,
        profile_symbols=interest_profile.liked_symbols,
        profile_terms=interest_profile.liked_terms,
    )
    negative_matches = count_feedback_matches(
        source=item_source,
        symbols=item_symbols,
        text=searchable_text,
        profile_sources=interest_profile.disliked_sources,
        profile_symbols=interest_profile.disliked_symbols,
        profile_terms=interest_profile.disliked_terms,
    )
    positive_adjustment = min(
        MAX_FEEDBACK_INTEREST_BONUS,
        positive_matches * FEEDBACK_INTEREST_MATCH_BONUS,
    )
    negative_adjustment = min(
        MAX_FEEDBACK_INTEREST_PENALTY,
        negative_matches * FEEDBACK_INTEREST_MATCH_PENALTY,
    )
    return round(positive_adjustment - negative_adjustment, 4)


def count_feedback_matches(
    source: str,
    symbols: set[str],
    text: str,
    profile_sources: frozenset[str],
    profile_symbols: frozenset[str],
    profile_terms: frozenset[str],
) -> int:
    matches = 0
    if source and source in profile_sources:
        matches += 1
    if symbols & profile_symbols:
        matches += 1
    for term in profile_terms:
        if term in text:
            matches += 1
            if matches >= 4:
                break
    return matches


def matching_terms(text: str, terms: frozenset[str]) -> list[str]:
    return sorted(term for term in terms if term in text)


def feedback_symbols_for_item(item: NormalizedItem) -> set[str]:
    return {
        normalize_interest_symbol(value)
        for value in [*(item.tickers or []), *(item.companies or [])]
        if normalize_interest_symbol(value)
    }


def feedback_terms_for_item(item: NormalizedItem) -> set[str]:
    return {
        normalize_interest_term(value)
        for value in [
            item.category,
            item.subcategory or "",
            *(item.topics or []),
            *(item.products or []),
            *(item.companies or []),
        ]
        if normalize_interest_term(value)
    }


def build_interest_search_text(item: FeedItem) -> str:
    parts = [
        item.title,
        item.source_name,
        item.category,
        item.subcategory or "",
        item.summary_short or "",
        item.summary_detailed or "",
        item.why_it_matters or "",
        *item.topics,
        *item.products,
        *item.companies,
    ]
    return "\n".join(part.lower() for part in parts if part)


def normalize_interest_symbol(value: str) -> str:
    return value.strip().upper().removeprefix("$")


def normalize_interest_source(value: str) -> str:
    return " ".join(value.strip().lower().split())


def normalize_interest_term(value: str) -> str:
    normalized = " ".join(value.strip().lower().replace("-", " ").split())
    generic_terms = {
        "ai",
        "app",
        "apps",
        "tool",
        "tools",
        "launch",
        "technology",
        "nasdaq",
    }
    if len(normalized) < 3 or normalized in generic_terms:
        return ""
    return normalized


def get_action(db: Session, item_id: int) -> UserItemAction | None:
    return (
        db.query(UserItemAction)
        .filter(UserItemAction.user_id == LOCAL_USER_ID, UserItemAction.item_id == item_id)
        .one_or_none()
    )


def get_or_create_action(db: Session, item_id: int) -> UserItemAction:
    action = get_action(db, item_id)
    if action:
        return action

    action = UserItemAction(user_id=LOCAL_USER_ID, item_id=item_id)
    db.add(action)
    db.flush()
    return action


def update_item_action(
    db: Session,
    item: NormalizedItem,
    action_name: str,
) -> FeedItem:
    action = get_or_create_action(db, item.id)
    if action_name == "save":
        action.is_saved = True
    elif action_name == "unsave":
        action.is_saved = False
    elif action_name == "hide":
        action.is_hidden = True
    elif action_name == "unhide":
        action.is_hidden = False
    elif action_name == "mark-important":
        action.is_important = True
    elif action_name == "unmark-important":
        action.is_important = False
    elif action_name == "mark-read":
        action.is_read = True
        action.read_at = datetime.now(UTC)
    elif action_name == "mark-unread":
        action.is_read = False
        action.read_at = None
    elif action_name == "mark-useful":
        action.usefulness_feedback = "useful"
        action.usefulness_feedback_at = datetime.now(UTC)
    elif action_name == "mark-not-useful":
        action.usefulness_feedback = "not_useful"
        action.usefulness_feedback_at = datetime.now(UTC)
    elif action_name == "clear-feedback":
        action.usefulness_feedback = None
        action.usefulness_feedback_at = None
    else:
        raise ValueError(f"Unsupported action: {action_name}")

    db.add(action)
    db.commit()
    db.refresh(action)
    return serialize_feed_item(item, action)


def update_item_personal_metadata(
    db: Session,
    item: NormalizedItem,
    personal_note: str | None,
    manual_tags: list[str],
) -> FeedItemDetail:
    action = get_or_create_action(db, item.id)
    normalized_note = str(personal_note or "").strip()
    action.personal_note = normalized_note or None
    action.manual_tags = normalize_manual_tags(manual_tags)

    db.add(action)
    db.commit()
    db.refresh(action)
    return serialize_feed_item_detail(
        item,
        action,
        interest_profile=build_feed_interest_profile(db),
        db=db,
    )


def normalize_manual_tags(values: list[str] | None) -> list[str]:
    seen = set()
    tags = []
    for value in values or []:
        normalized = " ".join(str(value).strip().split())
        key = normalized.lower()
        if normalized and key not in seen:
            tags.append(normalized[:60])
            seen.add(key)
    return tags[:12]


def normalize_usefulness_feedback(value: str | None) -> str | None:
    normalized = str(value or "").strip().lower().replace("-", "_")
    if normalized in {"useful", "not_useful"}:
        return normalized
    return None
