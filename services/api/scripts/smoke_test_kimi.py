import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.llm.kimi_coding import KimiCodingClient


async def main() -> None:
    settings = get_settings()
    client = KimiCodingClient(settings=settings)
    result = await client.create_message("Reply with only OK.", max_tokens=8)
    print(
        {
            "model": result.model,
            "text": result.text,
            "total_tokens": result.total_tokens,
        }
    )


if __name__ == "__main__":
    asyncio.run(main())
