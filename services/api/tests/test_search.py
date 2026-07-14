from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes import search as search_routes
from app.db.models import Base, NormalizedItem, RawItem, UserItemAction
from app.schemas.preferences import RankingWeights
from app.schemas.search import SearchIntentResponse
from app.services.feed_actions import serialize_feed_item
from app.services.search import (
    build_search_summary,
    infer_search_intent,
    latest_stored_item_date,
    normalize_filter_value,
    normalize_read_status,
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


def test_normalize_read_status_accepts_read_and_unread() -> None:
    assert normalize_read_status(" unread ") == "unread"
    assert normalize_read_status("read") == "read"
    assert normalize_read_status("ignored") is None
    assert normalize_read_status(None) is None


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


def test_infer_search_intent_handles_source_query() -> None:
    intent = infer_search_intent(
        "Find recent arXiv papers about agent harness.",
        today=date(2026, 6, 26),
    )

    assert intent.source == "arXiv"
    assert intent.category == "research"
    assert intent.topic == "agent harness"
    assert intent.query == "agent harness"
    assert intent.date_from == date(2026, 6, 19)


def test_infer_search_intent_strips_source_terms_from_keyword_query() -> None:
    intent = infer_search_intent("Show GitHub MCP repos.")

    assert intent.source == "GitHub"
    assert intent.query == "MCP"


def test_infer_search_intent_handles_reddit_source_query() -> None:
    intent = infer_search_intent("Show Reddit posts about local LLM coding agents.")

    assert intent.source == "Reddit"
    assert intent.topic == "coding agent"
    assert intent.query == "coding agent"


def test_infer_search_intent_handles_product_discovery_query() -> None:
    intent = infer_search_intent(
        "What are the latest AI coding products?",
        today=date(2026, 6, 26),
    )

    assert intent.category == "product"
    assert intent.subcategory == "product_coding"
    assert intent.topic == "ai coding"
    assert intent.query == "AI coding"
    assert intent.date_from == date(2026, 6, 19)


def test_infer_search_intent_can_anchor_recent_queries_to_stored_data() -> None:
    intent = infer_search_intent(
        "What are the latest AI coding products?",
        today=date(2026, 7, 15),
        recent_anchor_date=date(2026, 6, 26),
    )

    assert intent.date_from == date(2026, 6, 19)


def test_latest_stored_item_date_uses_created_at_when_publish_date_is_missing() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        item = make_search_item(
            1,
            "Manual agent note",
            "Agent note.",
            topics=["agent"],
        )
        item.published_at = None
        item.created_at = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
        db.add(item)
        db.commit()

        assert latest_stored_item_date(db) == date(2026, 6, 25)


def test_infer_search_intent_prefers_chinese_social_context() -> None:
    intent = infer_search_intent("Show Chinese social media posts about AI photo tools.")

    assert intent.category == "social_trend"
    assert intent.language == "zh"
    assert intent.query == "AI photo"


def test_infer_search_intent_handles_ai_relevance_review_query() -> None:
    intent = infer_search_intent("Show not AI-related items that need relevance review.")

    assert intent.ai_related is False
    assert intent.query is None


def test_infer_search_intent_handles_explicit_ai_related_query() -> None:
    intent = infer_search_intent("Show AI-related stock news.")

    assert intent.ai_related is True
    assert intent.category == "stock_company_event"


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


def test_infer_search_intent_handles_popular_social_signal_query() -> None:
    intent = infer_search_intent("Show viral AI photo tools with high engagement.")

    assert intent.category == "product"
    assert intent.query == "AI photo"
    assert intent.min_social_signal_score == 0.65


@pytest.mark.parametrize(
    ("query", "expected_category"),
    [
        ("Show AI policy and export control updates.", "policy_regulation"),
        ("Find AI startup funding and M&A news.", "funding_mna"),
        ("Summarize agent benchmark evaluation results.", "benchmark_evaluation"),
        ("Show open-source model release signals.", "open_source_release"),
        ("Find AI tutorial and opinion essays.", "tutorial_opinion"),
    ],
)
def test_infer_search_intent_handles_prd_secondary_categories(
    query: str,
    expected_category: str,
) -> None:
    intent = infer_search_intent(query)

    assert intent.category == expected_category


def test_infer_search_intent_handles_saved_items_query() -> None:
    intent = infer_search_intent("Find saved discussion about agent harness.")

    assert intent.category == "technical_trend"
    assert intent.topic == "agent harness"
    assert intent.query == "agent harness"
    assert intent.saved_only is True


def test_infer_search_intent_handles_manual_tag_query() -> None:
    intent = infer_search_intent("Find saved items tag:agent")

    assert intent.manual_tag == "agent"
    assert intent.query is None
    assert intent.saved_only is True


def test_infer_search_intent_handles_unread_saved_query() -> None:
    intent = infer_search_intent("Show saved unread items about agent harness.")

    assert intent.topic == "agent harness"
    assert intent.query == "agent harness"
    assert intent.saved_only is True
    assert intent.read_status == "unread"


def test_infer_search_intent_treats_read_later_as_saved_unread() -> None:
    intent = infer_search_intent("Show my read later agent harness items.")

    assert intent.topic == "agent harness"
    assert intent.query == "agent harness"
    assert intent.saved_only is True
    assert intent.read_status == "unread"


def test_infer_search_intent_handles_today_and_yesterday_dates() -> None:
    today_intent = infer_search_intent(
        "Show today's AI coding updates.",
        today=date(2026, 6, 26),
    )
    yesterday_intent = infer_search_intent(
        "Summarize yesterday's semiconductor AI news.",
        today=date(2026, 6, 26),
    )

    assert today_intent.date_from == date(2026, 6, 26)
    assert today_intent.date_to == date(2026, 6, 26)
    assert yesterday_intent.date_from == date(2026, 6, 25)
    assert yesterday_intent.date_to == date(2026, 6, 25)


def test_infer_search_intent_handles_extended_relative_dates() -> None:
    anchor = date(2026, 6, 26)

    past_day = infer_search_intent(
        "Show AI infrastructure from the past 24 hours.",
        today=date(2026, 7, 15),
        recent_anchor_date=anchor,
    )
    past_weeks = infer_search_intent(
        "Show model routing signals from the last 2 weeks.",
        today=date(2026, 7, 15),
        recent_anchor_date=anchor,
    )
    past_month = infer_search_intent(
        "Find AI coding products from the past month.",
        today=date(2026, 7, 15),
        recent_anchor_date=anchor,
    )
    this_month = infer_search_intent(
        "Show AI research this month.",
        today=date(2026, 7, 15),
        recent_anchor_date=anchor,
    )

    assert past_day.date_from == date(2026, 6, 25)
    assert past_weeks.date_from == date(2026, 6, 12)
    assert past_month.date_from == date(2026, 5, 27)
    assert this_month.date_from == date(2026, 6, 1)


def test_search_intent_response_serializes_inferred_filters() -> None:
    intent = infer_search_intent(
        "Show me recent news about MRVL and AI data centers.",
        today=date(2026, 6, 26),
    )

    response = SearchIntentResponse.model_validate(intent)

    assert response.ticker == "MRVL"
    assert response.source is None
    assert response.company == "Marvell"
    assert response.category == "stock_company_event"
    assert response.subcategory is None
    assert response.topic == "ai data center"
    assert response.manual_tag is None
    assert response.query == "AI data center"
    assert response.date_from == date(2026, 6, 19)
    assert response.date_to is None
    assert response.min_social_signal_score is None
    assert response.read_status is None


def test_build_search_summary_handles_summary_style_query() -> None:
    intent = infer_search_intent(
        "Summarize the most important semiconductor AI news this week.",
        today=date(2026, 6, 26),
    )
    item = make_feed_result(
        1,
        "Micron HBM demand rises",
        source_name="Alpha Vantage News",
        topics=["semiconductor", "hbm"],
        tickers=["MU"],
        summary_short="Micron demand signal for AI memory.",
        importance_score=0.84,
    )

    summary = build_search_summary(
        "Summarize the most important semiconductor AI news this week.",
        intent,
        [item],
    )

    assert summary is not None
    assert "Found 1 matching SignalLens items for semiconductor." in summary
    assert "Micron HBM demand rises (Alpha Vantage News)" in summary
    assert "Micron demand signal for AI memory." in summary
    assert "Tickers: MU." in summary
    assert "Importance 84." in summary


def test_build_search_summary_stays_empty_for_plain_keyword_search() -> None:
    intent = infer_search_intent("agent harness")

    assert build_search_summary("agent harness", intent, []) is None


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


def test_search_feed_items_topic_filter_matches_product_facets() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        matching = make_search_item(
            1,
            "Chinese social product signal",
            "AI creator workflow.",
            topics=["ai"],
            category="social_trend",
        )
        matching.products = ["AI photo tool"]
        non_matching = make_search_item(
            2,
            "Generic agent signal",
            "Agent workflow.",
            topics=["agent"],
            category="technical_trend",
        )
        db.add_all([matching, non_matching])
        db.commit()

        results = search_feed_items(db, topic="AI photo")

    assert [item.title for item in results] == ["Chinese social product signal"]


def test_search_feed_items_applies_inferred_source_filter() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_search_item(
                    1,
                    "Agent harness paper",
                    "Agent harness research.",
                    topics=["agent harness"],
                    category="research",
                    source_name="arXiv",
                ),
                make_search_item(
                    2,
                    "Agent harness discussion",
                    "Agent harness discussion.",
                    topics=["agent harness"],
                    category="research",
                    source_name="Hacker News",
                ),
            ]
        )
        db.commit()

        results = search_feed_items(db, query="Find recent arXiv papers about agent harness")

    assert [item.title for item in results] == ["Agent harness paper"]


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


