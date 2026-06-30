from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, NormalizedItem, RawItem, Source
from app.services.ingestion import (
    canonical_ingestion_url,
    compute_content_hash,
    store_raw_items,
)
from app.sources.base import RawItemInput


def test_canonical_ingestion_url_removes_tracking_noise() -> None:
    assert (
        canonical_ingestion_url(
            "https://Example.com/path/?utm_source=newsletter&b=2&a=1#section"
        )
        == "https://example.com/path?a=1&b=2"
    )


def test_compute_content_hash_ignores_source_ids_and_tracking_noise() -> None:
    first = RawItemInput(
        source_name="Selected RSS Feeds",
        external_id="feed-entry-1",
        url="https://example.com/agent-workflow?utm_source=newsletter",
        raw_title="OpenAI releases AI agent workflow",
        raw_text="Developers can use this AI agent workflow for coding tasks.",
    )
    second = RawItemInput(
        source_name="Another Feed",
        external_id="feed-entry-2",
        url="https://example.com/agent-workflow?utm_medium=social",
        raw_title="OpenAI releases AI agent workflow",
        raw_text="Developers can use this AI agent workflow for coding tasks.",
    )

    assert compute_content_hash(first) == compute_content_hash(second)


def test_store_raw_items_deduplicates_tracking_url_variants() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        source = Source(
            name="Selected RSS Feeds",
            type="blog",
            access_method="rss",
            priority=50,
        )
        db.add(source)
        db.commit()
        db.refresh(source)

        stored_count = store_raw_items(
            db,
            source=source,
            items=[
                RawItemInput(
                    source_name="Selected RSS Feeds",
                    external_id=None,
                    url="https://example.com/agent-workflow?utm_source=newsletter",
                    raw_title="OpenAI releases AI agent workflow",
                    raw_text="Developers can use this AI agent workflow for coding tasks.",
                ),
                RawItemInput(
                    source_name="Selected RSS Feeds",
                    external_id=None,
                    url="https://example.com/agent-workflow?utm_medium=social",
                    raw_title="OpenAI releases AI agent workflow",
                    raw_text="Developers can use this AI agent workflow for coding tasks.",
                ),
            ],
        )

        assert stored_count == 1
        assert db.query(RawItem).count() == 1
        assert db.query(NormalizedItem).count() == 1


def test_store_raw_items_deduplicates_same_canonical_url_with_changed_text() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        source = Source(
            name="Selected RSS Feeds",
            type="blog",
            access_method="rss",
            priority=50,
        )
        db.add(source)
        db.commit()
        db.refresh(source)

        stored_count = store_raw_items(
            db,
            source=source,
            items=[
                RawItemInput(
                    source_name="Selected RSS Feeds",
                    external_id=None,
                    url="https://example.com/agent-workflow?utm_source=newsletter",
                    raw_title="OpenAI releases AI agent workflow",
                    raw_text="Developers can use this AI agent workflow for coding tasks.",
                ),
                RawItemInput(
                    source_name="Selected RSS Feeds",
                    external_id=None,
                    url="https://example.com/agent-workflow?utm_medium=social",
                    raw_title="OpenAI updates AI agent workflow",
                    raw_text="The updated excerpt adds more detail about agent coding workflows.",
                ),
            ],
        )

        assert stored_count == 1
        assert db.query(RawItem).count() == 1
        assert db.query(NormalizedItem).count() == 1
