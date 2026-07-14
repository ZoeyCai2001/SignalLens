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
    assert_minimum(seed_payload, "seeded_demo_manual_submission_count", 1)
    assert_minimum(seed_payload, "seeded_demo_price_count", 6)
    assert_minimum(seed_payload, "seeded_demo_alert_rule_count", 9)
    assert_minimum(seed_payload, "seeded_demo_digest_snapshot_count", 1)
    assert_minimum(seed_payload, "seeded_demo_digest_item_count", 1)

    feed = get_json(client, "/api/feed?limit=50")
    if len(feed) < 6:
        raise AssertionError(f"Expected at least 6 feed items, got {len(feed)}")
    saved_items = get_json(client, "/api/feed?limit=20&saved_only=true")
    if not any(
        item["source_name"] == "Demo Manual Capture" and "coding-agent" in item["manual_tags"]
        for item in saved_items
    ):
        raise AssertionError("Expected demo manual submission to be saved/read-later")

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
    moved_stocks = post_json(
        client,
        "/api/watchlist/stocks/MRVL/move",
        json_body={"direction": "up"},
    )
    moved_tickers = [item["ticker"] for item in moved_stocks]
    if moved_tickers[:2] != ["MRVL", "MU"]:
        raise AssertionError(f"Expected MRVL to move above MU, got {moved_tickers}")
    updated_stock = patch_json(
        client,
        "/api/watchlist/stocks/MRVL",
        json_body={"market_cap_usd": 1_200_000_000},
    )
    if updated_stock["market_cap_usd"] != 1_200_000_000:
        raise AssertionError(
            "Expected stock market cap to round trip through the watchlist API, "
            f"got {updated_stock['market_cap_usd']!r}"
        )

    companies = get_json(client, "/api/watchlist/companies")
    topics = get_json(client, "/api/watchlist/topics")
    products = get_json(client, "/api/watchlist/products")
    assert_minimum_collection(companies, "company watchlist rows", 5)
    assert_minimum_collection(topics, "topic watchlist rows", 5)
    assert_minimum_collection(products, "product watchlist rows", 3)
    company_briefing_counts = [
        get_json(
            client,
            f"/api/watchlist/companies/{company['company_key']}/briefing?limit=20",
        )["item_count"]
        for company in companies[:5]
    ]
    topic_briefing_counts = [
        get_json(client, f"/api/watchlist/topics/{topic['topic']}/briefing?limit=20")[
            "item_count"
        ]
        for topic in topics[:5]
    ]
    product_briefings = [
        get_json(
            client,
            f"/api/watchlist/products/{product['category']}/briefing?limit=20",
        )
        for product in products[:3]
    ]
    product_briefing_counts = [briefing["item_count"] for briefing in product_briefings]
    assert_any_positive(company_briefing_counts, "company briefing item counts")
    assert_any_positive(topic_briefing_counts, "topic briefing item counts")
    assert_any_positive(product_briefing_counts, "product briefing item counts")
    if not any(briefing["discovery_scores"] for briefing in product_briefings):
        raise AssertionError("Expected product briefings to expose discovery score evidence")

    source_health = get_json(client, "/api/sources/health")
    if len(source_health) < 8:
        raise AssertionError(f"Expected at least 8 source-health rows, got {len(source_health)}")
    source_policy = "Store demo source metadata, summaries, attribution, and short excerpts only."
    updated_source = patch_json(
        client,
        f"/api/sources/{source_health[0]['id']}",
        json_body={"raw_content_policy": source_policy},
    )
    if updated_source["raw_content_policy"] != source_policy:
        raise AssertionError("Expected source raw-content policy to round trip through the API")

    quality_metrics = get_json(client, "/api/quality-metrics")
    assert_minimum(quality_metrics, "recent_item_count", 5)
    assert_minimum(quality_metrics, "covered_module_count", 5)
    mvp_checklist = get_json(client, "/api/mvp-checklist")
    if mvp_checklist["total_count"] != 9:
        raise AssertionError(
            f"Expected 9 PRD MVP checklist rows, got {mvp_checklist['total_count']}"
        )
    checklist_by_key = {item["key"]: item for item in mvp_checklist["items"]}
    for key in [
        "dashboard-feed",
        "source-ingestion",
        "watchlists",
        "stock-watchlist",
        "daily-digest",
        "alerts",
        "manual-submission",
    ]:
        if checklist_by_key[key]["status"] != "ready":
            raise AssertionError(
                f"Expected checklist row {key} to be ready, "
                f"got {checklist_by_key[key]['status']}"
            )
    if checklist_by_key["manual-submission"]["action_module"] != "submit":
        raise AssertionError(
            "Expected ready manual-submission checklist action to open Submit URL"
        )
    if not checklist_by_key["source-ingestion"]["metric"].startswith("8/8 PRD families"):
        raise AssertionError(
            "Expected source-ingestion checklist to show full PRD source-family coverage, "
            f"got {checklist_by_key['source-ingestion']['metric']!r}"
        )

    digest = get_json(client, "/api/digest/daily")
    if digest["total_items"] <= 0:
        raise AssertionError("Expected the demo daily digest to contain items")
    digest_snapshots = get_json(client, "/api/digest/daily/snapshots")
    if not digest_snapshots:
        raise AssertionError("Expected demo data seeding to save a daily digest snapshot")
    feedback_snapshot = patch_json(
        client,
        f"/api/digest/daily/snapshots/{digest_snapshots[0]['id']}/feedback",
        json_body={"usefulness_feedback": "useful"},
    )
    if feedback_snapshot["usefulness_feedback"] != "useful":
        raise AssertionError(
            "Expected digest snapshot feedback to round trip as useful, "
            f"got {feedback_snapshot['usefulness_feedback']!r}"
        )
    quality_metrics = get_json(client, "/api/quality-metrics")
    if quality_metrics["digest_feedback_count"] < 1:
        raise AssertionError("Expected digest feedback to appear in quality metrics")
    if quality_metrics["digest_feedback_usefulness_rate"] != 1:
        raise AssertionError(
            "Expected useful digest feedback rate to be 1, "
            f"got {quality_metrics['digest_feedback_usefulness_rate']!r}"
        )

    clusters = get_json(client, "/api/events/clusters?limit=8&min_items=1")
    alerts = get_json(client, "/api/alerts")
    health = get_json(client, "/api/health")
    backup = get_json(client, "/api/settings/backup")
    backup_text = json.dumps(backup).lower()
    if backup["version"] != 1:
        raise AssertionError(f"Expected settings backup version 1, got {backup['version']!r}")
    if "api_key" in backup_text or "moonshot" in backup_text or "raw_items" in backup_text:
        raise AssertionError("Settings backup exposed secret or raw-item fields")
    assert_minimum_collection(backup["sources"], "backup sources", 8)
    assert_minimum_collection(backup["alert_rules"], "backup alert rules", 8)
    assert_minimum_collection(backup["stock_watchlist"], "backup stock watchlist rows", 3)
    backed_up_stocks = {stock["ticker"]: stock for stock in backup["stock_watchlist"]}
    if backed_up_stocks["MRVL"]["market_cap_usd"] != 1_200_000_000:
        raise AssertionError("Expected settings backup to include stock market cap")
    backed_up_sources = {source["name"]: source for source in backup["sources"]}
    if backed_up_sources[updated_source["name"]]["raw_content_policy"] != source_policy:
        raise AssertionError("Expected settings backup to include source raw-content policy")
    assert_minimum_collection(backup["company_watchlist"], "backup company watchlist rows", 5)
    assert_minimum_collection(backup["topic_watchlist"], "backup topic watchlist rows", 5)
    assert_minimum_collection(backup["product_watchlist"], "backup product watchlist rows", 3)
    patch_json(
        client,
        "/api/preferences",
        json_body={
            "blocked_sources": ["Temporary Noisy Source"],
            "language_preferences": ["zh"],
        },
    )
    restore_result = post_json(client, "/api/settings/restore", json_body=backup)
    restored_preferences = get_json(client, "/api/preferences")
    expected_blocked_sources = backup["preferences"]["blocked_sources"]
    expected_languages = backup["preferences"]["language_preferences"]
    if restored_preferences["blocked_sources"] != expected_blocked_sources:
        raise AssertionError(
            "Expected settings restore to recover blocked sources, "
            f"got {restored_preferences['blocked_sources']!r}"
        )
    if restored_preferences["language_preferences"] != expected_languages:
        raise AssertionError(
            "Expected settings restore to recover language preferences, "
            f"got {restored_preferences['language_preferences']!r}"
        )
    restored_sources = {
        source["name"]: source for source in get_json(client, "/api/sources/health")
    }
    source_policy_restored = (
        restored_sources[updated_source["name"]]["raw_content_policy"] == source_policy
    )
    if not source_policy_restored:
        raise AssertionError("Expected settings restore to recover source raw-content policy")

    return {
        "seed": seed_payload,
        "feed_items": len(feed),
        "saved_items": len(saved_items),
        "module_counts": module_counts,
        "stock_rows": len(stocks),
        "stock_move_order": moved_tickers,
        "company_watchlist_rows": len(companies),
        "topic_watchlist_rows": len(topics),
        "product_watchlist_rows": len(products),
        "company_briefing_counts": company_briefing_counts,
        "topic_briefing_counts": topic_briefing_counts,
        "product_briefing_counts": product_briefing_counts,
        "product_discovery_score_count": sum(
            len(briefing["discovery_scores"]) for briefing in product_briefings
        ),
        "source_health_rows": len(source_health),
        "digest_items": digest["total_items"],
        "digest_snapshot_count": len(digest_snapshots),
        "latest_digest_snapshot_items": digest_snapshots[0]["total_items"],
        "cluster_count": len(clusters),
        "alert_count": len(alerts),
        "quality": {
            "recent_item_count": quality_metrics["recent_item_count"],
            "covered_module_count": quality_metrics["covered_module_count"],
            "relevance_precision_proxy": quality_metrics["relevance_precision_proxy"],
            "duplicate_rate": quality_metrics["duplicate_rate"],
            "summary_coverage": quality_metrics["summary_coverage"],
            "classification_coverage": quality_metrics["classification_coverage"],
            "low_confidence_item_count": quality_metrics["low_confidence_item_count"],
            "recent_source_count": quality_metrics["recent_source_count"],
            "trusted_source_coverage": quality_metrics["trusted_source_coverage"],
            "search_facet_coverage": quality_metrics["search_facet_coverage"],
            "source_failure_rate": quality_metrics["source_failure_rate"],
            "high_value_item_count": quality_metrics["high_value_item_count"],
            "high_value_items_per_day": quality_metrics["high_value_items_per_day"],
            "high_value_unsummarized_count": quality_metrics[
                "high_value_unsummarized_count"
            ],
            "digest_snapshot_count": quality_metrics["digest_snapshot_count"],
            "digest_feedback_count": quality_metrics["digest_feedback_count"],
            "digest_feedback_usefulness_rate": quality_metrics[
                "digest_feedback_usefulness_rate"
            ],
            "digest_usefulness_proxy": quality_metrics["digest_usefulness_proxy"],
            "latest_digest_age_days": quality_metrics["latest_digest_age_days"],
            "manual_submission_count": quality_metrics["manual_submission_count"],
            "manual_enrichment_gap_count": quality_metrics["manual_enrichment_gap_count"],
            "saved_read_later_count": quality_metrics["saved_read_later_count"],
            "alert_usefulness_proxy": quality_metrics["alert_usefulness_proxy"],
            "llm_call_count": quality_metrics["llm_call_count"],
            "llm_total_tokens": quality_metrics["llm_total_tokens"],
            "llm_projected_monthly_cost_usd": quality_metrics[
                "llm_projected_monthly_cost_usd"
            ],
            "source_api_call_count": quality_metrics["source_api_call_count"],
            "source_api_calls_per_recent_item": quality_metrics[
                "source_api_calls_per_recent_item"
            ],
            "source_api_projected_monthly_cost_usd": quality_metrics[
                "source_api_projected_monthly_cost_usd"
            ],
        },
        "mvp_checklist": {
            "ready_count": mvp_checklist["ready_count"],
            "partial_count": mvp_checklist["partial_count"],
            "needs_action_count": mvp_checklist["needs_action_count"],
            "source_ingestion_metric": checklist_by_key["source-ingestion"]["metric"],
        },
        "health": {
            "status": health["status"],
            "core_ready": health["setup_summary"]["core_ready"],
        },
        "settings_backup": {
            "sources": len(backup["sources"]),
            "alert_rules": len(backup["alert_rules"]),
            "stock_watchlist": len(backup["stock_watchlist"]),
            "stock_market_cap_restored": backed_up_stocks["MRVL"]["market_cap_usd"]
            == 1_200_000_000,
            "source_raw_content_policy_restored": source_policy_restored,
            "company_watchlist": len(backup["company_watchlist"]),
            "topic_watchlist": len(backup["topic_watchlist"]),
            "product_watchlist": len(backup["product_watchlist"]),
            "preferences_restored": restore_result["preferences_updated"],
            "sources_upserted": restore_result["sources_upserted"],
            "alert_rules_upserted": restore_result["alert_rules_upserted"],
        },
    }


