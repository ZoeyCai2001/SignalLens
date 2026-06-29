from app.db.models import RawItem, Source
from app.services.ingestion import normalize_item
from app.sources.hacker_news import HackerNewsConnector, clean_hn_text


def test_hacker_news_payload_maps_to_raw_item() -> None:
    connector = HackerNewsConnector(limit=1)

    item = connector._to_raw_item(
        {
            "id": 123,
            "title": "Show HN: An AI agent benchmark",
            "url": "https://example.com/agent",
            "by": "alice",
            "score": 42,
            "descendants": 7,
            "type": "story",
            "time": 1_700_000_000,
        }
    )

    assert item is not None
    assert item.source_name == "Hacker News"
    assert item.external_id == "123"
    assert item.raw_title == "Show HN: An AI agent benchmark"
    assert item.raw_author == "alice"
    assert item.raw_metadata["score"] == 42


def test_hacker_news_payload_includes_clean_comment_preview() -> None:
    connector = HackerNewsConnector(limit=1)

    item = connector._to_raw_item(
        {
            "id": 123,
            "title": "Show HN: An AI agent benchmark",
            "by": "alice",
            "score": 42,
            "descendants": 7,
            "type": "story",
        },
        comments=[
            {
                "id": 1,
                "by": "bob",
                "text": "This benchmark caught real agent failures.",
            }
        ],
    )

    assert item is not None
    assert "HN comment by bob" in item.raw_text
    assert item.raw_metadata["top_comment_count"] == 1
    assert item.raw_metadata["top_comments"][0]["text"] == (
        "This benchmark caught real agent failures."
    )


def test_clean_hn_text_strips_html_and_unescapes_entities() -> None:
    assert clean_hn_text("AI&nbsp;<p>agents &amp; evals</p>") == "AI agents & evals"


def test_hacker_news_normalization_builds_discussion_summary() -> None:
    source = Source(id=1, name="Hacker News", type="community", access_method="official_api")
    raw = RawItem(
        id=1,
        raw_title="Show HN: AI agent harness benchmark",
        url="https://news.ycombinator.com/item?id=123",
        raw_text=(
            "Developers discuss an AI agent benchmark.\n\n"
            "HN comment by bob: This benchmark caught real coding agent failures."
        ),
        raw_author="alice",
        raw_metadata={
            "score": 42,
            "descendants": 7,
            "top_comments": [
                {
                    "id": 1,
                    "by": "bob",
                    "text": "This benchmark caught real coding agent failures.",
                }
            ],
        },
    )

    item = normalize_item(raw=raw, source=source)

    assert item is not None
    assert item.category == "technical_trend"
    assert item.subcategory == "community_discussion"
    assert item.summary_detailed is not None
    assert "Discussion summary: Developers discuss an AI agent benchmark." in item.summary_detailed
    assert "Discussion signal: 42 HN points, 7 comments, 1 sampled top comment." in (
        item.summary_detailed
    )
    assert "Top comment by bob: This benchmark caught real coding agent failures." in (
        item.summary_detailed
    )
