from datetime import UTC, datetime

from app.db.models import DailyDigestSnapshot as DailyDigestSnapshotModel
from app.schemas.digest import DailyDigest
from app.schemas.feed import FeedItem
from app.services.daily_digest import (
    build_digest_sections,
    build_headline,
    build_source_coverage,
    digest_rank_score,
    filter_items_by_excluded_topics,
    render_digest_markdown,
    serialize_daily_digest_snapshot,
    sort_for_digest,
)


def test_daily_digest_sections_group_items() -> None:
    items = [
        make_item(1, "Research", "research", 0.9, topics=["llm"]),
        make_item(2, "Product", "product", 0.8, products=["Tool"]),
        make_item(3, "Stock", "stock_company_event", 0.7, tickers=["MU"]),
        make_item(4, "Repo", "technical_trend", 0.6, source_name="GitHub"),
        make_item(5, "Saved", "technical_trend", 0.5, is_saved=True),
    ]

    sections = build_digest_sections(items, limit_per_section=3)

    section_map = {section.key: section for section in sections}
    assert section_map["top_signals"].items[0].title == "Research"
    assert section_map["research"].items[0].title == "Research"
    assert section_map["products"].items[0].title == "Product"
    assert section_map["stock_watchlist"].items[0].title == "Stock"
    assert section_map["developer_highlights"].items[0].title == "Repo"
    assert section_map["read_later"].items[0].title == "Saved"


def test_daily_digest_source_coverage_counts_sources() -> None:
    items = [
        make_item(1, "A", "research", 0.9, source_name="arXiv"),
        make_item(2, "B", "research", 0.8, source_name="arXiv"),
        make_item(3, "C", "product", 0.7, source_name="Hacker News"),
    ]

    coverage = build_source_coverage(items)

    assert coverage[0].source_name == "arXiv"
    assert coverage[0].item_count == 2
    assert coverage[1].source_name == "Hacker News"


def test_sort_for_digest_uses_source_quality_and_confidence() -> None:
    lower_trust = make_item(
        1,
        "Slightly higher importance rumor",
        "technical_trend",
        0.74,
        source_quality_score=0.55,
        classification_confidence=0.5,
    )
    trusted = make_item(
        2,
        "Trusted source confirmation",
        "technical_trend",
        0.7,
        source_quality_score=0.9,
        classification_confidence=0.85,
    )

    ranked = sort_for_digest([lower_trust, trusted])

    assert ranked[0].title == "Trusted source confirmation"
    assert digest_rank_score(trusted) > digest_rank_score(lower_trust)


def test_daily_digest_headline_handles_empty_day() -> None:
    headline = build_headline([], datetime(2026, 6, 25, tzinfo=UTC).date())

    assert headline == "No collected AI signals for 2026-06-25."


def test_filter_items_by_excluded_topics_removes_digest_excluded_terms() -> None:
    items = [
        make_item(1, "Keep", "technical_trend", 0.8, topics=["agent"]),
        make_item(2, "Exclude", "technical_trend", 0.9, topics=["model routing"]),
        make_item(3, "Product Exclude", "product", 0.7, products=["AI search"]),
    ]

    filtered = filter_items_by_excluded_topics(items, {"model routing", "ai search"})

    assert [item.title for item in filtered] == ["Keep"]


def test_render_digest_markdown_includes_sections_links_and_disclaimer() -> None:
    items = [
        make_item(1, "Research", "research", 0.9, topics=["llm"]),
        make_item(2, "Stock", "stock_company_event", 0.8, tickers=["MU"]),
    ]
    digest = DailyDigest(
        digest_date=datetime(2026, 6, 25, tzinfo=UTC).date(),
        generated_at=datetime(2026, 6, 25, 13, 0, tzinfo=UTC),
        headline="2 AI signals for 2026-06-25.",
        total_items=2,
        sections=build_digest_sections(items, limit_per_section=2),
        source_coverage=build_source_coverage(items),
        watchlist_tickers=["MU", "MRVL"],
        disclaimer="Informational only.",
    )

    markdown = render_digest_markdown(digest)

    assert markdown.startswith("# SignalLens Daily Digest - 2026-06-25")
    assert "Watchlist: MU, MRVL" in markdown
    assert "## AI Research" in markdown
    assert "- [Research](https://example.com/1) - Test Source" in markdown
    assert "## Disclaimer" in markdown
    assert markdown.endswith("Informational only.\n")


def test_serialize_daily_digest_snapshot_round_trips_payload() -> None:
    digest = DailyDigest(
        digest_date=datetime(2026, 6, 25, tzinfo=UTC).date(),
        generated_at=datetime(2026, 6, 25, 13, 0, tzinfo=UTC),
        headline="Snapshot headline",
        total_items=0,
        sections=[],
        source_coverage=[],
        watchlist_tickers=[],
        disclaimer="Informational only.",
    )
    timestamp = datetime(2026, 6, 25, 13, 5, tzinfo=UTC)
    snapshot = DailyDigestSnapshotModel(
        id=7,
        user_id="local",
        digest_date=digest.digest_date,
        generated_at=digest.generated_at,
        headline=digest.headline,
        total_items=digest.total_items,
        limit_per_section=5,
        payload=digest.model_dump(mode="json"),
        markdown="# Snapshot\n",
        created_at=timestamp,
        updated_at=timestamp,
    )

    serialized = serialize_daily_digest_snapshot(snapshot)

    assert serialized.id == 7
    assert serialized.digest.headline == "Snapshot headline"
    assert serialized.markdown == "# Snapshot\n"


def make_item(
    item_id: int,
    title: str,
    category: str,
    importance_score: float,
    source_name: str = "Test Source",
    topics: list[str] | None = None,
    products: list[str] | None = None,
    tickers: list[str] | None = None,
    is_saved: bool = False,
    source_quality_score: float = 0.7,
    classification_confidence: float = 0.5,
) -> FeedItem:
    return FeedItem(
        id=item_id,
        title=title,
        url=f"https://example.com/{item_id}",
        source_name=source_name,
        author=None,
        language="en",
        published_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
        category=category,
        subcategory=None,
        tickers=tickers or [],
        companies=[],
        products=products or [],
        topics=topics or [],
        sentiment="neutral",
        relevance_score=0.8,
        classification_confidence=classification_confidence,
        importance_score=importance_score,
        novelty_score=0.7,
        source_quality_score=source_quality_score,
        stock_impact_score=0.0,
        summary_short=None,
        summary_detailed=None,
        why_it_matters=None,
        is_saved=is_saved,
    )
