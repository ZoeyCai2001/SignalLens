from scripts.smoke_test_demo import create_demo_smoke_client, run_demo_smoke_checks


def test_demo_smoke_check_exercises_local_mvp_api_path() -> None:
    with create_demo_smoke_client() as client:
        result = run_demo_smoke_checks(client)

    assert result["feed_items"] >= 6
    assert result["saved_items"] >= 1
    assert result["stock_rows"] >= 3
    assert result["stock_move_order"][:2] == ["MRVL", "MU"]
    assert result["source_health_rows"] >= 5
    assert result["digest_items"] >= 1
    assert result["digest_snapshot_count"] == 1
    assert result["latest_digest_snapshot_items"] >= 1
    assert result["quality"]["covered_module_count"] == 5
    assert result["quality"]["classification_coverage"] >= 0.7
    assert result["quality"]["digest_snapshot_count"] == 1
    assert result["quality"]["latest_digest_age_days"] == 0
    assert result["quality"]["manual_submission_count"] == 1
    assert result["quality"]["saved_read_later_count"] >= 1
    assert result["mvp_checklist"]["ready_count"] >= 7
    assert result["mvp_checklist"]["needs_action_count"] <= 1
    assert result["module_counts"] == {
        "chinese": 1,
        "products": 3,
        "research": 1,
        "stocks": 1,
        "trends": 2,
    }
