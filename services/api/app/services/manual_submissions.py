import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import unquote, urlparse

from sqlalchemy.orm import Session

from app.db.models import NormalizedItem, RawItem, Source
from app.schemas.feed import FeedItem
from app.schemas.manual_submissions import ManualSubmissionRequest
from app.services.feed_actions import (
    get_action,
    get_or_create_action,
    normalize_manual_tags,
    serialize_feed_item,
    update_item_action,
)
from app.services.ingestion import (
    canonical_ingestion_url,
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
    infer_product_use_case,
    is_ai_relevant,
    relevance_score,
)
from app.sources.base import RawItemInput


@dataclass(frozen=True)
class ManualSubmissionSaveResult:
    item: FeedItem
    created: bool
    updated_existing: bool


@dataclass(frozen=True)
class RawManualItemSaveResult:
    raw: RawItem
    created: bool
    updated_existing: bool


def create_manual_submission(db: Session, request: ManualSubmissionRequest) -> FeedItem:
    return create_manual_submission_result(db=db, request=request).item


def create_manual_submission_result(
    db: Session,
    request: ManualSubmissionRequest,
) -> ManualSubmissionSaveResult:
    source_name = resolve_manual_source_name(request)
    source = get_or_create_source(
        db,
        name=source_name,
        source_type="manual",
        access_method="manual_submission",
        base_url=source_base_url_from_request(request),
        auth_required=False,
        rate_limit="User submitted.",
        polling_interval="Manual only.",
        enabled=True,
        priority=5,
        terms_notes="Stores user-provided URL, title, and optional excerpt.",
    )
    raw_result = save_raw_manual_item(db=db, source=source, request=request)
    raw = raw_result.raw
    if raw.normalized_item:
        reset_manual_normalized_item(raw.normalized_item, raw, source)
        enrich_manual_normalized_item(raw.normalized_item, raw)
        db.add(raw.normalized_item)
        db.commit()
        db.refresh(raw.normalized_item)
        return ManualSubmissionSaveResult(
            item=serialize_manual_item_with_requested_actions(
                db=db,
                item=raw.normalized_item,
                request=request,
            ),
            created=raw_result.created,
            updated_existing=raw_result.updated_existing,
        )

    normalized = normalize_item(raw=raw, source=source) or create_manual_normalized_item(
        raw=raw,
        source=source,
    )
    enrich_manual_normalized_item(normalized, raw)
    db.add(normalized)
    db.commit()
    db.refresh(normalized)
    return ManualSubmissionSaveResult(
        item=serialize_manual_item_with_requested_actions(
            db=db,
            item=normalized,
            request=request,
        ),
        created=raw_result.created,
        updated_existing=raw_result.updated_existing,
    )


def serialize_manual_item_with_requested_actions(
    db: Session,
    item: NormalizedItem,
    request: ManualSubmissionRequest,
) -> FeedItem:
    note_was_supplied = "personal_note" in request.model_fields_set
    tags_were_supplied = "manual_tags" in request.model_fields_set
    if request.save_item and not note_was_supplied and not tags_were_supplied:
        return update_item_action(db=db, item=item, action_name="save")

    if request.save_item or note_was_supplied or tags_were_supplied:
        action = get_or_create_action(db, item.id)
        if request.save_item:
            action.is_saved = True
        if note_was_supplied:
            normalized_note = str(request.personal_note or "").strip()
            action.personal_note = normalized_note or None
        if tags_were_supplied:
            action.manual_tags = normalize_manual_tags(request.manual_tags)
        db.add(action)
        db.commit()
        db.refresh(action)
        return serialize_feed_item(item, action)

    return serialize_feed_item(item, get_action(db, item.id))


def create_raw_manual_item(
    db: Session,
    source: Source,
    request: ManualSubmissionRequest,
) -> RawItem:
    return save_raw_manual_item(db=db, source=source, request=request).raw


