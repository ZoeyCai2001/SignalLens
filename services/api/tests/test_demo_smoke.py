from scripts.smoke_test_demo import create_demo_smoke_client, run_demo_smoke_checks


def test_demo_smoke_check_exercises_local_mvp_api_path() -> None:
    with create_demo_smoke_client() as client:
        result = run_demo_smoke_checks(client)

    assert result["feed_items"] >= 6
    assert result["saved_items"] >= 1
    assert result["stock_rows"] >= 3
    assert result["stock_move_order"][:2] == ["MRVL", "MU"]
    assert result["company_watchlist_rows"] >= 5
    assert result["topic_watchlist_rows"] >= 5
    assert result["product_watchlist_rows"] >= 3
    assert max(result["company_briefing_counts"]) > 0
    assert max(result["topic_briefing_counts"]) > 0
    assert max(result["product_briefing_counts"]) > 0
    assert result["product_discovery_score_count"] > 0
    assert result["source_health_rows"] >= 8
    assert result["digest_items"] >= 1
    assert result["digest_snapshot_count"] == 1
    assert result["latest_digest_snapshot_items"] >= 1
    assert result["quality"]["covered_module_count"] == 5
    assert result["quality"]["relevance_precision_proxy"] >= 0.7
    assert result["quality"]["duplicate_rate"] == 0
    assert result["quality"]["summary_coverage"] == 1
    assert result["quality"]["classification_coverage"] == 1
    assert result["quality"]["low_confidence_item_count"] == 0
    assert result["quality"]["trusted_source_coverage"] >= 0.7
    assert result["quality"]["search_facet_coverage"] == 1
    assert result["quality"]["source_failure_rate"] == 0
    assert result["quality"]["high_value_item_count"] >= 1
    assert result["quality"]["high_value_items_per_day"] > 0
    assert result["quality"]["high_value_unsummarized_count"] == 0
    assert result["quality"]["digest_snapshot_count"] == 1
    assert result["quality"]["digest_feedback_count"] == 1
    assert result["quality"]["digest_feedback_usefulness_rate"] == 1
    assert result["quality"]["digest_usefulness_proxy"] >= 0.9
    assert result["quality"]["item_feedback_count"] == 2
    assert result["quality"]["item_feedback_usefulness_rate"] == 0.5
    assert result["quality"]["alert_feedback_count"] == 1
    assert result["quality"]["alert_feedback_usefulness_rate"] == 1
    assert result["quality"]["latest_digest_age_days"] == 0
    assert result["quality"]["manual_submission_count"] == 1
    assert result["quality"]["manual_enrichment_gap_count"] == 0
    assert result["quality"]["saved_read_later_count"] >= 1
    assert result["quality"]["alert_usefulness_proxy"] > 0
    assert result["quality"]["llm_call_count"] == 0
    assert result["quality"]["llm_total_tokens"] == 0
    assert result["quality"]["llm_projected_monthly_cost_usd"] == 0
    assert result["quality"]["source_api_call_count"] >= 8
    assert result["quality"]["source_api_calls_per_recent_item"] > 0
    assert result["quality"]["source_api_projected_monthly_cost_usd"] == 0
    assert result["mvp_checklist"] == {
        "ready_count": 9,
        "partial_count": 0,
        "needs_action_count": 0,
        "source_ingestion_metric": "8/8 PRD families; 9 recent sources",
    }
    assert result["settings_backup"]["sources"] >= 8
    assert result["settings_backup"]["alert_rules"] >= 8
    assert result["settings_backup"]["stock_watchlist"] >= 3
    assert result["settings_backup"]["stock_market_cap_restored"] is True
    assert result["settings_backup"]["company_watchlist"] >= 5
    assert result["settings_backup"]["topic_watchlist"] >= 5
    assert result["settings_backup"]["product_watchlist"] >= 3
    assert result["settings_backup"]["preferences_restored"] is True
    assert result["settings_backup"]["sources_upserted"] >= 8
    assert result["settings_backup"]["alert_rules_upserted"] >= 8
    assert result["module_counts"] == {
        "chinese": 1,
        "products": 4,
        "research": 1,
        "stocks": 1,
        "trends": 4,
    }
    assert result["search"]["stock_items"] >= 1
    assert result["search"]["product_items"] >= 1
    assert result["search"]["product_intent_category"] == "product"
    assert result["search"]["chinese_items"] >= 1
    assert result["search"]["chinese_intent_language"] == "zh"
    assert result["search"]["manual_tag_items"] >= 1
