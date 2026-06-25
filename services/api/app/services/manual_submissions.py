from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import NormalizedItem, RawItem, Source
from app.schemas.feed import FeedItem
from app.schemas.manual_submissions import ManualSubmissionRequest
from app.services.feed_actions import get_action, serialize_feed_item
from app.services.ingestion import compute_content_hash, get_or_create_source, normalize_item
from app.sources.base import RawItemInput


def create_manual_submission(db: Session, request: ManualSubmissionRequest) -> FeedItem:
    source = get_or_create_source(
        db,
        name=request.source_name,
        source_type="manual",
        access_method="manual_submission",
        base_url="",
        auth_required=False,
        rate_limit="User submitted.",
        polling_interval="Manual only.",
        enabled=True,
        priority=5,
        terms_notes="Stores user-provided URL, title, and optional excerpt.",
    )
    raw = create_raw_manual_item(db=db, source=source, request=request)
    if raw.normalized_item:
        return serialize_feed_item(raw.normalized_item, get_action(db, raw.normalized_item.id))

    normalized = normalize_item(raw=raw, source=source) or create_manual_normalized_item(
        raw=raw,
        source=source,
    )
    db.add(normalized)
    db.commit()
    db.refresh(normalized)
    return serialize_feed_item(normalized)


def create_raw_manual_item(
    db: Session,
    source: Source,
    request: ManualSubmissionRequest,
) -> RawItem:
    raw_input = RawItemInput(
        source_name=source.name,
        external_id=str(request.url),
        url=str(request.url),
        raw_title=request.title,
        raw_text=request.text,
        raw_author=None,
        raw_metadata={"submission_type": "manual"},
        published_at=datetime.now(UTC),
    )
    content_hash = compute_content_hash(raw_input)

    existing = db.query(RawItem).filter(RawItem.content_hash == content_hash).one_or_none()
    if existing:
        return existing

    raw = RawItem(
        source_id=source.id,
        external_id=raw_input.external_id,
        url=raw_input.url,
        raw_title=raw_input.raw_title,
        raw_text=raw_input.raw_text,
        raw_author=raw_input.raw_author,
        raw_metadata=raw_input.raw_metadata,
        content_hash=content_hash,
        published_at=raw_input.published_at,
    )
    db.add(raw)
    db.flush()
    return raw


def create_manual_normalized_item(raw: RawItem, source: Source) -> NormalizedItem:
    return NormalizedItem(
        raw_item_id=raw.id,
        title=raw.raw_title,
        url=raw.url,
        source_name=source.name,
        author=raw.raw_author,
        language="en",
        published_at=raw.published_at,
        text=raw.raw_text,
        category="manual_submission",
        subcategory="user_submitted_url",
        tickers=[],
        companies=[],
        products=[],
        topics=[],
        sentiment="neutral",
        relevance_score=0.3,
        importance_score=0.3,
        novelty_score=1.0,
        source_quality_score=0.6,
        stock_impact_score=0,
        summary_short=f"Manual submission: {raw.raw_title}",
        why_it_matters="This item was manually submitted for review.",
    )
