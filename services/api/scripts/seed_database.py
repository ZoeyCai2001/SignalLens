import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.services.demo_data import seed_demo_data
from app.services.watchlist import (
    seed_initial_company_watchlist,
    seed_initial_product_watchlist,
    seed_initial_stock_watchlist,
    seed_initial_topic_watchlist,
)


def seed_database(db, include_demo_data: bool = False) -> dict[str, int]:
    stocks = seed_initial_stock_watchlist(db)
    companies = seed_initial_company_watchlist(db)
    topics = seed_initial_topic_watchlist(db)
    products = seed_initial_product_watchlist(db)
    result = {
        "seeded_stock_watchlist_count": len(stocks),
        "seeded_company_watchlist_count": len(companies),
        "seeded_topic_watchlist_count": len(topics),
        "seeded_product_watchlist_count": len(products),
    }
    if include_demo_data:
        result.update(seed_demo_data(db))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed SignalLens local MVP data.")
    parser.add_argument(
        "--demo-data",
        action="store_true",
        help="Also seed local demo feed items, price points, source runs, and alerts.",
    )
    args = parser.parse_args()
    with SessionLocal() as db:
        print(seed_database(db, include_demo_data=args.demo_data))


if __name__ == "__main__":
    main()
