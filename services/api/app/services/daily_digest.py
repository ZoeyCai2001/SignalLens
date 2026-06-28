from collections import Counter
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.db.models import (
    DailyDigestSnapshot as DailyDigestSnapshotModel,
)
from app.db.models import (
    CompanyWatchlistItem,
    NormalizedItem,
    ProductWatchlistItem,
    StockWatchlistItem,
    TopicWatchlistItem,
    UserItemAction,
)
from app.schemas.digest import (
    DailyDigest,
    DailyDigestSnapshot,
    DigestSection,
    DigestSourceCoverage,
)
from app.schemas.feed import FeedItem
from app.services.feed_actions import LOCAL_USER_ID, serialize_feed_item

NON_FINANCIAL_ADVICE_DISCLAIMER = (
    "SignalLens is informational only and does not provide investment advice."
)


def generate_daily_digest(
    db: Session,
    digest_date: date | None = None,
    limit_per_section: int = 5,
) -> DailyDigest:
    selected_date = digest_date or select_latest_digest_date(db) or datetime.now(UTC).date()
    items = list_visible_items_for_digest_date(db=db, digest_date=selected_date)
    feed_items = [serialize_feed_item(item, action) for item, action in items]
    feed_items = filter_items_by_excluded_topics(
        feed_items,
        excluded_terms=list_excluded_digest_terms(db),
    )
    sections = build_digest_sections(feed_items, limit_per_section=limit_per_section)
    coverage = build_source_coverage(feed_items)
    tickers = list_watchlist_tickers(db)
    companies = list_watchlist_companies(db)

    return DailyDigest(
        digest_date=selected_date,
        generated_at=datetime.now(UTC),
        headline=build_headline(feed_items, selected_date),
        total_items=len(feed_items),
        sections=sections,
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

    for section in digest.sections:
        if not section.items:
            continue
        lines.extend([f"## {section.title}", ""])
        for item in section.items:
            summary = item.summary_short or item.why_it_matters or item.summary_detailed
            labels = [*item.tickers[:3], *item.topics[:3]]
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


def save_daily_digest_snapshot(
    db: Session,
    digest_date: date | None = None,
    limit_per_section: int = 5,
) -> DailyDigestSnapshotModel:
    digest = generate_daily_digest(
        db=db,
        digest_date=digest_date,
        limit_per_section=limit_per_section,
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


def select_latest_digest_date(db: Session) -> date | None:
    row = (
        db.query(NormalizedItem)
        .outerjoin(
            UserItemAction,
            (UserItemAction.item_id == NormalizedItem.id)
            & (UserItemAction.user_id == LOCAL_USER_ID),
        )
        .filter((UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None)))
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
) -> list[tuple[NormalizedItem, UserItemAction | None]]:
    start = datetime.combine(digest_date, time.min, tzinfo=UTC)
    end = start + timedelta(days=1)

    return (
        db.query(NormalizedItem, UserItemAction)
        .outerjoin(
            UserItemAction,
            (UserItemAction.item_id == NormalizedItem.id)
            & (UserItemAction.user_id == LOCAL_USER_ID),
        )
        .filter((UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None)))
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
            lambda item: item.category == "research",
        ),
        (
            "technical_trends",
            "AI Technical Trends",
            "Engineering themes, infrastructure, models, and agent workflows.",
            lambda item: item.category == "technical_trend",
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
            lambda item: item.category == "stock_company_event" or bool(item.tickers),
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
            lambda item: item.source_name in {"GitHub", "Hugging Face"},
        ),
        (
            "read_later",
            "Items to Read Later",
            "Saved items from today's collected signals.",
            lambda item: item.is_saved,
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
            )
        )
    return sections


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
        for term in [*item.topics, *item.products, *item.companies, *item.tickers]
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
        + 0.10 * item.stock_impact_score
        + 0.08 * item.novelty_score,
        4,
    )


def build_source_coverage(items: list[FeedItem]) -> list[DigestSourceCoverage]:
    counts = Counter(item.source_name for item in items)
    return [
        DigestSourceCoverage(source_name=source_name, item_count=count)
        for source_name, count in counts.most_common()
    ]


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
        terms.update(
            term.strip().lower()
            for term in [row.category, row.label, *row.related_terms]
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
