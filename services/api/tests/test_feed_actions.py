from app.db.models import NormalizedItem, UserItemAction
from app.services.feed_actions import serialize_feed_item


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
