from datetime import UTC, datetime

from app.schemas.feed import FeedItem
from app.services.event_clustering import build_cluster_key, build_event_cluster, item_tickers


def test_event_cluster_groups_strong_ticker_terms() -> None:
    item = make_item(1, "OpenAI and Broadcom unveil inference chip", tickers=["AVGO"])

    assert build_cluster_key(item) == "strong|technical_trend|avgo"


def test_event_cluster_infers_ticker_aliases_from_title() -> None:
    item = make_item(1, "OpenAI unveils custom chip built by Broadcom")

    assert item_tickers(item) == ["AVGO"]
    assert build_cluster_key(item) == "strong|technical_trend|avgo"


def test_event_cluster_builds_representative_summary() -> None:
    items = [
        make_item(
            3,
            "OpenAI and Broadcom unveil inference chip",
            source_name="RSS",
            tickers=["AVGO"],
        ),
        make_item(2, "Broadcom chip discussion", source_name="Hacker News", tickers=["AVGO"]),
    ]

    cluster = build_event_cluster("strong|technical_trend|avgo", items)

    assert cluster.item_count == 2
    assert cluster.tickers == ["AVGO"]
    assert cluster.sources == ["RSS", "Hacker News"]
    assert cluster.representative_item.title == "OpenAI and Broadcom unveil inference chip"
    assert "2 related items" in cluster.title


def make_item(
    item_id: int,
    title: str,
    source_name: str = "Test Source",
    tickers: list[str] | None = None,
) -> FeedItem:
    return FeedItem(
        id=item_id,
        title=title,
        url=f"https://example.com/{item_id}",
        source_name=source_name,
        author=None,
        language="en",
        published_at=datetime(2026, 6, 25, 12, item_id, tzinfo=UTC),
        category="technical_trend",
        subcategory=None,
        tickers=tickers or [],
        companies=[],
        products=[],
        topics=["ai", "inference"],
        sentiment="neutral",
        relevance_score=0.8,
        importance_score=0.7 + item_id * 0.01,
        novelty_score=0.7,
        source_quality_score=0.7,
        stock_impact_score=0.2 if tickers else 0.0,
        summary_short=None,
        summary_detailed=None,
        why_it_matters=None,
    )
