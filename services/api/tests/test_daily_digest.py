from datetime import UTC, datetime

from app.schemas.feed import FeedItem
from app.services.daily_digest import build_digest_sections, build_headline, build_source_coverage


def test_daily_digest_sections_group_items() -> None:
    items = [
        make_item(1, "Research", "research", 0.9, topics=["llm"]),
        make_item(2, "Product", "product", 0.8, products=["Tool"]),
        make_item(3, "Stock", "stock_company_event", 0.7, tickers=["MU"]),
    ]

    sections = build_digest_sections(items, limit_per_section=3)

    section_map = {section.key: section for section in sections}
    assert section_map["top_signals"].items[0].title == "Research"
    assert section_map["research"].items[0].title == "Research"
    assert section_map["products"].items[0].title == "Product"
    assert section_map["stock_watchlist"].items[0].title == "Stock"


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


def test_daily_digest_headline_handles_empty_day() -> None:
    headline = build_headline([], datetime(2026, 6, 25, tzinfo=UTC).date())

    assert headline == "No collected AI signals for 2026-06-25."


def make_item(
    item_id: int,
    title: str,
    category: str,
    importance_score: float,
    source_name: str = "Test Source",
    topics: list[str] | None = None,
    products: list[str] | None = None,
    tickers: list[str] | None = None,
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
        importance_score=importance_score,
        novelty_score=0.7,
        source_quality_score=0.7,
        stock_impact_score=0.0,
        summary_short=None,
        summary_detailed=None,
        why_it_matters=None,
    )