def test_search_feed_items_filters_by_product_subcategory() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_search_item(
                    1,
                    "AI coding assistant",
                    "Developer workflow tool.",
                    topics=["ai coding"],
                    category="product",
                    subcategory="product_coding",
                ),
                make_search_item(
                    2,
                    "AI image studio",
                    "Creator media tool.",
                    topics=["ai photo"],
                    category="product",
                    subcategory="product_media",
                ),
            ]
        )
        db.commit()

        explicit_results = search_feed_items(db, category="product", subcategory="product_coding")
        inferred_results = search_feed_items(db, query="latest AI coding products")

    assert [item.title for item in explicit_results] == ["AI coding assistant"]
    assert [item.title for item in inferred_results] == ["AI coding assistant"]


def test_search_feed_items_filters_by_prd_secondary_category() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_search_item(
                    1,
                    "AI policy update",
                    "Export control guidance for AI chips.",
                    topics=["policy"],
                    category="policy_regulation",
                ),
                make_search_item(
                    2,
                    "Agent product launch",
                    "A coding agent product update.",
                    topics=["agent"],
                    category="product",
                ),
            ]
        )
        db.commit()

        explicit_results = search_feed_items(db, category="policy_regulation")
        inferred_results = search_feed_items(db, query="Show AI export control policy updates")

    assert [item.title for item in explicit_results] == ["AI policy update"]
    assert [item.title for item in inferred_results] == ["AI policy update"]


