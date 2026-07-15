import re
from collections import Counter, defaultdict
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.schemas.events import EventCluster, EventClusterMarketReaction, EventClusterTimelineItem
from app.schemas.feed import FeedItem
from app.schemas.preferences import RankingWeights
from app.schemas.watchlist import StockMarketSnapshot
from app.services.feed_actions import list_visible_feed_items
from app.services.scoring import TICKER_ALIASES, detect_tickers
from app.services.watchlist import build_stock_market_snapshot

STOP_WORDS = {
    "about",
    "after",
    "from",
    "into",
    "more",
    "new",
    "news",
    "over",
    "that",
    "their",
    "this",
    "with",
    "using",
}

EVENT_SIGNATURE_TERMS = [
    "earnings",
    "guidance",
    "upgrade",
    "downgrade",
    "analyst",
    "partnership",
    "deal",
    "chip",
    "silicon",
    "gpu",
    "memory",
    "hbm",
    "datacenter",
    "data-center",
    "capex",
    "launch",
    "release",
    "model",
    "benchmark",
    "agent",
    "agents",
    "inference",
    "training",
    "supply",
    "export",
]

GENERIC_TITLE_TERMS = {
    "announces",
    "announced",
    "announce",
    "discuss",
    "discusses",
    "discussion",
    "report",
    "reports",
    "says",
    "show",
    "shows",
    "unveil",
    "unveils",
    "update",
    "updates",
}


def list_event_clusters(
    db: Session,
    limit: int = 12,
    items_limit: int = 200,
    min_items: int = 1,
    ranking_weights: RankingWeights | dict | None = None,
    preferred_sources: list[str] | None = None,
    blocked_sources: list[str] | None = None,
) -> list[EventCluster]:
    items = list_visible_feed_items(
        db=db,
        limit=items_limit,
        ranking_weights=ranking_weights,
        preferred_sources=preferred_sources,
        blocked_sources=blocked_sources,
    )
    clusters = build_event_clusters_from_items(items=items, limit=limit, min_items=min_items)
    return [attach_market_context(db=db, cluster=cluster) for cluster in clusters]


def get_event_cluster(
    db: Session,
    cluster_key: str,
    items_limit: int = 500,
    min_items: int = 1,
    ranking_weights: RankingWeights | dict | None = None,
    preferred_sources: list[str] | None = None,
    blocked_sources: list[str] | None = None,
) -> EventCluster | None:
    items = list_visible_feed_items(
        db=db,
        limit=items_limit,
        ranking_weights=ranking_weights,
        preferred_sources=preferred_sources,
        blocked_sources=blocked_sources,
    )
    grouped = group_items_by_cluster(items)
    cluster_items = grouped.get(cluster_key, [])
    if len(cluster_items) < min_items:
        return None
    return attach_market_context(
        db=db,
        cluster=build_event_cluster(cluster_key=cluster_key, items=cluster_items),
    )


def build_event_clusters_from_items(
    items: list[FeedItem],
    limit: int = 12,
    min_items: int = 1,
) -> list[EventCluster]:
    grouped = group_items_by_cluster(items)
    clusters = [
        build_event_cluster(cluster_key=cluster_key, items=cluster_items)
        for cluster_key, cluster_items in grouped.items()
        if len(cluster_items) >= min_items
    ]
    clusters.sort(
        key=lambda cluster: (
            cluster.item_count,
            cluster.top_score,
            cluster.last_seen_at or datetime.min,
        ),
        reverse=True,
    )
    return clusters[:limit]


def group_items_by_cluster(items: list[FeedItem]) -> dict[str, list[FeedItem]]:
    grouped: dict[str, list[FeedItem]] = defaultdict(list)
    for item in items:
        grouped[build_cluster_key(item)].append(item)
    return grouped


