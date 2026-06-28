import re
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import httpx

from app.sources.base import FetchCursor, FetchResult, RawItemInput, SourceConnector

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
CONTENT_NS = {"content": "http://purl.org/rss/1.0/modules/content/"}
DC_NS = {"dc": "http://purl.org/dc/elements/1.1/"}


@dataclass(frozen=True)
class RssFeedSpec:
    name: str
    url: str


DEFAULT_RSS_FEEDS = [
    RssFeedSpec(name="OpenAI News", url="https://openai.com/news/rss.xml"),
    RssFeedSpec(name="Anthropic News", url="https://www.anthropic.com/news/rss.xml"),
    RssFeedSpec(name="Google AI Blog", url="https://blog.google/technology/ai/rss/"),
    RssFeedSpec(name="Google DeepMind Blog", url="https://deepmind.google/discover/blog/rss.xml"),
]


class RssConnector(SourceConnector):
    source_name = "Selected RSS Feeds"
    source_type = "rss"

    def __init__(
        self,
        limit: int = 25,
        feeds: list[RssFeedSpec] | None = None,
        source_name: str | None = None,
        source_type: str | None = None,
        include_terms: list[str] | None = None,
    ) -> None:
        self.limit = limit
        self.feeds = feeds or DEFAULT_RSS_FEEDS
        self.include_terms = [term.strip() for term in (include_terms or []) if term.strip()]
        if source_name:
            self.source_name = source_name
        if source_type:
            self.source_type = source_type

    async def fetch(self, cursor: FetchCursor) -> FetchResult:
        items: list[RawItemInput] = []
        failures: dict[str, str] = {}
        per_feed_limit = max(1, self.limit)
        headers = {"User-Agent": "SignalLens/0.1"}

        async with httpx.AsyncClient(
            timeout=25.0,
            headers=headers,
            follow_redirects=True,
        ) as client:
            for feed in self.feeds:
                try:
                    response = await client.get(feed.url)
                    response.raise_for_status()
                    parsed_items = self._parse_feed(feed=feed, xml_text=response.text)
                    items.extend(parsed_items[:per_feed_limit])
                except Exception as exc:
                    failures[feed.name] = str(exc)

        if not items and failures:
            failure_text = "; ".join(f"{name}: {error}" for name, error in failures.items())
            raise RuntimeError(f"All RSS feeds failed: {failure_text}")

        return FetchResult(
            items=items[: self.limit],
            next_cursor=FetchCursor(
                metadata={
                    "last_limit": self.limit,
                    "feed_count": len(self.feeds),
                    "failures": failures,
                }
            ),
        )

    def _parse_feed(self, feed: RssFeedSpec, xml_text: str) -> list[RawItemInput]:
        root = ElementTree.fromstring(xml_text)
        if root.tag.endswith("feed"):
            return self._parse_atom_feed(feed=feed, root=root)
        return self._parse_rss_feed(feed=feed, root=root)

    def _parse_rss_feed(self, feed: RssFeedSpec, root: ElementTree.Element) -> list[RawItemInput]:
        entries = root.findall("./channel/item")
        return [
            item
            for entry in entries
            if (item := self._rss_entry_to_raw_item(feed, entry))
            if self._matches_include_terms(item)
        ]

    def _parse_atom_feed(self, feed: RssFeedSpec, root: ElementTree.Element) -> list[RawItemInput]:
        entries = root.findall("atom:entry", ATOM_NS)
        return [
            item
            for entry in entries
            if (item := self._atom_entry_to_raw_item(feed, entry))
            if self._matches_include_terms(item)
        ]

    def _rss_entry_to_raw_item(
        self,
        feed: RssFeedSpec,
        entry: ElementTree.Element,
    ) -> RawItemInput | None:
        title = self._find_text(entry, "title")
        link = self._find_text(entry, "link")
        if not title or not link:
            return None

        description = self._find_text(entry, "description")
        content = self._find_text(entry, "content:encoded", CONTENT_NS)
        author = self._find_text(entry, "dc:creator", DC_NS) or self._find_text(entry, "author")
        guid = self._find_text(entry, "guid")
        published_at = self._parse_datetime(
            self._find_text(entry, "pubDate") or self._find_text(entry, "published")
        )
        raw_text = self._clean_html(content or description or "")

        return RawItemInput(
            source_name=self.source_name,
            external_id=guid or link,
            url=link,
            raw_title=self._clean_text(title),
            raw_text=raw_text,
            raw_author=author or feed.name,
            raw_metadata={
                "feed_name": feed.name,
                "feed_url": feed.url,
                "guid": guid,
                "format": "rss",
            },
            published_at=published_at,
        )

    def _atom_entry_to_raw_item(
        self,
        feed: RssFeedSpec,
        entry: ElementTree.Element,
    ) -> RawItemInput | None:
        title = self._find_text(entry, "atom:title", ATOM_NS)
        link = self._atom_link(entry)
        external_id = self._find_text(entry, "atom:id", ATOM_NS) or link
        if not title or not link:
            return None

        summary = self._find_text(entry, "atom:summary", ATOM_NS)
        content = self._find_text(entry, "atom:content", ATOM_NS)
        author = self._atom_author(entry) or feed.name
        published_at = self._parse_datetime(
            self._find_text(entry, "atom:published", ATOM_NS)
            or self._find_text(entry, "atom:updated", ATOM_NS)
        )

        return RawItemInput(
            source_name=self.source_name,
            external_id=external_id,
            url=link,
            raw_title=self._clean_text(title),
            raw_text=self._clean_html(content or summary or ""),
            raw_author=author,
            raw_metadata={
                "feed_name": feed.name,
                "feed_url": feed.url,
                "format": "atom",
            },
            published_at=published_at,
        )

    def _find_text(
        self,
        entry: ElementTree.Element,
        path: str,
        namespaces: dict[str, str] | None = None,
    ) -> str | None:
        node = entry.find(path, namespaces or {})
        if node is None or node.text is None:
            return None
        text = node.text.strip()
        return text or None

    def _atom_link(self, entry: ElementTree.Element) -> str | None:
        for link in entry.findall("atom:link", ATOM_NS):
            href = link.attrib.get("href")
            rel = link.attrib.get("rel", "alternate")
            if href and rel == "alternate":
                return href
        return None

    def _atom_author(self, entry: ElementTree.Element) -> str | None:
        author = entry.find("atom:author", ATOM_NS)
        if author is None:
            return None
        return self._find_text(author, "atom:name", ATOM_NS)

    def _matches_include_terms(self, item: RawItemInput) -> bool:
        if not self.include_terms:
            return True
        search_text = self._normalize_search_text(
            " ".join([item.raw_title, item.raw_text or "", item.url])
        )
        return any(
            normalized_term in search_text
            for term in self.include_terms
            if (normalized_term := self._normalize_search_text(term))
        )

    def _normalize_search_text(self, value: str) -> str:
        return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", value.lower()).strip()

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    def _clean_html(self, value: str) -> str:
        without_tags = re.sub(r"<[^>]+>", " ", value)
        return self._clean_text(without_tags)

    def _clean_text(self, value: str) -> str:
        return " ".join(value.split())
