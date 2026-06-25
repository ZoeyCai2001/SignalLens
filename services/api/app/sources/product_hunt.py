from datetime import UTC, datetime
from typing import Any

import httpx

from app.sources.base import FetchCursor, FetchResult, RawItemInput, SourceConnector


class ProductHuntConnector(SourceConnector):
    source_name = "Product Hunt"
    source_type = "product_launch"

    def __init__(self, api_token: str, limit: int = 25) -> None:
        self.api_token = api_token
        self.limit = limit
        self.base_url = "https://api.producthunt.com/v2/api/graphql"

    async def fetch(self, cursor: FetchCursor) -> FetchResult:
        query = """
        query SignalLensProductLaunches($first: Int!) {
          posts(first: $first, order: RANKING) {
            edges {
              node {
                id
                name
                tagline
                description
                url
                website
                createdAt
                votesCount
                commentsCount
                user {
                  name
                  username
                }
                topics {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
        """
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "User-Agent": "SignalLens/0.1",
        }
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.post(
                self.base_url,
                json={"query": query, "variables": {"first": self.limit}},
            )
            response.raise_for_status()

        payload = response.json()
        if payload.get("errors"):
            raise ValueError(str(payload["errors"]))

        edges = payload.get("data", {}).get("posts", {}).get("edges", [])
        items = [
            raw_item
            for edge in edges[: self.limit]
            if (raw_item := self._post_to_raw_item(edge.get("node") or {}))
        ]
        return FetchResult(
            items=items,
            next_cursor=FetchCursor(metadata={"last_limit": self.limit}),
        )

    def _post_to_raw_item(self, post: dict[str, Any]) -> RawItemInput | None:
        post_id = post.get("id")
        name = post.get("name")
        product_url = post.get("website") or post.get("url")
        if not post_id or not name or not product_url:
            return None

        tagline = post.get("tagline") or ""
        description = post.get("description") or ""
        topics = self._topic_names(post.get("topics") or {})
        user = post.get("user") or {}
        author = user.get("username") or user.get("name")
        created_at = self._parse_datetime(post.get("createdAt"))
        raw_title = f"{name}: {tagline}" if tagline else str(name)
        raw_text = " ".join(
            part
            for part in [
                tagline,
                description,
                f"Topics: {', '.join(topics)}" if topics else None,
                f"Votes: {post.get('votesCount')}" if post.get("votesCount") is not None else None,
                (
                    f"Comments: {post.get('commentsCount')}"
                    if post.get("commentsCount") is not None
                    else None
                ),
            ]
            if part
        )

        return RawItemInput(
            source_name=self.source_name,
            external_id=str(post_id),
            url=str(product_url),
            raw_title=raw_title,
            raw_text=raw_text,
            raw_author=author,
            raw_metadata={
                "product_name": name,
                "tagline": tagline,
                "description": description,
                "product_hunt_url": post.get("url"),
                "website": post.get("website"),
                "votes_count": post.get("votesCount"),
                "comments_count": post.get("commentsCount"),
                "topics": topics,
                "created_at": post.get("createdAt"),
            },
            published_at=created_at,
        )

    def _topic_names(self, topics: dict[str, Any]) -> list[str]:
        names: list[str] = []
        for edge in topics.get("edges", []):
            node = edge.get("node") or {}
            name = str(node.get("name") or "").strip()
            if name:
                names.append(name)
        return names

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
