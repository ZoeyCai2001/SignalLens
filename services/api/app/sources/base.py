from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class FetchCursor:
    last_successful_fetch_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RawItemInput:
    source_name: str
    external_id: str | None
    url: str
    raw_title: str
    raw_text: str | None = None
    raw_author: str | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)
    published_at: datetime | None = None


@dataclass(frozen=True)
class FetchResult:
    items: list[RawItemInput]
    next_cursor: FetchCursor


class SourceConnector(ABC):
    source_name: str
    source_type: str

    @abstractmethod
    async def fetch(self, cursor: FetchCursor) -> FetchResult:
        """Fetch raw items from an external source."""
