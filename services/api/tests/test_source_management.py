import pytest

from app.db.models import Source, SourceRun
from app.schemas.sources import SourceUpdate
from app.services.ingestion import run_connector_ingestion
from app.services.source_health import serialize_source_health, update_source
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


class NeverFetchConnector(SourceConnector):
    source_name = "Never Fetch"
    source_type = "test"

    def __init__(self) -> None:
        self.fetch_called = False

    async def fetch(self, cursor: FetchCursor) -> FetchResult:
        self.fetch_called = True
        raise AssertionError("Disabled sources should not be fetched.")
