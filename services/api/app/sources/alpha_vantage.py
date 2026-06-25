from datetime import UTC, datetime
from typing import Any

import httpx

from app.sources.base import FetchCursor, FetchResult, RawItemInput, SourceConnector


class AlphaVantageNewsConnector(SourceConnector):
    source_name = "Alpha Vantage News"
    source_type = "finance_news"

    def __init__(self, api_key: str, tickers: list[str], limit: int = 25) -> None:
        self.api_key = api_key
        self.tickers = tickers
        self.limit = limit
        self.base_url = "https://www.alphavantage.co/query"

    async def fetch(self, cursor: FetchCursor) -> FetchResult:
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": ",".join(self.tickers),
            "sort": "LATEST",
            "limit": self.limit,
            "apikey": self.api_key,
        }
        headers = {"User-Agent": "SignalLens/0.1"}
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()

        payload = response.json()
        if "Error Message" in payload:
            raise ValueError(str(payload["Error Message"]))
        if "Information" in payload:
            raise ValueError(str(payload["Information"]))

        feed = payload.get("feed", [])
        items = [
            raw_item
            for entry in feed[: self.limit]
            if (raw_item := self._entry_to_raw_item(entry))
        ]
        return FetchResult(
            items=items,
            next_cursor=FetchCursor(metadata={"last_limit": self.limit}),
        )

    def _entry_to_raw_item(self, entry: dict[str, Any]) -> RawItemInput | None:
        title = entry.get("title")
        url = entry.get("url")
        if not title or not url:
            return None

        topics = self._topic_names(entry.get("topics") or [])
        ticker_sentiment = self._ticker_sentiment(entry.get("ticker_sentiment") or [])
        tickers = [item["ticker"] for item in ticker_sentiment]
        summary = entry.get("summary") or ""
        source = entry.get("source")
        authors = [str(author) for author in entry.get("authors", []) if str(author).strip()]
        published_at = self._parse_datetime(entry.get("time_published"))
        raw_text = " ".join(
            part
            for part in [
                summary,
                f"Topics: {', '.join(topics)}" if topics else None,
                f"Tickers: {', '.join(tickers)}" if tickers else None,
                (
                    f"Sentiment: {entry.get('overall_sentiment_label')}"
                    if entry.get("overall_sentiment_label")
                    else None
                ),
            ]
            if part
        )

        return RawItemInput(
            source_name=self.source_name,
            external_id=str(url),
            url=str(url),
            raw_title=str(title),
            raw_text=raw_text,
            raw_author=", ".join(authors) if authors else source,
            raw_metadata={
                "source": source,
                "source_domain": entry.get("source_domain"),
                "category_within_source": entry.get("category_within_source"),
                "topics": topics,
                "ticker_sentiment": ticker_sentiment,
                "overall_sentiment_score": entry.get("overall_sentiment_score"),
                "overall_sentiment_label": entry.get("overall_sentiment_label"),
                "time_published": entry.get("time_published"),
            },
            published_at=published_at,
        )

    def _topic_names(self, topics: list[dict[str, Any]]) -> list[str]:
        return [
            str(topic.get("topic")).strip()
            for topic in topics
            if str(topic.get("topic") or "").strip()
        ]

    def _ticker_sentiment(self, values: list[dict[str, Any]]) -> list[dict[str, str | None]]:
        return [
            {
                "ticker": str(item.get("ticker")).strip().upper(),
                "relevance_score": item.get("relevance_score"),
                "sentiment_label": item.get("ticker_sentiment_label"),
            }
            for item in values
            if str(item.get("ticker") or "").strip()
        ]

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=UTC)
