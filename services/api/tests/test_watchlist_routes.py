import pytest

from app.api.routes import watchlist as watchlist_routes
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
