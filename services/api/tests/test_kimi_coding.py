from app.core.config import Settings
from app.llm.kimi_coding import KimiCodingClient


def test_parse_message_response_extracts_text_and_usage() -> None:
    client = KimiCodingClient(
        settings=Settings(
            MOONSHOT_API_KEY="test-key",
            MOONSHOT_BASE_URL="https://api.kimi.com/coding/v1",
            MOONSHOT_MODEL="kimi-for-coding",
        )
    )

    result = client._parse_message_response(
        {
            "model": "kimi-for-coding",
            "content": [{"type": "text", "text": "OK."}],
            "usage": {
                "input_tokens": 14,
                "output_tokens": 3,
                "total_tokens": 17,
            },
        }
    )

    assert result.model == "kimi-for-coding"
    assert result.text == "OK."
    assert result.input_tokens == 14
    assert result.output_tokens == 3
    assert result.total_tokens == 17
