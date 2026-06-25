from datetime import UTC, datetime
from urllib.parse import urlencode
from xml.etree import ElementTree

import httpx

from app.sources.base import FetchCursor, FetchResult, RawItemInput, SourceConnector

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivConnector(SourceConnector):
    source_name = "arXiv"
    source_type = "research"

    def __init__(self, limit: int = 25) -> None:
        self.limit = limit
        self.base_url = "https://export.arxiv.org/api/query"
        self.categories = ["cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.RO"]
        self.keywords = [
            "agent",
            "tool use",
            "retrieval",
            "coding agent",
            "reasoning",
            "multimodal",
            "inference",
            "benchmark",
            "alignment",
            "memory",
        ]

    async def fetch(self, cursor: FetchCursor) -> FetchResult:
        query = self._build_query()
        params = urlencode(
            {
                "search_query": query,
                "start": 0,
                "max_results": self.limit,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self.base_url}?{params}")
            response.raise_for_status()

        items = self._parse_feed(response.text)
        return FetchResult(
            items=items,
            next_cursor=FetchCursor(metadata={"last_limit": self.limit}),
        )

    def _build_query(self) -> str:
        category_clause = " OR ".join(f"cat:{category}" for category in self.categories)
        keyword_clause = " OR ".join(f'all:"{keyword}"' for keyword in self.keywords)
        return f"({category_clause}) AND ({keyword_clause})"

    def _parse_feed(self, xml_text: str) -> list[RawItemInput]:
        root = ElementTree.fromstring(xml_text)
        entries = root.findall("atom:entry", ATOM_NS)
        return [item for entry in entries if (item := self._entry_to_raw_item(entry))]

    def _entry_to_raw_item(self, entry: ElementTree.Element) -> RawItemInput | None:
        title = self._find_text(entry, "atom:title")
        abstract = self._find_text(entry, "atom:summary")
        external_id = self._find_text(entry, "atom:id")
        if not title or not external_id:
            return None

        authors = [
            name.text.strip()
            for author in entry.findall("atom:author", ATOM_NS)
            if (name := author.find("atom:name", ATOM_NS)) is not None and name.text
        ]
        published_at = self._parse_datetime(self._find_text(entry, "atom:published"))
        categories = [
            category.attrib.get("term")
            for category in entry.findall("atom:category", ATOM_NS)
            if category.attrib.get("term")
        ]

        return RawItemInput(
            source_name=self.source_name,
            external_id=external_id,
            url=external_id,
            raw_title=self._clean_text(title),
            raw_text=self._clean_text(abstract or ""),
            raw_author=", ".join(authors) if authors else None,
            raw_metadata={
                "categories": categories,
                "primary_category": categories[0] if categories else None,
                "authors": authors,
            },
            published_at=published_at,
        )

    def _find_text(self, entry: ElementTree.Element, path: str) -> str | None:
        node = entry.find(path, ATOM_NS)
        if node is None or node.text is None:
            return None
        return node.text.strip()

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)

    def _clean_text(self, value: str) -> str:
        return " ".join(value.split())
