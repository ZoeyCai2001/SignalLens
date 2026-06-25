from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from sqlalchemy.orm import Session

from app.db.models import NormalizedItem, RawItem, Source, SourceRun
from app.services.scoring import (
    detect_tickers,
    detect_topics,
    importance_score,
    is_ai_relevant,
    relevance_score,
)
from app.sources.arxiv import ArxivConnector
from app.sources.base import FetchCursor, RawItemInput
from app.sources.github import GitHubConnector
from app.sources.hacker_news import HackerNewsConnector
from app.sources.hugging_face import HuggingFaceConnector


@dataclass(frozen=True)
class IngestionResult:
    source_name: str
    status: str
    items_fetched: int
    items_stored: int
    error_message: str | None = None


async def run_hacker_news_ingestion(db: Session, limit: int = 30) -> IngestionResult:
    connector = HackerNewsConnector(limit=limit)
    source = get_or_create_source(
        db,
        name="Hacker News",
        source_type="community",
        access_method="official_api",
        base_url="https://hacker-news.firebaseio.com/v0",
        auth_required=False,
        rate_limit="Public Firebase API; keep polling conservative.",
        polling_interval="30 minutes",
        enabled=True,
        priority=20,
        terms_notes="Uses public Hacker News Firebase API metadata and URLs.",
    )
    return await run_connector_ingestion(db=db, connector=connector, source=source)


async def run_arxiv_ingestion(db: Session, limit: int = 25) -> IngestionResult:
    connector = ArxivConnector(limit=limit)
    source = get_or_create_source(
        db,
        name="arXiv",
        source_type="research",
        access_method="official_api",
        base_url="https://export.arxiv.org/api/query",
        auth_required=False,
        rate_limit="Public API; keep requests conservative and cache results.",
        polling_interval="6 hours",
        enabled=True,
        priority=10,
        terms_notes="Uses arXiv Atom API metadata and abstracts.",
    )
    return await run_connector_ingestion(db=db, connector=connector, source=source)


async def run_github_ingestion(db: Session, limit: int = 25) -> IngestionResult:
    connector = GitHubConnector(limit=limit)
    source = get_or_create_source(
        db,
        name="GitHub",
        source_type="developer",
        access_method="official_api",
        base_url="https://api.github.com/search/repositories",
        auth_required=False,
        rate_limit="Unauthenticated public API; keep polling conservative.",
        polling_interval="6 hours",
        enabled=True,
        priority=15,
        terms_notes="Uses GitHub public repository search metadata only.",
    )
    return await run_connector_ingestion(db=db, connector=connector, source=source)


async def run_hugging_face_ingestion(db: Session, limit: int = 25) -> IngestionResult:
    connector = HuggingFaceConnector(limit=limit)
    source = get_or_create_source(
        db,
        name="Hugging Face",
        source_type="model_hub",
        access_method="official_api",
        base_url="https://huggingface.co/api/models",
        auth_required=False,
        rate_limit="Public API; keep polling conservative.",
        polling_interval="6 hours",
        enabled=True,
        priority=12,
        terms_notes="Uses Hugging Face public model metadata only.",
    )
    return await run_connector_ingestion(db=db, connector=connector, source=source)