def save_raw_manual_item(
    db: Session,
    source: Source,
    request: ManualSubmissionRequest,
) -> RawManualItemSaveResult:
    title = resolve_manual_title(request)
    canonical_url = canonical_ingestion_url(str(request.url))
    raw_input = RawItemInput(
        source_name=source.name,
        external_id=canonical_url,
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

    existing = find_existing_manual_raw_item(
        db=db,
        source=source,
        external_id=raw_input.external_id,
        content_hash=content_hash,
    )
    if existing:
        update_existing_manual_raw_item(existing, raw_input=raw_input, content_hash=content_hash)
        db.add(existing)
        db.flush()
        return RawManualItemSaveResult(raw=existing, created=False, updated_existing=True)

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
    return RawManualItemSaveResult(raw=raw, created=True, updated_existing=False)


def find_existing_manual_raw_item(
    db: Session,
    source: Source,
    external_id: str | None,
    content_hash: str,
) -> RawItem | None:
    existing = db.query(RawItem).filter(RawItem.content_hash == content_hash).one_or_none()
    if existing is not None:
        return existing
    if not external_id:
        return None
    return (
        db.query(RawItem)
        .join(Source, Source.id == RawItem.source_id)
        .filter(
            Source.type == "manual",
            RawItem.external_id == external_id,
        )
        .one_or_none()
    )


def update_existing_manual_raw_item(
    raw: RawItem,
    raw_input: RawItemInput,
    content_hash: str,
) -> None:
    raw.url = raw_input.url
    raw.raw_title = raw_input.raw_title
    raw.raw_text = raw_input.raw_text
    raw.raw_author = raw_input.raw_author
    raw.raw_metadata = {
        **(raw.raw_metadata or {}),
        **raw_input.raw_metadata,
        "resubmitted_at": raw_input.published_at.isoformat() if raw_input.published_at else None,
    }
    raw.content_hash = content_hash
    raw.published_at = raw_input.published_at
    if raw.normalized_item is not None:
        raw.normalized_item.title = raw_input.raw_title
        raw.normalized_item.text = raw_input.raw_text
        raw.normalized_item.summary_short = build_manual_summary(raw)


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


def resolve_manual_source_name(request: ManualSubmissionRequest) -> str:
    requested_source = request.source_name.strip()
    if requested_source and requested_source != "Manual Submission":
        return requested_source

    parsed = urlparse(str(request.url))
    host = normalized_manual_host(parsed.netloc)
    known_sources = {
        "arxiv.org": "arXiv",
        "github.com": "GitHub",
        "huggingface.co": "Hugging Face",
        "news.ycombinator.com": "Hacker News",
        "producthunt.com": "Product Hunt",
        "sec.gov": "SEC EDGAR",
        "openai.com": "OpenAI",
        "anthropic.com": "Anthropic",
        "deepmind.google": "Google DeepMind",
        "ai.meta.com": "Meta AI",
        "microsoft.com": "Microsoft",
        "nvidia.com": "NVIDIA",
    }
    if host in known_sources:
        return known_sources[host]
    registered_domain = registered_manual_domain(host)
    if registered_domain in known_sources:
        return known_sources[registered_domain]
    return readable_manual_domain(registered_domain or host) or "Manual Submission"


def source_base_url_from_request(request: ManualSubmissionRequest) -> str:
    parsed = urlparse(str(request.url))
    host = normalized_manual_host(parsed.netloc)
    return f"{parsed.scheme}://{host}" if parsed.scheme and host else ""


def normalized_manual_host(netloc: str) -> str:
    host = netloc.lower().split("@")[-1].split(":")[0].strip()
    return host[4:] if host.startswith("www.") else host


def registered_manual_domain(host: str) -> str:
    if not host:
        return ""
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])


def readable_manual_domain(domain: str) -> str:
    if not domain:
        return ""
    label = domain.split(".", 1)[0].replace("-", " ").strip()
    if not label:
        return domain
    known_uppercase = {"ai": "AI", "sec": "SEC"}
    return " ".join(known_uppercase.get(part, part.capitalize()) for part in label.split())


def create_manual_normalized_item(raw: RawItem, source: Source) -> NormalizedItem:
    item = NormalizedItem(raw_item_id=raw.id)
    reset_manual_normalized_item(item, raw, source)
    return item


def reset_manual_normalized_item(item: NormalizedItem, raw: RawItem, source: Source) -> None:
    combined_text = combined_manual_text(raw)
    item.title = raw.raw_title
    item.url = raw.url
    item.source_name = source.name
    item.author = raw.raw_author
    item.language = detect_language(combined_text)
    item.published_at = raw.published_at
    item.text = raw.raw_text
    item.category = "manual_submission"
    item.subcategory = "user_submitted_url"
    item.tickers = []
    item.companies = []
    item.products = []
    item.topics = []
    item.sentiment = "neutral"
    item.relevance_score = 0.3
    item.classification_confidence = 0.5
    item.importance_score = 0.3
    item.novelty_score = 1.0
    item.source_quality_score = 0.6
    item.stock_impact_score = 0
    item.summary_short = build_manual_summary(raw)
    item.summary_detailed = None
    item.why_it_matters = "This item was manually submitted for review."


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
        return "product", infer_product_use_case(text)
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
