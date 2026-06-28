from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routes import events
from app.schemas.feed import FeedItem
from app.schemas.watchlist import StockMarketSnapshot
from app.services import event_clustering
from app.services.event_clustering import (
    build_cluster_key,
    build_event_cluster,
    build_event_cluster_llm_prompt,
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
    assert "Cross-source cluster with 2 related items" in cluster.main_summary
    assert cluster.earliest_source == "Hacker News"
    assert cluster.latest_update_at == datetime(2026, 6, 25, 12, 3, tzinfo=UTC)
    assert cluster.confidence == 0.62
    assert cluster.importance_score == cluster.top_score
    assert [item.source_name for item in cluster.timeline] == ["Hacker News", "RSS"]
    assert "2 sources mention related signals" in cluster.explanation
    assert "affected ticker context: AVGO" in cluster.explanation
    assert cluster.uncertainty_notes == [
        "Average classifier confidence is below the stronger-confirmation threshold."
    ]


def test_event_cluster_explains_single_source_uncertainties() -> None:
    cluster = build_event_cluster(
        "technical_trend|agent",
        [make_item(1, "Agent framework update", tickers=[])],
    )

    assert "single-source event candidate" in cluster.explanation
    assert "Only one source is currently represented" in cluster.uncertainty_notes[0]
    assert any("No affected ticker was extracted" in note for note in cluster.uncertainty_notes)


def test_event_cluster_llm_prompt_uses_evidence_and_guardrails() -> None:
    cluster = build_event_cluster(
        "strong|technical_trend|avgo",
        [
            make_item(1, "OpenAI and Broadcom unveil inference chip", tickers=["AVGO"]),
            make_item(2, "Broadcom chip discussion", source_name="Hacker News", tickers=["AVGO"]),
        ],
    )

    prompt = build_event_cluster_llm_prompt(cluster)

    assert "Use only the supplied evidence" in prompt
    assert "Do not provide investment advice" in prompt
    assert "OpenAI and Broadcom unveil inference chip" in prompt
    assert "Hacker News" in prompt
    assert "AVGO" in prompt


def test_event_clusters_can_be_retrieved_by_cluster_key() -> None:
    items = [
        make_item(1, "OpenAI and Broadcom unveil inference chip", tickers=["AVGO"]),
        make_item(2, "Broadcom chip discussion", tickers=["AVGO"]),
        make_item(3, "New multimodal benchmark", tickers=[]),
    ]

    grouped = group_items_by_cluster(items)
    clusters = build_event_clusters_from_items(items, min_items=2)
    cluster = build_event_cluster(
        "strong|technical_trend|avgo",
        grouped["strong|technical_trend|avgo"],
    )

    assert len(clusters) == 1
    assert clusters[0].cluster_key == "strong|technical_trend|avgo"
    assert cluster.item_count == 2
    assert [item.id for item in cluster.items] == [2, 1]


def test_list_event_clusters_attaches_related_market_context(monkeypatch) -> None:
    items = [
        make_item(1, "OpenAI and Broadcom unveil inference chip", tickers=["AVGO"]),
        make_item(2, "Broadcom chip discussion", tickers=["AVGO"]),
    ]
    snapshot = StockMarketSnapshot()
    seen: dict[str, object] = {}

    monkeypatch.setattr(event_clustering, "list_visible_feed_items", lambda **_kwargs: items)

    def fake_market_snapshot(db, ticker: str, limit: int = 30):
        seen["db"] = db
        seen["ticker"] = ticker
        seen["limit"] = limit
        return snapshot

    monkeypatch.setattr(event_clustering, "build_stock_market_snapshot", fake_market_snapshot)

    db = object()
    clusters = event_clustering.list_event_clusters(db=db, min_items=2)

    assert clusters[0].related_market_ticker == "AVGO"
    assert clusters[0].related_market is snapshot
    assert seen == {"db": db, "ticker": "AVGO", "limit": 30}


@pytest.mark.anyio
async def test_list_clusters_route_passes_user_preferences(monkeypatch) -> None:
    expected = [
        build_event_cluster(
            "strong|technical_trend|avgo",
            [
                make_item(1, "OpenAI and Broadcom unveil inference chip", tickers=["AVGO"]),
                make_item(2, "Broadcom chip discussion", tickers=["AVGO"]),
            ],
        )
    ]
    preferences = make_preferences()

    monkeypatch.setattr(events, "get_user_preferences", lambda db: preferences)

    def fake_list_event_clusters(
        db,
        limit: int = 12,
        min_items: int = 1,
        ranking_weights=None,
        preferred_sources=None,
        blocked_sources=None,
    ):
        assert limit == 7
        assert min_items == 2
        assert ranking_weights == preferences.ranking_weights
        assert preferred_sources == preferences.preferred_sources
        assert blocked_sources == preferences.blocked_sources
        return expected

    monkeypatch.setattr(events, "list_event_clusters", fake_list_event_clusters)

    result = await events.list_clusters(db=object(), limit=7, min_items=2)

    assert result == expected


@pytest.mark.anyio
async def test_get_cluster_route_returns_detail(monkeypatch) -> None:
    expected = build_event_cluster(
        "strong|technical_trend|avgo",
        [
            make_item(1, "OpenAI and Broadcom unveil inference chip", tickers=["AVGO"]),
            make_item(2, "Broadcom chip discussion", tickers=["AVGO"]),
        ],
    )
    preferences = make_preferences()

    monkeypatch.setattr(events, "get_user_preferences", lambda db: preferences)

    def fake_get_event_cluster(
        db,
        cluster_key: str,
        min_items: int = 1,
        ranking_weights=None,
        preferred_sources=None,
        blocked_sources=None,
    ):
        assert cluster_key == "strong|technical_trend|avgo"
        assert min_items == 2
        assert ranking_weights == preferences.ranking_weights
        assert preferred_sources == preferences.preferred_sources
        assert blocked_sources == preferences.blocked_sources
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
    monkeypatch.setattr(events, "get_user_preferences", lambda db: make_preferences())
    monkeypatch.setattr(events, "get_event_cluster", lambda **_kwargs: None)

    with pytest.raises(HTTPException) as exc_info:
        await events.get_cluster(cluster_key="missing", db=object())

    assert exc_info.value.status_code == 404


@pytest.mark.anyio
async def test_explain_cluster_route_uses_kimi_and_preferences(monkeypatch) -> None:
    expected = build_event_cluster(
        "strong|technical_trend|avgo",
        [
            make_item(1, "OpenAI and Broadcom unveil inference chip", tickers=["AVGO"]),
            make_item(2, "Broadcom chip discussion", tickers=["AVGO"]),
        ],
    )
    preferences = make_preferences()
    seen: dict[str, object] = {}

    monkeypatch.setattr(events, "get_user_preferences", lambda db: preferences)
    monkeypatch.setattr(
        events,
        "get_settings",
        lambda: SimpleNamespace(moonshot_api_key="test-key"),
    )

    def fake_get_event_cluster(
        db,
        cluster_key: str,
        min_items: int = 1,
        ranking_weights=None,
        preferred_sources=None,
        blocked_sources=None,
    ):
        seen["cluster_key"] = cluster_key
        seen["min_items"] = min_items
        seen["ranking_weights"] = ranking_weights
        seen["preferred_sources"] = preferred_sources
        seen["blocked_sources"] = blocked_sources
        return expected

    class FakeKimiClient:
        def __init__(self, settings) -> None:
            seen["settings"] = settings

        async def create_message(self, prompt: str, max_tokens: int):
            seen["prompt"] = prompt
            seen["max_tokens"] = max_tokens
            return SimpleNamespace(
                model="kimi-test",
                text="What happened: concise cluster explanation.",
                input_tokens=20,
                output_tokens=8,
                total_tokens=28,
            )

    monkeypatch.setattr(events, "get_event_cluster", fake_get_event_cluster)
    monkeypatch.setattr(events, "KimiCodingClient", FakeKimiClient)

    result = await events.explain_cluster_with_llm(
        cluster_key="strong|technical_trend|avgo",
        db=object(),
        min_items=2,
    )

    assert result.cluster_key == "strong|technical_trend|avgo"
    assert result.model == "kimi-test"
    assert result.explanation.startswith("What happened")
    assert result.total_tokens == 28
    assert seen["min_items"] == 2
    assert seen["ranking_weights"] == preferences.ranking_weights
    assert seen["preferred_sources"] == preferences.preferred_sources
    assert seen["blocked_sources"] == preferences.blocked_sources
    assert seen["max_tokens"] == 420
    assert "OpenAI and Broadcom" in str(seen["prompt"])


@pytest.mark.anyio
async def test_explain_cluster_route_requires_kimi_key(monkeypatch) -> None:
    monkeypatch.setattr(
        events,
        "get_settings",
        lambda: SimpleNamespace(moonshot_api_key=None),
    )

    with pytest.raises(HTTPException) as exc_info:
        await events.explain_cluster_with_llm(cluster_key="cluster", db=object())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "MOONSHOT_API_KEY is not configured."


@pytest.mark.anyio
async def test_explain_cluster_route_raises_404_when_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        events,
        "get_settings",
        lambda: SimpleNamespace(moonshot_api_key="test-key"),
    )
    monkeypatch.setattr(events, "get_user_preferences", lambda db: make_preferences())
    monkeypatch.setattr(events, "get_event_cluster", lambda **_kwargs: None)

    with pytest.raises(HTTPException) as exc_info:
        await events.explain_cluster_with_llm(cluster_key="missing", db=object())

    assert exc_info.value.status_code == 404


def make_preferences() -> SimpleNamespace:
    return SimpleNamespace(
        ranking_weights={"stock_impact": 1},
        preferred_sources=["RSS"],
        blocked_sources=["Blocked Source"],
    )


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
