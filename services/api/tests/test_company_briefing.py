from datetime import UTC, datetime

from app.schemas.feed import FeedItem
from app.schemas.watchlist import CompanyWatchlistItem
from app.services.watchlist import build_company_briefing, build_company_match_terms


def test_build_company_briefing_groups_sources_topics_products_and_activity() -> None:
    company = make_company()
    items = [
        make_item(
            1,
            "NVIDIA ships new GPU stack",
            source_name="NVIDIA Blog",
            topics=["GPU", "inference"],
            products=["CUDA"],
            tickers=["NVDA"],
            published_at=datetime(2026, 6, 27, 10, 0, tzinfo=UTC),
            importance_score=0.85,
        ),
        make_item(
            2,
            "Developer discussion about CUDA",
            source_name="Hacker News",
            topics=["developer tooling"],
            products=["CUDA"],
            tickers=["NVDA"],
            published_at=datetime(2026, 6, 27, 8, 0, tzinfo=UTC),
            stock_impact_score=0.8,
        ),
        make_item(
            3,
            "NVIDIA data center update",
            source_name="NVIDIA Blog",
            topics=["data center"],
            products=[],
            tickers=["NVDA"],
            published_at=datetime(2026, 6, 26, 8, 0, tzinfo=UTC),
        ),
    ]

    briefing = build_company_briefing(company=company, items=items)

    assert briefing.company.company_key == "nvidia"
    assert briefing.item_count == 3
    assert briefing.high_impact_count == 2
    assert briefing.average_importance_score == (0.85 + 0.7 + 0.7) / 3
    assert briefing.trending_sources[0].source_name == "NVIDIA Blog"
    assert briefing.trending_sources[0].item_count == 2
    assert briefing.related_topics[:3] == ["GPU", "inference", "developer tooling"]
    assert briefing.related_products == ["CUDA"]
    assert briefing.related_tickers == ["NVDA"]
    assert [bucket.item_count for bucket in briefing.activity_timeline] == [2, 1]
    assert [item.title for item in briefing.recent_timeline] == [
        "NVIDIA ships new GPU stack",
        "Developer discussion about CUDA",
        "NVIDIA data center update",
    ]


def test_build_company_match_terms_includes_key_name_ticker_and_related_terms() -> None:
    company = make_company()

    terms = build_company_match_terms(company)

    assert "NVIDIA" in terms
    assert "NVDA" in terms
    assert "AI accelerator" in terms
    assert len(terms) == len(set(term.lower() for term in terms))


def make_company() -> CompanyWatchlistItem:
    return CompanyWatchlistItem(
        company_key="nvidia",
        company_name="NVIDIA",
        ticker="NVDA",
        category="semiconductor",
        priority="High",
        is_pinned=True,
        include_in_digest=True,
        related_terms=["GPU", "AI accelerator"],
    )


def make_item(
    item_id: int,
    title: str,
    source_name: str,
    topics: list[str],
    products: list[str],
    tickers: list[str],
    published_at: datetime,
    importance_score: float = 0.7,
    stock_impact_score: float = 0.1,
) -> FeedItem:
    return FeedItem(
        id=item_id,
        title=title,
        url=f"https://example.com/{item_id}",
        source_name=source_name,
        author=None,
        language="en",
        published_at=published_at,
        category="technical_trend",
        subcategory=None,
        tickers=tickers,
        companies=["NVIDIA"],
        products=products,
        topics=topics,
        sentiment="neutral",
        relevance_score=0.8,
        importance_score=importance_score,
        novelty_score=0.7,
        source_quality_score=0.7,
        stock_impact_score=stock_impact_score,
        summary_short=None,
        summary_detailed=None,
        why_it_matters=None,
    )
