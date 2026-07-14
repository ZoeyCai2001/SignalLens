from datetime import UTC, datetime

import pytest

from app.schemas.feed import FeedItem
from app.schemas.watchlist import ProductWatchlistItem
from app.services.watchlist import (
    build_product_briefing,
    build_product_match_terms,
    build_product_use_case_terms,
)


def test_build_product_briefing_groups_sources_products_traction_and_activity() -> None:
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
            subcategory="product_coding",
            published_at=datetime(2026, 6, 25, 10, 0, tzinfo=UTC),
            importance_score=0.8,
            novelty_score=0.85,
            summary_detailed="Traction signal: 240 Product Hunt votes, 18 comments",
        ),
        make_item(
            2,
            "IDE agent ships",
            source_name="GitHub",
            products=["CodePilot"],
            companies=["CodePilot"],
            subcategory="product_coding",
            published_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
            importance_score=0.6,
            novelty_score=0.95,
            summary_detailed="Traction signal: 1200 GitHub stars, 80 stars/day",
        ),
        make_item(
            3,
            "AgentDesk update",
            source_name="Product Hunt",
            products=["AgentDesk"],
            companies=["AgentDesk"],
            subcategory="product_business",
            published_at=datetime(2026, 6, 24, 12, 0, tzinfo=UTC),
            importance_score=0.9,
            novelty_score=0.4,
        ),
    ]

    briefing = build_product_briefing(product=product, items=items)

    assert briefing.product.category == "ai-coding-tools"
    assert briefing.item_count == 3
    assert briefing.high_impact_count == 2
    assert briefing.average_importance_score == (0.8 + 0.6 + 0.9) / 3
    assert briefing.average_novelty_score == pytest.approx((0.85 + 0.95 + 0.4) / 3)
    assert briefing.trending_sources[0].source_name == "Product Hunt"
    assert briefing.trending_sources[0].item_count == 2
    assert [(bucket.source_name, bucket.item_count) for bucket in briefing.use_case_counts] == [
        ("Coding", 2),
        ("Business", 1),
    ]
    assert briefing.matched_products[:2] == ["AgentDesk", "CodePilot"]
    assert briefing.related_companies[:2] == ["AgentDesk", "CodePilot"]
    assert briefing.traction_signals == [
        "IDE agent ships: 1200 GitHub stars, 80 stars/day",
        "AgentDesk launches: 240 Product Hunt votes, 18 comments",
    ]
    assert [bucket.item_count for bucket in briefing.activity_timeline] == [2, 1]
    assert [item.title for item in briefing.recent_timeline] == [
        "IDE agent ships",
        "AgentDesk launches",
        "AgentDesk update",
    ]
    assert [score.item_id for score in briefing.discovery_scores] == [2, 1, 3]
    assert briefing.discovery_scores[0].score == pytest.approx(0.84)
    assert briefing.discovery_scores[0].novelty_score == 0.95
    assert briefing.discovery_scores[0].traction_score == 1
    assert briefing.discovery_scores[0].importance_score == 0.6
    assert briefing.discovery_scores[0].relevance_score == 0.8


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


def test_build_product_use_case_terms_maps_prd_product_categories() -> None:
    assert build_product_use_case_terms(
        ProductWatchlistItem(category="ai-coding-tools", label="AI coding tools")
    ) == ["product_coding"]
    assert build_product_use_case_terms(
        ProductWatchlistItem(category="ai-search-browsers", label="AI search and browsers")
    ) == ["product_search"]
    assert build_product_use_case_terms(
        ProductWatchlistItem(category="ai-productivity", label="AI productivity")
    ) == ["product_productivity"]


def make_item(
    item_id: int,
    title: str,
    source_name: str,
    products: list[str],
    companies: list[str],
    published_at: datetime,
    subcategory: str | None = None,
    importance_score: float = 0.7,
    novelty_score: float = 0.7,
    summary_detailed: str | None = None,
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
        subcategory=subcategory,
        tickers=[],
        companies=companies,
        products=products,
        topics=["developer agent"],
        sentiment="neutral",
        relevance_score=0.8,
        importance_score=importance_score,
        novelty_score=novelty_score,
        source_quality_score=0.7,
        stock_impact_score=0.0,
        summary_short=None,
        summary_detailed=summary_detailed,
        why_it_matters=None,
    )
