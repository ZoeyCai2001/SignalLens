from collections import Counter
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import and_, case, or_
from sqlalchemy.orm import Session

from app.db.models import (
    DailyDigestSnapshot as DailyDigestSnapshotModel,
)
from app.db.models import (
    Alert,
    AlertRule,
    CompanyWatchlistItem,
    NormalizedItem,
    ProductWatchlistItem,
    StockWatchlistItem,
    TopicWatchlistItem,
    UserItemAction,
)
from app.schemas.digest import (
    DailyDigest,
    DigestAlertItem,
    DailyDigestSnapshot,
    DigestSection,
    DigestSectionMetrics,
    DigestSourceCoverage,
)
from app.schemas.feed import FeedItem
from app.services.feed_actions import (
    LOCAL_USER_ID,
    get_action,
    normalize_language_codes,
    normalize_source_names,
    serialize_feed_item,
)
from app.services.preferences import get_user_preferences
from app.services.watchlist import build_product_use_case_terms, format_product_use_case_label

NON_FINANCIAL_ADVICE_DISCLAIMER = (
    "SignalLens is informational only and does not provide investment advice."
)

RESEARCH_DIGEST_CATEGORIES = {"research", "benchmark_evaluation"}
TECHNICAL_TREND_DIGEST_CATEGORIES = {
    "technical_trend",
    "policy_regulation",
    "infrastructure",
    "open_source_release",
    "tutorial_opinion",
}
STOCK_DIGEST_CATEGORIES = {"stock_company_event", "funding_mna"}
DEVELOPER_DIGEST_CATEGORIES = {"open_source_release"}


def generate_daily_digest(
    db: Session,
    digest_date: date | None = None,
    limit_per_section: int = 5,
    blocked_sources: list[str] | None = None,
    language_preferences: list[str] | None = None,
) -> DailyDigest:
    if blocked_sources is None or language_preferences is None:
        preferences = get_user_preferences(db)
        if blocked_sources is None:
            blocked_sources = preferences.blocked_sources
        if language_preferences is None:
            language_preferences = preferences.language_preferences
    selected_date = (
        digest_date
        or select_latest_digest_date(
            db,
            blocked_sources=blocked_sources,
            language_preferences=language_preferences,
        )
        or datetime.now(UTC).date()
    )
    items = list_visible_items_for_digest_date(
        db=db,
        digest_date=selected_date,
        blocked_sources=blocked_sources,
        language_preferences=language_preferences,
    )
    feed_items = [serialize_feed_item(item, action) for item, action in items]
    feed_items = filter_items_by_excluded_topics(
        feed_items,
        excluded_terms=list_excluded_digest_terms(db),
    )
    sections = build_digest_sections(feed_items, limit_per_section=limit_per_section)
    coverage = build_source_coverage(feed_items)
    tickers = list_watchlist_tickers(db)
    companies = list_watchlist_companies(db)
    metrics = build_digest_overview_metrics(feed_items, coverage)
    active_alerts = list_active_digest_alerts(
        db=db,
        blocked_sources=blocked_sources,
        limit=5,
    )

    return DailyDigest(
        digest_date=selected_date,
        generated_at=datetime.now(UTC),
        headline=build_headline(feed_items, selected_date),
        total_items=len(feed_items),
        high_impact_count=metrics["high_impact_count"],
        stock_signal_count=metrics["stock_signal_count"],
        read_later_count=metrics["read_later_count"],
        active_alert_count=len(active_alerts),
        source_count=metrics["source_count"],
        sections=sections,
        active_alerts=active_alerts,
        source_coverage=coverage,
        watchlist_tickers=tickers,
        watchlist_companies=companies,
        disclaimer=NON_FINANCIAL_ADVICE_DISCLAIMER,
    )


