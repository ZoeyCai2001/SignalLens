from datetime import UTC, datetime

from app.schemas.watchlist import ProductWatchlistItem
from app.services.watchlist import build_product_briefing, build_product_match_terms
from app.schemas.feed import FeedItem


def test_build_product_briefing_groups_sources_products_and_activity() -> None:
    product = ProductWatchlistItem(
        category="ai-coding-tools",
        label="AI coding tools",
        priority="High",
        related_terms=["developer agent"],
    )
    items = [
        make_item(
            1,
            "AgentDesk launches",
            source_name="Product Hunt",
            products=["AgentDesk"],
            companies=["AgentDesk"],
            published_at=datetime(2026, 6, 25, 10, 0, tzinfo=UTC),
        ),
        make_item(
            2,
            "IDE agent ships",
            source_name="GitHub",
            products=["CodePilot"],
            companies=["CodePilot"],
            published_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
        ),
        make_item(
            3,
            "AgentDesk update",
            source_name="Product Hunt",
            products=["AgentDesk"],
            companies=["AgentDesk"],
            published_at=datetime(2026, 6, 24, 12, 0, tzinfo=UTC),
        ),
    ]

    briefing = build_product_briefing(product=product, items=items)

    assert briefing.product.category == "ai-coding-tools"
    assert briefing.item_count == 3
    assert briefing.trending_sources[0].source_name == "Product Hunt"
    assert briefing.trending_sources[0].item_count == 2
    assert briefing.matched_products[:2] == ["AgentDesk", "CodePilot"]
    assert briefing.related_companies[:2] == ["AgentDesk", "CodePilot"]
    assert [bucket.item_count for bucket in briefing.activity_timeline] == [2, 1]
    assert [item.title for item in briefing.recent_timeline] == [
        "AgentDesk launches",
        "IDE agent ships",
        "AgentDesk update",
    ]


def test_build_product_match_terms_includes_slug_label_and_related_terms() -> None:
    product = ProductWatchlistItem(
        category="ai-search-browsers",
        label="AI search and browsers",
        related_terms=["answer engine"],
    )

    terms = build_product_match_terms(product)

    assert "ai-search-browsers" in terms
    assert "ai search browsers" in terms
    assert "AI search and browsers" in terms
    assert "answer engine" in terms


def make_item(
    item_id: int,
    title: str,
    source_name: str,
    products: list[str],
    companies: list[str],
    published_at: datetime,
) -> FeedItem:
    return FeedItem(
        id=item_id,
        title=title,
        url=f"https://example.com/{item_id}",
        source_name=source_name,
        author=None,
        language="en",
        published_at=published_at,
        category="product",
        subcategory=None,
        tickers=[],
        companies=companies,
        products=products,
        topics=["developer agent"],
        sentiment="neutral",
        relevance_score=0.8,
        importance_score=0.7,
        novelty_score=0.7,
        source_quality_score=0.7,
        stock_impact_score=0.0,
        summary_short=None,
        summary_detailed=None,
        why_it_matters=None,
    )
