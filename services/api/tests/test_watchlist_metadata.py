from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, CompanyWatchlistItem, ProductWatchlistItem, TopicWatchlistItem
from app.schemas.watchlist import (
    CompanyWatchlistItemUpdate,
    ProductWatchlistItemUpdate,
    TopicWatchlistItemUpdate,
)
from app.services.watchlist import (
    update_company_watchlist_item,
    update_product_watchlist_item,
    update_topic_watchlist_item,
)


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


def test_update_product_watchlist_item_edits_metadata_and_ignores_blank_label() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add(
            ProductWatchlistItem(
                user_id="local",
                category="ai-coding-tools",
                label="AI coding tools",
                priority="High",
                include_in_digest=True,
                related_terms=["coding agent"],
                notes="Original product note.",
            )
        )
        db.commit()

        updated = update_product_watchlist_item(
            db,
            "ai-coding-tools",
            ProductWatchlistItemUpdate(
                label="  Agent IDEs  ",
                related_terms=[" IDE agent ", "IDE agent", "coding workflow"],
                notes="  Track coding tool launches.  ",
            ),
        )
        assert updated is not None
        assert updated.label == "Agent IDEs"
        assert updated.related_terms == ["IDE agent", "coding workflow"]
        assert updated.notes == "Track coding tool launches."

        blank_update = update_product_watchlist_item(
            db,
            "ai-coding-tools",
            ProductWatchlistItemUpdate(label="   ", notes="   "),
        )

    assert blank_update is not None
    assert blank_update.label == "Agent IDEs"
    assert blank_update.notes is None


def test_update_company_watchlist_item_edits_metadata_and_ignores_blank_required_fields() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add(
            CompanyWatchlistItem(
                user_id="local",
                company_key="anthropic",
                company_name="Anthropic",
                ticker="ANTH",
                category="ai_lab",
                priority="High",
                include_in_digest=True,
                related_terms=["claude"],
                notes="Original company note.",
            )
        )
        db.commit()

        updated = update_company_watchlist_item(
            db,
            "anthropic",
            CompanyWatchlistItemUpdate(
                company_name="  Anthropic PBC  ",
                ticker="  ANTH  ",
                category="  ai_platform  ",
                related_terms=[" Claude ", "Claude", "constitutional AI"],
                notes="  Track Claude launches.  ",
            ),
        )
        assert updated is not None
        assert updated.company_name == "Anthropic PBC"
        assert updated.ticker == "ANTH"
        assert updated.category == "ai_platform"
        assert updated.related_terms == ["Claude", "constitutional AI"]
        assert updated.notes == "Track Claude launches."

        blank_update = update_company_watchlist_item(
            db,
            "anthropic",
            CompanyWatchlistItemUpdate(
                company_name="   ",
                ticker="   ",
                category="   ",
                priority="   ",
                notes="   ",
            ),
        )

    assert blank_update is not None
    assert blank_update.company_name == "Anthropic PBC"
    assert blank_update.ticker is None
    assert blank_update.category == "ai_platform"
    assert blank_update.priority == "High"
    assert blank_update.notes is None
