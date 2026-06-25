from app.services.seed_data import initial_stock_watchlist


def test_initial_stock_watchlist_contains_prd_tickers() -> None:
    tickers = {item.ticker for item in initial_stock_watchlist()}

    assert tickers == {"MU", "MRVL", "SNDK"}
