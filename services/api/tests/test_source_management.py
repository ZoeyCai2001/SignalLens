import pytest

from app.db.models import Source, SourceRun
from app.services.ingestion import run_connector_ingestion
from app.services.source_health import serialize_source_health
from app.sources.base import FetchCursor, FetchResult, SourceConnector


def test_serialize_source_health_includes_enabled_flag_and_run_status() -> None:
    source = Source(
        id=1,
        name="Test Source",
        type="rss",
        access_method="rss",
        enabled=False,
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
    assert health.latest_status == "skipped"
    assert health.latest_error == "disabled"


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


class NeverFetchConnector(SourceConnector):
    source_name = "Never Fetch"
    source_type = "test"

    def __init__(self) -> None:
        self.fetch_called = False

    async def fetch(self, cursor: FetchCursor) -> FetchResult:
        self.fetch_called = True
        raise AssertionError("Disabled sources should not be fetched.")
