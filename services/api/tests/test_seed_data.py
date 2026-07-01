import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, NormalizedItem, SourceRun, StockPricePoint
from app.schemas.watchlist import StockWatchlistItemUpdate
from app.services.demo_data import seed_demo_data
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
from scripts import seed_database as seed_database_script


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


def test_seed_database_script_seeds_all_default_watchlists(monkeypatch: pytest.MonkeyPatch) -> None:
    db = object()
    calls: list[str] = []

    def fake_seed(name: str, count: int):
        def run(seed_db):
            assert seed_db is db
            calls.append(name)
            return [object()] * count

        return run

    monkeypatch.setattr(seed_database_script, "seed_initial_stock_watchlist", fake_seed("stock", 3))
    monkeypatch.setattr(
        seed_database_script,
        "seed_initial_company_watchlist",
        fake_seed("company", 5),
    )
    monkeypatch.setattr(seed_database_script, "seed_initial_topic_watchlist", fake_seed("topic", 4))
    monkeypatch.setattr(
        seed_database_script,
        "seed_initial_product_watchlist",
        fake_seed("product", 2),
    )

    result = seed_database_script.seed_database(db)

    assert calls == ["stock", "company", "topic", "product"]
    assert result == {
        "seeded_stock_watchlist_count": 3,
        "seeded_company_watchlist_count": 5,
        "seeded_topic_watchlist_count": 4,
        "seeded_product_watchlist_count": 2,
    }


def test_seed_database_script_can_include_demo_data(monkeypatch: pytest.MonkeyPatch) -> None:
    db = object()
    monkeypatch.setattr(seed_database_script, "seed_initial_stock_watchlist", lambda _db: [])
    monkeypatch.setattr(seed_database_script, "seed_initial_company_watchlist", lambda _db: [])
    monkeypatch.setattr(seed_database_script, "seed_initial_topic_watchlist", lambda _db: [])
    monkeypatch.setattr(seed_database_script, "seed_initial_product_watchlist", lambda _db: [])
    monkeypatch.setattr(
        seed_database_script,
        "seed_demo_data",
        lambda seed_db: {
            "seeded_demo_item_count": 5,
            "seeded_demo_price_count": 6,
            "seeded_demo_alert_count": 2,
            "seeded_demo_alert_rule_count": 9,
        },
    )

    result = seed_database_script.seed_database(db, include_demo_data=True)

    assert result["seeded_demo_item_count"] == 5
    assert result["seeded_demo_price_count"] == 6


def test_seed_demo_data_populates_first_run_dashboard_examples() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        first = seed_demo_data(db)
        second = seed_demo_data(db)

        categories = {item.category for item in db.query(NormalizedItem).all()}

        assert first["seeded_demo_item_count"] == 5
        assert first["seeded_demo_price_count"] == 6
        assert first["seeded_demo_alert_rule_count"] == 9
        assert first["seeded_demo_alert_count"] >= 1
        assert second["seeded_demo_item_count"] == 0
        assert second["seeded_demo_price_count"] == 0
        expected_categories = {
            "research",
            "technical_trend",
            "product",
            "stock_company_event",
            "social_trend",
        }
        assert expected_categories.issubset(categories)
        assert db.query(SourceRun).count() == 5
        assert db.query(StockPricePoint).count() == 6


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
