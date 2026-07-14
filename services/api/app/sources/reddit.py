from datetime import UTC, datetime
from math import ceil
from typing import Any

import httpx

from app.sources.base import FetchCursor, FetchResult, RawItemInput, SourceConnector

DEFAULT_REDDIT_QUERY = (
    "AI OR LLM OR agents OR ChatGPT OR Claude OR multimodal OR \"coding agent\""
)
DEFAULT_REDDIT_SUBREDDITS = ("LocalLLaMA", "MachineLearning", "artificial", "singularity")


class RedditConnector(SourceConnector):
    source_name = "Reddit AI Communities"
    source_type = "community"

    def __init__(
        self,
        limit: int = 25,
        subreddits: list[str] | tuple[str, ...] | None = None,
        query: str = DEFAULT_REDDIT_QUERY,
        source_name: str | None = None,
        user_agent: str = "SignalLens/0.1 personal research",
    ) -> None:
        self.limit = limit
        self.subreddits = normalize_reddit_subreddits(subreddits or DEFAULT_REDDIT_SUBREDDITS)
        self.query = query.strip() or DEFAULT_REDDIT_QUERY
        self.source_name = source_name or "Reddit AI Communities"
        self.user_agent = user_agent
        self.base_url = "https://www.reddit.com"

    async def fetch(self, cursor: FetchCursor) -> FetchResult:
        if not self.subreddits:
            return FetchResult(
                items=[],
                next_cursor=FetchCursor(metadata={"last_limit": self.limit}),
            )

        per_subreddit_limit = max(1, ceil(self.limit / len(self.subreddits)))
        headers = {"User-Agent": self.user_agent}
        items: list[RawItemInput] = []

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            for subreddit in self.subreddits:
                payload = await self._get_listing(
                    client=client,
                    subreddit=subreddit,
                    limit=per_subreddit_limit,
                )
                items.extend(self._listing_to_raw_items(payload, subreddit=subreddit))

        return FetchResult(
            items=items[: self.limit],
            next_cursor=FetchCursor(
                metadata={
                    "last_limit": self.limit,
                    "subreddits": self.subreddits,
                    "query": self.query,
                }
            ),
        )

    async def _get_listing(
        self,
        client: httpx.AsyncClient,
        subreddit: str,
        limit: int,
    ) -> dict[str, Any]:
        response = await client.get(
            f"{self.base_url}/r/{subreddit}/search.json",
            params={
                "q": self.query,
                "restrict_sr": "on",
                "sort": "new",
                "t": "week",
                "limit": limit,
            },
        )
        response.raise_for_status()
        return response.json()

    def _listing_to_raw_items(
        self,
        payload: dict[str, Any],
        subreddit: str,
    ) -> list[RawItemInput]:
        children = payload.get("data", {}).get("children", [])
        return [
            raw_item
            for child in children
            if isinstance(child, dict)
            if (raw_item := self._post_to_raw_item(child.get("data") or {}, subreddit=subreddit))
        ]

    def _post_to_raw_item(
        self,
        post: dict[str, Any],
        subreddit: str | None = None,
    ) -> RawItemInput | None:
        post_id = post.get("id") or post.get("name")
        title = str(post.get("title") or "").strip()
        if not post_id or not title:
            return None

        permalink = str(post.get("permalink") or "").strip()
        reddit_url = (
            f"{self.base_url}{permalink}"
            if permalink.startswith("/")
            else permalink
            if permalink
            else f"{self.base_url}/comments/{post_id}"
        )
        outbound_url = str(post.get("url") or "").strip()
        url = outbound_url if outbound_url.startswith(("http://", "https://")) else reddit_url
        subreddit_name = str(post.get("subreddit") or subreddit or "").strip()
        created_at = parse_reddit_datetime(post.get("created_utc"))
        selftext = clean_reddit_text(post.get("selftext"))
        flair = clean_reddit_text(post.get("link_flair_text"))
        score = post.get("score")
        comments_count = post.get("num_comments")
        upvote_ratio = post.get("upvote_ratio")

        raw_text = " ".join(
            part
            for part in [
                selftext,
                f"Subreddit: r/{subreddit_name}" if subreddit_name else None,
                f"Flair: {flair}" if flair else None,
                f"Score: {score}" if score is not None else None,
                f"Comments: {comments_count}" if comments_count is not None else None,
            ]
            if part
        )

        return RawItemInput(
            source_name=self.source_name,
            external_id=str(post_id),
            url=url,
            raw_title=title,
            raw_text=raw_text or None,
            raw_author=post.get("author"),
            raw_metadata={
                "reddit_id": post_id,
                "reddit_name": post.get("name"),
                "subreddit": subreddit_name or None,
                "permalink": reddit_url,
                "outbound_url": outbound_url or None,
                "score": score,
                "comments_count": comments_count,
                "upvote_ratio": upvote_ratio,
                "domain": post.get("domain"),
                "flair": flair,
                "created_utc": post.get("created_utc"),
            },
            published_at=created_at,
        )


def clean_reddit_text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def parse_reddit_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


def normalize_reddit_subreddits(values: list[str] | tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    subreddits: list[str] = []
    for value in values:
        cleaned = str(value).strip().removeprefix("r/").strip("/")
        if not cleaned or cleaned.lower() in seen:
            continue
        seen.add(cleaned.lower())
        subreddits.append(cleaned)
    return subreddits
