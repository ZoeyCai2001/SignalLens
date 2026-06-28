from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes import search as search_routes
from app.db.models import Base, NormalizedItem
from app.schemas.preferences import RankingWeights
from app.schemas.search import SearchIntentResponse
from app.services.search import (
    infer_search_intent,
    normalize_filter_value,
    normalize_score,
    search_feed_items,
    start_of_day,
)


def test_normalize_filter_value_strips_empty_input() -> None:
    assert normalize_filter_value("  agent  ") == "agent"
    assert normalize_filter_value("   ") is None
    assert normalize_filter_value(None) is None


def test_normalize_score_clamps_optional_importance_filter() -> None:
    assert normalize_score(None) is None
    assert normalize_score(-0.5) == 0
    assert normalize_score(0.7) == 0.7
    assert normalize_score(1.5) == 1


def test_start_of_day_uses_utc_calendar_boundary() -> None:
    assert start_of_day(date(2026, 6, 26)) == datetime(2026, 6, 26, tzinfo=UTC)


def test_infer_search_intent_handles_recent_stock_query() -> None:
    intent = infer_search_intent(
        "Show me recent news about MRVL and AI data centers.",
        today=date(2026, 6, 26),
    )

    assert intent.ticker == "MRVL"
    assert intent.company == "Marvell"
    assert intent.category == "stock_company_event"
    assert intent.topic == "ai data center"
    assert intent.query == "AI data center"
    assert intent.date_from == date(2026, 6, 19)


def test_infer_search_intent_handles_product_discovery_query() -> None:
    intent = infer_search_intent(
        "What are the latest AI coding products?",
        today=date(2026, 6, 26),
    )

    assert intent.category == "product"
    assert intent.topic == "ai coding"
    assert intent.query == "AI coding"
    assert intent.date_from == date(2026, 6, 19)


def test_infer_search_intent_prefers_chinese_social_context() -> None:
    intent = infer_search_intent("Show Chinese social media posts about AI photo tools.")

    assert intent.category == "social_trend"
    assert intent.language == "zh"
    assert intent.query == "AI photo"


def test_infer_search_intent_handles_high_importance_semiconductor_query() -> None:
    intent = infer_search_intent(
        "Summarize the most important semiconductor AI news this week.",
        today=date(2026, 6, 26),
    )

    assert intent.category == "stock_company_event"
    assert intent.topic == "semiconductor"
    assert intent.query == "semiconductor AI"
    assert intent.min_importance_score == 0.7
    assert intent.date_from == date(2026, 6, 19)


def test_infer_search_intent_handles_saved_items_query() -> None:
    intent = infer_search_intent("Find saved discussion about agent harness.")

    assert intent.category == "technical_trend"
    assert intent.topic == "agent harness"
    assert intent.query == "agent harness"
    assert intent.saved_only is True


def test_search_intent_response_serializes_inferred_filters() -> None:
    intent = infer_search_intent(
        "Show me recent news about MRVL and AI data centers.",
        today=date(2026, 6, 26),
    )

    response = SearchIntentResponse.model_validate(intent)

    assert response.ticker == "MRVL"
    assert response.company == "Marvell"
    assert response.category == "stock_company_event"
    assert response.topic == "ai data center"
    assert response.query == "AI data center"
    assert response.date_from == date(2026, 6, 19)


def test_search_feed_items_applies_inferred_topic_filter() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_search_item(
                    1,
                    "Agent harness implementation notes",
                    "Agent harness discussion for coding agents.",
                    topics=["agent harness"],
                ),
                make_search_item(
                    2,
                    "Agent harness adjacent routing notes",
                    "Agent harness discussion that is really about routing.",
                    topics=["model routing"],
                ),
            ]
        )
        db.commit()

        results = search_feed_items(db, query="Find agent harness discussion")

    assert [item.title for item in results] == ["Agent harness implementation notes"]


def test_search_feed_items_filters_by_company() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_search_item(
                    1,
                    "Model release",
                    "Frontier model launch.",
                    topics=["model release"],
                    companies=["OpenAI"],
                ),
                make_search_item(
                    2,
                    "Benchmark update",
                    "Benchmark discussion.",
                    topics=["benchmark"],
                    companies=["Anthropic"],
                ),
            ]
        )
        db.commit()

        results = search_feed_items(db, company="OpenAI")

    assert [item.title for item in results] == ["Model release"]


