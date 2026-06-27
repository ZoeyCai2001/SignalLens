from app.db.models import RawItem, Source
from app.services.ingestion import normalize_item
from app.sources.product_hunt import ProductHuntConnector


def test_product_hunt_connector_converts_post_to_raw_item() -> None:
    connector = ProductHuntConnector(api_token="test-token", limit=3)

    item = connector._post_to_raw_item(
        {
            "id": "launch-1",
            "name": "AgentDesk",
            "tagline": "AI agents for product teams",
            "description": "Coordinate LLM workflows, research, and launch planning.",
            "url": "https://www.producthunt.com/posts/agentdesk",
            "website": "https://example.com/agentdesk",
            "createdAt": "2026-06-25T12:00:00Z",
            "votesCount": 340,
            "commentsCount": 24,
            "user": {"username": "founder"},
            "topics": {
                "edges": [
                    {"node": {"name": "Artificial Intelligence"}},
                    {"node": {"name": "Productivity"}},
                ]
            },
        }
    )

    assert item is not None
    assert item.external_id == "launch-1"
    assert item.raw_title == "AgentDesk: AI agents for product teams"
    assert item.url == "https://example.com/agentdesk"
    assert item.raw_author == "founder"
    assert item.raw_metadata["product_name"] == "AgentDesk"
    assert item.raw_metadata["votes_count"] == 340
    assert item.published_at is not None


def test_product_hunt_normalized_item_is_product_launch() -> None:
    source = Source(
        id=1,
        name="Product Hunt",
        type="product_launch",
        access_method="official_graphql_api",
    )
    raw = RawItem(
        id=1,
        raw_title="AgentDesk: AI agents for product teams",
        url="https://example.com/agentdesk",
        raw_text="AI agents coordinate LLM workflows for product teams.",
        raw_metadata={
            "product_name": "AgentDesk",
            "votes_count": 340,
            "comments_count": 24,
        },
    )

    item = normalize_item(raw=raw, source=source)

    assert item is not None
    assert item.category == "product"
    assert item.subcategory == "product_launch"
    assert item.products == ["AgentDesk"]
    assert item.summary_short == "Product Hunt launch: AgentDesk: AI agents for product teams"
    assert item.summary_detailed is not None
    assert "Product use case: AI agents coordinate LLM workflows" in item.summary_detailed
    assert "Product audience: product and growth teams" in item.summary_detailed
    assert "Traction signal: 340 Product Hunt votes, 24 comments" in item.summary_detailed
