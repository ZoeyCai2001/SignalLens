from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil
from typing import Any

import httpx

from app.sources.base import FetchCursor, FetchResult, RawItemInput, SourceConnector


class GitHubConnector(SourceConnector):
    source_name = "GitHub"
    source_type = "developer"

    def __init__(self, limit: int = 25, reference_time: datetime | None = None) -> None:
        self.limit = limit
        self.reference_time = reference_time
        self.base_url = "https://api.github.com"
        self.queries = [
            "llm in:name,description,readme stars:>50",
            "ai-agent in:name,description,readme stars:>20",
            '"coding agent" in:name,description,readme',
            "rag in:name,description,readme stars:>50",
            "inference in:name,description,readme stars:>50",
        ]

    async def fetch(self, cursor: FetchCursor) -> FetchResult:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "SignalLens/0.1",
        }
        per_query = min(20, max(5, ceil(self.limit / len(self.queries))))
        repos: list[dict[str, Any]] = []
        seen: set[str] = set()
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            for query in self.queries:
                response = await client.get(
                    f"{self.base_url}/search/repositories",
                    params={
                        "q": query,
                        "sort": "updated",
                        "order": "desc",
                        "per_page": per_query,
                    },
                )
                response.raise_for_status()
                for repo in response.json().get("items", []):
                    full_name = repo.get("full_name")
                    if not full_name or full_name in seen:
                        continue
                    seen.add(full_name)
                    repos.append(repo)
                    if len(repos) >= self.limit:
                        break
                if len(repos) >= self.limit:
                    break

        items = [
            raw_item
            for repo in repos[: self.limit]
            if (raw_item := self._repo_to_raw_item(repo))
        ]
        return FetchResult(
            items=items,
            next_cursor=FetchCursor(metadata={"last_limit": self.limit}),
        )

    def _repo_to_raw_item(self, repo: dict[str, Any]) -> RawItemInput | None:
        full_name = repo.get("full_name")
        html_url = repo.get("html_url")
        if not full_name or not html_url:
            return None

        description = repo.get("description") or ""
        topics = repo.get("topics") or []
        language = repo.get("language")
        stars = repo.get("stargazers_count")
        created_at = self._parse_datetime(repo.get("created_at"))
        updated_at = self._parse_datetime(repo.get("updated_at"))
        growth = compute_repo_growth(
            stars=stars,
            created_at=created_at,
            reference_time=self.reference_time,
        )
        raw_title = f"{full_name}: {description}" if description else str(full_name)
        raw_text = " ".join(
            part
            for part in [
                description,
                f"Language: {language}" if language else None,
                f"Topics: {', '.join(topics)}" if topics else None,
                f"Stars: {stars}" if stars is not None else None,
                f"Stars per day: {growth.stars_per_day}" if growth else None,
                f"Growth signal: {growth.label}" if growth else None,
            ]
            if part
        )

        owner = repo.get("owner") or {}
        return RawItemInput(
            source_name=self.source_name,
            external_id=str(repo.get("id")) if repo.get("id") else str(full_name),
            url=str(html_url),
            raw_title=raw_title,
            raw_text=raw_text,
            raw_author=owner.get("login"),
            raw_metadata={
                "full_name": full_name,
                "language": language,
                "stars": stars,
                "stars_per_day": growth.stars_per_day if growth else None,
                "growth_signal": growth.label if growth else None,
                "forks": repo.get("forks_count"),
                "open_issues": repo.get("open_issues_count"),
                "topics": topics,
                "license": (repo.get("license") or {}).get("spdx_id"),
                "created_at": repo.get("created_at"),
                "updated_at": repo.get("updated_at"),
            },
            published_at=updated_at or created_at,
        )

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


@dataclass(frozen=True)
class RepoGrowthSignal:
    stars_per_day: float
    label: str


def compute_repo_growth(
    stars: int | None,
    created_at: datetime | None,
    reference_time: datetime | None = None,
) -> RepoGrowthSignal | None:
    if stars is None or created_at is None:
        return None

    now = reference_time or datetime.now(UTC)
    age_days = max(1, (now - created_at).total_seconds() / 86_400)
    stars_per_day = round(float(stars) / age_days, 2)
    if stars_per_day >= 50:
        label = "fast-growing"
    elif stars_per_day >= 10:
        label = "gaining traction"
    else:
        label = "steady"
    return RepoGrowthSignal(stars_per_day=stars_per_day, label=label)
