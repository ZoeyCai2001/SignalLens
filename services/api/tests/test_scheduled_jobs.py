import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes import ingestion as ingestion_routes
from app.db.models import Base, Source, SourceRun
from app.services.ingestion import IngestionResult, SourceRunnerNotFoundError
from app.services.scheduled_jobs import (
    ScheduledCycleResult,
    ScheduledIngestionJob,
    list_enabled_custom_sources,
    parse_polling_interval,
    run_ingestion_cycle,
    scheduled_cycle_to_log_dict,
    source_due_for_cycle,
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
        seed_watchlists=lambda _db: (3, 5, 4, 2),
        generate_cycle_alerts_fn=lambda _db: 2,
        save_digest_snapshot_fn=lambda _db: date(2026, 6, 26),
        list_custom_sources_fn=lambda _db: [],
    )

    assert calls == ["one:3", "two:5"]
    assert result.seeded_stock_count == 3
    assert result.seeded_company_count == 5
    assert result.seeded_topic_count == 4
    assert result.seeded_product_count == 2
    assert result.generated_alert_count == 2
    assert result.saved_digest_date == date(2026, 6, 26)
    assert [item.source_name for item in result.ingestion_results] == ["one", "two"]


@pytest.mark.anyio
async def test_run_ingestion_cycle_continues_after_job_exception() -> None:
    calls: list[str] = []
    db = object()

    async def fake_runner(name: str, _db, limit: int) -> IngestionResult:
        calls.append(f"{name}:{limit}")
        if name == "broken":
            raise RuntimeError("source timeout")
        return IngestionResult(
            source_name=name,
            status="success",
            items_fetched=limit,
            items_stored=limit,
        )

    result = await run_ingestion_cycle(
        db,
        jobs=[
            make_job("broken", 3, fake_runner),
            make_job("healthy", 5, fake_runner),
        ],
        seed_watchlists=lambda _db: (0, 0, 0, 0),
        generate_cycle_alerts_fn=lambda _db: 4,
        save_digest_snapshot_fn=lambda _db: date(2026, 6, 26),
        list_custom_sources_fn=lambda _db: [],
    )

    assert calls == ["broken:3", "healthy:5"]
    assert result.generated_alert_count == 4
    assert result.saved_digest_date == date(2026, 6, 26)
    assert result.ingestion_results[0] == IngestionResult(
        source_name="broken",
        status="failed",
        items_fetched=0,
        items_stored=0,
        error_message="source timeout",
    )
    assert result.ingestion_results[1].source_name == "healthy"


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
            seed_watchlists=lambda _db: (3, 5, 4, 2),
            generate_cycle_alerts_fn=lambda _db: 1,
            save_digest_snapshot_fn=lambda _db: date(2026, 6, 26),
            list_custom_sources_fn=lambda _db: [],
        )

    log_data = scheduled_cycle_to_log_dict(asyncio.run(run_cycle()))

    assert log_data["seeded_stock_count"] == 3
    assert log_data["seeded_company_count"] == 5
    assert log_data["seeded_topic_count"] == 4
    assert log_data["seeded_product_count"] == 2
    assert log_data["generated_alert_count"] == 1
    assert log_data["saved_digest_date"] == "2026-06-26"
    assert isinstance(log_data["duration_seconds"], float)
    assert log_data["successful_source_count"] == 1
    assert log_data["failed_source_count"] == 0
    assert log_data["skipped_source_count"] == 0
    assert log_data["ingestion_results"] == [
        {
            "source_name": "test",
            "status": "success",
            "items_fetched": 1,
            "items_stored": 1,
            "error_message": None,
        }
    ]