def render_digest_markdown(digest: DailyDigest) -> str:
    lines = [
        f"# SignalLens Daily Digest - {digest.digest_date.isoformat()}",
        "",
        digest.headline,
        "",
    ]
    if digest.watchlist_tickers:
        lines.extend(
            [
                f"Ticker watchlist: {', '.join(digest.watchlist_tickers)}",
                "",
            ]
        )
    if digest.watchlist_companies:
        lines.extend(
            [
                f"Company watchlist: {', '.join(digest.watchlist_companies)}",
                "",
            ]
        )

    if digest.active_alerts:
        lines.extend(["## Active Alerts", ""])
        for alert in digest.active_alerts:
            lines.append(
                f"- [{alert.title}]({alert.item.url}) - {alert.severity} via {alert.rule_name}"
            )
            lines.append(f"  - {alert.reason}")
        lines.append("")

    for section in digest.sections:
        if not section.items:
            continue
        lines.extend([f"## {section.title}", ""])
        lines.extend([section.focus, ""])
        metric_text = format_digest_section_metrics(section.metrics)
        if metric_text:
            lines.extend([f"_Section signals: {metric_text}_", ""])
        for item in section.items:
            summary = item.summary_short or item.why_it_matters or item.summary_detailed
            labels = build_digest_item_labels(item)
            label_text = f" ({', '.join(labels)})" if labels else ""
            lines.append(f"- [{item.title}]({item.url}) - {item.source_name}{label_text}")
            if summary:
                lines.append(f"  - {summary}")
        lines.append("")

    if digest.source_coverage:
        coverage = ", ".join(
            f"{item.source_name}: {item.item_count}" for item in digest.source_coverage
        )
        lines.extend(["## Source Coverage", "", coverage, ""])

    lines.extend(["## Disclaimer", "", digest.disclaimer])
    return "\n".join(lines).strip() + "\n"


def build_digest_item_labels(item: FeedItem, limit: int = 4) -> list[str]:
    labels = [
        format_ai_relevance_label(item.is_ai_related),
        *item.tickers,
        *item.products,
        *item.technologies,
        format_market_impact_label(item.market_impact_type),
        format_product_use_case_label(item.subcategory) if item.category == "product" else "",
        *item.topics,
    ]
    return unique_digest_labels(labels)[:limit]


def format_ai_relevance_label(is_ai_related: bool) -> str:
    return "" if is_ai_related else "not AI-related"


def format_market_impact_label(value: str) -> str:
    if not value or value == "none":
        return ""
    labels = {
        "earnings_guidance": "earnings/guidance",
        "analyst_action": "analyst action",
        "partnership_customer": "partnership/customer",
        "supply_chain_regulation": "supply chain/regulation",
        "funding_mna": "funding/M&A",
        "demand_signal": "demand signal",
        "positive_signal": "positive market signal",
        "negative_signal": "negative market signal",
        "stock_signal": "stock signal",
    }
    return labels.get(value, value.replace("_", " "))


def unique_digest_labels(labels: list[str]) -> list[str]:
    seen = set()
    unique_labels = []
    for label in labels:
        normalized = label.strip()
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            unique_labels.append(normalized)
    return unique_labels


def save_daily_digest_snapshot(
    db: Session,
    digest_date: date | None = None,
    limit_per_section: int = 5,
    blocked_sources: list[str] | None = None,
    language_preferences: list[str] | None = None,
) -> DailyDigestSnapshotModel:
    digest = generate_daily_digest(
        db=db,
        digest_date=digest_date,
        limit_per_section=limit_per_section,
        blocked_sources=blocked_sources,
        language_preferences=language_preferences,
    )
    payload = digest.model_dump(mode="json")
    markdown = render_digest_markdown(digest)
    existing = (
        db.query(DailyDigestSnapshotModel)
        .filter(
            DailyDigestSnapshotModel.user_id == LOCAL_USER_ID,
            DailyDigestSnapshotModel.digest_date == digest.digest_date,
        )
        .one_or_none()
    )

    snapshot = existing or DailyDigestSnapshotModel(
        user_id=LOCAL_USER_ID,
        digest_date=digest.digest_date,
    )
    snapshot.generated_at = digest.generated_at
    snapshot.headline = digest.headline
    snapshot.total_items = digest.total_items
    snapshot.limit_per_section = limit_per_section
    snapshot.payload = payload
    snapshot.markdown = markdown

    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def list_daily_digest_snapshots(
    db: Session,
    limit: int = 10,
) -> list[DailyDigestSnapshotModel]:
    return (
        db.query(DailyDigestSnapshotModel)
        .filter(DailyDigestSnapshotModel.user_id == LOCAL_USER_ID)
        .order_by(
            DailyDigestSnapshotModel.digest_date.desc(),
            DailyDigestSnapshotModel.generated_at.desc(),
        )
        .limit(limit)
        .all()
    )


def delete_daily_digest_snapshot(db: Session, snapshot_id: int) -> bool:
    snapshot = (
        db.query(DailyDigestSnapshotModel)
        .filter(
            DailyDigestSnapshotModel.user_id == LOCAL_USER_ID,
            DailyDigestSnapshotModel.id == snapshot_id,
        )
        .one_or_none()
    )
    if snapshot is None:
        return False

    db.delete(snapshot)
    db.commit()
    return True


