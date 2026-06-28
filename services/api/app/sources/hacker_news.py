import re
from datetime import UTC, datetime
from html import unescape
from typing import Any

import httpx

from app.sources.base import FetchCursor, FetchResult, RawItemInput, SourceConnector


class HackerNewsConnector(SourceConnector):
    source_name = "Hacker News"
    source_type = "community"

    def __init__(self, limit: int = 30, comment_limit: int = 3) -> None:
        self.limit = limit
        self.comment_limit = comment_limit
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
                comments = await self._fetch_top_comments(client, payload.get("kids") or [])
                normalized = self._to_raw_item(payload, comments=comments)
                if normalized:
                    items.append(normalized)

        return FetchResult(
            items=items,
            next_cursor=FetchCursor(metadata={"last_limit": self.limit}),
        )

    async def _fetch_top_comments(
        self,
        client: httpx.AsyncClient,
        comment_ids: list[int],
    ) -> list[dict[str, Any]]:
        comments = []
        for comment_id in comment_ids[: self.comment_limit]:
            comment_response = await client.get(f"{self.base_url}/item/{comment_id}.json")
            comment_response.raise_for_status()
            payload = comment_response.json()
            if payload.get("deleted") or payload.get("dead") or payload.get("type") != "comment":
                continue
            text = clean_hn_text(payload.get("text"))
            if not text:
                continue
            comments.append(
                {
                    "id": payload.get("id"),
                    "by": payload.get("by"),
                    "text": text,
                }
            )
        return comments

    def _to_raw_item(
        self,
        payload: dict[str, Any],
        comments: list[dict[str, Any]] | None = None,
    ) -> RawItemInput | None:
        title = payload.get("title")
        if not title:
            return None

        story_id = payload.get("id")
        url = payload.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
        comments = comments or []
        published_at = None
        if payload.get("time"):
            published_at = datetime.fromtimestamp(int(payload["time"]), tz=UTC)

        return RawItemInput(
            source_name=self.source_name,
            external_id=str(story_id) if story_id else None,
            url=url,
            raw_title=str(title),
            raw_text=build_hn_text(clean_hn_text(payload.get("text")), comments),
            raw_author=payload.get("by"),
            raw_metadata={
                "hn_id": story_id,
                "score": payload.get("score"),
                "descendants": payload.get("descendants"),
                "type": payload.get("type"),
                "hn_url": f"https://news.ycombinator.com/item?id={story_id}",
                "top_comments": comments,
                "top_comment_count": len(comments),
            },
            published_at=published_at,
        )


def clean_hn_text(value: str | None) -> str | None:
    if not value:
        return None
    text = re.sub(r"<[^>]+>", " ", unescape(str(value)))
    text = " ".join(text.split())
    return text or None


def build_hn_text(
    story_text: str | None,
    comments: list[dict[str, Any]],
) -> str | None:
    parts = [story_text] if story_text else []
    for comment in comments:
        author = comment.get("by") or "unknown"
        text = comment.get("text")
        if text:
            parts.append(f"HN comment by {author}: {text}")
    return "\n\n".join(parts) if parts else None