def test_scheduled_cycle_result_counts_source_statuses() -> None:
    result = ScheduledCycleResult(
        started_at=datetime(2026, 6, 27, 8, 0, tzinfo=UTC),
        finished_at=datetime(2026, 6, 27, 8, 2, 5, tzinfo=UTC),
        seeded_stock_count=0,
        seeded_company_count=0,
        seeded_topic_count=0,
        seeded_product_count=0,
        generated_alert_count=0,
        saved_digest_date=None,
        ingestion_results=[
            IngestionResult(source_name="rss", status="success", items_fetched=5, items_stored=4),
            IngestionResult(source_name="github", status="failed", items_fetched=0, items_stored=0),
            IngestionResult(
                source_name="custom",
                status="skipped",
                items_fetched=0,
                items_stored=0,
            ),
        ],
    )

    assert result.duration_seconds == 125
    assert result.successful_source_count == 1
    assert result.failed_source_count == 1
    assert result.skipped_source_count == 1


def test_parse_polling_interval_handles_common_source_frequency_text() -> None:
    assert parse_polling_interval("hourly") == timedelta(hours=1)
    assert parse_polling_interval("daily") == timedelta(days=1)
    assert parse_polling_interval("every 4 hours") == timedelta(hours=4)
    assert parse_polling_interval("15 minutes") == timedelta(minutes=15)
    assert parse_polling_interval("unknown") is None


def test_source_due_for_cycle_respects_latest_run_and_interval() -> None:
    source = Source(
        id=1,
        name="Custom RSS",
        type="blog",
        access_method="rss",
        polling_interval="6 hours",
    )
    now = datetime(2026, 6, 28, 12, 0, tzinfo=UTC)

    assert source_due_for_cycle(source=source, latest_run=None, now=now)
    assert not source_due_for_cycle(
        source=source,
        latest_run=SourceRun(
            source_id=1,
            status="success",
            started_at=datetime(2026, 6, 28, 9, 0, tzinfo=UTC),
        ),
        now=now,
    )
    assert source_due_for_cycle(
        source=source,
        latest_run=SourceRun(
            source_id=1,
            status="success",
            started_at=datetime(2026, 6, 28, 5, 0, tzinfo=UTC),
        ),
        now=now,
    )


def test_list_enabled_custom_sources_skips_sources_before_polling_interval() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        due = Source(
            name="Due RSS",
            type="blog",
            access_method="rss",
            polling_interval="1 hour",
            enabled=True,
            priority=10,
        )
        recent = Source(
            name="Recent RSS",
            type="blog",
            access_method="rss",
            polling_interval="7 days",
            enabled=True,
            priority=20,
        )
        disabled = Source(
            name="Disabled RSS",
            type="blog",
            access_method="rss",
            polling_interval="1 hour",
            enabled=False,
            priority=30,
        )
        db.add_all([due, recent, disabled])
        db.flush()
        db.add(
            SourceRun(
                source_id=recent.id,
                status="success",
                started_at=datetime.now(UTC),
            )
        )
        db.commit()

        sources = list_enabled_custom_sources(db)

    assert [source.name for source in sources] == ["Due RSS"]


@pytest.mark.anyio
async def test_run_ingestion_cycle_runs_enabled_custom_sources_after_default_jobs() -> None:
    calls: list[str] = []
    db = object()

    async def fake_runner(name: str, _db, limit: int) -> IngestionResult:
        calls.append(f"default:{name}:{limit}")
        return IngestionResult(
            source_name=name,
            status="success",
            items_fetched=limit,
            items_stored=limit,
        )

    async def fake_custom_runner(_db, source_id: int) -> IngestionResult:
        calls.append(f"custom:{source_id}")
        return IngestionResult(
            source_name=f"Custom {source_id}",
            status="success",
            items_fetched=2,
            items_stored=1,
        )

    result = await run_ingestion_cycle(
        db,
        jobs=[make_job("rss", 5, fake_runner)],
        seed_watchlists=lambda _db: (0, 0, 0, 0),
        generate_cycle_alerts_fn=lambda _db: 0,
        save_digest_snapshot_fn=lambda _db: date(2026, 6, 26),
        list_custom_sources_fn=lambda _db: [
            SimpleNamespace(id=11, name="Custom RSS"),
            SimpleNamespace(id=12, name="LangChain Repo"),
        ],
        run_custom_source_fn=fake_custom_runner,
    )

    assert calls == ["default:rss:5", "custom:11", "custom:12"]
    assert [item.source_name for item in result.ingestion_results] == [
        "rss",
        "Custom 11",
        "Custom 12",
    ]


