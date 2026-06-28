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
