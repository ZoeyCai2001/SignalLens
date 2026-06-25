import pytest
from pydantic import ValidationError

from app.schemas.watchlist import StockWatchlistItemUpdate
from app.services.seed_data import initial_stock_watchlist, initial_topic_watchlist
from app.services.watchlist import (
    build_stock_match_terms,
    build_stock_symbol_terms,
    build_stock_text_terms,
    clean_terms,
    normalize_ticker,
    normalize_topic,
)


def test_initial_stock_watchlist_contains_prd_tickers() -> None:
    tickers = {item.ticker for item in initial_stock_watchlist()}

    assert tickers == {"MU", "MRVL", "SNDK"}


def test_initial_topic_watchlist_contains_core_ai_topics() -> None:
    topics = {item.topic for item in initial_topic_watchlist()}

    assert "ai-coding-agents" in topics
    assert "agent-workflows" in topics
    assert "open-source-llms" in topics


def test_stock_match_terms_include_ticker_company_and_related_terms() -> None:
    stock = initial_stock_watchlist()[0]

    terms = build_stock_match_terms(stock)

    assert "MU" in terms
    assert "Micron Technology" in terms
    assert "HBM" in terms
    assert "AI server memory" in terms


def test_stock_symbol_terms_are_separate_from_text_terms() -> None:
    stock = initial_stock_watchlist()[0]

    assert "MU" in build_stock_symbol_terms(stock)
    assert "NVDA" in build_stock_symbol_terms(stock)
    assert "MU" not in build_stock_text_terms(stock)
    assert "NVIDIA" in build_stock_text_terms(stock)


def test_stock_watchlist_input_helpers_normalize_user_values() -> None:
    assert normalize_ticker(" $avgo ") == "AVGO"
    assert clean_terms([" HBM ", "HBM", "", "ai memory"]) == ["HBM", "ai memory"]


def test_topic_watchlist_input_helpers_normalize_user_values() -> None:
    assert normalize_topic(" Model Routing ") == "model-routing"


def test_stock_watchlist_update_rejects_negative_portfolio_values() -> None:
    with pytest.raises(ValidationError):
        StockWatchlistItemUpdate(shares=-1)

    with pytest.raises(ValidationError):
        StockWatchlistItemUpdate(average_cost=-1)
