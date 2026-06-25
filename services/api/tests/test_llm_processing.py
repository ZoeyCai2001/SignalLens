import pytest

from app.core.config import Settings
from app.db.models import NormalizedItem
from app.services.llm_processing import process_llm_batch_items, should_summarize_item


def make_item(item_id: int, summary_detailed: str | None = None) -> NormalizedItem:
    return NormalizedItem(
        id=item_id,
        raw_item_id=item_id,
        title=f"Item {item_id}",
        url=f"https://example.com/{item_id}",
        source_name="Test",
        text="A relevant AI intelligence item.",
        summary_detailed=summary_detailed,
    )


def test_should_summarize_item_respects_existing_summary() -> None:
    item = make_item(1, summary_detailed="Already summarized")

    assert not should_summarize_item(item, skip_summarized=True)
    assert should_summarize_item(item, skip_summarized=False)


@pytest.mark.anyio
async def test_process_llm_batch_items_summarizes_unsummarized_items() -> None:
    items = [make_item(1), make_item(2, summary_detailed="Existing")]
    summarized_ids: list[int] = []

    async def fake_summarizer(db, item: NormalizedItem, settings: Settings) -> NormalizedItem:
        summarized_ids.append(item.id)
        item.summary_detailed = "Generated summary"
        return item

    result = await process_llm_batch_items(
        db=None,
        settings=Settings(),
        items=items,
        requested_limit=2,
        summarize=True,
        classify=False,
        skip_summarized=True,
        summarizer=fake_summarizer,
    )

    assert summarized_ids == [1]
    assert result.candidates_seen == 2
    assert result.summarized_count == 1
    assert result.skipped_count == 1
    assert result.item_ids == [1]
    assert result.errors == []


@pytest.mark.anyio
async def test_process_llm_batch_items_captures_classification_errors() -> None:
    items = [make_item(1), make_item(2)]
    summarized_ids: list[int] = []

    async def fake_classifier(db, item: NormalizedItem, settings: Settings) -> NormalizedItem:
        if item.id == 1:
            raise RuntimeError("classification failed")
        item.category = "social_trend"
        return item

    async def fake_summarizer(db, item: NormalizedItem, settings: Settings) -> NormalizedItem:
        summarized_ids.append(item.id)
        item.summary_detailed = "Generated summary"
        return item

    result = await process_llm_batch_items(
        db=None,
        settings=Settings(),
        items=items,
        requested_limit=2,
        summarize=True,
        classify=True,
        skip_summarized=True,
        summarizer=fake_summarizer,
        classifier=fake_classifier,
    )

    assert summarized_ids == [1, 2]
    assert result.summarized_count == 2
    assert result.classified_count == 1
    assert result.item_ids == [1, 2]
    assert len(result.errors) == 1
    assert result.errors[0].item_id == 1
    assert result.errors[0].stage == "classify"