def get_json(client: TestClient, path: str) -> Any:
    response = client.get(path)
    if response.status_code != 200:
        raise AssertionError(f"GET {path} failed: {response.status_code} {response.text}")
    return response.json()


def post_json(client: TestClient, path: str, json_body: dict[str, Any] | None = None) -> Any:
    response = client.post(path, json=json_body)
    if response.status_code != 200:
        raise AssertionError(f"POST {path} failed: {response.status_code} {response.text}")
    return response.json()


def patch_json(client: TestClient, path: str, json_body: dict[str, Any] | None = None) -> Any:
    response = client.patch(path, json=json_body)
    if response.status_code != 200:
        raise AssertionError(f"PATCH {path} failed: {response.status_code} {response.text}")
    return response.json()


def assert_minimum(payload: dict[str, Any], key: str, minimum: int) -> None:
    value = payload.get(key)
    if not isinstance(value, int) or value < minimum:
        raise AssertionError(f"Expected {key} >= {minimum}, got {value!r}")


def assert_minimum_collection(items: list[Any], label: str, minimum: int) -> None:
    if len(items) < minimum:
        raise AssertionError(f"Expected at least {minimum} {label}, got {len(items)}")


def assert_any_positive(values: list[int], label: str) -> None:
    if not any(value > 0 for value in values):
        raise AssertionError(f"Expected at least one positive {label}, got {values}")


def main() -> None:
    with create_demo_smoke_client() as client:
        result = run_demo_smoke_checks(client)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
