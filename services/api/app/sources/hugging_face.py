from datetime import UTC, datetime
from typing import Any

import httpx

from app.sources.base import FetchCursor, FetchResult, RawItemInput, SourceConnector


HUGGING_FACE_SURFACES = ("model", "dataset", "space")


class HuggingFaceConnector(SourceConnector):
    source_name = "Hugging Face"
    source_type = "model_hub"

    def __init__(self, limit: int = 25) -> None:
        self.limit = limit
        self.base_url = "https://huggingface.co"

    async def fetch(self, cursor: FetchCursor) -> FetchResult:
        headers = {"User-Agent": "SignalLens/0.1"}
        per_surface_limit = max(1, self.limit // len(HUGGING_FACE_SURFACES))
        items: list[RawItemInput] = []

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            model_payload = await self._get_json(
                client,
                "/api/models",
                {
                    "filter": "text-generation",
                    "sort": "lastModified",
                    "direction": "-1",
                    "limit": per_surface_limit,
                    "full": "true",
                },
            )
            dataset_payload = await self._get_json(
                client,
                "/api/datasets",
                {
                    "sort": "lastModified",
                    "direction": "-1",
                    "limit": per_surface_limit,
                    "full": "true",
                },
            )
            space_payload = await self._get_json(
                client,
                "/api/spaces",
                {
                    "sort": "lastModified",
                    "direction": "-1",
                    "limit": per_surface_limit,
                    "full": "true",
                },
            )

        items.extend(
            raw_item
            for model in as_payload_list(model_payload)[:per_surface_limit]
            if (raw_item := self._model_to_raw_item(model))
        )
        items.extend(
            raw_item
            for dataset in as_payload_list(dataset_payload)[:per_surface_limit]
            if (raw_item := self._dataset_to_raw_item(dataset))
        )
        items.extend(
            raw_item
            for space in as_payload_list(space_payload)[:per_surface_limit]
            if (raw_item := self._space_to_raw_item(space))
        )

        return FetchResult(
            items=items[: self.limit],
            next_cursor=FetchCursor(metadata={"last_limit": self.limit}),
        )

    async def _get_json(
        self,
        client: httpx.AsyncClient,
        path: str,
        params: dict[str, str | int],
    ) -> Any:
        response = await client.get(f"{self.base_url}{path}", params=params)
        response.raise_for_status()
        return response.json()

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
                "hf_kind": "model",
                "pipeline_tag": pipeline_tag,
                "tags": tags,
                "downloads": downloads,
                "likes": likes,
                "last_modified": model.get("lastModified"),
                "library_name": model.get("library_name"),
            },
            published_at=last_modified,
        )

    def _dataset_to_raw_item(self, dataset: dict[str, Any]) -> RawItemInput | None:
        dataset_id = dataset.get("id") or dataset.get("datasetId")
        if not dataset_id:
            return None

        tags = [str(tag) for tag in dataset.get("tags", []) if str(tag).strip()]
        downloads = dataset.get("downloads")
        likes = dataset.get("likes")
        last_modified = self._parse_datetime(dataset.get("lastModified"))
        author = str(dataset_id).split("/")[0] if "/" in str(dataset_id) else None
        raw_title = f"{dataset_id}: Hugging Face dataset update"
        raw_text = " ".join(
            part
            for part in [
                f"Dataset: {dataset_id}",
                f"Tags: {', '.join(tags)}" if tags else None,
                f"Downloads: {downloads}" if downloads is not None else None,
                f"Likes: {likes}" if likes is not None else None,
            ]
            if part
        )

        return RawItemInput(
            source_name=self.source_name,
            external_id=f"dataset:{dataset_id}",
            url=f"{self.base_url}/datasets/{dataset_id}",
            raw_title=raw_title,
            raw_text=raw_text,
            raw_author=author,
            raw_metadata={
                "dataset_id": dataset_id,
                "hf_kind": "dataset",
                "tags": tags,
                "downloads": downloads,
                "likes": likes,
                "last_modified": dataset.get("lastModified"),
            },
            published_at=last_modified,
        )

    def _space_to_raw_item(self, space: dict[str, Any]) -> RawItemInput | None:
        space_id = space.get("id") or space.get("name")
        if not space_id:
            return None

        tags = [str(tag) for tag in space.get("tags", []) if str(tag).strip()]
        likes = space.get("likes")
        sdk = space.get("sdk")
        last_modified = self._parse_datetime(space.get("lastModified"))
        author = str(space_id).split("/")[0] if "/" in str(space_id) else None
        raw_title = f"{space_id}: Hugging Face Space update"
        raw_text = " ".join(
            part
            for part in [
                f"Space demo: {space_id}",
                f"SDK: {sdk}" if sdk else None,
                f"Tags: {', '.join(tags)}" if tags else None,
                f"Likes: {likes}" if likes is not None else None,
            ]
            if part
        )

        return RawItemInput(
            source_name=self.source_name,
            external_id=f"space:{space_id}",
            url=f"{self.base_url}/spaces/{space_id}",
            raw_title=raw_title,
            raw_text=raw_text,
            raw_author=author,
            raw_metadata={
                "space_id": space_id,
                "hf_kind": "space",
                "sdk": sdk,
                "tags": tags,
                "likes": likes,
                "last_modified": space.get("lastModified"),
            },
            published_at=last_modified,
        )

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def as_payload_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        items = payload.get("items") or payload.get("results") or []
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    return []
