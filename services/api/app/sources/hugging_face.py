from datetime import UTC, datetime
from typing import Any

import httpx

from app.sources.base import FetchCursor, FetchResult, RawItemInput, SourceConnector


class HuggingFaceConnector(SourceConnector):
    source_name = "Hugging Face"
    source_type = "model_hub"

    def __init__(self, limit: int = 25) -> None:
        self.limit = limit
        self.base_url = "https://huggingface.co"

    async def fetch(self, cursor: FetchCursor) -> FetchResult:
        params = {
            "filter": "text-generation",
            "sort": "lastModified",
            "direction": "-1",
            "limit": self.limit,
            "full": "true",
        }
        headers = {"User-Agent": "SignalLens/0.1"}
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            response = await client.get(f"{self.base_url}/api/models", params=params)
            response.raise_for_status()

        items = [
            raw_item
            for model in response.json()[: self.limit]
            if (raw_item := self._model_to_raw_item(model))
        ]
        return FetchResult(
            items=items,
            next_cursor=FetchCursor(metadata={"last_limit": self.limit}),
        )

    def _model_to_raw_item(self, model: dict[str, Any]) -> RawItemInput | None:
        model_id = model.get("modelId") or model.get("id")
        if not model_id:
            return None

        tags = [str(tag) for tag in model.get("tags", []) if str(tag).strip()]
        pipeline_tag = model.get("pipeline_tag")
        downloads = model.get("downloads")
        likes = model.get("likes")
        last_modified = self._parse_datetime(model.get("lastModified"))
        author = str(model_id).split("/")[0] if "/" in str(model_id) else None
        raw_title = f"{model_id}: Hugging Face model update"
        raw_text = " ".join(
            part
            for part in [
                f"Pipeline: {pipeline_tag}" if pipeline_tag else None,
                f"Tags: {', '.join(tags)}" if tags else None,
                f"Downloads: {downloads}" if downloads is not None else None,
                f"Likes: {likes}" if likes is not None else None,
            ]
            if part
        )

        return RawItemInput(
            source_name=self.source_name,
            external_id=str(model_id),
            url=f"{self.base_url}/{model_id}",
            raw_title=raw_title,
            raw_text=raw_text,
            raw_author=author,
            raw_metadata={
                "model_id": model_id,
                "pipeline_tag": pipeline_tag,
                "tags": tags,
                "downloads": downloads,
                "likes": likes,
                "last_modified": model.get("lastModified"),
                "library_name": model.get("library_name"),
            },
            published_at=last_modified,
        )

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
