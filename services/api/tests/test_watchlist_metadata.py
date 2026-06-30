from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, TopicWatchlistItem
from app.schemas.watchlist import TopicWatchlistItemUpdate
from app.services.watchlist import update_topic_watchlist_item


def test_update_topic_watchlist_item_edits_metadata_and_ignores_blank_required_fields() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add(
            TopicWatchlistItem(
                user_id="local",
                topic="ai-coding-agents",
                label="AI coding agents",
                category="technical_trend",
                priority="High",
                include_in_digest=True,
                related_terms=["coding agent"],
                notes="Original note.",
            )
        )
        db.commit()

        updated = update_topic_watchlist_item(
            db,
            "ai-coding-agents",
            TopicWatchlistItemUpdate(
                label="  Agentic coding  ",
                category="  research  ",
                related_terms=[" agent harness ", "agent harness", "IDE agent"],
                notes="  Track practical workflows.  ",
            ),
        )
        assert updated is not None
        assert updated.label == "Agentic coding"
        assert updated.category == "research"
        assert updated.related_terms == ["agent harness", "IDE agent"]
        assert updated.notes == "Track practical workflows."

        blank_update = update_topic_watchlist_item(
            db,
            "ai-coding-agents",
            TopicWatchlistItemUpdate(label="   ", category="   ", notes="   "),
        )

    assert blank_update is not None
    assert blank_update.label == "Agentic coding"
    assert blank_update.category == "research"
    assert blank_update.notes is None
