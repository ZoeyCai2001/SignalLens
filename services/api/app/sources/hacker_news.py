from datetime import UTC, datetime
from typing import Any

import httpx

from app.sources.base import FetchCursor, FetchResult, RawItemInput, SourceConnector


class HackerNewsConnector(SourceConnector):
    source_name = "Hacker News"
    source_type = "community"

    def __init__(self, limit: int = 30) -> None:
        self.limit = limit
        self.base_url = "https://hacker-news.firebaseio.com/v0"

    async def fetch(self, cursor: FetchCursor) -> FetchResult:
        async with httpx.AsyncClient(timeout=20.0) as client:
            top_story_response = await client.get(f"{self.base_url}/topstories.json")
            top_story_response.raise_for_status()
            story_ids = top_story_response.json()[: self.limit]

            items: list[RawItemInput] = []
            for story_id in story_ids:
                item_response = await client.get(f"{self.base_url}/item/{story_id}.json")
                item_response.raise_for_status()
                payload = item_response.json()
                normalized = self._to_raw_item(payload)
                if normalized:
                    items.append(normalized)

        return FetchResult(
            items=items,
            next_cursor=FetchCursor(metadata={"last_limit": self.limit}),
        )

    def _to_raw_item(self, payload: dict[str, Any]) -> RawItemInput | None:
        title = payload.get("title")
        if not title:
            return None

        story_id = payload.get("id")
        url = payload.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
        published_at = None
        if payload.get("time"):
            published_at = datetime.fromtimestamp(int(payload["time"]), tz=UTC)

        return RawItemInput(
            source_name=self.source_name,
            external_id=str(story_id) if story_id else None,
            url=url,
            raw_title=str(title),
            raw_text=payload.get("text"),
            raw_author=payload.get("by"),
            raw_metadata={
                "hn_id": story_id,
                "score": payload.get("score"),
                "descendants": payload.get("descendants"),
                "type": payload.get("type"),
                "hn_url": f"https://news.ycombinator.com/item?id={story_id}",
            },
            published_at=published_at,
        )
