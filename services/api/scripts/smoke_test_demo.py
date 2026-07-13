# ruff: noqa: E402, I001
import json
import sys
import warnings
from pathlib import Path
from typing import Any

warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.models import Base
from app.db.session import get_db
from app.main import create_app


DEMO_MODULES = ("trends", "research", "products", "stocks", "chinese")


def create_demo_smoke_client() -> TestClient:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    app = create_app()

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def run_demo_smoke_checks(client: TestClient) -> dict[str, Any]:
    seed_payload = post_json(client, "/api/ingestion/demo-data")
    assert_minimum(seed_payload, "seeded_demo_item_count", 5)
    assert_minimum(seed_payload, "seeded_demo_price_count", 6)
    assert_minimum(seed_payload, "seeded_demo_alert_rule_count", 9)
    assert_minimum(seed_payload, "seeded_demo_digest_snapshot_count", 1)
    assert_minimum(seed_payload, "seeded_demo_digest_item_count", 1)

    feed = get_json(client, "/api/feed?limit=50")
    if len(feed) < 5:
        raise AssertionError(f"Expected at least 5 feed items, got {len(feed)}")

    module_counts = {}
    for module in DEMO_MODULES:
        module_items = get_json(client, f"/api/feed?module={module}&limit=20")
        if not module_items:
            raise AssertionError(f"Expected demo feed items for module {module}")
        module_counts[module] = len(module_items)

    stocks = get_json(client, "/api/stocks/watchlist-dashboard")
    tickers = {item["stock"]["ticker"] for item in stocks}
    missing_tickers = {"MU", "MRVL", "SNDK"} - tickers
    if missing_tickers:
        raise AssertionError(f"Missing seeded stock rows: {sorted(missing_tickers)}")

    source_health = get_json(client, "/api/sources/health")
    if len(source_health) < 5:
        raise AssertionError(f"Expected at least 5 source-health rows, got {len(source_health)}")

    quality_metrics = get_json(client, "/api/quality-metrics")
    assert_minimum(quality_metrics, "recent_item_count", 5)
    assert_minimum(quality_metrics, "covered_module_count", 5)

    digest = get_json(client, "/api/digest/daily")
    if digest["total_items"] <= 0:
        raise AssertionError("Expected the demo daily digest to contain items")
    digest_snapshots = get_json(client, "/api/digest/daily/snapshots")
    if not digest_snapshots:
        raise AssertionError("Expected demo data seeding to save a daily digest snapshot")

    clusters = get_json(client, "/api/events/clusters?limit=8&min_items=1")
    alerts = get_json(client, "/api/alerts")
    health = get_json(client, "/api/health")

    return {
        "seed": seed_payload,
        "feed_items": len(feed),
        "module_counts": module_counts,
        "stock_rows": len(stocks),
        "source_health_rows": len(source_health),
        "digest_items": digest["total_items"],
        "digest_snapshot_count": len(digest_snapshots),
        "latest_digest_snapshot_items": digest_snapshots[0]["total_items"],
        "cluster_count": len(clusters),
        "alert_count": len(alerts),
        "quality": {
            "recent_item_count": quality_metrics["recent_item_count"],
            "covered_module_count": quality_metrics["covered_module_count"],
            "recent_source_count": quality_metrics["recent_source_count"],
            "digest_snapshot_count": quality_metrics["digest_snapshot_count"],
            "latest_digest_age_days": quality_metrics["latest_digest_age_days"],
        },
        "health": {
            "status": health["status"],
            "core_ready": health["setup_summary"]["core_ready"],
        },
    }


def get_json(client: TestClient, path: str) -> Any:
    response = client.get(path)
    if response.status_code != 200:
        raise AssertionError(f"GET {path} failed: {response.status_code} {response.text}")
    return response.json()


def post_json(client: TestClient, path: str) -> Any:
    response = client.post(path)
    if response.status_code != 200:
        raise AssertionError(f"POST {path} failed: {response.status_code} {response.text}")
    return response.json()


def assert_minimum(payload: dict[str, Any], key: str, minimum: int) -> None:
    value = payload.get(key)
    if not isinstance(value, int) or value < minimum:
        raise AssertionError(f"Expected {key} >= {minimum}, got {value!r}")


def main() -> None:
    with create_demo_smoke_client() as client:
        result = run_demo_smoke_checks(client)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
