from datetime import UTC, datetime

import pytest

from app.db.models import Source, SourceRun
from app.schemas.sources import SourceCreate, SourceUpdate
from app.services import ingestion as ingestion_service
from app.services.ingestion import (
    IngestionResult,
    RegisteredSourceRunner,
    run_connector_ingestion,
    run_source_ingestion_by_id,
)
from app.services.source_health import (
    create_source,
    serialize_source_health,
    serialize_source_run_history_item,
    update_source,
)
from app.sources.base import FetchCursor, FetchResult, SourceConnector


def test_serialize_source_health_includes_enabled_flag_and_run_status() -> None:
    source = Source(
        id=1,
        name="Test Source",
        type="rss",
        access_method="rss",
        base_url="https://example.com/feed.xml",
        auth_required=False,
        rate_limit="60/hour",
        polling_interval="hourly",
        enabled=False,
        priority=20,
        terms_notes="Use RSS feed only.",
    )
    run = SourceRun(
        source_id=1,
        status="skipped",
        items_fetched=0,
        items_stored=0,
        error_message="disabled",
    )

    health = serialize_source_health(source, run)

    assert health.enabled is False
    assert health.base_url == "https://example.com/feed.xml"
    assert health.rate_limit == "60/hour"
    assert health.polling_interval == "hourly"
    assert health.priority == 20
    assert health.terms_notes == "Use RSS feed only."
    assert health.latest_status == "skipped"
    assert health.latest_error == "disabled"


def test_update_source_trims_editable_settings_and_clears_empty_notes() -> None:
    source = Source(
        id=7,
        name="Configurable Source",
        type="api",
        access_method="api",
        enabled=True,
        priority=100,
    )
    db = FakeSourceDb(source)

    updated = update_source(
        db,
        source_id=7,
        payload=SourceUpdate(
            enabled=False,
            priority=30,
            polling_interval="  every 4 hours ",
            rate_limit="  75/day  ",
            terms_notes="   ",
        ),
    )

    assert updated is source
    assert source.enabled is False
    assert source.priority == 30
    assert source.polling_interval == "every 4 hours"
    assert source.rate_limit == "75/day"
    assert source.terms_notes is None
    assert db.commits == 1


def test_create_source_registers_followed_rss_source() -> None:
    db = FakeCreateSourceDb()

    source = create_source(
        db,
        SourceCreate(
            name="  Latent Space RSS ",
            type="blog",
            access_method="rss",
            base_url=" https://example.com/rss.xml ",
            priority=45,
            terms_notes=" Public RSS feed only. ",
        ),
    )

    assert source.name == "Latent Space RSS"
    assert source.type == "blog"
    assert source.access_method == "rss"
    assert source.base_url == "https://example.com/rss.xml"
    assert source.priority == 45
    assert source.terms_notes == "Public RSS feed only."
    assert db.added == [source]
    assert db.commits == 1


def test_create_source_rejects_duplicate_name() -> None:
    existing = Source(id=1, name="Existing", type="blog", access_method="rss")
    db = FakeCreateSourceDb(existing=existing)

    with pytest.raises(ValueError):
        create_source(db, SourceCreate(name="Existing"))


def test_serialize_source_run_history_item_includes_source_name_and_counts() -> None:
    source = Source(id=3, name="arXiv", type="research", access_method="api")
    run = SourceRun(
        id=9,
        source_id=3,
        status="failed",
        items_fetched=4,
        items_stored=2,
        error_message="rate limited",
        started_at=datetime(2026, 6, 27, 8, 0, tzinfo=UTC),
        finished_at=datetime(2026, 6, 27, 8, 1, tzinfo=UTC),
    )

    item = serialize_source_run_history_item(run=run, source=source)

    assert item.id == 9
    assert item.source_name == "arXiv"
    assert item.status == "failed"
    assert item.items_fetched == 4
    assert item.items_stored == 2
    assert item.error_message == "rate limited"


@pytest.mark.anyio
async def test_disabled_source_ingestion_is_skipped_without_fetching() -> None:
    db = FakeDb()
    source = Source(
        id=1,
        name="Disabled Source",
        type="rss",
        access_method="rss",
        enabled=False,
    )
    connector = NeverFetchConnector()

    result = await run_connector_ingestion(db=db, connector=connector, source=source)

    assert result.status == "skipped"
    assert result.error_message == "Disabled Source is disabled."
    assert connector.fetch_called is False
    assert db.commits == 1


@pytest.mark.anyio
async def test_run_source_ingestion_by_id_uses_registered_runner_default_limit() -> None:
    source = Source(
        id=4,
        name="Hacker News",
        type="community",
        access_method="official_api",
    )
    db = FakeSourceDb(source)
    calls: list[tuple[object, int]] = []

    async def fake_runner(runner_db, limit: int) -> IngestionResult:
        calls.append((runner_db, limit))
        return IngestionResult(
            source_name="Hacker News",
            status="success",
            items_fetched=limit,
            items_stored=limit - 1,
        )

    result = await run_source_ingestion_by_id(
        db=db,
        source_id=4,
        runners_by_name={
            "Hacker News": RegisteredSourceRunner(
                source_name="Hacker News",
                runner=fake_runner,
                default_limit=30,
            )
        },
    )

    assert calls == [(db, 30)]
    assert result.source_name == "Hacker News"
    assert result.items_fetched == 30
    assert result.items_stored == 29


@pytest.mark.anyio
async def test_run_source_ingestion_by_id_runs_custom_rss_source(monkeypatch) -> None:
    source = Source(
        id=5,
        name="Custom Blog",
        type="blog",
        access_method="rss",
        base_url="https://example.com/feed.xml",
        enabled=True,
    )
    db = FakeSourceDb(source)
    calls = []

    async def fake_run_connector_ingestion(db, connector, source):
        calls.append((db, connector, source))
        return IngestionResult(
            source_name=source.name,
            status="success",
            items_fetched=3,
            items_stored=2,
        )

    monkeypatch.setattr(
        ingestion_service,
        "run_connector_ingestion",
        fake_run_connector_ingestion,
    )

    result = await ingestion_service.run_source_ingestion_by_id(
        db=db,
        source_id=5,
        limit=3,
        runners_by_name={},
    )

    assert result.source_name == "Custom Blog"
    assert result.items_fetched == 3
    assert calls[0][1].source_name == "Custom Blog"
    assert calls[0][1].feeds[0].url == "https://example.com/feed.xml"


class FakeDb:
    def __init__(self) -> None:
        self.commits = 0
        self.added = []

    def add(self, value) -> None:
        self.added.append(value)

    def commit(self) -> None:
        self.commits += 1


class FakeSourceDb(FakeDb):
    def __init__(self, source: Source) -> None:
        super().__init__()
        self.source = source

    def get(self, model, source_id: int):
        if model is Source and source_id == self.source.id:
            return self.source
        return None

    def refresh(self, value) -> None:
        return None


class FakeCreateSourceDb(FakeDb):
    def __init__(self, existing: Source | None = None) -> None:
        super().__init__()
        self.existing = existing

    def query(self, _model):
        return self

    def filter(self, *_args):
        return self

    def one_or_none(self):
        return self.existing

    def refresh(self, value) -> None:
        return None


class NeverFetchConnector(SourceConnector):
    source_name = "Never Fetch"
    source_type = "test"

    def __init__(self) -> None:
        self.fetch_called = False

    async def fetch(self, cursor: FetchCursor) -> FetchResult:
        self.fetch_called = True
        raise AssertionError("Disabled sources should not be fetched.")
