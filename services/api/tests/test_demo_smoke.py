from scripts.smoke_test_demo import create_demo_smoke_client, run_demo_smoke_checks


def test_demo_smoke_check_exercises_local_mvp_api_path() -> None:
    with create_demo_smoke_client() as client:
        result = run_demo_smoke_checks(client)

    assert result["feed_items"] >= 5
    assert result["stock_rows"] >= 3
    assert result["source_health_rows"] >= 5
    assert result["digest_items"] >= 1
    assert result["quality"]["covered_module_count"] == 5
    assert result["module_counts"] == {
        "chinese": 1,
        "products": 2,
        "research": 1,
        "stocks": 1,
        "trends": 1,
    }