def serialize_daily_digest_snapshot(snapshot: DailyDigestSnapshotModel) -> DailyDigestSnapshot:
    digest = DailyDigest.model_validate(snapshot.payload)
    return DailyDigestSnapshot(
        id=snapshot.id,
        digest_date=snapshot.digest_date,
        generated_at=snapshot.generated_at,
        headline=snapshot.headline,
        total_items=snapshot.total_items,
        limit_per_section=snapshot.limit_per_section,
        digest=digest,
        markdown=snapshot.markdown,
        created_at=snapshot.created_at,
        updated_at=snapshot.updated_at,
    )


def select_latest_digest_date(
    db: Session,
    blocked_sources: list[str] | None = None,
    language_preferences: list[str] | None = None,
) -> date | None:
    blocked_source_names = normalize_source_names(blocked_sources)
    preferred_languages = normalize_language_codes(language_preferences)
    query = (
        db.query(NormalizedItem)
        .outerjoin(
            UserItemAction,
            (UserItemAction.item_id == NormalizedItem.id)
            & (UserItemAction.user_id == LOCAL_USER_ID),
        )
        .filter((UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None)))
    )
    if blocked_source_names:
        query = query.filter(~NormalizedItem.source_name.in_(blocked_source_names))
    if preferred_languages:
        query = query.filter(NormalizedItem.language.in_(preferred_languages))

    row = (
        query
        .order_by(
            NormalizedItem.published_at.desc().nullslast(),
            NormalizedItem.created_at.desc(),
        )
        .first()
    )
    if row is None:
        return None

    timestamp = row.published_at or row.created_at
    return timestamp.date() if timestamp else None


def list_visible_items_for_digest_date(
    db: Session,
    digest_date: date,
    blocked_sources: list[str] | None = None,
    language_preferences: list[str] | None = None,
) -> list[tuple[NormalizedItem, UserItemAction | None]]:
    start = datetime.combine(digest_date, time.min, tzinfo=UTC)
    end = start + timedelta(days=1)
    blocked_source_names = normalize_source_names(blocked_sources)
    preferred_languages = normalize_language_codes(language_preferences)

    query = (
        db.query(NormalizedItem, UserItemAction)
        .outerjoin(
            UserItemAction,
            (UserItemAction.item_id == NormalizedItem.id)
            & (UserItemAction.user_id == LOCAL_USER_ID),
        )
        .filter((UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None)))
    )
    if blocked_source_names:
        query = query.filter(~NormalizedItem.source_name.in_(blocked_source_names))
    if preferred_languages:
        query = query.filter(NormalizedItem.language.in_(preferred_languages))

    return (
        query
        .filter(
            or_(
                and_(NormalizedItem.published_at >= start, NormalizedItem.published_at < end),
                and_(
                    NormalizedItem.published_at.is_(None),
                    NormalizedItem.created_at >= start,
                    NormalizedItem.created_at < end,
                ),
            )
        )
        .order_by(
            UserItemAction.is_important.desc().nullslast(),
            NormalizedItem.importance_score.desc(),
            NormalizedItem.relevance_score.desc(),
            NormalizedItem.published_at.desc().nullslast(),
            NormalizedItem.created_at.desc(),
        )
        .limit(100)
        .all()
    )


def list_active_digest_alerts(
    db: Session,
    blocked_sources: list[str] | None = None,
    limit: int = 5,
) -> list[DigestAlertItem]:
    blocked_source_names = normalize_source_names(blocked_sources)
    query = (
        db.query(Alert)
        .join(Alert.item)
        .join(Alert.rule)
        .outerjoin(
            UserItemAction,
            (UserItemAction.item_id == Alert.item_id)
            & (UserItemAction.user_id == LOCAL_USER_ID),
        )
        .filter(
            Alert.user_id == LOCAL_USER_ID,
            Alert.status == "active",
            Alert.rule.has(AlertRule.enabled.is_(True)),
        )
        .filter((UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None)))
    )
    if blocked_source_names:
        query = query.filter(~NormalizedItem.source_name.in_(blocked_source_names))

    rows = (
        query.order_by(
            case(
                (Alert.severity == "critical", 0),
                (Alert.severity == "high", 1),
                (Alert.severity == "medium", 2),
                (Alert.severity == "low", 3),
                else_=4,
            ),
            Alert.created_at.desc(),
            Alert.id.desc(),
        )
        .limit(limit)
        .all()
    )
    return [serialize_digest_alert(db, alert) for alert in rows]


