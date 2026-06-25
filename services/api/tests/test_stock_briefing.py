from datetime import UTC, datetime

from app.schemas.feed import FeedItem
from app.schemas.watchlist import StockSignalSummary, StockWatchlistItem
from app.services.watchlist import build_stock_briefing


def test_build_stock_briefing_summarizes_signal_state() -> None:
    summary = StockSignalSummary(
        stock=StockWatchlistItem(
            ticker="MU",
            company_name="Micron",
            exchange="NASDAQ",
            sector="Technology",
            industry="Semiconductors",
            priority="High",
            group_name="Watch Only",
            related_keywords=["HBM"],
            related_companies=[],
            related_ai_themes=["memory"],
        ),
        signal_count=2,
        top_signals=[
            make_feed_item(
                1,
                "Micron discusses HBM demand",
                sentiment="positive",
                stock_impact_score=0.84,
                importance_score=0.7,
                topics=["HBM", "AI infrastructure"],
                companies=["Micron"],
                why_it_matters="HBM demand links directly to watched memory names.",
                published_at=datetime(2026, 6, 25, 10, 0, tzinfo=UTC),
            ),
            make_feed_item(
                2,
                "AI memory supply chain note",
                sentiment="mixed",
                stock_impact_score=0.35,
                importance_score=0.55,
                topics=["HBM"],
                companies=["Micron"],
                published_at=datetime(2026, 6, 25, 8, 0, tzinfo=UTC),
            ),
        ],
        disclaimer="Informational only.",
    )

    briefing = build_stock_briefing(summary)

    assert briefing.urgency == "high"
    assert briefing.latest_signal_at == datetime(2026, 6, 25, 10, 0, tzinfo=UTC)
    assert briefing.sentiment_counts == {"positive": 1, "mixed": 1}
    assert briefing.key_themes[:2] == ["HBM", "Micron"]
    assert briefing.recent_timeline[0].signal_score == 0.84
    assert (
        briefing.recent_timeline[0].reason
        == "HBM demand links directly to watched memory names."
    )
    assert briefing.disclaimer == "Informational only."


def make_feed_item(
    item_id: int,
    title: str,
    sentiment: str,
    stock_impact_score: float,
    importance_score: float,
    topics: list[str],
    companies: list[str],
    why_it_matters: str | None = None,
    published_at: datetime | None = None,
) -> FeedItem:
    return FeedItem(
        id=item_id,
        title=title,
        url=f"https://example.com/{item_id}",
        source_name="Test",
        author=None,
        language="en",
        published_at=published_at,
        category="stock_company_event",
        subcategory=None,
        tickers=["MU"],
        companies=companies,
        products=[],
        topics=topics,
        sentiment=sentiment,
        relevance_score=0.8,
        importance_score=importance_score,
        novelty_score=0.4,
        source_quality_score=0.7,
        stock_impact_score=stock_impact_score,
        summary_short=None,
        summary_detailed=None,
        why_it_matters=why_it_matters,
    )
