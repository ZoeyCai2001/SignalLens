from datetime import UTC, datetime

from app.schemas.feed import FeedItem
from app.schemas.watchlist import TopicWatchlistItem
from app.services.watchlist import build_topic_briefing, build_topic_match_terms


def test_build_topic_match_terms_includes_slug_label_and_related_terms() -> None:
    topic = make_topic()

    terms = build_topic_match_terms(topic)

    assert "ai-coding-agents" in terms
    assert "AI coding agents" in terms
    assert "coding agent" in terms
    assert len(terms) == len(set(term.lower() for term in terms))


def test_build_topic_briefing_groups_sources_entities_and_activity() -> None:
    topic = make_topic()
    items = [
        make_item(
            item_id=1,
            title="Agent paper",
            category="research",
            source_name="arXiv",
            companies=["OpenAI"],
            published_at=datetime(2026, 6, 27, 10, 0, tzinfo=UTC),
            importance_score=0.8,
        ),
        make_item(
            item_id=2,
            title="Agent product",
            category="product",
            source_name="Product Hunt",
            products=["AgentDesk"],
            tickers=["MSFT"],
            published_at=datetime(2026, 6, 27, 8, 0, tzinfo=UTC),
            stock_impact_score=0.76,
        ),
        make_item(
            item_id=3,
            title="Developer discussion",
            category="technical_trend",
            source_name="arXiv",
            companies=["Anthropic"],
            published_at=datetime(2026, 6, 26, 8, 0, tzinfo=UTC),
            importance_score=0.4,
        ),
    ]

    briefing = build_topic_briefing(topic=topic, items=items)

    assert briefing.topic.topic == "ai-coding-agents"
    assert briefing.definition == (
        "AI coding agents is a technical trend watch topic focused on "
        "coding agent, agentic coding."
    )
    assert briefing.item_count == 3
    assert briefing.high_impact_count == 2
    assert briefing.average_importance_score == (0.8 + 0.7 + 0.4) / 3
    assert briefing.trending_sources[0].source_name == "arXiv"
    assert briefing.trending_sources[0].item_count == 2
    assert [item.title for item in briefing.related_papers] == ["Agent paper"]
    assert [item.title for item in briefing.related_products] == ["Agent product"]
    assert briefing.related_companies[:3] == ["OpenAI", "MSFT", "Anthropic"]
    assert [bucket.item_count for bucket in briefing.activity_timeline] == [2, 1]
    assert [item.title for item in briefing.recent_timeline] == [
        "Agent paper",
        "Agent product",
        "Developer discussion",
    ]


def test_build_topic_briefing_uses_notes_as_definition() -> None:
    topic = make_topic(notes="Track practical coding-agent workflows and adoption signals.")

    briefing = build_topic_briefing(topic=topic, items=[])

    assert briefing.definition == "Track practical coding-agent workflows and adoption signals."


def make_topic(notes: str | None = None) -> TopicWatchlistItem:
    return TopicWatchlistItem(
        topic="ai-coding-agents",
        label="AI coding agents",
        category="technical_trend",
        priority="High",
        is_pinned=True,
        include_in_digest=True,
        related_terms=["coding agent", "agentic coding"],
        notes=notes,
    )


def make_item(
    item_id: int,
    title: str,
    category: str,
    source_name: str,
    companies: list[str] | None = None,
    products: list[str] | None = None,
    tickers: list[str] | None = None,
    published_at: datetime | None = None,
    importance_score: float = 0.7,
    stock_impact_score: float = 0.1,
) -> FeedItem:
    return FeedItem(
        id=item_id,
        title=title,
        url=f"https://example.com/{item_id}",
        source_name=source_name,
        author=None,
        language="en",
        published_at=published_at,
        category=category,
        subcategory=None,
        tickers=tickers or [],
        companies=companies or [],
        products=products or [],
        topics=["ai coding agents"],
        sentiment="neutral",
        relevance_score=0.8,
        importance_score=importance_score,
        novelty_score=0.7,
        source_quality_score=0.7,
        stock_impact_score=stock_impact_score,
        summary_short=None,
        summary_detailed=None,
        why_it_matters=None,
    )
