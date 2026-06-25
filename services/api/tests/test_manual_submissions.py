from app.db.models import RawItem, Source
from app.services.manual_submissions import create_manual_normalized_item


def test_manual_fallback_normalization_keeps_user_submission() -> None:
    source = Source(
        id=1,
        name="Manual Submission",
        type="manual",
        access_method="manual_submission",
        enabled=True,
        priority=5,
    )
    raw = RawItem(
        id=1,
        source_id=1,
        external_id="https://example.com/product",
        url="https://example.com/product",
        raw_title="Interesting AI product",
        raw_text="A user-submitted product note.",
        raw_metadata={},
        content_hash="abc",
    )

    item = create_manual_normalized_item(raw=raw, source=source)

    assert item.category == "manual_submission"
    assert item.summary_short == "Manual submission: Interesting AI product"
    assert item.source_name == "Manual Submission"
