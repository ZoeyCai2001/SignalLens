from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routes import watchlist as watchlist_routes
from app.schemas.feed import FeedItem
from app.schemas.watchlist import (
    StockBriefing,
    StockBriefingTimelineItem,
    StockMarketImpactEvent,
    StockWatchlistItem,
)
from app.services.seed_data import (
    initial_company_watchlist,
    initial_product_watchlist,
    initial_stock_watchlist,
    initial_topic_watchlist,
)


@pytest.mark.anyio
async def test_watchlist_list_routes_seed_defaults_when_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = object()
    calls: list[str] = []

    monkeypatch.setattr(watchlist_routes, "list_stock_watchlist_items", lambda seed_db: [])
    monkeypatch.setattr(watchlist_routes, "list_company_watchlist", lambda seed_db: [])
    monkeypatch.setattr(watchlist_routes, "list_topic_watchlist", lambda seed_db: [])
    monkeypatch.setattr(watchlist_routes, "list_product_watchlist", lambda seed_db: [])

    def seed(name: str, items):
        def run(seed_db):
            assert seed_db is db
            calls.append(name)
            return items

        return run

    monkeypatch.setattr(
        watchlist_routes,
        "seed_initial_stock_watchlist",
        seed("stocks", initial_stock_watchlist()),
    )
    monkeypatch.setattr(
        watchlist_routes,
        "seed_initial_company_watchlist",
        seed("companies", initial_company_watchlist()),
    )
    monkeypatch.setattr(
        watchlist_routes,
        "seed_initial_topic_watchlist",
        seed("topics", initial_topic_watchlist()),
    )
    monkeypatch.setattr(
        watchlist_routes,
        "seed_initial_product_watchlist",
        seed("products", initial_product_watchlist()),
    )

    stocks = await watchlist_routes.list_stock_watchlist(db)
    companies = await watchlist_routes.list_companies(db)
    topics = await watchlist_routes.list_topics(db)
    products = await watchlist_routes.list_products(db)

    assert calls == ["stocks", "companies", "topics", "products"]
    assert {stock.ticker for stock in stocks} == {"MU", "MRVL", "SNDK"}
    assert any(company.company_key == "openai" for company in companies)
    assert any(topic.topic == "ai-coding-agents" for topic in topics)
    assert any(product.category == "ai-coding-tools" for product in products)


@pytest.mark.anyio
async def test_stock_briefing_llm_summary_route_uses_kimi_and_preferences(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preferences = SimpleNamespace(blocked_sources=["Blocked Source"])
    briefing = make_stock_briefing()
    seen: dict[str, object] = {}

    monkeypatch.setattr(watchlist_routes, "get_user_preferences", lambda db: preferences)
    monkeypatch.setattr(
        watchlist_routes,
        "get_settings",
        lambda: SimpleNamespace(moonshot_api_key="test-key"),
    )

    def fake_get_stock_briefing(db, ticker: str, limit: int = 10, blocked_sources=None):
        seen["db"] = db
        seen["ticker"] = ticker
        seen["limit"] = limit
        seen["blocked_sources"] = blocked_sources
        return briefing

    class FakeKimiClient:
        def __init__(self, settings) -> None:
            seen["settings"] = settings

        async def create_message(self, prompt: str, max_tokens: int):
            seen["prompt"] = prompt
            seen["max_tokens"] = max_tokens
            return SimpleNamespace(
                model="kimi-test",
                text="What happened\nMicron HBM demand strengthened.",
                input_tokens=30,
                output_tokens=12,
                total_tokens=42,
            )

    monkeypatch.setattr(watchlist_routes, "get_stock_briefing", fake_get_stock_briefing)
    monkeypatch.setattr(watchlist_routes, "KimiCodingClient", FakeKimiClient)

    db = object()
    result = await watchlist_routes.summarize_stock_briefing_with_llm(
        ticker="MU",
        db=db,
        limit=8,
    )

    assert result.ticker == "MU"
    assert result.model == "kimi-test"
    assert result.summary.startswith("What happened")
    assert result.total_tokens == 42
    assert seen["db"] is db
    assert seen["ticker"] == "MU"
    assert seen["limit"] == 8
    assert seen["blocked_sources"] == preferences.blocked_sources
    assert seen["max_tokens"] == 520
    assert "Micron discusses HBM demand" in str(seen["prompt"])


@pytest.mark.anyio
async def test_stock_briefing_llm_summary_route_requires_kimi_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        watchlist_routes,
        "get_settings",
        lambda: SimpleNamespace(moonshot_api_key=None),
    )

    with pytest.raises(HTTPException) as exc_info:
        await watchlist_routes.summarize_stock_briefing_with_llm(ticker="MU", db=object())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "MOONSHOT_API_KEY is not configured."


def make_stock_briefing() -> StockBriefing:
    feed_item = FeedItem(
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
    return StockBriefing(
        stock=StockWatchlistItem(
            ticker="MU",
            company_name="Micron",
            exchange="NASDAQ",
            sector="Technology",
            industry="Semiconductors",
            priority="High",
            group_name="Watch Only",
            related_ai_themes=["HBM"],
        ),
        signal_count=1,
        attention_score=0.82,
        market=None,
        urgency="high",
        latest_signal_at=feed_item.published_at,
        sentiment_counts={"positive": 1},
        key_themes=["HBM", "AI infrastructure"],
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
        recent_timeline=[
            StockBriefingTimelineItem(
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
        ],
        disclaimer="Informational only.",
    )
