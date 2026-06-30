from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes import sources as source_routes
from app.db.models import Base, RawItem, Source, SourceRun
from app.schemas.sources import SourceCreate, SourceUpdate
from app.services import ingestion as ingestion_service
from app.services.ingestion import (
    IngestionResult,
    RegisteredSourceRunner,
    run_connector_ingestion,
    run_source_ingestion_by_id,
    source_quality_score_for_source,
)
from app.services.source_health import (
    create_source,
    delete_source,
    failure_handling_for_source,
    list_source_run_history,
    raw_content_policy_for_source,
    serialize_source_health,
    serialize_source_run_history_item,
    source_is_stale,
    source_needs_attention,
    source_next_run_due_at,
    summarize_recent_source_runs,
    update_source,
)
from app.sources.base import FetchCursor, FetchResult, SourceConnector


def test_serialize_source_health_includes_enabled_flag_and_run_status() -> None:
    last_success_at = datetime(2026, 6, 27, 8, 0, tzinfo=UTC)
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

    health = serialize_source_health(source, run, last_success_at=last_success_at)

    assert health.enabled is False
    assert health.base_url == "https://example.com/feed.xml"
    assert health.rate_limit == "60/hour"
    assert health.polling_interval == "hourly"
    assert health.priority == 20
    assert health.terms_notes == "Use RSS feed only."
    assert health.raw_content_policy == (
        "Store public feed metadata, title, excerpt, URL, and publication time."
    )
    assert health.failure_handling == (
        "Record failures, preserve the last success time, and retry at the next polling window."
    )
    assert health.latest_status == "skipped"
    assert health.latest_error == "disabled"
    assert health.last_success_at == last_success_at
    assert health.next_run_due_at == datetime(2026, 6, 27, 9, 0, tzinfo=UTC)
    assert health.is_stale is False
    assert health.failure_count == 0
    assert health.needs_attention is False
    assert health.recent_run_count == 0
    assert health.recent_success_rate is None
    assert health.recent_store_rate is None
    assert health.recent_items_fetched == 0
    assert health.recent_items_stored == 0


def test_serialize_source_health_marks_failed_sources_for_attention() -> None:
    source = Source(
        id=2,
        name="Failing Source",
        type="api",
        access_method="official_api",
        enabled=True,
    )
    run = SourceRun(
        source_id=2,
        status="failed",
        items_fetched=2,
        items_stored=0,
        error_message="rate limited",
    )

    health = serialize_source_health(source, run, failure_count=1)

    assert health.failure_count == 1
    assert health.needs_attention is True


def test_source_health_derives_compliance_policy_by_source_type() -> None:
    assert raw_content_policy_for_source(
        Source(name="Manual URL", type="manual", access_method="manual_submission")
    ) == "Store the submitted URL, title, excerpt, and optional user-provided text."
    assert raw_content_policy_for_source(
        Source(name="Chinese RSS", type="social_keyword", access_method="rss")
    ) == "Store public RSS/Atom metadata and snippets only; avoid login-protected content."
    assert raw_content_policy_for_source(
        Source(name="Product Hunt AI", type="product_topic", access_method="official_graphql_api")
    ) == "Store Product Hunt launch metadata returned by the official GraphQL API."
    assert raw_content_policy_for_source(
        Source(name="Repo", type="github_repository", access_method="official_api")
    ) == "Store public repository metadata and summaries; do not clone repository contents."


def test_source_health_derives_failure_handling_from_auth_and_polling() -> None:
    assert failure_handling_for_source(
        Source(name="API", type="api", access_method="official_api", auth_required=True)
    ) == "Record the failed run and latest error; update credentials or disable the source."
    assert failure_handling_for_source(
        Source(name="RSS", type="rss", access_method="rss", polling_interval="daily")
    ) == "Record failures, preserve the last success time, and retry at the next polling window."
    assert failure_handling_for_source(
        Source(name="Manual", type="manual", access_method="manual_submission")
    ) == "Record failures in run history; use a manual run after fixing source configuration."


def test_source_attention_uses_recent_failure_count_threshold() -> None:
    assert source_needs_attention("success", 1) is False
    assert source_needs_attention("success", 2) is True
    assert source_needs_attention("success", 0, is_stale=True) is True


