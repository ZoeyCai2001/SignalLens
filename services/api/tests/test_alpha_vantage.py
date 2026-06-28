from app.db.models import RawItem, Source
from app.services.ingestion import normalize_item
from app.sources.alpha_vantage import AlphaVantageDailyPriceConnector, AlphaVantageNewsConnector


def test_alpha_vantage_connector_converts_news_entry_to_raw_item() -> None:
    connector = AlphaVantageNewsConnector(api_key="test-key", tickers=["MU"], limit=3)

    item = connector._entry_to_raw_item(
        {
            "title": "Micron says AI data center demand lifts HBM outlook",
            "url": "https://example.com/micron-ai-hbm",
            "time_published": "20260625T123000",
            "authors": ["Analyst Desk"],
            "summary": "Micron discussed AI server memory demand and HBM supply.",
            "source": "Example Finance",
            "source_domain": "example.com",
            "topics": [{"topic": "Technology"}, {"topic": "Financial Markets"}],
            "overall_sentiment_score": "0.31",
            "overall_sentiment_label": "Somewhat-Bullish",
            "ticker_sentiment": [
                {
                    "ticker": "MU",
                    "relevance_score": "0.92",
                    "ticker_sentiment_label": "Bullish",
                }
            ],
        }
    )

    assert item is not None
    assert item.external_id == "https://example.com/micron-ai-hbm"
    assert item.raw_author == "Analyst Desk"
    assert "Tickers: MU" in (item.raw_text or "")
    assert item.raw_metadata["ticker_sentiment"][0]["ticker"] == "MU"
    assert item.published_at is not None


def test_alpha_vantage_normalized_item_is_stock_company_event() -> None:
    source = Source(
        id=1,
        name="Alpha Vantage News",
        type="finance_news",
        access_method="official_api",
    )
    raw = RawItem(
        id=1,
        raw_title="Micron AI data center memory demand expands",
        url="https://example.com/micron-ai-hbm",
        raw_text="Micron discussed AI server memory, HBM, and GPU infrastructure demand.",
        raw_metadata={
            "ticker_sentiment": [
                {
                    "ticker": "MU",
                    "relevance_score": "0.92",
                    "sentiment_label": "Bullish",
                }
            ]
        },
    )

    item = normalize_item(raw=raw, source=source)

    assert item is not None
    assert item.category == "stock_company_event"
    assert item.subcategory == "finance_news"
    assert item.tickers == ["MU"]
    assert item.companies == ["Micron Technology"]
    assert item.source_quality_score == 0.82
    assert item.stock_impact_score == 0.55


def test_alpha_vantage_daily_price_connector_parses_recent_points() -> None:
    connector = AlphaVantageDailyPriceConnector(api_key="test-key", limit=2)

    points = connector.parse_daily_prices(
        ticker="mu",
        payload={
            "Time Series (Daily)": {
                "2026-06-25": {
                    "1. open": "110.00",
                    "2. high": "113.00",
                    "3. low": "109.00",
                    "4. close": "112.50",
                    "5. adjusted close": "112.50",
                    "6. volume": "123456",
                },
                "2026-06-24": {
                    "1. open": "108.00",
                    "2. high": "111.00",
                    "3. low": "107.50",
                    "4. close": "110.00",
                    "5. adjusted close": "110.00",
                    "6. volume": "98765",
                },
                "2026-06-23": {
                    "1. open": "106.00",
                    "2. high": "109.00",
                    "3. low": "105.00",
                    "4. close": "108.00",
                    "5. adjusted close": "108.00",
                    "6. volume": "77777",
                },
            }
        },
    )

    assert [point.price_date.isoformat() for point in points] == ["2026-06-25", "2026-06-24"]
    assert points[0].ticker == "MU"
    assert points[0].close_price == 112.5
    assert points[0].volume == 123456
