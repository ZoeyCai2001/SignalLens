from app.services.seed_data import initial_stock_watchlist, initial_topic_watchlist


def test_initial_stock_watchlist_contains_prd_tickers() -> None:
    tickers = {item.ticker for item in initial_stock_watchlist()}

    assert tickers == {"MU", "MRVL", "SNDK"}


def test_initial_topic_watchlist_contains_core_ai_topics() -> None:
    topics = {item.topic for item in initial_topic_watchlist()}

    assert "ai-coding-agents" in topics
    assert "agent-workflows" in topics
    assert "open-source-llms" in topics