def test_search_feed_items_matches_company_entities_in_query() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add(
            make_search_item(
                1,
                "Frontier model launch",
                "New reasoning model launch.",
                topics=["model release"],
                companies=["OpenAI"],
            )
        )
        db.commit()

        results = search_feed_items(db, query="OpenAI")

    assert [item.title for item in results] == ["Frontier model launch"]


@pytest.mark.anyio
async def test_search_route_passes_user_preferences(monkeypatch) -> None:
    preferences = make_preferences()

    monkeypatch.setattr(search_routes, "get_user_preferences", lambda db: preferences)

    def fake_search_feed_items(**kwargs):
        assert kwargs["query"] == "agent"
        assert kwargs["limit"] == 5
        assert kwargs["ranking_weights"] == preferences.ranking_weights
        assert kwargs["preferred_sources"] == preferences.preferred_sources
        assert kwargs["blocked_sources"] == preferences.blocked_sources
        return []

    monkeypatch.setattr(search_routes, "search_feed_items", fake_search_feed_items)

    result = await search_routes.search_items(db=object(), q="agent", limit=5)

    assert result == []


@pytest.mark.anyio
async def test_natural_language_search_route_passes_user_preferences(monkeypatch) -> None:
    preferences = make_preferences()

    monkeypatch.setattr(search_routes, "get_user_preferences", lambda db: preferences)

    def fake_search_feed_items(**kwargs):
        assert kwargs["query"] == "latest AI coding products"
        assert kwargs["limit"] == 8
        assert kwargs["ranking_weights"] == preferences.ranking_weights
        assert kwargs["preferred_sources"] == preferences.preferred_sources
        assert kwargs["blocked_sources"] == preferences.blocked_sources
        return []

    monkeypatch.setattr(search_routes, "search_feed_items", fake_search_feed_items)

    result = await search_routes.search_items_with_natural_language(
        payload=search_routes.NaturalLanguageSearchRequest(
            query="latest AI coding products",
            limit=8,
        ),
        db=object(),
    )

    assert result.items == []
    assert result.intent.category == "product"


def test_search_feed_items_excludes_blocked_sources() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_search_item(
                    1,
                    "Agent launch from blocked source",
                    "Agent launch details.",
                    topics=["agent"],
                    source_name="Noisy Blog",
                ),
                make_search_item(
                    2,
                    "Agent launch from trusted source",
                    "Agent launch details.",
                    topics=["agent"],
                    source_name="Trusted Blog",
                ),
            ]
        )
        db.commit()

        results = search_feed_items(db, query="agent", blocked_sources=["Noisy Blog"])

    assert [item.source_name for item in results] == ["Trusted Blog"]


def test_search_feed_items_ranks_preferred_sources_first() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_search_item(
                    1,
                    "Agent launch from regular source",
                    "Agent launch details.",
                    topics=["agent"],
                    source_name="Regular Blog",
                ),
                make_search_item(
                    2,
                    "Agent launch from preferred source",
                    "Agent launch details.",
                    topics=["agent"],
                    source_name="Trusted Blog",
                ),
            ]
        )
        db.commit()

        results = search_feed_items(
            db,
            query="agent",
            ranking_weights=RankingWeights(
                relevance=1,
                importance=0,
                novelty=0,
                source_quality=0,
                stock_impact=0,
                freshness=0,
            ),
            preferred_sources=["Trusted Blog"],
        )

    assert [item.source_name for item in results] == ["Trusted Blog", "Regular Blog"]


def make_preferences() -> SimpleNamespace:
    return SimpleNamespace(
        ranking_weights={"relevance": 1},
        preferred_sources=["Trusted Blog"],
        blocked_sources=["Noisy Blog"],
    )


def make_search_item(
    item_id: int,
    title: str,
    text: str,
    topics: list[str],
    companies: list[str] | None = None,
    source_name: str = "Test Source",
) -> NormalizedItem:
    return NormalizedItem(
        id=item_id,
        raw_item_id=item_id,
        title=title,
        url=f"https://example.com/{item_id}",
        source_name=source_name,
        author=None,
        language="en",
        published_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
        text=text,
        category="technical_trend",
        subcategory=None,
        tickers=[],
        companies=companies or [],
        products=[],
        topics=topics,
        sentiment="neutral",
        relevance_score=0.8,
        classification_confidence=0.8,
        importance_score=0.7,
        novelty_score=0.6,
        source_quality_score=0.7,
        stock_impact_score=0,
    )