def test_search_feed_items_filters_by_ai_relevance_state() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        related = make_search_item(
            1,
            "Low-score Marvell note",
            "Marvell AI infrastructure note.",
            topics=[],
            category="stock_company_event",
        )
        related.relevance_score = 0.2
        related.tickers = ["MRVL"]
        manual_review = make_search_item(
            2,
            "Unenriched manual link",
            "Generic saved URL.",
            topics=[],
            category="manual_submission",
        )
        manual_review.relevance_score = 0.2
        noise = make_search_item(
            3,
            "Unrelated office software update",
            "Office software maintenance release.",
            topics=[],
            category="noise_irrelevant",
        )
        db.add_all([related, manual_review, noise])
        db.commit()

        related_results = search_feed_items(db, ai_related=True)
        review_results = search_feed_items(db, ai_related=False)

    assert [item.title for item in related_results] == ["Low-score Marvell note"]
    assert {item.title for item in review_results} == {
        "Unenriched manual link",
        "Unrelated office software update",
    }


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


def test_search_feed_items_matches_personal_notes() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_search_item(1, "Agent launch", "Agent launch.", ["agent"]),
                make_search_item(2, "Benchmark update", "Benchmark update.", ["benchmark"]),
            ]
        )
        db.add(
            UserItemAction(
                user_id="local",
                item_id=2,
                personal_note="Review for weekend digest.",
                manual_tags=[],
            )
        )
        db.commit()

        results = search_feed_items(db, query="weekend digest")

    assert [item.title for item in results] == ["Benchmark update"]