def serialize_digest_alert(db: Session, alert: Alert) -> DigestAlertItem:
    return DigestAlertItem(
        id=alert.id,
        title=alert.title,
        reason=alert.reason,
        severity=alert.severity,
        rule_name=alert.rule.name,
        created_at=alert.created_at,
        item=serialize_feed_item(alert.item, get_action(db, alert.item_id)),
    )


def build_digest_sections(
    items: list[FeedItem],
    limit_per_section: int = 5,
) -> list[DigestSection]:
    ranked_items = sort_for_digest(items)
    section_specs = [
        (
            "top_signals",
            "Top Signals",
            "Highest ranked items across all AI sources.",
            lambda item: True,
        ),
        (
            "research",
            "AI Research",
            "Papers, benchmarks, and research discussions.",
            is_digest_research_item,
        ),
        (
            "technical_trends",
            "AI Technical Trends",
            "Engineering themes, infrastructure, models, and agent workflows.",
            is_digest_technical_trend_item,
        ),
        (
            "products",
            "AI Products",
            "Product launches, tools, and user-facing AI applications.",
            lambda item: item.category == "product" or bool(item.products),
        ),
        (
            "company_watchlist",
            "AI Company Watchlist",
            "Company-linked AI signals across watched companies and AI labs.",
            lambda item: bool(item.companies),
        ),
        (
            "stock_watchlist",
            "AI Stock Watchlist",
            "Company and ticker-linked AI signals, informational only.",
            is_digest_stock_item,
        ),
        (
            "chinese_social",
            "Chinese Social Trends",
            "Chinese-language AI signals from configured public sources.",
            lambda item: item.category == "social_trend" or item.language == "zh",
        ),
        (
            "developer_highlights",
            "GitHub and Hugging Face Highlights",
            "Open-source repositories, models, and developer ecosystem activity.",
            is_digest_developer_highlight_item,
        ),
        (
            "read_later",
            "Items to Read Later",
            "Saved items from today's collected signals that are still unread.",
            lambda item: item.is_saved and not item.is_read,
        ),
    ]

    sections: list[DigestSection] = []
    for key, title, focus, predicate in section_specs:
        section_items = [item for item in ranked_items if predicate(item)][:limit_per_section]
        sections.append(
            DigestSection(
                key=key,
                title=title,
                focus=focus,
                items=section_items,
                metrics=build_digest_section_metrics(section_items),
            )
        )
    return sections


def is_digest_research_item(item: FeedItem) -> bool:
    return item.category in RESEARCH_DIGEST_CATEGORIES


def is_digest_technical_trend_item(item: FeedItem) -> bool:
    return item.category in TECHNICAL_TREND_DIGEST_CATEGORIES


def is_digest_stock_item(item: FeedItem) -> bool:
    return item.category in STOCK_DIGEST_CATEGORIES or bool(item.tickers)


def is_digest_developer_highlight_item(item: FeedItem) -> bool:
    return item.category in DEVELOPER_DIGEST_CATEGORIES or item.source_name in {
        "GitHub",
        "Hugging Face",
    }


def build_digest_section_metrics(items: list[FeedItem]) -> DigestSectionMetrics:
    return DigestSectionMetrics(
        item_count=len(items),
        high_impact_count=sum(1 for item in items if item.importance_score >= 0.75),
        stock_signal_count=sum(
            1 for item in items if item.category == "stock_company_event" or bool(item.tickers)
        ),
        read_later_count=sum(1 for item in items if item.is_saved and not item.is_read),
        source_count=len({item.source_name for item in items}),
    )


def format_digest_section_metrics(metrics: DigestSectionMetrics) -> str:
    if metrics.item_count <= 0:
        return ""
    parts = [f"{metrics.item_count} items", f"{metrics.source_count} sources"]
    if metrics.high_impact_count:
        parts.append(f"{metrics.high_impact_count} high-impact")
    if metrics.stock_signal_count:
        parts.append(f"{metrics.stock_signal_count} stock-linked")
    if metrics.read_later_count:
        parts.append(f"{metrics.read_later_count} read-later")
    return ", ".join(parts)


def filter_items_by_excluded_topics(
    items: list[FeedItem],
    excluded_terms: set[str],
) -> list[FeedItem]:
    if not excluded_terms:
        return items
    return [item for item in items if not matches_excluded_topic(item, excluded_terms)]


def matches_excluded_topic(item: FeedItem, excluded_terms: set[str]) -> bool:
    item_terms = {
        term.strip().lower()
        for term in [
            item.subcategory or "",
            *item.topics,
            *item.products,
            *item.companies,
            *item.tickers,
        ]
        if term.strip()
    }
    return bool(item_terms & excluded_terms)


