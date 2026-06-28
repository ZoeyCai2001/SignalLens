from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, NormalizedItem, UserItemAction
from app.schemas.feed import FeedItem
from app.schemas.preferences import RankingWeights
from app.services.feed_actions import (
    FeedInterestProfile,
    build_feed_interest_profile,
    build_score_explanation,
    feed_interest_bonus,
    freshness_score,
    normalize_source_names,
    rank_feed_items,
    serialize_feed_item,
    serialize_feed_item_detail,
    weighted_feed_score,
)


def test_serialize_feed_item_includes_user_action_flags() -> None:
    item = NormalizedItem(
        id=1,
        raw_item_id=1,
        title="AI agent item",
        url="https://example.com",
        source_name="Manual Submission",
        language="en",
        category="manual_submission",
        tickers=[],
        companies=[],
        products=[],
        topics=["agent"],
        sentiment="neutral",
        relevance_score=0.5,
        importance_score=0.4,
        novelty_score=1.0,
        source_quality_score=0.6,
        stock_impact_score=0,
    )
    action = UserItemAction(
        item_id=1,
        user_id="local",
        is_saved=True,
        is_hidden=False,
        is_important=True,
    )

    serialized = serialize_feed_item(item, action)

    assert serialized.is_saved is True
    assert serialized.is_hidden is False
    assert serialized.is_important is True


def test_serialize_feed_item_detail_includes_text_actions_and_explanation() -> None:
    item = NormalizedItem(
        id=1,
        raw_item_id=1,
        title="Micron HBM demand",
        url="https://example.com",
        source_name="Alpha Vantage News",
        author=None,
        language="en",
        published_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
        text="Source article text.",
        category="stock_company_event",
        tickers=["MU"],
        companies=["Micron"],
        products=[],
        topics=["HBM"],
        sentiment="positive",
        relevance_score=0.8,
        importance_score=0.82,
        novelty_score=0.7,
        source_quality_score=0.82,
        stock_impact_score=0.9,
    )
    action = UserItemAction(
        item_id=1,
        user_id="local",
        is_saved=True,
        is_hidden=False,
        is_important=True,
    )

    detail = serialize_feed_item_detail(item, action)

    assert detail.text == "Source article text."
    assert detail.action_state == {
        "is_saved": True,
        "is_hidden": False,
        "is_important": True,
    }
    assert "matched tickers MU" in detail.score_explanation
    assert "high source credibility" in detail.score_explanation
    assert "high stock-impact score" in detail.score_explanation


def test_build_score_explanation_flags_lower_confidence_and_source_credibility() -> None:
    item = make_feed_item(1, "Manual rumor", relevance_score=0.6, importance_score=0.5)
    item.category = "manual_submission"
    item.source_quality_score = 0.55
    item.classification_confidence = 0.45

    explanation = build_score_explanation(item)

    assert "lower source credibility; review the original source" in explanation
    assert "lower classifier confidence" in explanation


def test_build_score_explanation_has_default_reason() -> None:
    item = make_feed_item(1, "Fallback")
    item.category = ""
    item.source_quality_score = 0.65
    item.classification_confidence = 0.7

    assert build_score_explanation(item) == "Shown because it matched the AI relevance prefilter."


def test_rank_feed_items_keeps_important_saved_flags() -> None:
    now = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    important = make_feed_item(1, "Important", relevance_score=0.1, importance_score=0.1)
    important.is_important = True
    high_score = make_feed_item(2, "High score", relevance_score=1, importance_score=1)

    ranked = rank_feed_items([high_score, important], now=now)

    assert [item.title for item in ranked] == ["Important", "High score"]


def test_rank_feed_items_uses_configurable_weights() -> None:
    now = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    relevance_item = make_feed_item(1, "Relevant", relevance_score=0.95, importance_score=0.1)
    importance_item = make_feed_item(2, "Important", relevance_score=0.1, importance_score=0.95)

    ranked = rank_feed_items(
        [importance_item, relevance_item],
        ranking_weights=RankingWeights(
            relevance=1,
            importance=0,
            novelty=0,
            source_quality=0,
            stock_impact=0,
            freshness=0,
        ),
        now=now,
    )

    assert [item.title for item in ranked] == ["Relevant", "Important"]