def test_search_feed_items_filters_by_manual_tag() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_search_item(1, "Agent launch", "Agent launch.", ["agent"]),
                make_search_item(2, "Market impact note", "Market impact.", ["stocks"]),
            ]
        )
        db.add_all(
            [
                UserItemAction(
                    user_id="local",
                    item_id=1,
                    personal_note=None,
                    manual_tags=["Agent"],
                ),
                UserItemAction(
                    user_id="local",
                    item_id=2,
                    personal_note=None,
                    manual_tags=["Market Impact"],
                ),
            ]
        )
        db.commit()

        results = search_feed_items(db, manual_tag="agent")
        natural_language_results = search_feed_items(db, query="tag:agent")

    assert [item.title for item in results] == ["Agent launch"]
    assert [item.title for item in natural_language_results] == ["Agent launch"]


def test_search_feed_items_filters_by_read_status() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_search_item(1, "Read agent signal", "Agent launch.", ["agent"]),
                make_search_item(2, "Unread saved signal", "Agent launch.", ["agent"]),
                make_search_item(3, "Implicit unread signal", "Agent launch.", ["agent"]),
            ]
        )
        db.add_all(
            [
                UserItemAction(user_id="local", item_id=1, is_saved=True, is_read=True),
                UserItemAction(user_id="local", item_id=2, is_saved=True, is_read=False),
            ]
        )
        db.commit()

        read_results = search_feed_items(db, query="agent", read_status="read")
        unread_saved_results = search_feed_items(
            db,
            query="agent",
            saved_only=True,
            read_status="unread",
        )
        unread_results = search_feed_items(db, query="agent", read_status="unread")

    assert [item.title for item in read_results] == ["Read agent signal"]
    assert [item.title for item in unread_saved_results] == ["Unread saved signal"]
    assert {item.title for item in unread_results} == {
        "Unread saved signal",
        "Implicit unread signal",
    }


def test_search_feed_items_filters_by_module_before_limit() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_search_item(
                    1,
                    "High importance agent overview",
                    "Agent overview.",
                    ["agent"],
                    category="technical_trend",
                    importance_score=1.0,
                ),
                make_search_item(
                    2,
                    "Agent benchmark paper",
                    "Agent benchmark research.",
                    ["agent"],
                    category="research",
                    importance_score=0.9,
                ),
                make_search_item(
                    3,
                    "Agent evaluation paper",
                    "Agent evaluation research.",
                    ["agent"],
                    category="research",
                    importance_score=0.8,
                ),
            ]
        )
        db.commit()

        results = search_feed_items(db, query="agent", module="research", limit=2)

    assert [item.title for item in results] == [
        "Agent benchmark paper",
        "Agent evaluation paper",
    ]


@pytest.mark.anyio
async def test_search_route_passes_user_preferences(monkeypatch) -> None:
    preferences = make_preferences()

    monkeypatch.setattr(search_routes, "get_user_preferences", lambda db: preferences)

    def fake_search_feed_items(**kwargs):
        assert kwargs["query"] == "agent"
        assert kwargs["limit"] == 5
        assert kwargs["subcategory"] == "product_coding"
        assert kwargs["read_status"] == "unread"
        assert kwargs["ranking_weights"] == preferences.ranking_weights
        assert kwargs["preferred_sources"] == preferences.preferred_sources
        assert kwargs["blocked_sources"] == preferences.blocked_sources
        assert kwargs["language_preferences"] == preferences.language_preferences
        assert kwargs["module"] == "research"
        return []

    monkeypatch.setattr(search_routes, "search_feed_items", fake_search_feed_items)

    result = await search_routes.search_items(
        db=object(),
        q="agent",
        subcategory="product_coding",
        read_status="unread",
        module="research",
        limit=5,
    )

    assert result == []


@pytest.mark.anyio
async def test_natural_language_search_route_passes_user_preferences(monkeypatch) -> None:
    preferences = make_preferences()

    monkeypatch.setattr(search_routes, "get_user_preferences", lambda db: preferences)
    monkeypatch.setattr(search_routes, "latest_stored_item_date", lambda db: None)

    def fake_search_feed_items(**kwargs):
        assert kwargs["query"] == "summarize latest AI coding products"
        assert kwargs["ai_related"] is None
        assert kwargs["limit"] == 8
        assert kwargs["ranking_weights"] == preferences.ranking_weights
        assert kwargs["preferred_sources"] == preferences.preferred_sources
        assert kwargs["blocked_sources"] == preferences.blocked_sources
        assert kwargs["language_preferences"] == preferences.language_preferences
        assert kwargs["module"] == "products"
        return []

    monkeypatch.setattr(search_routes, "search_feed_items", fake_search_feed_items)

    result = await search_routes.search_items_with_natural_language(
        payload=search_routes.NaturalLanguageSearchRequest(
            query="summarize latest AI coding products",
            limit=8,
            module="products",
        ),
        db=object(),
    )

    assert result.items == []
    assert result.intent.category == "product"
    assert (
        result.summary
        == "No matching SignalLens items were found for this natural-language search."
    )


@pytest.mark.anyio
async def test_natural_language_search_route_passes_ai_relevance_intent(monkeypatch) -> None:
    preferences = make_preferences()

    monkeypatch.setattr(search_routes, "get_user_preferences", lambda db: preferences)
    monkeypatch.setattr(search_routes, "latest_stored_item_date", lambda db: None)

    def fake_search_feed_items(**kwargs):
        assert kwargs["ai_related"] is False
        return []

    monkeypatch.setattr(search_routes, "search_feed_items", fake_search_feed_items)

    result = await search_routes.search_items_with_natural_language(
        payload=search_routes.NaturalLanguageSearchRequest(
            query="Show not AI-related items that need relevance review.",
            limit=8,
        ),
        db=object(),
    )

    assert result.intent.ai_related is False


@pytest.mark.anyio
async def test_natural_language_search_route_returns_data_anchored_intent(
    monkeypatch,
) -> None:
    preferences = make_preferences()

    monkeypatch.setattr(search_routes, "get_user_preferences", lambda db: preferences)
    monkeypatch.setattr(
        search_routes,
        "latest_stored_item_date",
        lambda db: date(2026, 6, 26),
    )
    monkeypatch.setattr(search_routes, "search_feed_items", lambda **kwargs: [])

    result = await search_routes.search_items_with_natural_language(
        payload=search_routes.NaturalLanguageSearchRequest(
            query="summarize latest AI coding products",
            limit=8,
            module="products",
        ),
        db=object(),
    )

    assert result.intent.category == "product"
    assert result.intent.date_from == date(2026, 6, 19)
    assert result.intent.date_to is None


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


def test_search_feed_items_filters_by_language_preferences() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_search_item(
                    1,
                    "English agent signal",
                    "Agent launch.",
                    ["agent"],
                    language="en",
                ),
                make_search_item(
                    2,
                    "Chinese agent signal",
                    "Agent launch.",
                    ["agent"],
                    language="zh",
                ),
            ]
        )
        db.commit()

        results = search_feed_items(db, query="agent", language_preferences=["zh"])

    assert [item.title for item in results] == ["Chinese agent signal"]


def test_search_feed_items_filters_by_inferred_social_signal() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    popular = make_search_item(
        1,
        "Viral AI photo workflow",
        "AI photo workflow launch.",
        ["AI photo"],
        source_name="Xiaohongshu Manual Watch",
        category="product",
        subcategory="product_media",
    )
    popular.raw_item = RawItem(
        id=1,
        source_id=1,
        url=popular.url,
        raw_title=popular.title,
        raw_metadata={
            "likes": 1600,
            "comments_count": 280,
            "collects": 600,
            "reposts": 80,
            "views": 90000,
        },
        content_hash="popular",
    )
    quiet = make_search_item(
        2,
        "Quiet AI photo workflow",
        "AI photo workflow launch.",
        ["AI photo"],
        source_name="Xiaohongshu Manual Watch",
        category="product",
        subcategory="product_media",
    )
    quiet.raw_item = RawItem(
        id=2,
        source_id=1,
        url=quiet.url,
        raw_title=quiet.title,
        raw_metadata={"likes": 12, "comments_count": 1, "views": 200},
        content_hash="quiet",
    )

    with session_factory() as db:
        db.add_all([popular, quiet])
        db.commit()

        results = search_feed_items(db, query="Show viral AI photo tools with high engagement")

    assert [item.title for item in results] == ["Viral AI photo workflow"]
    assert results[0].social_signal_score >= 0.65


