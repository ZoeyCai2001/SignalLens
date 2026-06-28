from datetime import UTC, datetime

from app.db.models import RawItem, Source
from app.schemas.feed import FeedItem
from app.services.daily_digest import build_digest_sections
from app.services.ingestion import detect_language, normalize_item, parse_chinese_rss_feeds


def test_parse_chinese_rss_feeds_supports_named_entries() -> None:
    feeds = parse_chinese_rss_feeds("AI News|https://example.com/rss,https://example.org/feed")

    assert feeds[0].name == "AI News"
    assert feeds[0].url == "https://example.com/rss"
    assert feeds[1].name == "Chinese Feed 2"


def test_chinese_rss_normalizes_to_social_trend() -> None:
    source = Source(
        id=1,
        name="Chinese RSS Feeds",
        type="chinese_social",
        access_method="rss",
    )
    raw = RawItem(
        id=1,
        raw_title="国产大模型智能体产品开始流行",
        url="https://example.com/chinese-ai",
        raw_text="人工智能应用和AI产品在中文社区获得讨论。",
        raw_metadata={"feed_name": "AI News"},
    )

    item = normalize_item(raw=raw, source=source)

    assert item is not None
    assert item.category == "social_trend"
    assert item.subcategory == "chinese_rss"
    assert item.language == "zh"
    assert item.source_quality_score == 0.62


def test_social_keyword_source_normalizes_to_experimental_social_trend() -> None:
    source = Source(
        id=2,
        name="Xiaohongshu AI Photo",
        type="social_keyword",
        access_method="rss",
    )
    raw = RawItem(
        id=2,
        raw_title="AI写真工具开始流行",
        url="https://example.com/xhs-ai-photo",
        raw_text="小红书用户讨论人工智能修图和AI产品工作流。",
        raw_metadata={"feed_name": "Public Social Feed"},
    )

    item = normalize_item(raw=raw, source=source)

    assert item is not None
    assert item.category == "social_trend"
    assert item.subcategory == "chinese_social_keyword"
    assert item.language == "zh"
    assert item.source_quality_score == 0.58
    assert "public RSS/Atom metadata" in item.why_it_matters


def test_detect_language_marks_cjk_text_as_chinese() -> None:
    assert detect_language("AI 大模型") == "zh"
    assert detect_language("AI model") == "en"


def test_daily_digest_includes_chinese_social_section() -> None:
    sections = build_digest_sections(
        [
            FeedItem(
                id=1,
                title="国产大模型智能体产品开始流行",
                url="https://example.com/chinese-ai",
                source_name="Chinese RSS Feeds",
                author=None,
                language="zh",
                published_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
                category="social_trend",
                subcategory="chinese_rss",
                tickers=[],
                companies=[],
                products=[],
                topics=["大模型", "智能体"],
                sentiment="neutral",
                relevance_score=0.8,
                importance_score=0.7,
                novelty_score=1.0,
                source_quality_score=0.75,
                stock_impact_score=0,
                summary_short=None,
                summary_detailed=None,
                why_it_matters=None,
            )
        ],
        limit_per_section=3,
    )

    section_map = {section.key: section for section in sections}
    assert section_map["chinese_social"].items[0].language == "zh"
