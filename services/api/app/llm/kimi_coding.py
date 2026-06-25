from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import Settings


class KimiCodingError(RuntimeError):
    """Raised when the Kimi Coding API returns an unusable response."""


@dataclass(frozen=True)
class KimiMessageResult:
    model: str
    text: str
    input_tokens: int
    output_tokens: int
    total_tokens: int


class KimiCodingClient:
    """Client for Kimi Coding's Anthropic-style Messages API."""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.moonshot_api_key
        self._base_url = settings.moonshot_base_url.rstrip("/")
        self._model = settings.moonshot_model

    async def create_message(self, prompt: str, max_tokens: int = 64) -> KimiMessageResult:
        if not self._api_key:
            raise KimiCodingError("MOONSHOT_API_KEY is not configured.")

        payload = {
            "model": self._model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._base_url}/messages",
                headers=headers,
                json=payload,
            )

        if response.status_code >= 400:
            raise KimiCodingError(
                f"Kimi Coding API error {response.status_code}: {response.text}"
            )

        data = response.json()
        return self._parse_message_response(data)

    def _parse_message_response(self, data: dict[str, Any]) -> KimiMessageResult:
        content = data.get("content", [])
        text_parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        text = "\n".join(part for part in text_parts if part).strip()
        if not text:
            raise KimiCodingError("Kimi Coding API response did not include text content.")

        usage = data.get("usage", {})
        input_tokens = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)

        return KimiMessageResult(
            model=str(data.get("model") or self._model),
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )
