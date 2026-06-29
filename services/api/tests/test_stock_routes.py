from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routes import stocks as stock_routes
from app.main import create_app
from app.schemas.feed import FeedItem
from app.schemas.watchlist import (
    StockBriefing,
    StockBriefingTimelineItem,
    StockMarketImpactEvent,
    StockMarketSnapshot,
    StockPricePoint,
    StockSignalSummary,
    StockWatchlistItem,
)


def test_prd_stock_routes_are_registered() -> None:
    app = create_app()
    paths = {route.path for route in app.routes}

    assert "/api/stocks/watchlist-dashboard" in paths
    assert "/api/stocks/{ticker}" in paths
    assert "/api/stocks/{ticker}/events" in paths
    assert "/api/stocks/{ticker}/price-series" in paths


@pytest.mark.anyio
async def test_stock_watchlist_dashboard_uses_preferences(monkeypatch: pytest.MonkeyPatch) -> None:
    db = object()
    preferences = SimpleNamespace(blocked_sources=["Blocked Source"])
    summary = make_stock_summary()
    seen: dict[str, object] = {}

    monkeypatch.setattr(stock_routes, "get_user_preferences", lambda route_db: preferences)

    def fake_summarize_stock_signals(route_db, limit_per_stock: int, blocked_sources=None):
        seen["db"] = route_db
        seen["limit_per_stock"] = limit_per_stock
        seen["blocked_sources"] = blocked_sources
        return [summary]

    monkeypatch.setattr(stock_routes, "summarize_stock_signals", fake_summarize_stock_signals)

    result = await stock_routes.get_stock_watchlist_dashboard(db=db, limit_per_stock=4)

    assert result == [summary]
    assert seen == {
        "db": db,
        "limit_per_stock": 4,
        "blocked_sources": preferences.blocked_sources,
    }


@pytest.mark.anyio
async def test_stock_detail_and_events_reuse_preference_aware_briefing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = object()
    briefing = make_stock_briefing()
    seen: list[tuple[object, str, int]] = []

    def fake_get_preference_aware_stock_briefing(db, ticker: str, limit: int):
        seen.append((db, ticker, limit))
        return briefing

    monkeypatch.setattr(
        stock_routes,
        "get_preference_aware_stock_briefing",
        fake_get_preference_aware_stock_briefing,
    )

    detail = await stock_routes.get_stock_detail(ticker="MU", db=db, limit=8)
    events = await stock_routes.get_stock_events(ticker="MU", db=db, limit=12)

    assert detail is briefing
    assert events == briefing.recent_timeline
    assert seen == [(db, "MU", 8), (db, "MU", 12)]


@pytest.mark.anyio
async def test_stock_detail_returns_404_for_missing_ticker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        stock_routes,
        "get_preference_aware_stock_briefing",
        lambda **_kwargs: None,
    )

    with pytest.raises(HTTPException) as exc_info:
        await stock_routes.get_stock_detail(ticker="NONE", db=object())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Stock ticker not found in watchlist."


@pytest.mark.anyio
async def test_stock_price_series_uses_market_snapshot_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = object()
    snapshot = StockMarketSnapshot(
        latest=StockPricePoint(
            price_date=datetime(2026, 6, 25, tzinfo=UTC).date(),
            open_price=100,
            high_price=105,
            low_price=99,
            close_price=104,
        ),
        history=[],
    )
    seen: dict[str, object] = {}

    def fake_build_stock_market_snapshot(db, ticker: str, limit: int):
        seen["db"] = db
        seen["ticker"] = ticker
        seen["limit"] = limit
        return snapshot

    monkeypatch.setattr(
        stock_routes,
        "build_stock_market_snapshot",
        fake_build_stock_market_snapshot,
    )

    result = await stock_routes.get_stock_price_series(ticker="MU", db=db, limit=120)

    assert result is snapshot
    assert seen == {"db": db, "ticker": "MU", "limit": 120}


def make_stock_summary() -> StockSignalSummary:
    feed_item = make_feed_item()
    return StockSignalSummary(
        stock=make_stock(),
        signal_count=1,
        today_signal_count=1,
        high_impact_count=1,
        attention_score=0.82,
        market=None,
        latest_event_title=feed_item.title,
        latest_event_at=feed_item.published_at,
        last_updated_at=feed_item.published_at,
        sentiment_counts={"positive": 1},
        top_signals=[feed_item],
        disclaimer="Informational only.",
    )


def make_stock_briefing() -> StockBriefing:
    feed_item = make_feed_item()
    timeline_item = StockBriefingTimelineItem(
        item=feed_item,
        signal_score=0.84,
        reason="HBM demand links directly to watched memory names.",
        event_type="demand_signal",
        possible_market_impact="positive",
        price_reaction="no_price_data",
        confidence=0.71,
        time_sensitivity="high",
        event_summary="Micron demand commentary is related to watched AI themes.",
        uncertainties=["Review the original source."],
    )
    return StockBriefing(
        stock=make_stock(),
        signal_count=1,
        attention_score=0.82,
        market=None,
        urgency="high",
        latest_signal_at=feed_item.published_at,
        sentiment_counts={"positive": 1},
        key_themes=["HBM"],
        ai_relevance_summary="Micron is watched for HBM demand.",
        theme_breakdown=[],
        market_impact_events=[
            StockMarketImpactEvent(
                event_type="demand_signal",
                item_count=1,
                latest_title=feed_item.title,
                latest_at=feed_item.published_at,
            )
        ],
        recent_timeline=[timeline_item],
        disclaimer="Informational only.",
    )


def make_stock() -> StockWatchlistItem:
    return StockWatchlistItem(
        ticker="MU",
        company_name="Micron",
        exchange="NASDAQ",
        sector="Technology",
        industry="Semiconductors",
        priority="High",
        group_name="Watch Only",
        related_ai_themes=["HBM"],
    )


def make_feed_item() -> FeedItem:
    return FeedItem(
        id=1,
        title="Micron discusses HBM demand",
        url="https://example.com/mu",
        source_name="Test",
        author=None,
        language="en",
        published_at=datetime(2026, 6, 25, 10, 0, tzinfo=UTC),
        category="stock_company_event",
        subcategory=None,
        tickers=["MU"],
        companies=["Micron"],
        products=[],
        topics=["HBM", "AI infrastructure"],
        sentiment="positive",
        relevance_score=0.8,
        importance_score=0.7,
        novelty_score=0.4,
        source_quality_score=0.7,
        stock_impact_score=0.84,
        summary_short=None,
        summary_detailed=None,
        why_it_matters="HBM demand links directly to watched memory names.",
    )