def test_source_staleness_uses_polling_interval_and_last_success() -> None:
    last_success_at = datetime(2026, 6, 28, 6, 0, tzinfo=UTC)

    assert source_next_run_due_at(last_success_at, "6 hours") == datetime(
        2026,
        6,
        28,
        12,
        0,
        tzinfo=UTC,
    )
    assert source_is_stale(
        last_success_at,
        "6 hours",
        now=datetime(2026, 6, 28, 11, 59, tzinfo=UTC),
    ) is False
    assert source_is_stale(
        last_success_at,
        "6 hours",
        now=datetime(2026, 6, 28, 12, 0, tzinfo=UTC),
    ) is True
    assert source_is_stale(None, "6 hours", now=datetime(2026, 6, 28, 12, 0, tzinfo=UTC)) is False


def test_serialize_source_health_marks_enabled_overdue_sources_stale() -> None:
    source = Source(
        id=3,
        name="Overdue RSS",
        type="rss",
        access_method="rss",
        enabled=True,
        polling_interval="daily",
    )
    run = SourceRun(
        source_id=3,
        status="success",
        items_fetched=8,
        items_stored=6,
        started_at=datetime(2026, 6, 27, 8, 0, tzinfo=UTC),
        finished_at=datetime(2026, 6, 27, 8, 5, tzinfo=UTC),
    )

    health = serialize_source_health(
        source,
        run,
        last_success_at=datetime(2026, 6, 27, 8, 5, tzinfo=UTC),
    )

    assert health.next_run_due_at == datetime(2026, 6, 28, 8, 5, tzinfo=UTC)
    assert health.is_stale is True
    assert health.needs_attention is True


def test_summarize_recent_source_runs_reports_quality_metrics() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        source = Source(name="Quality RSS", type="blog", access_method="rss")
        db.add(source)
        db.flush()
        db.add_all(
            [
                SourceRun(
                    source_id=source.id,
                    status="success",
                    items_fetched=10,
                    items_stored=8,
                    started_at=datetime(2026, 6, 27, 8, 0, tzinfo=UTC),
                ),
                SourceRun(
                    source_id=source.id,
                    status="failed",
                    items_fetched=0,
                    items_stored=0,
                    started_at=datetime(2026, 6, 27, 9, 0, tzinfo=UTC),
                ),
                SourceRun(
                    source_id=source.id,
                    status="success",
                    items_fetched=20,
                    items_stored=5,
                    started_at=datetime(2026, 6, 27, 10, 0, tzinfo=UTC),
                ),
            ]
        )
        db.commit()

        quality = summarize_recent_source_runs(db, source.id)

    assert quality.run_count == 3
    assert quality.success_rate == pytest.approx(2 / 3)
    assert quality.items_fetched == 30
    assert quality.items_stored == 13
    assert quality.store_rate == pytest.approx(13 / 30)


def test_source_quality_falls_back_to_access_method_then_type() -> None:
    official_source = Source(
        id=10,
        name="New Official Source",
        type="community",
        access_method="official_api",
    )
    rss_source = Source(
        id=11,
        name="Custom Blog",
        type="blog",
        access_method="rss",
    )
    type_only_source = Source(
        id=12,
        name="Typed Custom Source",
        type="blog",
        access_method="unknown",
    )
    unknown_source = Source(
        id=13,
        name="Unknown",
        type="unknown",
        access_method="unknown",
    )

    assert source_quality_score_for_source(official_source) == 0.76
    assert source_quality_score_for_source(rss_source) == 0.65
    assert source_quality_score_for_source(type_only_source) == 0.66
    assert source_quality_score_for_source(unknown_source) == 0.65


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


def test_update_source_ignores_null_priority() -> None:
    source = Source(
        id=8,
        name="Configurable Source",
        type="api",
        access_method="api",
        enabled=True,
        priority=70,
    )
    db = FakeSourceDb(source)

    updated = update_source(
        db,
        source_id=8,
        payload=SourceUpdate(priority=None),
    )

    assert updated is source
    assert source.priority == 70
    assert db.commits == 1


def test_update_source_edits_identity_and_connector_configuration() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        source = Source(
            name="Old Repo Source",
            type="blog",
            access_method="rss",
            base_url="https://example.com/feed.xml",
            auth_required=False,
            priority=80,
        )
        db.add(source)
        db.commit()

        updated = update_source(
            db,
            source_id=source.id,
            payload=SourceUpdate(
                name="  LangChain Repo  ",
                type="github_repository",
                access_method="rss",
                base_url=" https://github.com/langchain-ai/langchain ",
                auth_required=True,
                priority=25,
            ),
        )

    assert updated is not None
    assert updated.name == "LangChain Repo"
    assert updated.type == "github_repository"
    assert updated.access_method == "official_api"
    assert updated.base_url == "https://github.com/langchain-ai/langchain"
    assert updated.auth_required is True
    assert updated.priority == 25


