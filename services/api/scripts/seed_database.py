import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.services.watchlist import (
    seed_initial_company_watchlist,
    seed_initial_product_watchlist,
    seed_initial_stock_watchlist,
    seed_initial_topic_watchlist,
)


def seed_database(db) -> dict[str, int]:
    stocks = seed_initial_stock_watchlist(db)
    companies = seed_initial_company_watchlist(db)
    topics = seed_initial_topic_watchlist(db)
    products = seed_initial_product_watchlist(db)
    return {
        "seeded_stock_watchlist_count": len(stocks),
        "seeded_company_watchlist_count": len(companies),
        "seeded_topic_watchlist_count": len(topics),
        "seeded_product_watchlist_count": len(products),
    }


def main() -> None:
    with SessionLocal() as db:
        print(seed_database(db))


if __name__ == "__main__":
    main()
