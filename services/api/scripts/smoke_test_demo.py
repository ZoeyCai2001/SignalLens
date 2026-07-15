# ruff: noqa: E402, I001
import json
import sys
import warnings
from pathlib import Path
from time import perf_counter
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
FEED_RESPONSE_BUDGET_SECONDS = 3.0
SEARCH_RESPONSE_BUDGET_SECONDS = 5.0
DIGEST_RESPONSE_BUDGET_SECONDS = 300.0
SOURCE_HEALTH_OPERATIONAL_FIELDS = {
    "raw_content_policy",
    "failure_handling",
    "latest_status",
    "latest_duration_seconds",
    "last_success_at",
    "next_run_due_at",
    "is_stale",
    "needs_attention",
    "recent_run_count",
    "recent_success_rate",
    "recent_store_rate",
    "recent_items_fetched",
    "recent_items_stored",
}


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

    feed, feed_elapsed_seconds = timed_get_json(client, "/api/feed?limit=50")
    assert_response_budget(
        label="Dashboard initial feed",
        elapsed_seconds=feed_elapsed_seconds,
        budget_seconds=FEED_RESPONSE_BUDGET_SECONDS,
    )
    if len(feed) < 6:
        raise AssertionError(f"Expected at least 6 feed items, got {len(feed)}")
    primary_item = feed[0]
    if not primary_item["title"] or not primary_item["source_name"] or not primary_item["url"]:
        raise AssertionError("Expected feed cards to include title, source, and original URL")
    if primary_item["summary_short"] is None and primary_item["summary_detailed"] is None:
        raise AssertionError("Expected feed cards to include a summary")
    if primary_item["relevance_score"] < 0 or primary_item["novelty_score"] < 0:
        raise AssertionError(
            "Expected feed cards to include non-negative relevance and novelty scores"
        )
    if primary_item["importance_score"] < 0:
        raise AssertionError("Expected feed cards to include a non-negative importance score")
    item_detail = get_json(client, f"/api/feed/{primary_item['id']}")
    if not item_detail["score_explanation"]:
        raise AssertionError("Expected item detail to include a why-am-I-seeing-this explanation")
    if not item_detail["one_line_summary"]:
        raise AssertionError("Expected item detail to include a one-line summary profile")
    if not item_detail["card_summary"]:
        raise AssertionError("Expected item detail to include a card summary profile")
    if not item_detail["why_it_matters"]:
        raise AssertionError("Expected item detail to include why-it-matters context")
    detailed_item = next((item for item in feed if item["summary_detailed"]), None)
    if detailed_item is None:
        raise AssertionError("Expected demo feed to include an item with a detailed summary")
    detailed_detail = get_json(client, f"/api/feed/{detailed_item['id']}")
    if not detailed_detail["summary_detailed"]:
        raise AssertionError("Expected item detail to include a detailed summary")
    technical_item = next(
        (
            item
            for item in feed
            if item["category"]
            in {
                "research",
                "technical_trend",
                "infrastructure",
                "benchmark_evaluation",
                "open_source_release",
            }
        ),
        None,
    )
    if technical_item is None:
        raise AssertionError("Expected demo feed to include a technical or research item")
    technical_detail = get_json(client, f"/api/feed/{technical_item['id']}")
    if not technical_detail["technical_summary"]:
        raise AssertionError(
            "Expected technical/research item detail to include a technical summary profile"
        )
    market_item = next((item for item in feed if item["tickers"]), None)
    if market_item is None:
        raise AssertionError("Expected demo feed to include a stock-linked item")
    market_detail = get_json(client, f"/api/feed/{market_item['id']}")
    if not market_detail["market_watch_summary"]:
        raise AssertionError(
            "Expected stock-linked item detail to include a market-watch summary profile"
        )
    if not isinstance(item_detail["action_state"], dict):
        raise AssertionError("Expected item detail to include action state")
    action_item = next(
        (
            item
            for item in feed
            if item["source_name"] != "Demo Manual Capture"
            and item["id"] not in {feed[0]["id"], feed[1]["id"]}
        ),
        feed[2],
    )
    action_item_id = action_item["id"]
    saved_action = post_json(client, f"/api/feed/{action_item_id}/save")
    if saved_action["is_saved"] is not True:
        raise AssertionError("Expected save action to mark a feed item saved")
    important_action = post_json(client, f"/api/feed/{action_item_id}/mark-important")
    if important_action["is_important"] is not True:
        raise AssertionError("Expected important action to mark a feed item important")
    hidden_action = post_json(client, f"/api/feed/{action_item_id}/hide")
    if hidden_action["is_hidden"] is not True:
        raise AssertionError("Expected hide action to hide a feed item")
    hidden_items = get_json(client, "/api/feed?hidden_only=true&limit=20")
    if not any(item["id"] == action_item_id for item in hidden_items):
        raise AssertionError("Expected hidden feed query to include the hidden item")
    unhidden_action = post_json(client, f"/api/feed/{action_item_id}/unhide")
    if unhidden_action["is_hidden"] is not False:
        raise AssertionError("Expected unhide action to restore a feed item")
    post_json(client, f"/api/feed/{action_item_id}/unsave")
    post_json(client, f"/api/feed/{action_item_id}/unmark-important")
    useful_item = post_json(client, f"/api/feed/{feed[0]['id']}/mark-useful")
    not_useful_item = post_json(client, f"/api/feed/{feed[1]['id']}/mark-not-useful")
    if useful_item["usefulness_feedback"] != "useful":
        raise AssertionError("Expected item useful feedback to round trip")
    if not_useful_item["usefulness_feedback"] != "not_useful":
        raise AssertionError("Expected item not-useful feedback to round trip")
    feedback_profile = get_json(client, "/api/preferences/feedback-profile")
    if feedback_profile["useful_count"] < 1 or feedback_profile["not_useful_count"] < 1:
        raise AssertionError(
            "Expected feedback profile to expose useful and not-useful item signals"
        )
    if not feedback_profile["liked_terms"] or not feedback_profile["disliked_terms"]:
        raise AssertionError("Expected feedback profile to expose learned feedback terms")
    saved_items = get_json(client, "/api/feed?limit=20&saved_only=true")
    if not any(
        item["source_name"] == "Demo Manual Capture" and "coding-agent" in item["manual_tags"]
        for item in saved_items
    ):
        raise AssertionError("Expected demo manual submission to be saved/read-later")
    saved_json_export = get_json(client, "/api/feed/saved/export/json?limit=100")
    if saved_json_export["item_count"] != len(saved_json_export["items"]):
        raise AssertionError("Expected saved JSON export count to match exported items")
    if not any(
        item["source_name"] == "Demo Manual Capture"
        and "coding-agent" in item["manual_tags"]
        and item["is_saved"] is True
        for item in saved_json_export["items"]
    ):
        raise AssertionError("Expected saved JSON export to preserve manual notes and tags")
    unread_saved_json_export = get_json(
        client,
        "/api/feed/saved/export/json?include_read=false&limit=100",
    )
    if any(item["is_read"] for item in unread_saved_json_export["items"]):
        raise AssertionError("Expected unread saved JSON export to exclude read items")

    module_counts = {}
    for module in DEMO_MODULES:
        module_items = get_json(client, f"/api/feed?module={module}&limit=20")
        if not module_items:
            raise AssertionError(f"Expected demo feed items for module {module}")
        module_counts[module] = len(module_items)

    stock_search, structured_search_elapsed_seconds = timed_get_json(
        client,
        "/api/search?category=stock_company_event&ticker=MU&limit=10",
    )
    assert_response_budget(
        label="Structured search",
        elapsed_seconds=structured_search_elapsed_seconds,
        budget_seconds=SEARCH_RESPONSE_BUDGET_SECONDS,
    )
    if not stock_search:
        raise AssertionError("Expected structured stock search to find MU demo news")
    product_search, product_search_elapsed_seconds = timed_post_json(
        client,
        "/api/search/natural-language",
        json_body={
            "query": "What are the latest AI search products?",
            "limit": 10,
            "module": "products",
        },
    )
    assert_response_budget(
        label="Natural-language product search",
        elapsed_seconds=product_search_elapsed_seconds,
        budget_seconds=SEARCH_RESPONSE_BUDGET_SECONDS,
    )
    if product_search["intent"]["category"] != "product":
        raise AssertionError(
            "Expected natural-language product search to infer product category, "
            f"got {product_search['intent']['category']!r}"
        )
    if not product_search["items"]:
        raise AssertionError("Expected natural-language product search to find demo products")
    chinese_search, chinese_search_elapsed_seconds = timed_post_json(
        client,
        "/api/search/natural-language",
        json_body={
            "query": "Show Chinese social media posts about AI photo tools.",
            "limit": 10,
            "module": "chinese",
        },
    )
    assert_response_budget(
        label="Natural-language Chinese search",
        elapsed_seconds=chinese_search_elapsed_seconds,
        budget_seconds=SEARCH_RESPONSE_BUDGET_SECONDS,
    )
    if chinese_search["intent"]["language"] != "zh":
        raise AssertionError(
            "Expected natural-language Chinese search to infer zh language, "
            f"got {chinese_search['intent']['language']!r}"
        )
    if not chinese_search["items"]:
        raise AssertionError("Expected natural-language Chinese search to find demo signals")
    reddit_search, reddit_search_elapsed_seconds = timed_post_json(
        client,
        "/api/search/natural-language",
        json_body={
            "query": "Show Reddit posts about local LLM coding agents.",
            "limit": 10,
            "module": "trends",
        },
    )
    assert_response_budget(
        label="Natural-language Reddit search",
        elapsed_seconds=reddit_search_elapsed_seconds,
        budget_seconds=SEARCH_RESPONSE_BUDGET_SECONDS,
    )
    if reddit_search["intent"]["source"] != "Reddit":
        raise AssertionError(
            "Expected natural-language Reddit search to infer Reddit source, "
            f"got {reddit_search['intent']['source']!r}"
        )
    if not any(item["source_name"] == "Reddit AI Communities" for item in reddit_search["items"]):
        raise AssertionError("Expected natural-language Reddit search to find demo Reddit signals")
    manual_tag_search, manual_tag_search_elapsed_seconds = timed_get_json(
        client,
        "/api/search?manual_tag=coding-agent&limit=10",
    )
    assert_response_budget(
        label="Manual-tag search",
        elapsed_seconds=manual_tag_search_elapsed_seconds,
        budget_seconds=SEARCH_RESPONSE_BUDGET_SECONDS,
    )
    if not any(item["source_name"] == "Demo Manual Capture" for item in manual_tag_search):
        raise AssertionError("Expected manual-tag search to find the saved demo capture")

    stocks = get_json(client, "/api/stocks/watchlist-dashboard")
    tickers = {item["stock"]["ticker"] for item in stocks}
    missing_tickers = {"MU", "MRVL", "SNDK"} - tickers
    if missing_tickers:
        raise AssertionError(f"Missing seeded stock rows: {sorted(missing_tickers)}")
    stock_detail = get_json(client, "/api/stocks/MU")
    if "does not provide investment advice" not in stock_detail["disclaimer"]:
        raise AssertionError("Expected stock detail to expose the non-financial-advice disclaimer")
    if not stock_detail["ai_relevance_summary"]:
        raise AssertionError("Expected stock detail to include an AI relevance summary")
    if not stock_detail["recent_timeline"]:
        raise AssertionError("Expected stock detail to include a recent stock-news timeline")
    stock_events = get_json(client, "/api/stocks/MU/events?limit=10")
    if not stock_events:
        raise AssertionError("Expected stock events endpoint to return MU timeline rows")
    stock_price_series = get_json(client, "/api/stocks/MU/price-series?limit=30")
    if stock_price_series is None or not stock_price_series["history"]:
        raise AssertionError("Expected stock price-series endpoint to return seeded MU prices")
    created_stock = post_json(
        client,
        "/api/watchlist/stocks",
        json_body={
            "ticker": "AVGO",
            "company_name": "Broadcom",
            "priority": "Low",
            "related_ai_themes": ["AI networking"],
        },
        expected_status=201,
    )
    if created_stock["ticker"] != "AVGO":
        raise AssertionError(
            "Expected temporary stock creation to resolve AVGO, "
            f"got {created_stock['ticker']!r}"
        )
    delete_no_content(client, "/api/watchlist/stocks/AVGO")
    after_delete_stocks = get_json(client, "/api/watchlist/stocks")
    if any(stock["ticker"] == "AVGO" for stock in after_delete_stocks):
        raise AssertionError("Expected temporary stock deletion to remove AVGO")
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
    source_health_evidence = assert_source_health_operational_contract(source_health)
    scheduler_status = get_json(client, "/api/ingestion/schedule")
    if scheduler_status["interval_minutes"] < 1:
        raise AssertionError(
            "Expected scheduler interval to be positive, "
            f"got {scheduler_status['interval_minutes']!r}"
        )
    if not scheduler_status["built_in_jobs"]:
        raise AssertionError("Expected scheduler status to expose built-in ingestion jobs")
    if "python scripts/run_scheduler.py" not in scheduler_status["command_hint"]:
        raise AssertionError("Expected scheduler status to include the runnable command hint")
    if (
        scheduler_status["digest_target_hour_utc"] < 0
        or scheduler_status["digest_target_hour_utc"] > 23
    ):
        raise AssertionError(
            "Expected digest target hour to stay in UTC hour range, "
            f"got {scheduler_status['digest_target_hour_utc']!r}"
        )
    if scheduler_status["due_custom_source_count"] != len(scheduler_status["due_custom_sources"]):
        raise AssertionError("Expected due custom source count to match listed due sources")
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
    assert_minimum(quality_metrics, "recent_product_signal_count", 1)
    assert_minimum(quality_metrics, "high_traction_product_signal_count", 1)
    assert_minimum(quality_metrics, "product_signal_source_count", 1)
    if quality_metrics["relevance_precision_proxy"] < 0.7:
        raise AssertionError(
            "Expected demo quality metrics to satisfy the PRD 70% relevance target, "
            f"got {quality_metrics['relevance_precision_proxy']!r}"
        )
    latest_item_age_hours = quality_metrics["latest_item_age_hours"]
    if latest_item_age_hours is None or latest_item_age_hours > 36:
        raise AssertionError(
            "Expected demo quality metrics to prove fresh daily collection, "
            f"got latest item age {latest_item_age_hours!r}h"
        )
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
    if not checklist_by_key["source-ingestion"]["metric"].startswith("9/9 PRD families"):
        raise AssertionError(
            "Expected source-ingestion checklist to show full PRD source-family coverage, "
            f"got {checklist_by_key['source-ingestion']['metric']!r}"
        )

    alerts = get_json(client, "/api/alerts?limit=20")
    if not alerts:
        raise AssertionError("Expected demo alert generation to create dashboard alerts")
    feedback_alert = patch_json(
        client,
        f"/api/alerts/{alerts[0]['id']}/feedback",
        json_body={"usefulness_feedback": "useful"},
    )
    if feedback_alert["usefulness_feedback"] != "useful":
        raise AssertionError(
            "Expected alert feedback to round trip as useful, "
            f"got {feedback_alert['usefulness_feedback']!r}"
        )

    digest, digest_generation_elapsed_seconds = timed_post_json(
        client,
        "/api/digest/daily/generate",
    )
    assert_response_budget(
        label="Daily digest generation",
        elapsed_seconds=digest_generation_elapsed_seconds,
        budget_seconds=DIGEST_RESPONSE_BUDGET_SECONDS,
    )
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
    if quality_metrics["item_feedback_count"] != 2:
        raise AssertionError(
            "Expected two item feedback samples, "
            f"got {quality_metrics['item_feedback_count']!r}"
        )
    if quality_metrics["item_feedback_usefulness_rate"] != 0.5:
        raise AssertionError(
            "Expected item feedback usefulness rate to be 0.5, "
            f"got {quality_metrics['item_feedback_usefulness_rate']!r}"
        )
    if quality_metrics["alert_feedback_count"] < 1:
        raise AssertionError("Expected alert feedback to appear in quality metrics")
    if quality_metrics["alert_feedback_usefulness_rate"] != 1:
        raise AssertionError(
            "Expected alert feedback usefulness rate to be useful, "
            f"got {quality_metrics['alert_feedback_usefulness_rate']!r}"
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

    deletion_probe = post_json(
        client,
        "/api/manual-submissions",
        json_body={
            "title": "Temporary deletion probe for privacy workflow",
            "url": "https://example.com/demo/delete-probe",
            "text": (
                "Temporary AI note used only to verify permanent deletion of stored "
                "content and personal action state."
            ),
            "source_name": "Manual Submission",
            "save_item": True,
            "manual_tags": ["delete-probe"],
        },
    )
    deletion_item_id = deletion_probe["item"]["id"]
    saved_deletion_probe = get_json(client, f"/api/feed/{deletion_item_id}")
    if saved_deletion_probe["action_state"]["is_saved"] is not True:
        raise AssertionError("Expected deletion probe to be saved before deletion")
    delete_no_content(client, f"/api/feed/{deletion_item_id}")
    deleted_detail_status = get_status(client, f"/api/feed/{deletion_item_id}")
    if deleted_detail_status != 404:
        raise AssertionError(
            "Expected deleted feed item detail to return 404, "
            f"got {deleted_detail_status}"
        )

    return {
        "seed": seed_payload,
        "feed_items": len(feed),
        "feed_detail": {
            "id": item_detail["id"],
            "has_score_explanation": bool(item_detail["score_explanation"]),
            "has_one_line_summary": bool(item_detail["one_line_summary"]),
            "card_summary_count": len(item_detail["card_summary"]),
            "has_detailed_summary": bool(detailed_detail["summary_detailed"]),
            "has_why_it_matters": bool(item_detail["why_it_matters"]),
            "has_technical_summary": bool(technical_detail["technical_summary"]),
            "has_market_watch_summary": bool(market_detail["market_watch_summary"]),
            "has_action_state": isinstance(item_detail["action_state"], dict),
        },
        "feed_actions": {
            "saved_item_id": saved_action["id"],
            "important_item_id": important_action["id"],
            "hidden_item_id": hidden_action["id"],
            "hidden_query_count": len(hidden_items),
            "unhidden": unhidden_action["is_hidden"] is False,
        },
        "feedback_profile": {
            "useful_count": feedback_profile["useful_count"],
            "not_useful_count": feedback_profile["not_useful_count"],
            "liked_terms": len(feedback_profile["liked_terms"]),
            "disliked_terms": len(feedback_profile["disliked_terms"]),
            "watchlist_terms": len(feedback_profile["watchlist_terms"]),
        },
        "saved_items": len(saved_items),
        "saved_json_export_items": saved_json_export["item_count"],
        "saved_unread_json_export_items": unread_saved_json_export["item_count"],
        "module_counts": module_counts,
        "search": {
            "stock_items": len(stock_search),
            "product_items": len(product_search["items"]),
            "product_intent_category": product_search["intent"]["category"],
            "reddit_items": len(reddit_search["items"]),
            "reddit_intent_source": reddit_search["intent"]["source"],
            "chinese_items": len(chinese_search["items"]),
            "chinese_intent_language": chinese_search["intent"]["language"],
            "manual_tag_items": len(manual_tag_search),
        },
        "performance": {
            "feed_ms": elapsed_milliseconds(feed_elapsed_seconds),
            "structured_search_ms": elapsed_milliseconds(structured_search_elapsed_seconds),
            "product_natural_search_ms": elapsed_milliseconds(product_search_elapsed_seconds),
            "reddit_natural_search_ms": elapsed_milliseconds(reddit_search_elapsed_seconds),
            "chinese_natural_search_ms": elapsed_milliseconds(chinese_search_elapsed_seconds),
            "manual_tag_search_ms": elapsed_milliseconds(manual_tag_search_elapsed_seconds),
            "digest_generation_ms": elapsed_milliseconds(digest_generation_elapsed_seconds),
            "feed_budget_ms": elapsed_milliseconds(FEED_RESPONSE_BUDGET_SECONDS),
            "search_budget_ms": elapsed_milliseconds(SEARCH_RESPONSE_BUDGET_SECONDS),
            "digest_budget_ms": elapsed_milliseconds(DIGEST_RESPONSE_BUDGET_SECONDS),
        },
        "stock_rows": len(stocks),
        "stock_detail": {
            "ticker": stock_detail["stock"]["ticker"],
            "timeline_items": len(stock_detail["recent_timeline"]),
            "event_rows": len(stock_events),
            "linked_tickers": sorted(
                {
                    ticker
                    for event in stock_events
                    for ticker in event["item"].get("tickers", [])
                }
            ),
            "ai_related_event_rows": sum(
                1 for event in stock_events if event["item"]["is_ai_related"]
            ),
            "high_impact_events": sum(
                1
                for event in stock_events
                if event["item"]["stock_impact_score"] >= 0.75
                or event["item"]["importance_score"] >= 0.75
            ),
            "price_points": len(stock_price_series["history"]),
            "has_ai_relevance_summary": bool(stock_detail["ai_relevance_summary"]),
            "has_disclaimer": "does not provide investment advice"
            in stock_detail["disclaimer"],
            "created_deleted_ticker": created_stock["ticker"],
            "post_delete_rows": len(after_delete_stocks),
        },
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
        "source_health": source_health_evidence,
        "scheduler": {
            "mode": scheduler_status["mode"],
            "interval_minutes": scheduler_status["interval_minutes"],
            "built_in_job_count": len(scheduler_status["built_in_jobs"]),
            "due_custom_source_count": scheduler_status["due_custom_source_count"],
            "digest_snapshot_fresh": scheduler_status["digest_snapshot_fresh"],
        },
        "digest_items": digest["total_items"],
        "digest_snapshot_count": len(digest_snapshots),
        "latest_digest_snapshot_items": digest_snapshots[0]["total_items"],
        "cluster_count": len(clusters),
        "alert_count": len(alerts),
        "quality": {
            "recent_item_count": quality_metrics["recent_item_count"],
            "latest_item_age_hours": quality_metrics["latest_item_age_hours"],
            "covered_module_count": quality_metrics["covered_module_count"],
            "relevance_precision_proxy": quality_metrics["relevance_precision_proxy"],
            "duplicate_rate": quality_metrics["duplicate_rate"],
            "summary_coverage": quality_metrics["summary_coverage"],
            "summary_quality_proxy": quality_metrics["summary_quality_proxy"],
            "thin_summary_count": quality_metrics["thin_summary_count"],
            "classification_coverage": quality_metrics["classification_coverage"],
            "low_confidence_item_count": quality_metrics["low_confidence_item_count"],
            "recent_source_count": quality_metrics["recent_source_count"],
            "trusted_source_coverage": quality_metrics["trusted_source_coverage"],
            "search_facet_coverage": quality_metrics["search_facet_coverage"],
            "source_failure_rate": quality_metrics["source_failure_rate"],
            "source_total_count": quality_metrics["source_total_count"],
            "enabled_source_count": quality_metrics["enabled_source_count"],
            "runnable_source_count": quality_metrics["runnable_source_count"],
            "manual_source_count": quality_metrics["manual_source_count"],
            "unconfigured_source_count": quality_metrics["unconfigured_source_count"],
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
            "item_feedback_count": quality_metrics["item_feedback_count"],
            "item_feedback_usefulness_rate": quality_metrics[
                "item_feedback_usefulness_rate"
            ],
            "alert_feedback_count": quality_metrics["alert_feedback_count"],
            "alert_feedback_usefulness_rate": quality_metrics[
                "alert_feedback_usefulness_rate"
            ],
            "latest_digest_age_days": quality_metrics["latest_digest_age_days"],
            "manual_submission_count": quality_metrics["manual_submission_count"],
            "manual_enrichment_gap_count": quality_metrics["manual_enrichment_gap_count"],
            "recent_product_signal_count": quality_metrics["recent_product_signal_count"],
            "high_traction_product_signal_count": quality_metrics[
                "high_traction_product_signal_count"
            ],
            "product_signal_source_count": quality_metrics["product_signal_source_count"],
            "event_cluster_count": quality_metrics["event_cluster_count"],
            "confirmed_event_cluster_count": quality_metrics[
                "confirmed_event_cluster_count"
            ],
            "event_cluster_timeline_item_count": quality_metrics[
                "event_cluster_timeline_item_count"
            ],
            "clustered_recent_item_share": quality_metrics["clustered_recent_item_share"],
            "recent_stock_signal_count": quality_metrics["recent_stock_signal_count"],
            "recent_stock_high_impact_count": quality_metrics[
                "recent_stock_high_impact_count"
            ],
            "stock_signal_ticker_count": quality_metrics["stock_signal_ticker_count"],
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
            "stock_watchlist_metric": checklist_by_key["stock-watchlist"]["metric"],
        },
        "health": {
            "status": health["status"],
            "core_ready": health["setup_summary"]["core_ready"],
            "reddit_user_agent_ready": health["integrations"]["reddit_user_agent"],
            "setup_env_vars": [item["env_var"] for item in health["setup_items"]],
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
        "privacy_deletion": {
            "deleted_item_id": deletion_item_id,
            "detail_status_after_delete": deleted_detail_status,
        },
    }


def get_json(client: TestClient, path: str) -> Any:
    response = client.get(path)
    if response.status_code != 200:
        raise AssertionError(f"GET {path} failed: {response.status_code} {response.text}")
    return response.json()


def timed_get_json(client: TestClient, path: str) -> tuple[Any, float]:
    started_at = perf_counter()
    payload = get_json(client, path)
    return payload, perf_counter() - started_at


def get_status(client: TestClient, path: str) -> int:
    return client.get(path).status_code


def post_json(
    client: TestClient,
    path: str,
    json_body: dict[str, Any] | None = None,
    expected_status: int = 200,
) -> Any:
    response = client.post(path, json=json_body)
    if response.status_code != expected_status:
        raise AssertionError(f"POST {path} failed: {response.status_code} {response.text}")
    return response.json()


def timed_post_json(
    client: TestClient,
    path: str,
    json_body: dict[str, Any] | None = None,
    expected_status: int = 200,
) -> tuple[Any, float]:
    started_at = perf_counter()
    payload = post_json(
        client=client,
        path=path,
        json_body=json_body,
        expected_status=expected_status,
    )
    return payload, perf_counter() - started_at


def delete_no_content(client: TestClient, path: str) -> None:
    response = client.delete(path)
    if response.status_code != 204:
        raise AssertionError(f"DELETE {path} failed: {response.status_code} {response.text}")


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


def assert_response_budget(label: str, elapsed_seconds: float, budget_seconds: float) -> None:
    if elapsed_seconds > budget_seconds:
        raise AssertionError(
            f"{label} took {elapsed_seconds:.3f}s, above the {budget_seconds:.3f}s PRD budget"
        )


def elapsed_milliseconds(elapsed_seconds: float) -> int:
    return round(elapsed_seconds * 1000)


def assert_source_health_operational_contract(
    source_health: list[dict[str, Any]],
) -> dict[str, int]:
    missing_fields_by_source = {
        source["name"]: sorted(SOURCE_HEALTH_OPERATIONAL_FIELDS - set(source))
        for source in source_health
        if SOURCE_HEALTH_OPERATIONAL_FIELDS - set(source)
    }
    if missing_fields_by_source:
        raise AssertionError(
            "Expected source health rows to expose operational dashboard fields, "
            f"missing {missing_fields_by_source!r}"
        )

    policy_rows = [
        source
        for source in source_health
        if source["raw_content_policy"] and source["failure_handling"]
    ]
    recent_run_rows = [source for source in source_health if source["recent_run_count"] > 0]
    quality_rows = [
        source
        for source in recent_run_rows
        if source["recent_success_rate"] is not None
        and source["recent_store_rate"] is not None
        and source["recent_items_fetched"] >= source["recent_items_stored"] >= 0
    ]
    if len(policy_rows) != len(source_health):
        raise AssertionError("Expected every source-health row to expose policy guidance")
    if len(recent_run_rows) < 8:
        raise AssertionError(
            "Expected demo source health to include recent run evidence for PRD source families, "
            f"got {len(recent_run_rows)} rows"
        )
    if len(quality_rows) != len(recent_run_rows):
        raise AssertionError(
            "Expected recent source runs to include success and store-rate metrics"
        )

    return {
        "policy_rows": len(policy_rows),
        "recent_run_rows": len(recent_run_rows),
        "quality_rows": len(quality_rows),
    }


def main() -> None:
    with create_demo_smoke_client() as client:
        result = run_demo_smoke_checks(client)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