def test_update_source_rejects_duplicate_renames() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        first = Source(name="First Source", type="blog", access_method="rss")
        second = Source(name="Second Source", type="blog", access_method="rss")
        db.add_all([first, second])
        db.commit()

        with pytest.raises(ValueError):
            update_source(
                db,
                source_id=second.id,
                payload=SourceUpdate(name=" First Source "),
            )


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


def test_create_source_uses_official_api_for_github_repository() -> None:
    db = FakeCreateSourceDb()

    source = create_source(
        db,
        SourceCreate(
            name="LangChain Repo",
            type="github_repository",
            access_method="rss",
            base_url="https://github.com/langchain-ai/langchain",
        ),
    )

    assert source.type == "github_repository"
    assert source.access_method == "official_api"
    assert source.base_url == "https://github.com/langchain-ai/langchain"


def test_create_source_uses_product_hunt_api_for_product_topic() -> None:
    db = FakeCreateSourceDb()

    source = create_source(
        db,
        SourceCreate(
            name="Product Hunt AI Coding",
            type="product_topic",
            access_method="manual_watch",
            base_url="https://www.producthunt.com/topics/artificial-intelligence",
            terms_notes="Developer Tools, AI Coding",
        ),
    )

    assert source.type == "product_topic"
    assert source.access_method == "official_graphql_api"
    assert source.auth_required is True
    assert source.rate_limit == "Product Hunt API token required; keep topic polling conservative."
    assert source.polling_interval == "6 hours"
    assert source.terms_notes == "Developer Tools, AI Coding"


def test_create_source_uses_public_rss_for_social_keyword_with_feed() -> None:
    db = FakeCreateSourceDb()

    source = create_source(
        db,
        SourceCreate(
            name="Xiaohongshu AI Photo",
            type="social_keyword",
            access_method="manual_watch",
            base_url="https://example.com/social/rss.xml",
            terms_notes="AI写真, AI photo",
        ),
    )

    assert source.type == "social_keyword"
    assert source.access_method == "rss"
    assert source.auth_required is False
    assert source.rate_limit == "Public RSS/Atom metadata only; no login-protected social scraping."
    assert source.polling_interval == "6 hours"
    assert source.terms_notes == "AI写真, AI photo"


def test_product_hunt_topic_terms_strip_common_source_prefix() -> None:
    source = Source(
        id=3,
        name="Product Hunt AI Coding",
        type="product_topic",
        access_method="official_graphql_api",
    )

    assert ingestion_service.product_hunt_topic_terms_for_source(source) == [
        "AI Coding",
        "Product Hunt AI Coding",
    ]


def test_social_keyword_terms_strip_common_source_prefix() -> None:
    source = Source(
        id=4,
        name="Xiaohongshu AI Photo",
        type="social_keyword",
        access_method="rss",
    )

    assert ingestion_service.social_keyword_terms_for_source(source) == [
        "AI Photo",
        "Xiaohongshu AI Photo",
    ]


def test_create_source_rejects_duplicate_name() -> None:
    existing = Source(id=1, name="Existing", type="blog", access_method="rss")
    db = FakeCreateSourceDb(existing=existing)

    with pytest.raises(ValueError):
        create_source(db, SourceCreate(name="Existing"))


def test_delete_source_removes_source_without_history() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        source = Source(
            name="Unused Custom RSS",
            type="blog",
            access_method="rss",
            base_url="https://example.com/rss.xml",
        )
        db.add(source)
        db.commit()
        source_id = source.id

        deleted = delete_source(db, source_id)

        assert deleted is True
        assert db.get(Source, source_id) is None


def test_delete_source_preserves_sources_with_history() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        source = Source(name="Historical RSS", type="blog", access_method="rss")
        db.add(source)
        db.commit()
        source_id = source.id
        db.add(SourceRun(source_id=source_id, status="success", items_fetched=1, items_stored=0))
        db.commit()

        with pytest.raises(ValueError, match="disable the source instead"):
            delete_source(db, source_id)

        assert db.get(Source, source_id) is not None


