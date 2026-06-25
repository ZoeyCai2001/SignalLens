from app.sources.arxiv import ArxivConnector


def test_arxiv_feed_maps_entries_to_raw_items() -> None:
    connector = ArxivConnector(limit=1)
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <id>http://arxiv.org/abs/2606.00001v1</id>
        <title>Agent Benchmarks for Tool Use</title>
        <summary>We evaluate AI agents that use tools.</summary>
        <published>2026-06-24T00:00:00Z</published>
        <author><name>Alice Researcher</name></author>
        <category term="cs.AI" />
      </entry>
    </feed>
    """

    items = connector._parse_feed(xml)

    assert len(items) == 1
    assert items[0].source_name == "arXiv"
    assert items[0].external_id == "http://arxiv.org/abs/2606.00001v1"
    assert items[0].raw_title == "Agent Benchmarks for Tool Use"
    assert items[0].raw_author == "Alice Researcher"
    assert items[0].raw_metadata["categories"] == ["cs.AI"]