def build_event_cluster(cluster_key: str, items: list[FeedItem]) -> EventCluster:
    ranked_items = sorted(
        items,
        key=lambda item: (
            item.is_important,
            item.importance_score,
            item.relevance_score,
            item.published_at or datetime.min,
        ),
        reverse=True,
    )
    representative = ranked_items[0]
    timestamps = [item.published_at for item in items if item.published_at is not None]
    topics = most_common_values(value for item in items for value in item.topics)
    tickers = most_common_values(value for item in items for value in item_tickers(item))
    sources = most_common_values(item.source_name for item in items)
    timeline = build_cluster_timeline(items)
    first_seen_at = min(timestamps) if timestamps else None
    last_seen_at = max(timestamps) if timestamps else None
    earliest_source = timeline[0].source_name if timeline else None
    top_score = max(item.importance_score for item in items)
    source_count = len(sources)
    duplicate_item_count = max(len(items) - source_count, 0)
    confirmation_level = cluster_confirmation_level(
        item_count=len(items),
        source_count=source_count,
    )

    return EventCluster(
        cluster_key=cluster_key,
        title=build_cluster_title(representative, item_count=len(items), sources=sources),
        main_summary=build_cluster_main_summary(
            representative,
            item_count=len(items),
            sources=sources,
        ),
        explanation=build_cluster_explanation(
            representative=representative,
            items=ranked_items,
            sources=sources,
            topics=topics,
            tickers=tickers,
        ),
        uncertainty_notes=build_cluster_uncertainty_notes(
            items=items,
            sources=sources,
            tickers=tickers,
            first_seen_at=first_seen_at,
            last_seen_at=last_seen_at,
        ),
        category=representative.category,
        topics=topics[:8],
        tickers=tickers[:6],
        sources=sources,
        item_count=len(items),
        source_count=source_count,
        duplicate_item_count=duplicate_item_count,
        confirmation_level=confirmation_level,
        top_score=top_score,
        importance_score=top_score,
        confidence=compute_cluster_confidence(items=items, sources=sources),
        earliest_source=earliest_source,
        first_seen_at=first_seen_at,
        last_seen_at=last_seen_at,
        latest_update_at=last_seen_at,
        timeline=timeline,
        representative_item=representative,
        items=ranked_items[:5],
    )


def attach_market_context(db: Session, cluster: EventCluster) -> EventCluster:
    if not cluster.tickers:
        return cluster

    ticker = cluster.tickers[0].upper()
    cluster.related_market_ticker = ticker
    cluster.related_market = build_stock_market_snapshot(db=db, ticker=ticker)
    cluster.related_market_reaction = build_cluster_market_reaction(
        ticker=ticker,
        market=cluster.related_market,
        representative=cluster.representative_item,
    )
    return cluster


def build_cluster_market_reaction(
    *,
    ticker: str,
    market: StockMarketSnapshot | None,
    representative: FeedItem,
) -> EventClusterMarketReaction | None:
    if market is None or not market.history or representative.published_at is None:
        return None

    event_price_date, event_price_change_percent = infer_cluster_event_price_move(
        market=market,
        event_date=representative.published_at.date(),
    )
    possible_market_impact = infer_cluster_possible_market_impact(representative)
    price_reaction = infer_cluster_price_reaction(
        possible_market_impact=possible_market_impact,
        change_percent=event_price_change_percent,
    )
    return EventClusterMarketReaction(
        ticker=ticker,
        possible_market_impact=possible_market_impact,
        price_reaction=price_reaction,
        event_price_date=event_price_date,
        event_price_change_percent=event_price_change_percent,
        summary=format_cluster_market_reaction_summary(
            ticker=ticker,
            possible_market_impact=possible_market_impact,
            price_reaction=price_reaction,
            event_price_date=event_price_date,
            event_price_change_percent=event_price_change_percent,
        ),
    )


def infer_cluster_event_price_move(
    *,
    market: StockMarketSnapshot,
    event_date: date,
) -> tuple[date | None, float | None]:
    history = sorted(market.history, key=lambda point: point.price_date)
    for index, point in enumerate(history):
        if point.price_date < event_date:
            continue
        if index == 0:
            return point.price_date, None
        previous = history[index - 1]
        if not previous.close_price:
            return point.price_date, None
        change_percent = round(
            ((point.close_price - previous.close_price) / previous.close_price) * 100,
            2,
        )
        return point.price_date, change_percent
    return None, None


def infer_cluster_possible_market_impact(item: FeedItem) -> str:
    if item.sentiment == "positive" and item.stock_impact_score >= 0.45:
        return "positive"
    if item.sentiment == "negative" and item.stock_impact_score >= 0.45:
        return "negative"
    return "uncertain"