def test_weighted_feed_score_boosts_preferred_sources() -> None:
    now = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    item = make_feed_item(1, "Preferred")
    item.source_name = "GitHub"

    score = weighted_feed_score(
        item,
        RankingWeights(),
        now=now,
        preferred_sources={"GitHub"},
    )
    baseline = weighted_feed_score(item, RankingWeights(), now=now)

    assert score == baseline + 0.08


def test_weighted_feed_score_boosts_watchlist_interest_matches() -> None:
    now = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    item = make_feed_item(1, "Micron HBM demand")
    item.tickers = ["MU"]
    item.topics = ["HBM memory"]
    profile = FeedInterestProfile(
        symbols=frozenset({"MU"}),
        terms=frozenset({"hbm memory"}),
    )

    score = weighted_feed_score(
        item,
        RankingWeights(),
        now=now,
        interest_profile=profile,
    )
    baseline = weighted_feed_score(item, RankingWeights(), now=now)

    assert score == baseline + 0.08


def test_rank_feed_items_uses_watchlist_interest_profile() -> None:
    now = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    generic = make_feed_item(1, "Generic item", relevance_score=0.5, importance_score=0.5)
    watched = make_feed_item(2, "Agent coding launch", relevance_score=0.5, importance_score=0.5)
    watched.topics = ["coding agent"]

    ranked = rank_feed_items(
        [generic, watched],
        ranking_weights=RankingWeights(
            relevance=1,
            importance=0,
            novelty=0,
            source_quality=0,
            stock_impact=0,
            freshness=0,
        ),
        interest_profile=FeedInterestProfile(
            symbols=frozenset(),
            terms=frozenset({"coding agent"}),
        ),
        now=now,
    )

    assert [item.title for item in ranked] == ["Agent coding launch", "Generic item"]


def test_feed_interest_bonus_caps_multiple_matches() -> None:
    item = make_feed_item(1, "Agent coding launch for Micron HBM")
    item.tickers = ["MU"]
    item.topics = ["coding agent", "HBM memory"]
    item.products = ["IDE agent"]
    profile = FeedInterestProfile(
        symbols=frozenset({"MU"}),
        terms=frozenset({"coding agent", "hbm memory", "ide agent", "micron"}),
    )

    assert feed_interest_bonus(item, profile) == 0.12


def test_build_feed_interest_profile_includes_default_company_watchlist() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        profile = build_feed_interest_profile(db)

    assert "NVDA" in profile.symbols
    assert "nvidia" in profile.terms
    assert "openai" in profile.terms


def test_normalize_source_names_trims_empty_values() -> None:
    assert normalize_source_names([" GitHub ", "", "RSS"]) == {"GitHub", "RSS"}


def test_freshness_score_decays_over_three_days() -> None:
    now = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    fresh = make_feed_item(1, "Fresh", published_at=now)
    old = make_feed_item(2, "Old", published_at=now - timedelta(days=4))

    assert freshness_score(fresh, now=now) == 1
    assert freshness_score(old, now=now) == 0


def make_feed_item(
    item_id: int,
    title: str,
    relevance_score: float = 0.5,
    importance_score: float = 0.5,
    published_at: datetime | None = None,
) -> FeedItem:
    return FeedItem(
        id=item_id,
        title=title,
        url=f"https://example.com/{item_id}",
        source_name="Test",
        author=None,
        language="en",
        published_at=published_at,
        category="technical_trend",
        subcategory=None,
        tickers=[],
        companies=[],
        products=[],
        topics=[],
        sentiment="neutral",
        relevance_score=relevance_score,
        importance_score=importance_score,
        novelty_score=0.5,
        source_quality_score=0.5,
        stock_impact_score=0,
        summary_short=None,
        summary_detailed=None,
        why_it_matters=None,
    )
