from datetime import UTC, datetime

from app.schemas.feed import FeedItem
from app.schemas.watchlist import (
    StockMarketSnapshot,
    StockPricePoint,
    StockSignalSummary,
    StockWatchlistItem,
)
from app.services.watchlist import build_stock_briefing, compute_stock_attention_score


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
        high_impact_count=1,
        attention_score=0.812,
        market=StockMarketSnapshot(
            latest=StockPricePoint(
                price_date=datetime(2026, 6, 25, tzinfo=UTC).date(),
                open_price=110,
                high_price=113,
                low_price=109,
                close_price=112.5,
                adjusted_close=112.5,
                volume=123456,
            ),
            previous_close=110,
            change=2.5,
            change_percent=2.27,
            history=[],
        ),
        latest_event_title="Micron discusses HBM demand",
        latest_event_at=datetime(2026, 6, 25, 10, 0, tzinfo=UTC),
        sentiment_counts={"positive": 1, "mixed": 1},
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

    assert briefing.attention_score == 0.812
    assert summary.high_impact_count == 1
    assert summary.latest_event_title == "Micron discusses HBM demand"
    assert briefing.market is not None
    assert briefing.market.change_percent == 2.27
    assert briefing.urgency == "high"
    assert briefing.latest_signal_at == datetime(2026, 6, 25, 10, 0, tzinfo=UTC)
    assert briefing.sentiment_counts == {"positive": 1, "mixed": 1}
    assert briefing.key_themes[:2] == ["HBM", "Micron"]
    assert "Micron (MU) is watched for memory" in briefing.ai_relevance_summary
    assert briefing.theme_breakdown[0].theme == "HBM"
    assert briefing.market_impact_events[0].event_type == "demand_signal"
    assert briefing.recent_timeline[0].signal_score == 0.84
    assert (
        briefing.recent_timeline[0].reason
        == "HBM demand links directly to watched memory names."
    )
    assert briefing.disclaimer == "Informational only."


def test_compute_stock_attention_score_combines_signal_volume_and_preferences() -> None:
    stock = StockWatchlistItem(
        ticker="MU",
        company_name="Micron",
        exchange="NASDAQ",
        sector="Technology",
        industry="Semiconductors",
        priority="High",
        group_name="Watch Only",
        is_pinned=True,
    )
    signals = [
        make_feed_item(
            1,
            "Micron high impact item",
            sentiment="positive",
            stock_impact_score=0.8,
            importance_score=0.6,
            topics=["HBM"],
            companies=["Micron"],
        )
    ]

    score = compute_stock_attention_score(stock=stock, top_signals=signals, signal_count=4)

    assert score == 0.74


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
