from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession
from app.core.config import get_settings
from app.schemas.llm import (
    FeedProcessingRequest,
    FeedProcessingResponse,
    SmokeTestRequest,
    SmokeTestResponse,
)
from app.services.feed_actions import normalize_feed_module_filter
from app.services.llm_processing import process_feed_with_llm
from app.services.preferences import get_user_preferences

router = APIRouter()


@router.post("/smoke-test", response_model=SmokeTestResponse)
async def smoke_test(request: SmokeTestRequest) -> SmokeTestResponse:
    settings = get_settings()
    if not settings.moonshot_api_key:
        raise HTTPException(status_code=400, detail="MOONSHOT_API_KEY is not configured.")

    from app.llm.kimi_coding import KimiCodingClient, KimiCodingError

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


@router.post("/process-feed", response_model=FeedProcessingResponse)
async def process_feed_items(
    request: FeedProcessingRequest,
    db: DbSession,
) -> FeedProcessingResponse:
    settings = get_settings()
    if not request.dry_run and not settings.moonshot_api_key:
        raise HTTPException(status_code=400, detail="MOONSHOT_API_KEY is not configured.")
    if not request.summarize and not request.classify:
        raise HTTPException(status_code=400, detail="Enable summarize or classify.")
    if request.module and not normalize_feed_module_filter(request.module):
        raise HTTPException(
            status_code=400,
            detail="Unsupported feed module. Use trends, research, products, stocks, or chinese.",
        )

    preferences = get_user_preferences(db)
    return await process_feed_with_llm(
        db=db,
        settings=settings,
        limit=request.limit,
        summarize=request.summarize,
        classify=request.classify,
        dry_run=request.dry_run,
        skip_summarized=request.skip_summarized,
        skip_classified=request.skip_classified,
        min_classification_confidence=request.min_classification_confidence,
        blocked_sources=preferences.blocked_sources,
        module=request.module,
    )