@pytest.mark.anyio
async def test_run_ingestion_cycle_records_skipped_custom_source_without_runner() -> None:
    db = FakeDb()

    async def fake_custom_runner(_db, _source_id: int) -> IngestionResult:
        raise SourceRunnerNotFoundError("No runnable connector is registered.")

    result = await run_ingestion_cycle(
        db,
        jobs=[],
        seed_watchlists=lambda _db: (0, 0, 0, 0),
        generate_cycle_alerts_fn=lambda _db: 0,
        save_digest_snapshot_fn=lambda _db: date(2026, 6, 26),
        list_custom_sources_fn=lambda _db: [
            SimpleNamespace(id=11, name="Manual Watch"),
        ],
        run_custom_source_fn=fake_custom_runner,
    )

    assert result.ingestion_results[0].status == "skipped"
    assert result.ingestion_results[0].error_message == "No runnable connector is registered."
    assert db.added[0].source_id == 11
    assert db.added[0].status == "skipped"
    assert db.commits == 1


@pytest.mark.anyio
async def test_run_ingestion_cycle_records_failed_custom_source_and_continues() -> None:
    async def fake_custom_runner(_db, _source_id: int) -> IngestionResult:
        raise RuntimeError("custom feed failed")

    result = await run_ingestion_cycle(
        object(),
        jobs=[],
        seed_watchlists=lambda _db: (0, 0, 0, 0),
        generate_cycle_alerts_fn=lambda _db: 1,
        save_digest_snapshot_fn=lambda _db: date(2026, 6, 26),
        list_custom_sources_fn=lambda _db: [
            SimpleNamespace(id=11, name="Custom RSS"),
        ],
        run_custom_source_fn=fake_custom_runner,
    )

    assert result.generated_alert_count == 1
    assert result.saved_digest_date == date(2026, 6, 26)
    assert result.ingestion_results == [
        IngestionResult(
            source_name="Custom RSS",
            status="failed",
            items_fetched=0,
            items_stored=0,
            error_message="custom feed failed",
        )
    ]


@pytest.mark.anyio
async def test_ingestion_cycle_route_serializes_result(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_cycle(db) -> ScheduledCycleResult:
        assert db == "db-session"
        return ScheduledCycleResult(
            started_at=datetime(2026, 6, 27, 8, 0, tzinfo=UTC),
            finished_at=datetime(2026, 6, 27, 8, 1, tzinfo=UTC),
            seeded_stock_count=2,
            seeded_company_count=5,
            seeded_topic_count=3,
            seeded_product_count=4,
            generated_alert_count=1,
            saved_digest_date=date(2026, 6, 27),
            ingestion_results=[
                IngestionResult(
                    source_name="rss",
                    status="success",
                    items_fetched=5,
                    items_stored=4,
                )
            ],
        )

    monkeypatch.setattr(ingestion_routes, "run_ingestion_cycle", fake_cycle)

    response = await ingestion_routes.run_scheduled_ingestion_cycle("db-session")

    assert response.seeded_stock_count == 2
    assert response.seeded_company_count == 5
    assert response.seeded_topic_count == 3
    assert response.seeded_product_count == 4
    assert response.generated_alert_count == 1
    assert response.saved_digest_date == date(2026, 6, 27)
    assert response.duration_seconds == 60
    assert response.successful_source_count == 1
    assert response.failed_source_count == 0
    assert response.skipped_source_count == 0
    assert response.ingestion_results[0].source_name == "rss"
    assert response.ingestion_results[0].items_stored == 4


def make_job(
    name: str,
    limit: int,
    fake_runner: Callable[[str, object, int], Awaitable[IngestionResult]],
) -> ScheduledIngestionJob:
    async def runner(db, runner_limit: int) -> IngestionResult:
        return await fake_runner(name, db, runner_limit)

    return ScheduledIngestionJob(name=name, runner=runner, limit=limit)


class FakeDb:
    def __init__(self) -> None:
        self.added = []
        self.commits = 0

    def add(self, value) -> None:
        self.added.append(value)

    def commit(self) -> None:
        self.commits += 1
