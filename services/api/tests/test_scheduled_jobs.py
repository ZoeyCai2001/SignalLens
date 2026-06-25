import asyncio
from collections.abc import Awaitable, Callable
from datetime import date

import pytest

from app.services.ingestion import IngestionResult
from app.services.scheduled_jobs import (
    ScheduledIngestionJob,
    run_ingestion_cycle,
    scheduled_cycle_to_log_dict,
)


@pytest.mark.anyio
async def test_run_ingestion_cycle_runs_jobs_in_order() -> None:
    calls: list[str] = []
    db = object()

    async def fake_runner(name: str, _db, limit: int) -> IngestionResult:
        calls.append(f"{name}:{limit}")
        return IngestionResult(
            source_name=name,
            status="success",
            items_fetched=limit,
            items_stored=limit - 1,
        )

    jobs = [
        make_job("one", 3, fake_runner),
        make_job("two", 5, fake_runner),
    ]

    result = await run_ingestion_cycle(
        db,
        jobs=jobs,
        seed_watchlists=lambda _db: (3, 4),
        generate_cycle_alerts_fn=lambda _db: 2,
        save_digest_snapshot_fn=lambda _db: date(2026, 6, 26),
    )

    assert calls == ["one:3", "two:5"]
    assert result.seeded_stock_count == 3
    assert result.seeded_topic_count == 4
    assert result.generated_alert_count == 2
    assert result.saved_digest_date == date(2026, 6, 26)
    assert [item.source_name for item in result.ingestion_results] == ["one", "two"]


def test_scheduled_cycle_to_log_dict_is_json_ready() -> None:
    async def fake_runner(_db, limit: int) -> IngestionResult:
        return IngestionResult(
            source_name="test",
            status="success",
            items_fetched=limit,
            items_stored=limit,
        )

    job = ScheduledIngestionJob(name="test", runner=fake_runner, limit=1)

    async def run_cycle():
        return await run_ingestion_cycle(
            object(),
            jobs=[job],
            seed_watchlists=lambda _db: (3, 4),
            generate_cycle_alerts_fn=lambda _db: 1,
            save_digest_snapshot_fn=lambda _db: date(2026, 6, 26),
        )

    log_data = scheduled_cycle_to_log_dict(asyncio.run(run_cycle()))

    assert log_data["seeded_stock_count"] == 3
    assert log_data["seeded_topic_count"] == 4
    assert log_data["generated_alert_count"] == 1
    assert log_data["saved_digest_date"] == "2026-06-26"
    assert log_data["ingestion_results"] == [
        {
            "source_name": "test",
            "status": "success",
            "items_fetched": 1,
            "items_stored": 1,
            "error_message": None,
        }
    ]


def make_job(
    name: str,
    limit: int,
    fake_runner: Callable[[str, object, int], Awaitable[IngestionResult]],
) -> ScheduledIngestionJob:
    async def runner(db, runner_limit: int) -> IngestionResult:
        return await fake_runner(name, db, runner_limit)

    return ScheduledIngestionJob(name=name, runner=runner, limit=limit)