def test_delete_source_preserves_sources_with_collected_items() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        source = Source(name="Collected RSS", type="blog", access_method="rss")
        db.add(source)
        db.commit()
        source_id = source.id
        db.add(
            RawItem(
                source_id=source_id,
                url="https://example.com/item",
                raw_title="Collected item",
                raw_metadata={},
                content_hash="collected-item-hash",
            )
        )
        db.commit()

        with pytest.raises(ValueError, match="disable the source instead"):
            delete_source(db, source_id)

        assert db.get(Source, source_id) is not None


@pytest.mark.anyio
async def test_list_sources_route_uses_source_health_listing(monkeypatch) -> None:
    expected = []

    monkeypatch.setattr(source_routes, "list_source_health_items", lambda db: expected)

    assert await source_routes.list_sources(db=object()) is expected


@pytest.mark.anyio
async def test_delete_source_route_maps_service_errors(monkeypatch) -> None:
    monkeypatch.setattr(source_routes, "delete_source", lambda *_args, **_kwargs: False)

    with pytest.raises(HTTPException) as missing:
        await source_routes.delete_followed_source(source_id=99, db=object())

    assert missing.value.status_code == 404

    def blocked_delete(*_args, **_kwargs):
        raise ValueError("disable the source instead")

    monkeypatch.setattr(source_routes, "delete_source", blocked_delete)

    with pytest.raises(HTTPException) as blocked:
        await source_routes.delete_followed_source(source_id=1, db=object())

    assert blocked.value.status_code == 400
    assert blocked.value.detail == "disable the source instead"


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


def test_list_source_run_history_filters_by_status() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        source = Source(name="arXiv", type="research", access_method="api", enabled=True)
        other_source = Source(name="Hacker News", type="community", access_method="api", enabled=True)
        db.add_all([source, other_source])
        db.flush()
        db.add_all(
            [
                SourceRun(
                    source_id=source.id,
                    status="success",
                    items_fetched=5,
                    items_stored=5,
                    started_at=datetime(2026, 6, 27, 8, 0, tzinfo=UTC),
                ),
                SourceRun(
                    source_id=source.id,
                    status="failed",
                    items_fetched=0,
                    items_stored=0,
                    error_message="rate limited",
                    started_at=datetime(2026, 6, 27, 9, 0, tzinfo=UTC),
                ),
                SourceRun(
                    source_id=other_source.id,
                    status="failed",
                    items_fetched=0,
                    items_stored=0,
                    error_message="timeout",
                    started_at=datetime(2026, 6, 27, 10, 0, tzinfo=UTC),
                ),
            ]
        )
        db.commit()

        failed_runs = list_source_run_history(db=db, status="failed")
        source_failed_runs = list_source_run_history(
            db=db,
            status="failed",
            source_id=source.id,
        )

    assert [run.source_name for run in failed_runs] == ["Hacker News", "arXiv"]
    assert [run.status for run in source_failed_runs] == ["failed"]
    assert source_failed_runs[0].source_name == "arXiv"
    assert source_failed_runs[0].error_message == "rate limited"


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


@pytest.mark.anyio
async def test_run_source_ingestion_by_id_runs_custom_github_repository(monkeypatch) -> None:
    source = Source(
        id=6,
        name="LangChain Repo",
        type="github_repository",
        access_method="official_api",
        base_url="https://github.com/langchain-ai/langchain",
        enabled=True,
    )
    db = FakeSourceDb(source)
    calls = []

    async def fake_run_connector_ingestion(db, connector, source):
        calls.append((db, connector, source))
        return IngestionResult(
            source_name=source.name,
            status="success",
            items_fetched=1,
            items_stored=1,
        )

    monkeypatch.setattr(
        ingestion_service,
        "run_connector_ingestion",
        fake_run_connector_ingestion,
    )

    result = await ingestion_service.run_source_ingestion_by_id(
        db=db,
        source_id=6,
        runners_by_name={},
    )

    assert result.source_name == "LangChain Repo"
    assert result.items_fetched == 1
    assert calls[0][1].source_name == "LangChain Repo"
    assert calls[0][1].repositories == ["langchain-ai/langchain"]


