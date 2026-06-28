from app.db.models import RawItem, Source
from app.services.ingestion import normalize_item
from app.sources.rss import RssConnector, RssFeedSpec


def test_rss_connector_parses_rss_items() -> None:
    connector = RssConnector()
    feed = RssFeedSpec(name="Test Feed", url="https://example.com/rss")

    items = connector._parse_feed(
        feed=feed,
        xml_text="""
        <rss version="2.0">
          <channel>
            <item>
              <title>New AI agent product</title>
              <link>https://example.com/agent</link>
              <guid>agent-1</guid>
              <description>
                <![CDATA[<p>An LLM agent update for coding workflows.</p>]]>
              </description>
              <pubDate>Thu, 25 Jun 2026 10:30:00 GMT</pubDate>
              <author>editor@example.com</author>
            </item>
          </channel>
        </rss>
        """,
    )

    assert len(items) == 1
    assert items[0].external_id == "agent-1"
    assert items[0].raw_title == "New AI agent product"
    assert items[0].raw_text == "An LLM agent update for coding workflows."
    assert items[0].published_at is not None


def test_rss_connector_parses_atom_items() -> None:
    connector = RssConnector()
    feed = RssFeedSpec(name="Atom Feed", url="https://example.com/atom")

    items = connector._parse_feed(
        feed=feed,
        xml_text="""
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>tag:example.com,2026:ai</id>
            <title>AI model routing update</title>
            <link href="https://example.com/model-routing" />
            <summary>Model routing and inference infrastructure notes.</summary>
            <updated>2026-06-25T10:30:00Z</updated>
            <author><name>Example AI</name></author>
          </entry>
        </feed>
        """,
    )

    assert len(items) == 1
    assert items[0].external_id == "tag:example.com,2026:ai"
    assert items[0].url == "https://example.com/model-routing"
    assert items[0].raw_author == "Example AI"


def test_rss_connector_filters_items_by_include_terms() -> None:
    connector = RssConnector(include_terms=["AI photo tools"])
    feed = RssFeedSpec(name="Social Feed", url="https://example.com/rss")

    items = connector._parse_feed(
        feed=feed,
        xml_text="""
        <rss version="2.0">
          <channel>
            <item>
              <title>AI photo tools trend</title>
              <link>https://example.com/ai-photo</link>
              <description>Creators are sharing AI image workflows.</description>
            </item>
            <item>
              <title>Restaurant map update</title>
              <link>https://example.com/food</link>
              <description>Food discovery notes.</description>
            </item>
          </channel>
        </rss>
        """,
    )

    assert len(items) == 1
    assert items[0].url == "https://example.com/ai-photo"


def test_rss_connector_filters_items_by_chinese_include_terms() -> None:
    connector = RssConnector(include_terms=["AI写真"])
    feed = RssFeedSpec(name="Chinese Social Feed", url="https://example.com/rss")

    items = connector._parse_feed(
        feed=feed,
        xml_text="""
        <rss version="2.0">
          <channel>
            <item>
              <title>AI写真工具开始流行</title>
              <link>https://example.com/photo</link>
              <description>小红书用户讨论人工智能修图工作流。</description>
            </item>
            <item>
              <title>普通生活帖子</title>
              <link>https://example.com/life</link>
            </item>
          </channel>
        </rss>
        """,
    )

    assert len(items) == 1
    assert items[0].raw_title == "AI写真工具开始流行"


def test_rss_connector_skips_items_without_title_or_link() -> None:
    connector = RssConnector()
    feed = RssFeedSpec(name="Test Feed", url="https://example.com/rss")

    items = connector._parse_feed(
        feed=feed,
        xml_text="""
        <rss version="2.0">
          <channel>
            <item>
              <title>Missing link</title>
            </item>
          </channel>
        </rss>
        """,
    )

    assert items == []


def test_rss_normalization_detects_private_ai_lab_companies() -> None:
    source = Source(
        id=1,
        name="Selected RSS Feeds",
        type="rss",
        access_method="rss",
    )
    raw = RawItem(
        id=1,
        raw_title="OpenAI updates ChatGPT agents",
        url="https://example.com/openai-agents",
        raw_text="OpenAI described ChatGPT agent infrastructure and enterprise workflows.",
        raw_metadata={},
    )

    item = normalize_item(raw=raw, source=source)

    assert item is not None
    assert item.companies == ["OpenAI"]
    assert item.products == ["ChatGPT"]
    assert item.subcategory == "company_blog"
