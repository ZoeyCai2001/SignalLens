import re
from datetime import UTC, datetime
from urllib.parse import unquote, urlparse

from sqlalchemy.orm import Session

from app.db.models import NormalizedItem, RawItem, Source
from app.schemas.feed import FeedItem
from app.schemas.manual_submissions import ManualSubmissionRequest
from app.services.feed_actions import get_action, serialize_feed_item
from app.services.ingestion import (
    compute_content_hash,
    detect_language,
    get_or_create_source,
    normalize_item,
)
from app.services.scoring import (
    detect_companies,
    detect_products,
    detect_tickers,
    detect_topics,
    importance_score,
    is_ai_relevant,
    relevance_score,
)
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
        enrich_manual_normalized_item(raw.normalized_item, raw)
        db.add(raw.normalized_item)
        db.commit()
        db.refresh(raw.normalized_item)
        return serialize_feed_item(raw.normalized_item, get_action(db, raw.normalized_item.id))

    normalized = normalize_item(raw=raw, source=source) or create_manual_normalized_item(
        raw=raw,
        source=source,
    )
    enrich_manual_normalized_item(normalized, raw)
    db.add(normalized)
    db.commit()
    db.refresh(normalized)
    return serialize_feed_item(normalized)


def create_raw_manual_item(
    db: Session,
    source: Source,
    request: ManualSubmissionRequest,
) -> RawItem:
    title = resolve_manual_title(request)
    raw_input = RawItemInput(
        source_name=source.name,
        external_id=str(request.url),
        url=str(request.url),
        raw_title=title,
        raw_text=request.text,
        raw_author=None,
        raw_metadata={
            "submission_type": "manual",
            "title_was_inferred": request.title is None,
        },
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


def resolve_manual_title(request: ManualSubmissionRequest) -> str:
    if request.title:
        return request.title

    sentence = first_sentence(request.text or "", limit=140)
    if sentence:
        return sentence

    parsed = urlparse(str(request.url))
    path_title = unquote(parsed.path.rstrip("/").rsplit("/", 1)[-1]).replace("-", " ").strip()
    if path_title:
        return f"{parsed.netloc}: {path_title[:140]}"
    return parsed.netloc or "Manual URL submission"


def create_manual_normalized_item(raw: RawItem, source: Source) -> NormalizedItem:
    combined_text = combined_manual_text(raw)
    return NormalizedItem(
        raw_item_id=raw.id,
        title=raw.raw_title,
        url=raw.url,
        source_name=source.name,
        author=raw.raw_author,
        language=detect_language(combined_text),
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
        classification_confidence=0.5,
        importance_score=0.3,
        novelty_score=1.0,
        source_quality_score=0.6,
        stock_impact_score=0,
        summary_short=f"Manual submission: {raw.raw_title}",
        why_it_matters="This item was manually submitted for review.",
    )


def enrich_manual_normalized_item(item: NormalizedItem, raw: RawItem) -> None:
    combined_text = combined_manual_text(raw)
    if not is_ai_relevant(combined_text):
        return

    category, subcategory = infer_manual_category(combined_text)
    topics = detect_topics(combined_text)
    tickers = detect_tickers(combined_text)
    companies = detect_companies(combined_text)
    products = detect_manual_products(raw.raw_title, combined_text)
    source_quality = 0.65

    item.language = detect_language(combined_text)
    item.category = category
    item.subcategory = subcategory
    item.tickers = tickers
    item.companies = companies
    item.products = products
    item.topics = topics
    item.classification_confidence = max(item.classification_confidence or 0, 0.65)
    item.relevance_score = max(item.relevance_score or 0, relevance_score(combined_text))
    item.importance_score = max(
        item.importance_score or 0,
        importance_score(source_quality_score=source_quality, text=combined_text),
    )
    item.source_quality_score = max(item.source_quality_score or 0, source_quality)
    item.stock_impact_score = 0.35 if tickers and category == "stock_company_event" else 0
    item.summary_short = build_manual_summary(raw)
    item.why_it_matters = build_manual_why_it_matters(category=category, tickers=tickers)


def combined_manual_text(raw: RawItem) -> str:
    return " ".join(part for part in [raw.raw_title, raw.raw_text or ""] if part)


def infer_manual_category(text: str) -> tuple[str, str]:
    lowered = text.lower()
    if detect_tickers(text) or re.search(
        r"\b(earnings|guidance|semiconductor|chip|data center|capex|revenue|stock)\b",
        lowered,
    ):
        return "stock_company_event", "manual_stock_signal"
    if re.search(r"\b(paper|research|arxiv|benchmark|study|evaluation)\b", lowered):
        return "research", "manual_research"
    if re.search(r"\b(chinese|xiaohongshu|wechat|social trend|viral)\b", lowered) or any(
        term in text for term in ["中文", "小红书", "微信"]
    ):
        return "social_trend", "manual_social_signal"
    if re.search(r"\b(product|launch|app|tool|workflow|browser|photo|video)\b", lowered):
        return "product", "manual_product"
    return "technical_trend", "manual_ai_signal"


def detect_manual_products(title: str, text: str) -> list[str]:
    products: list[str] = []
    if ":" in title:
        candidate = title.split(":", 1)[0].strip()
        if 2 <= len(candidate) <= 60:
            products.append(candidate)

    for product in detect_products(text):
        if product not in products:
            products.append(product)
    return products[:6]


def build_manual_summary(raw: RawItem) -> str:
    excerpt = first_sentence(raw.raw_text or "")
    if excerpt:
        return f"Manual submission: {raw.raw_title} - {excerpt}"
    return f"Manual submission: {raw.raw_title}"


def first_sentence(text: str, limit: int = 220) -> str | None:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return None
    match = re.search(r"(.+?[.!?。！？])", cleaned)
    sentence = match.group(1) if match else cleaned
    return sentence[:limit].rstrip()


def build_manual_why_it_matters(category: str, tickers: list[str]) -> str:
    if category == "stock_company_event" and tickers:
        return f"This user-submitted item matched watched AI tickers: {', '.join(tickers)}."
    if category == "product":
        return "This user-submitted item appears to describe an AI product or workflow."
    if category == "research":
        return "This user-submitted item appears to be AI research or evaluation material."
    if category == "social_trend":
        return "This user-submitted item appears to be an AI social trend signal."
    return "This user-submitted item matched AI relevance signals for technical review."