def infer_cluster_price_reaction(
    *,
    possible_market_impact: str,
    change_percent: float | None,
) -> str:
    if change_percent is None:
        return "no_comparable_price"
    if abs(change_percent) < 0.5:
        return "muted_or_unclear"
    if possible_market_impact == "positive":
        return "aligned_up" if change_percent > 0 else "opposite_move"
    if possible_market_impact == "negative":
        return "aligned_down" if change_percent < 0 else "opposite_move"
    return "muted_or_unclear"


def format_cluster_market_reaction_summary(
    *,
    ticker: str,
    possible_market_impact: str,
    price_reaction: str,
    event_price_date: date | None,
    event_price_change_percent: float | None,
) -> str:
    if event_price_date is None or event_price_change_percent is None:
        return (
            f"Stored prices do not yet show a comparable close for {ticker} around this "
            "cluster."
        )

    direction = "+" if event_price_change_percent > 0 else ""
    reaction_label = price_reaction.replace("_", " ")
    impact_label = possible_market_impact.replace("_", " ")
    return (
        f"{ticker} moved {direction}{event_price_change_percent:.2f}% on "
        f"{event_price_date.isoformat()}; price reaction is {reaction_label} against "
        f"a {impact_label} market-impact read."
    )


def build_cluster_key(item: FeedItem) -> str:
    strong_terms = [*item_tickers(item), *item.products]
    if strong_terms:
        key_parts = ["strong", item.category, *sorted(term.lower() for term in strong_terms)]
        signature = event_signature_term(item, strong_terms)
        if signature:
            key_parts.append(f"event:{signature}")
        return "|".join(key_parts)

    title_terms = extract_title_terms(item.title)
    topic_terms = [topic.lower() for topic in item.topics[:4]]
    key_terms = sorted(set([*topic_terms, *title_terms[:4]]))
    return "|".join([item.category, *key_terms]) if key_terms else f"item:{item.id}"


def item_tickers(item: FeedItem) -> list[str]:
    if item.tickers:
        return item.tickers
    text = " ".join(
        part
        for part in [item.title, item.summary_short or "", item.why_it_matters or ""]
        if part
    )
    return detect_tickers(text)


def extract_title_terms(title: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9-]{2,}", title.lower())
    return [word for word in words if word not in STOP_WORDS]


def event_signature_term(item: FeedItem, entity_terms: list[str]) -> str | None:
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
    for term in EVENT_SIGNATURE_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", text):
            return term

    excluded_terms = entity_title_terms(entity_terms)
    for term in extract_title_terms(item.title):
        if term in excluded_terms or term in GENERIC_TITLE_TERMS:
            continue
        return term
    return None


def entity_title_terms(entity_terms: list[str]) -> set[str]:
    excluded: set[str] = set()
    for entity in entity_terms:
        normalized = entity.upper()
        excluded.update(extract_title_terms(entity))
        for alias in TICKER_ALIASES.get(normalized, []):
            excluded.update(extract_title_terms(alias))
    return excluded


def most_common_values(values) -> list[str]:
    counts = Counter(value for value in values if value)
    return [value for value, _count in counts.most_common()]


def build_cluster_title(item: FeedItem, item_count: int, sources: list[str]) -> str:
    if item_count <= 1:
        return item.title
    source_text = ", ".join(sources[:3])
    return f"{item.title} ({item_count} related items from {source_text})"


def build_cluster_main_summary(item: FeedItem, item_count: int, sources: list[str]) -> str:
    source_text = ", ".join(sources[:3]) if sources else item.source_name
    base_summary = item.summary_short or item.why_it_matters or item.title
    if item_count <= 1:
        return f"{base_summary} Source: {source_text}."
    return (
        f"{base_summary} Cross-source cluster with {item_count} related items "
        f"from {source_text}."
    )


def build_cluster_explanation(
    representative: FeedItem,
    items: list[FeedItem],
    sources: list[str],
    topics: list[str],
    tickers: list[str],
) -> str:
    evidence_bits: list[str] = []
    confirmation_level = cluster_confirmation_level(
        item_count=len(items),
        source_count=len(sources),
    )
    evidence_bits.append(f"confirmation level is {confirmation_level.replace('_', ' ')}")
    if len(items) <= 1 and len(sources) <= 1:
        evidence_bits.append("the item is currently a single-source event candidate")
    if len(sources) > 1:
        evidence_bits.append(f"{len(sources)} sources mention related signals")
    if tickers:
        evidence_bits.append(f"affected ticker context: {', '.join(tickers[:3])}")
    if topics:
        evidence_bits.append(f"shared topics: {', '.join(topics[:4])}")
    if len(items) > 1:
        evidence_bits.append(f"{len(items)} items were grouped by shared entities or title terms")
    if representative.stock_impact_score >= 0.35:
        evidence_bits.append(
            "the representative item has stock-impact score "
            f"{round(representative.stock_impact_score * 100)}"
        )
    return "This cluster is surfaced because " + "; ".join(evidence_bits) + "."


