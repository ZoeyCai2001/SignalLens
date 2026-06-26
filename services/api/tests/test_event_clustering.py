from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from app.api.routes import events
from app.schemas.feed import FeedItem
from app.services.event_clustering import (
    build_cluster_key,
    build_event_cluster,
    build_event_clusters_from_items,
    group_items_by_cluster,
    item_tickers,
)


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


def test_event_clusters_can_be_retrieved_by_cluster_key() -> None:
    items = [
        make_item(1, "OpenAI and Broadcom unveil inference chip", tickers=["AVGO"]),
        make_item(2, "Broadcom chip discussion", tickers=["AVGO"]),
        make_item(3, "New multimodal benchmark", tickers=[]),
    ]

    grouped = group_items_by_cluster(items)
    clusters = build_event_clusters_from_items(items, min_items=2)
    cluster = build_event_cluster("strong|technical_trend|avgo", grouped["strong|technical_trend|avgo"])

    assert len(clusters) == 1
    assert clusters[0].cluster_key == "strong|technical_trend|avgo"
    assert cluster.item_count == 2
    assert [item.id for item in cluster.items] == [2, 1]


@pytest.mark.anyio
async def test_get_cluster_route_returns_detail(monkeypatch) -> None:
    expected = build_event_cluster(
        "strong|technical_trend|avgo",
        [
            make_item(1, "OpenAI and Broadcom unveil inference chip", tickers=["AVGO"]),
            make_item(2, "Broadcom chip discussion", tickers=["AVGO"]),
        ],
    )

    def fake_get_event_cluster(db, cluster_key: str, min_items: int = 1):
        assert cluster_key == "strong|technical_trend|avgo"
        assert min_items == 2
        return expected

    monkeypatch.setattr(events, "get_event_cluster", fake_get_event_cluster)

    result = await events.get_cluster(
        cluster_key="strong|technical_trend|avgo",
        db=object(),
        min_items=2,
    )

    assert result is expected


@pytest.mark.anyio
async def test_get_cluster_route_raises_404_when_missing(monkeypatch) -> None:
    monkeypatch.setattr(events, "get_event_cluster", lambda **_kwargs: None)

    with pytest.raises(HTTPException) as exc_info:
        await events.get_cluster(cluster_key="missing", db=object())

    assert exc_info.value.status_code == 404


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
