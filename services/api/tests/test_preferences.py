from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, NormalizedItem, UserItemAction
from app.services.preferences import (
    DEFAULT_RANKING_WEIGHTS,
    get_feedback_profile_summary,
    normalize_language_preferences,
    normalize_ranking_weights,
    normalize_source_preferences,
)


def test_normalize_ranking_weights_merges_partial_values_with_defaults() -> None:
    weights = normalize_ranking_weights({"importance": 0.8})

    assert weights["importance"] == 0.8
    assert weights["relevance"] == DEFAULT_RANKING_WEIGHTS.relevance


def test_normalize_source_preferences_trims_and_deduplicates_names() -> None:
    assert normalize_source_preferences([" RSS ", "rss", "", "GitHub"]) == ["RSS", "GitHub"]


def test_normalize_language_preferences_maps_aliases_and_deduplicates() -> None:
    assert normalize_language_preferences([" English ", "en-us", "ZH_CN", "cn", ""]) == [
        "en",
        "zh",
    ]


def test_get_feedback_profile_summary_reports_learned_signals() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                NormalizedItem(
                    id=1,
                    raw_item_id=1,
                    title="Saved coding agent",
                    url="https://example.com/saved",
                    source_name="GitHub",
                    language="en",
                    category="ai_trend",
                    topics=["coding agent"],
                    tickers=["MSFT"],
                    companies=["Microsoft"],
                    products=["IDE agent"],
                ),
                NormalizedItem(
                    id=2,
                    raw_item_id=2,
                    title="Hidden crypto bot",
                    url="https://example.com/hidden",
                    source_name="Noisy RSS",
                    language="en",
                    category="noise_irrelevant",
                    topics=["crypto trading bot"],
                    products=["sales bot"],
                ),
                NormalizedItem(
                    id=3,
                    raw_item_id=3,
                    title="Useful benchmark agent",
                    url="https://example.com/useful",
                    source_name="Research Blog",
                    language="en",
                    category="research",
                    topics=["benchmark agent"],
                    products=["eval tool"],
                ),
            ]
        )
        db.add_all(
            [
                UserItemAction(user_id="local", item_id=1, is_saved=True, is_important=True),
                UserItemAction(
                    user_id="local",
                    item_id=2,
                    is_hidden=True,
                    usefulness_feedback="not_useful",
                ),
                UserItemAction(user_id="local", item_id=3, usefulness_feedback="useful"),
            ]
        )
        db.commit()

        summary = get_feedback_profile_summary(db)

    assert summary.saved_count == 1
    assert summary.hidden_count == 1
    assert summary.important_count == 1
    assert summary.useful_count == 1
    assert summary.not_useful_count == 1
    assert "github" in summary.liked_sources
    assert "research blog" in summary.liked_sources
    assert "noisy rss" in summary.disliked_sources
    assert "MSFT" in summary.liked_symbols
    assert "coding agent" in summary.liked_terms
    assert "crypto trading bot" in summary.disliked_terms
    assert len(summary.watchlist_terms) <= 12