def cluster_confirmation_level(item_count: int, source_count: int) -> str:
    if source_count >= 3 or (source_count >= 2 and item_count >= 3):
        return "strong_cross_source"
    if source_count >= 2:
        return "cross_source"
    if item_count > 1:
        return "repeated_single_source"
    return "single_source"


def build_cluster_uncertainty_notes(
    items: list[FeedItem],
    sources: list[str],
    tickers: list[str],
    first_seen_at: datetime | None,
    last_seen_at: datetime | None,
) -> list[str]:
    notes: list[str] = []
    if len(sources) <= 1:
        notes.append(
            "Only one source is currently represented, so cross-source confirmation is weak."
        )
    if len(items) <= 1:
        notes.append("Only one item is currently grouped into this event.")
    average_confidence = (
        sum(item.classification_confidence for item in items) / len(items) if items else 0
    )
    if average_confidence < 0.65:
        notes.append("Average classifier confidence is below the stronger-confirmation threshold.")
    if not tickers:
        notes.append("No affected ticker was extracted from the grouped items.")
    if first_seen_at is not None and last_seen_at is not None and first_seen_at == last_seen_at:
        notes.append(
            "The timeline has a single observed timestamp so event evolution is not "
            "established yet."
        )
    return notes or ["No major uncertainty flags from the available cluster evidence."]


def build_event_cluster_llm_prompt(cluster: EventCluster) -> str:
    evidence_rows = [
        (
            f"- {item.title} | source={item.source_name} | "
            f"importance={round(item.importance_score * 100)} | "
            f"summary={item.summary_short or item.why_it_matters or item.title}"
        )
        for item in cluster.items[:6]
    ]
    timeline_rows = [
        (
            f"- {entry.published_at.isoformat() if entry.published_at else 'undated'} | "
            f"{entry.source_name} | {entry.title}"
        )
        for entry in cluster.timeline[:8]
    ]
    return "\n".join(
        [
            "You are helping summarize an event cluster for a personal AI intelligence dashboard.",
            "Write in concise English. Use only the supplied evidence.",
            "Do not provide investment advice. For market impact, use conservative wording.",
            "Return 3 short sections: What happened, Why it matters, What is uncertain.",
            "",
            f"Cluster title: {cluster.title}",
            f"Category: {cluster.category}",
            f"Tickers: {', '.join(cluster.tickers) if cluster.tickers else 'none'}",
            f"Topics: {', '.join(cluster.topics) if cluster.topics else 'none'}",
            f"Sources: {', '.join(cluster.sources) if cluster.sources else 'none'}",
            f"Deterministic summary: {cluster.main_summary}",
            f"Deterministic explanation: {cluster.explanation}",
            f"Uncertainty notes: {' '.join(cluster.uncertainty_notes)}",
            "",
            "Evidence items:",
            *evidence_rows,
            "",
            "Timeline:",
            *timeline_rows,
        ]
    )


def compute_cluster_confidence(items: list[FeedItem], sources: list[str]) -> float:
    if not items:
        return 0
    average_item_confidence = sum(item.classification_confidence for item in items) / len(items)
    source_bonus = min(max(len(sources) - 1, 0) * 0.08, 0.2)
    item_bonus = min(max(len(items) - 1, 0) * 0.04, 0.16)
    return round(min(1, average_item_confidence + source_bonus + item_bonus), 3)


def build_cluster_timeline(items: list[FeedItem], limit: int = 8) -> list[EventClusterTimelineItem]:
    timeline_items = sorted(
        items,
        key=lambda item: (
            item.published_at or datetime.min,
            item.id,
        ),
    )
    return [
        EventClusterTimelineItem(
            item_id=item.id,
            title=item.title,
            source_name=item.source_name,
            published_at=item.published_at,
            importance_score=item.importance_score,
        )
        for item in timeline_items[:limit]
    ]
