from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.llm.kimi_coding import KimiCodingClient, KimiCodingError
from app.schemas.llm import SmokeTestRequest, SmokeTestResponse

router = APIRouter()


@router.post("/smoke-test", response_model=SmokeTestResponse)
async def smoke_test(request: SmokeTestRequest) -> SmokeTestResponse:
    settings = get_settings()
    if not settings.moonshot_api_key:
        raise HTTPException(status_code=400, detail="MOONSHOT_API_KEY is not configured.")

    client = KimiCodingClient(settings=settings)
    try:
        result = await client.create_message(
            prompt=request.prompt,
            max_tokens=request.max_tokens,
        )
    except KimiCodingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SmokeTestResponse(
        model=result.model,
        text=result.text,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        total_tokens=result.total_tokens,
    )