@pytest.mark.anyio
async def test_run_source_ingestion_by_id_runs_custom_product_hunt_topic(monkeypatch) -> None:
    source = Source(
        id=7,
        name="Product Hunt AI Coding",
        type="product_topic",
        access_method="official_graphql_api",
        base_url="https://www.producthunt.com/topics/artificial-intelligence",
        terms_notes="Developer Tools, AI Coding",
        enabled=True,
    )
    db = FakeSourceDb(source)
    calls = []

    async def fake_run_connector_ingestion(db, connector, source):
        calls.append((db, connector, source))
        return IngestionResult(
            source_name=source.name,
            status="success",
            items_fetched=2,
            items_stored=2,
        )

    monkeypatch.setattr(
        ingestion_service,
        "get_settings",
        lambda: SimpleNamespace(product_hunt_api_token="ph-token"),
    )
    monkeypatch.setattr(
        ingestion_service,
        "run_connector_ingestion",
        fake_run_connector_ingestion,
    )

    result = await ingestion_service.run_source_ingestion_by_id(
        db=db,
        source_id=7,
        limit=9,
        runners_by_name={},
    )

    assert result.source_name == "Product Hunt AI Coding"
    assert result.items_fetched == 2
    connector = calls[0][1]
    assert connector.source_name == "Product Hunt AI Coding"
    assert connector.limit == 9
    assert connector.api_token == "ph-token"
    assert connector.topic_terms == [
        "Developer Tools",
        "AI Coding",
        "artificial intelligence",
        "Product Hunt AI Coding",
    ]


@pytest.mark.anyio
async def test_run_source_ingestion_by_id_runs_social_keyword_rss_source(monkeypatch) -> None:
    source = Source(
        id=8,
        name="Xiaohongshu AI Photo",
        type="social_keyword",
        access_method="rss",
        base_url="AI Photo Feed|https://example.com/social/rss.xml",
        terms_notes="AI写真, AI photo",
        enabled=True,
    )
    db = FakeSourceDb(source)
    calls = []

    async def fake_run_connector_ingestion(db, connector, source):
        calls.append((db, connector, source))
        return IngestionResult(
            source_name=source.name,
            status="success",
            items_fetched=4,
            items_stored=2,
        )

    monkeypatch.setattr(
        ingestion_service,
        "run_connector_ingestion",
        fake_run_connector_ingestion,
    )

    result = await ingestion_service.run_source_ingestion_by_id(
        db=db,
        source_id=8,
        limit=12,
        runners_by_name={},
    )

    assert result.source_name == "Xiaohongshu AI Photo"
    assert result.items_stored == 2
    connector = calls[0][1]
    assert connector.source_name == "Xiaohongshu AI Photo"
    assert connector.source_type == "social_keyword"
    assert connector.limit == 12
    assert connector.feeds[0].name == "AI Photo Feed"
    assert connector.feeds[0].url == "https://example.com/social/rss.xml"
    assert connector.include_terms == [
        "AI写真",
        "AI photo",
        "Xiaohongshu AI Photo",
    ]


@pytest.mark.anyio
async def test_run_source_ingestion_by_id_skips_social_keyword_without_feed() -> None:
    source = Source(
        id=9,
        name="Xiaohongshu AI Photo",
        type="social_keyword",
        access_method="manual_watch",
        enabled=True,
    )
    db = FakeSourceDb(source)

    result = await ingestion_service.run_source_ingestion_by_id(
        db=db,
        source_id=9,
        runners_by_name={},
    )

    assert result.status == "skipped"
    assert (
        result.error_message
        == "Social keyword source needs at least one public RSS/Atom feed URL."
    )


@pytest.mark.anyio
async def test_run_source_ingestion_by_id_skips_product_topic_without_token(monkeypatch) -> None:
    source = Source(
        id=8,
        name="Product Hunt AI Coding",
        type="product_topic",
        access_method="official_graphql_api",
        terms_notes="AI Coding",
        enabled=True,
    )
    db = FakeSourceDb(source)

    monkeypatch.setattr(
        ingestion_service,
        "get_settings",
        lambda: SimpleNamespace(product_hunt_api_token=None),
    )

    result = await ingestion_service.run_source_ingestion_by_id(
        db=db,
        source_id=8,
        runners_by_name={},
    )

    assert result.status == "skipped"
    assert result.error_message == "PRODUCT_HUNT_API_TOKEN is not configured."
    assert db.commits == 1
    assert db.added[0].status == "skipped"


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
