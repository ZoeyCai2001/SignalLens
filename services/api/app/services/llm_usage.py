from sqlalchemy.orm import Session

from app.db.models import LlmUsageEvent
from app.llm.kimi_coding import KimiMessageResult
from app.services.feed_actions import LOCAL_USER_ID


def record_llm_usage(
    db: Session,
    operation: str,
    provider: str,
    result: KimiMessageResult,
    item_id: int | None = None,
) -> LlmUsageEvent:
    event = LlmUsageEvent(
        user_id=LOCAL_USER_ID,
        operation=operation,
        provider=provider,
        model=result.model,
        item_id=item_id,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        total_tokens=result.total_tokens,
    )
    db.add(event)
    return event
