from datetime import UTC, datetime, timedelta

from app.db.models import NormalizedItem, UserItemAction
from app.schemas.feed import FeedItem
from app.schemas.preferences import RankingWeights
from app.services.feed_actions import freshness_score, rank_feed_items, serialize_feed_item


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
