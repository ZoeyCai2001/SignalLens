from app.sources.hacker_news import HackerNewsConnector


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