def test_search_feed_items_filters_by_explicit_social_signal() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    popular = make_search_item(
        1,
        "Popular AI workflow",
        "AI workflow launch.",
        ["agent"],
        source_name="Product Hunt",
        category="product",
    )
    popular.raw_item = RawItem(
        id=1,
        source_id=1,
        url=popular.url,
        raw_title=popular.title,
        raw_metadata={"votes_count": 900, "comments_count": 130},
        content_hash="popular-explicit",
    )
    quiet = make_search_item(
        2,
        "Quiet AI workflow",
        "AI workflow launch.",
        ["agent"],
        source_name="Product Hunt",
        category="product",
    )
    quiet.raw_item = RawItem(
        id=2,
        source_id=1,
        url=quiet.url,
        raw_title=quiet.title,
        raw_metadata={"votes_count": 20, "comments_count": 1},
        content_hash="quiet-explicit",
    )

    with session_factory() as db:
        db.add_all([popular, quiet])
        db.commit()

        results = search_feed_items(
            db,
            query="AI workflow",
            min_social_signal_score=0.65,
        )

    assert [item.title for item in results] == ["Popular AI workflow"]


def test_search_feed_items_applies_inferred_yesterday_date_range() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    today = datetime.now(UTC).date()
    yesterday = today - timedelta(days=1)

    with session_factory() as db:
        db.add_all(
            [
                make_search_item(
                    1,
                    "Yesterday agent signal",
                    "Agent launch.",
                    ["agent"],
                    published_at=datetime.combine(yesterday, datetime.min.time(), tzinfo=UTC),
                ),
                make_search_item(
                    2,
                    "Today agent signal",
                    "Agent launch.",
                    ["agent"],
                    published_at=datetime.combine(today, datetime.min.time(), tzinfo=UTC),
                ),
            ]
        )
        db.commit()

        results = search_feed_items(db, query="yesterday agent")

    assert [item.title for item in results] == ["Yesterday agent signal"]


def test_search_feed_items_applies_inferred_rolling_date_range_from_stored_data() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    anchor = date(2026, 6, 26)

    with session_factory() as db:
        db.add_all(
            [
                make_search_item(
                    1,
                    "Fresh coding product",
                    "AI coding product launch.",
                    ["ai coding"],
                    category="product",
                    subcategory="product_coding",
                    published_at=datetime.combine(anchor, datetime.min.time(), tzinfo=UTC),
                ),
                make_search_item(
                    2,
                    "Older coding product",
                    "AI coding product launch.",
                    ["ai coding"],
                    category="product",
                    subcategory="product_coding",
                    published_at=datetime.combine(
                        anchor - timedelta(days=45),
                        datetime.min.time(),
                        tzinfo=UTC,
                    ),
                ),
            ]
        )
        db.commit()

        results = search_feed_items(db, query="AI coding products from the past month")

    assert [item.title for item in results] == ["Fresh coding product"]


def test_search_feed_items_explicit_language_overrides_preferences() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_search_item(
                    1,
                    "English agent signal",
                    "Agent launch.",
                    ["agent"],
                    language="en",
                ),
                make_search_item(
                    2,
                    "Chinese agent signal",
                    "Agent launch.",
                    ["agent"],
                    language="zh",
                ),
            ]
        )
        db.commit()

        results = search_feed_items(
            db,
            query="agent",
            language="en",
            language_preferences=["zh"],
        )

    assert [item.title for item in results] == ["English agent signal"]


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
        language_preferences=["en"],
    )


def make_feed_result(
    item_id: int,
    title: str,
    source_name: str = "Test Source",
    topics: list[str] | None = None,
    tickers: list[str] | None = None,
    summary_short: str | None = None,
    importance_score: float = 0.7,
):
    item = make_search_item(
        item_id,
        title,
        title,
        topics=topics or [],
        source_name=source_name,
        importance_score=importance_score,
    )
    item.tickers = tickers or []
    item.summary_short = summary_short
    return serialize_feed_item(item)


def make_search_item(
    item_id: int,
    title: str,
    text: str,
    topics: list[str],
    companies: list[str] | None = None,
    source_name: str = "Test Source",
    language: str = "en",
    category: str = "technical_trend",
    subcategory: str | None = None,
    importance_score: float = 0.7,
    published_at: datetime | None = None,
) -> NormalizedItem:
    return NormalizedItem(
        id=item_id,
        raw_item_id=item_id,
        title=title,
        url=f"https://example.com/{item_id}",
        source_name=source_name,
        author=None,
        language=language,
        published_at=published_at or datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
        text=text,
        category=category,
        subcategory=subcategory,
        tickers=[],
        companies=companies or [],
        products=[],
        topics=topics,
        sentiment="neutral",
        relevance_score=0.8,
        classification_confidence=0.8,
        importance_score=importance_score,
        novelty_score=0.6,
        source_quality_score=0.7,
        stock_impact_score=0,
    )
