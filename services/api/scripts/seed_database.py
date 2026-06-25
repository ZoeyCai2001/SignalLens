import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.services.watchlist import seed_initial_stock_watchlist


def main() -> None:
    with SessionLocal() as db:
        items = seed_initial_stock_watchlist(db)
        print({"seeded_stock_watchlist_count": len(items)})


if __name__ == "__main__":
    main()
