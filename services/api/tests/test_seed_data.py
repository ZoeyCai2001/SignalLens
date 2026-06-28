import pytest
from pydantic import ValidationError

from app.schemas.watchlist import StockWatchlistItemUpdate
from app.services.seed_data import (
    initial_company_watchlist,
    initial_product_watchlist,
    initial_stock_watchlist,
    initial_topic_watchlist,
)
from app.services.watchlist import (
    build_stock_match_terms,
    build_stock_symbol_terms,
    build_stock_text_terms,
    clean_terms,
    normalize_company_key,
    normalize_product_category,
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


def test_initial_product_watchlist_contains_prd_product_categories() -> None:
    categories = {item.category for item in initial_product_watchlist()}

    assert "ai-coding-tools" in categories
    assert "ai-search-browsers" in categories
    assert "ai-productivity" in categories


def test_initial_company_watchlist_contains_prd_related_companies_and_ai_labs() -> None:
    companies = {item.company_key: item for item in initial_company_watchlist()}

    assert companies["nvidia"].ticker == "NVDA"
    assert companies["amd"].ticker == "AMD"
    assert companies["broadcom"].ticker == "AVGO"
    assert companies["openai"].ticker is None


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


def test_product_watchlist_input_helpers_normalize_user_values() -> None:
    assert normalize_product_category(" AI Coding Tools ") == "ai-coding-tools"


def test_company_watchlist_input_helpers_normalize_user_values() -> None:
    assert normalize_company_key(" NVIDIA / Data Center ") == "nvidia-data-center"


def test_stock_watchlist_update_rejects_negative_portfolio_values() -> None:
    with pytest.raises(ValidationError):
        StockWatchlistItemUpdate(shares=-1)

    with pytest.raises(ValidationError):
        StockWatchlistItemUpdate(average_cost=-1)