def sort_for_digest(items: list[FeedItem]) -> list[FeedItem]:
    return sorted(
        items,
        key=lambda item: (
            item.is_important,
            digest_rank_score(item),
            item.published_at or datetime.min.replace(tzinfo=UTC),
        ),
        reverse=True,
    )


def digest_rank_score(item: FeedItem) -> float:
    return round(
        0.32 * item.importance_score
        + 0.22 * item.relevance_score
        + 0.16 * item.source_quality_score
        + 0.12 * item.classification_confidence
        + 0.08 * item.social_signal_score
        + 0.06 * item.stock_impact_score
        + 0.04 * item.novelty_score,
        4,
    )


def build_source_coverage(items: list[FeedItem]) -> list[DigestSourceCoverage]:
    counts = Counter(item.source_name for item in items)
    return [
        DigestSourceCoverage(source_name=source_name, item_count=count)
        for source_name, count in counts.most_common()
    ]


def build_digest_overview_metrics(
    items: list[FeedItem],
    coverage: list[DigestSourceCoverage],
) -> dict[str, int]:
    return {
        "high_impact_count": sum(1 for item in items if item.importance_score >= 0.75),
        "stock_signal_count": sum(
            1 for item in items if item.category == "stock_company_event" or bool(item.tickers)
        ),
        "read_later_count": sum(1 for item in items if item.is_saved and not item.is_read),
        "source_count": len(coverage),
    }


def build_headline(items: list[FeedItem], digest_date: date) -> str:
    if not items:
        return f"No collected AI signals for {digest_date.isoformat()}."

    categories = Counter(item.category for item in items)
    leading_category = categories.most_common(1)[0][0].replace("_", " ")
    return f"{len(items)} AI signals for {digest_date.isoformat()}, led by {leading_category}."


def list_watchlist_tickers(db: Session) -> list[str]:
    rows = (
        db.query(StockWatchlistItem.ticker)
        .filter(StockWatchlistItem.user_id == LOCAL_USER_ID)
        .order_by(StockWatchlistItem.is_pinned.desc(), StockWatchlistItem.ticker.asc())
        .all()
    )
    return [row[0] for row in rows]


def list_watchlist_companies(db: Session) -> list[str]:
    rows = (
        db.query(CompanyWatchlistItem)
        .filter(
            CompanyWatchlistItem.user_id == LOCAL_USER_ID,
            CompanyWatchlistItem.include_in_digest.is_(True),
        )
        .order_by(
            CompanyWatchlistItem.is_pinned.desc(),
            CompanyWatchlistItem.priority.asc(),
            CompanyWatchlistItem.company_name.asc(),
        )
        .all()
    )
    return [row.company_name for row in rows]


def list_excluded_digest_terms(db: Session) -> set[str]:
    return (
        list_excluded_digest_topic_terms(db)
        | list_excluded_digest_product_terms(db)
        | list_excluded_digest_company_terms(db)
    )


def list_excluded_digest_topic_terms(db: Session) -> set[str]:
    rows = (
        db.query(TopicWatchlistItem)
        .filter(
            TopicWatchlistItem.user_id == LOCAL_USER_ID,
            TopicWatchlistItem.include_in_digest.is_(False),
        )
        .all()
    )
    terms: set[str] = set()
    for row in rows:
        terms.update(
            term.strip().lower()
            for term in [row.topic, row.label, *row.related_terms]
            if term.strip()
        )
    return terms


def list_excluded_digest_product_terms(db: Session) -> set[str]:
    rows = (
        db.query(ProductWatchlistItem)
        .filter(
            ProductWatchlistItem.user_id == LOCAL_USER_ID,
            ProductWatchlistItem.include_in_digest.is_(False),
        )
        .all()
    )
    terms: set[str] = set()
    for row in rows:
        use_case_terms = build_product_use_case_terms(row)
        terms.update(
            term.strip().lower()
            for term in [row.category, row.label, *row.related_terms, *use_case_terms]
            if term.strip()
        )
    return terms


def list_excluded_digest_company_terms(db: Session) -> set[str]:
    rows = (
        db.query(CompanyWatchlistItem)
        .filter(
            CompanyWatchlistItem.user_id == LOCAL_USER_ID,
            CompanyWatchlistItem.include_in_digest.is_(False),
        )
        .all()
    )
    terms: set[str] = set()
    for row in rows:
        terms.update(
            term.strip().lower()
            for term in [
                row.company_key,
                row.company_name,
                row.ticker or "",
                row.category,
                *row.related_terms,
            ]
            if term.strip()
        )
    return terms