async def run_connector_ingestion(
    db: Session,
    connector: HackerNewsConnector | ArxivConnector | GitHubConnector | HuggingFaceConnector,
    source: Source,
) -> IngestionResult:
    run = SourceRun(source_id=source.id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        fetch_result = await connector.fetch(FetchCursor())
        stored_count = store_raw_items(db, source=source, items=fetch_result.items)
        run.status = "success"
        run.items_fetched = len(fetch_result.items)
        run.items_stored = stored_count
        run.finished_at = datetime.now(UTC)
        db.commit()
        return IngestionResult(
            source_name=source.name,
            status=run.status,
            items_fetched=run.items_fetched,
            items_stored=run.items_stored,
        )
    except Exception as exc:
        db.rollback()
        run.status = "failed"
        run.error_message = str(exc)
        run.finished_at = datetime.now(UTC)
        db.add(run)
        db.commit()
        return IngestionResult(
            source_name=source.name,
            status=run.status,
            items_fetched=run.items_fetched,
            items_stored=run.items_stored,
            error_message=run.error_message,
        )


def get_or_create_source(
    db: Session,
    name: str,
    source_type: str,
    access_method: str,
    base_url: str,
    auth_required: bool,
    rate_limit: str,
    polling_interval: str,
    enabled: bool,
    priority: int,
    terms_notes: str,
) -> Source:
    source = db.query(Source).filter(Source.name == name).one_or_none()
    if source:
        return source

    source = Source(
        name=name,
        type=source_type,
        access_method=access_method,
        base_url=base_url,
        auth_required=auth_required,
        rate_limit=rate_limit,
        polling_interval=polling_interval,
        enabled=enabled,
        priority=priority,
        terms_notes=terms_notes,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def store_raw_items(db: Session, source: Source, items: list[RawItemInput]) -> int:
    stored_count = 0
    for item in items:
        content_hash = compute_content_hash(item)
        if raw_item_exists(
            db,
            source_id=source.id,
            external_id=item.external_id,
            content_hash=content_hash,
        ):
            continue

        raw = RawItem(
            source_id=source.id,
            external_id=item.external_id,
            url=item.url,
            raw_title=item.raw_title,
            raw_text=item.raw_text,
            raw_author=item.raw_author,
            raw_metadata=item.raw_metadata,
            content_hash=content_hash,
            published_at=item.published_at,
        )
        db.add(raw)
        db.flush()

        normalized = normalize_item(raw=raw, source=source)
        if normalized:
            db.add(normalized)
            stored_count += 1

    db.commit()
    return stored_count


def raw_item_exists(
    db: Session,
    source_id: int,
    external_id: str | None,
    content_hash: str,
) -> bool:
    query = db.query(RawItem).filter(RawItem.content_hash == content_hash)
    if db.query(query.exists()).scalar():
        return True
    if external_id:
        external_query = db.query(RawItem).filter(
            RawItem.source_id == source_id,
            RawItem.external_id == external_id,
        )
        return bool(db.query(external_query.exists()).scalar())
    return False


def compute_content_hash(item: RawItemInput) -> str:
    hash_input = "|".join(
        [
            item.source_name,
            item.external_id or "",
            item.url,
            item.raw_title,
            item.raw_text or "",
        ]
    )
    return sha256(hash_input.encode("utf-8")).hexdigest()


def normalize_item(raw: RawItem, source: Source) -> NormalizedItem | None:
    combined_text = " ".join(part for part in [raw.raw_title, raw.raw_text or ""] if part)
    if not is_ai_relevant(combined_text):
        return None

    topics = detect_topics(combined_text)
    tickers = detect_tickers(combined_text)
    source_quality = 0.75
    relevance = relevance_score(combined_text)
    importance = importance_score(source_quality_score=source_quality, text=combined_text)

    if source.name == "arXiv":
        category = "research"
        subcategory = "paper"
        summary_prefix = "arXiv paper"
        why_it_matters = (
            "This research item matched the AI relevance prefilter from arXiv metadata."
        )
    elif source.name == "GitHub":
        category = "technical_trend"
        subcategory = "open_source_project"
        summary_prefix = "GitHub repository"
        why_it_matters = (
            "This repository matched the AI relevance prefilter from GitHub metadata."
        )
    elif source.name == "Hugging Face":
        category = "research"
        subcategory = "model_release"
        summary_prefix = "Hugging Face model"
        why_it_matters = (
            "This model metadata matched the AI relevance prefilter from Hugging Face."
        )
    elif source.type == "manual":
        category = "manual_submission"
        subcategory = "user_submitted_url"
        summary_prefix = "Manual submission"
        why_it_matters = "This user-submitted item matched the AI relevance prefilter."
    else:
        category = "technical_trend"
        subcategory = "community_discussion"
        summary_prefix = "Hacker News discussion"
        why_it_matters = (
            "This item matched the AI relevance prefilter from a developer community source."
        )

    return NormalizedItem(
        raw_item_id=raw.id,
        title=raw.raw_title,
        url=raw.url,
        source_name=source.name,
        author=raw.raw_author,
        language="en",
        published_at=raw.published_at,
        text=raw.raw_text,
        category=category,
        subcategory=subcategory,
        tickers=tickers,
        companies=[],
        products=[],
        topics=topics,
        sentiment="neutral",
        relevance_score=relevance,
        importance_score=importance,
        novelty_score=1.0,
        source_quality_score=source_quality,
        stock_impact_score=0.2 if tickers else 0,
        summary_short=f"{summary_prefix}: {raw.raw_title}",
        why_it_matters=why_it_matters,
    )
