import logging
import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
from hashlib import sha256
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models import (
    NormalizedItem,
    RawItem,
    Source,
    SourceRun,
    StockPricePoint,
    StockWatchlistItem,
)
from app.services.scoring import (
    TICKER_ALIASES,
    company_names_for_tickers,
    detect_companies,
    detect_products,
    detect_tickers,
    detect_topics,
    importance_score,
    infer_product_use_case,
    is_ai_relevant,
    relevance_score,
)
from app.sources.alpha_vantage import AlphaVantageDailyPriceConnector, AlphaVantageNewsConnector
from app.sources.arxiv import ArxivConnector
from app.sources.base import FetchCursor, RawItemInput, SourceConnector
from app.sources.github import GitHubConnector, parse_github_repository
from app.sources.hacker_news import HackerNewsConnector
from app.sources.hugging_face import HuggingFaceConnector
from app.sources.product_hunt import ProductHuntConnector
from app.sources.rss import DEFAULT_RSS_FEEDS, RssConnector, RssFeedSpec
from app.sources.sec_filings import SecFilingsConnector, parse_sec_forms

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestionResult:
    source_name: str
    status: str
    items_fetched: int
    items_stored: int
    error_message: str | None = None


IngestionRunner = Callable[[Session, int], Awaitable[IngestionResult]]


@dataclass(frozen=True)
class RegisteredSourceRunner:
    source_name: str
    runner: IngestionRunner
    default_limit: int


class SourceNotFoundError(ValueError):
    pass


class SourceRunnerNotFoundError(ValueError):
    pass


SOURCE_QUALITY_BY_NAME = {
    "arxiv": 0.9,
    "sec filings": 0.9,
    "alpha vantage news": 0.82,
    "github": 0.8,
    "hugging face": 0.78,
    "product hunt": 0.74,
    "selected rss feeds": 0.72,
    "hacker news": 0.7,
    "chinese rss feeds": 0.62,
    "manual submission": 0.55,
}

SOURCE_QUALITY_BY_ACCESS_METHOD = {
    "official api": 0.76,
    "official graphql api": 0.76,
    "rss": 0.65,
    "manual": 0.55,
    "manual watch": 0.55,
}

TRACKING_QUERY_PARAMS = {
    "fbclid",
    "gclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}

NEAR_DUPLICATE_TITLE_THRESHOLD = 0.92
NOVELTY_TITLE_SIMILARITY_THRESHOLD = 0.84
NOVELTY_LOOKBACK_DAYS = 7
SAME_SOURCE_FOLLOWUP_NOVELTY = 0.65
CROSS_SOURCE_CONFIRMATION_NOVELTY = 0.82
TITLE_DEDUPE_STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "in",
    "of",
    "on",
    "the",
    "to",
    "with",
}

SOURCE_QUALITY_BY_TYPE = {
    "research": 0.78,
    "finance filings": 0.84,
    "finance news": 0.76,
    "developer": 0.74,
    "github repository": 0.74,
    "model hub": 0.74,
    "community": 0.68,
    "product launch": 0.68,
    "blog": 0.66,
    "chinese social": 0.6,
    "social keyword": 0.58,
    "manual": 0.55,
}


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
        terms_notes=(
            "Uses public Hacker News Firebase API metadata, URLs, and top comment previews."
        ),
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
    settings = get_settings()
    connector = GitHubConnector(limit=limit, api_token=settings.github_token)
    source = get_or_create_source(
        db,
        name="GitHub",
        source_type="developer",
        access_method="official_api",
        base_url="https://api.github.com/search/repositories",
        auth_required=False,
        rate_limit=(
            "Authenticated public API when GITHUB_TOKEN is configured; "
            "otherwise unauthenticated low-rate search."
        ),
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


async def run_rss_ingestion(db: Session, limit: int = 25) -> IngestionResult:
    connector = RssConnector(limit=limit)
    source = get_or_create_source(
        db,
        name="Selected RSS Feeds",
        source_type="rss",
        access_method="rss",
        base_url=", ".join(feed.url for feed in DEFAULT_RSS_FEEDS),
        auth_required=False,
        rate_limit="Public RSS feeds; keep polling conservative.",
        polling_interval="6 hours",
        enabled=True,
        priority=18,
        terms_notes="Uses public RSS/Atom metadata and excerpts from selected AI sources.",
    )
    return await run_connector_ingestion(db=db, connector=connector, source=source)


async def run_chinese_rss_ingestion(
    db: Session,
    limit: int = 25,
    settings: Settings | None = None,
) -> IngestionResult:
    resolved_settings = settings or get_settings()
    feeds = parse_chinese_rss_feeds(resolved_settings.chinese_rss_feeds)
    source = get_or_create_source(
        db,
        name="Chinese RSS Feeds",
        source_type="chinese_social",
        access_method="rss",
        base_url=(
            ", ".join(feed.url for feed in feeds)
            if feeds
            else "configured via CHINESE_RSS_FEEDS"
        ),
        auth_required=False,
        rate_limit="Public RSS feeds only; keep polling conservative.",
        polling_interval="6 hours",
        enabled=True,
        priority=19,
        terms_notes=(
            "Uses user-configured public Chinese RSS/Atom feeds; "
            "no private or login-protected scraping."
        ),
    )
    if not feeds:
        return record_skipped_run(
            db=db,
            source=source,
            message="CHINESE_RSS_FEEDS is not configured.",
        )

    connector = RssConnector(
        limit=limit,
        feeds=feeds,
        source_name="Chinese RSS Feeds",
        source_type="chinese_social",
    )
    return await run_connector_ingestion(db=db, connector=connector, source=source)


async def run_product_hunt_ingestion(
    db: Session,
    limit: int = 25,
    settings: Settings | None = None,
) -> IngestionResult:
    resolved_settings = settings or get_settings()
    source = get_or_create_source(
        db,
        name="Product Hunt",
        source_type="product_launch",
        access_method="official_graphql_api",
        base_url="https://api.producthunt.com/v2/api/graphql",
        auth_required=True,
        rate_limit="Official API token required; keep polling conservative.",
        polling_interval="6 hours",
        enabled=True,
        priority=16,
        terms_notes="Uses Product Hunt API metadata for public product launches.",
    )
    if not resolved_settings.product_hunt_api_token:
        return record_skipped_run(
            db=db,
            source=source,
            message="PRODUCT_HUNT_API_TOKEN is not configured.",
        )

    connector = ProductHuntConnector(
        api_token=resolved_settings.product_hunt_api_token,
        limit=limit,
    )
    return await run_connector_ingestion(db=db, connector=connector, source=source)


async def run_alpha_vantage_news_ingestion(
    db: Session,
    limit: int = 25,
    settings: Settings | None = None,
) -> IngestionResult:
    resolved_settings = settings or get_settings()
    source = get_or_create_source(
        db,
        name="Alpha Vantage News",
        source_type="finance_news",
        access_method="official_api",
        base_url="https://www.alphavantage.co/query",
        auth_required=True,
        rate_limit="Free API key available; keep polling conservative.",
        polling_interval="6 hours",
        enabled=True,
        priority=14,
        terms_notes="Uses Alpha Vantage news sentiment metadata for public stock-related news.",
    )
    if not resolved_settings.alpha_vantage_api_key:
        return record_skipped_run(
            db=db,
            source=source,
            message="ALPHA_VANTAGE_API_KEY is not configured.",
        )

    connector = AlphaVantageNewsConnector(
        api_key=resolved_settings.alpha_vantage_api_key,
        tickers=default_finance_news_tickers(),
        limit=limit,
    )
    return await run_connector_ingestion(db=db, connector=connector, source=source)


async def run_alpha_vantage_price_ingestion(
    db: Session,
    limit: int = 30,
    settings: Settings | None = None,
) -> IngestionResult:
    resolved_settings = settings or get_settings()
    source = get_or_create_source(
        db,
        name="Alpha Vantage Prices",
        source_type="stock_prices",
        access_method="official_api",
        base_url="https://www.alphavantage.co/query",
        auth_required=True,
        rate_limit="Free API key available; daily time-series endpoint; keep polling conservative.",
        polling_interval="daily",
        enabled=True,
        priority=13,
        terms_notes="Uses Alpha Vantage daily adjusted price data for watched tickers.",
    )
    if not resolved_settings.alpha_vantage_api_key:
        return record_skipped_run(
            db=db,
            source=source,
            message="ALPHA_VANTAGE_API_KEY is not configured.",
        )
    if not source.enabled:
        return record_skipped_run(
            db=db,
            source=source,
            message=f"{source.name} is disabled.",
        )

    tickers = list_price_watchlist_tickers(db)
    connector = AlphaVantageDailyPriceConnector(
        api_key=resolved_settings.alpha_vantage_api_key,
        limit=limit,
    )
    run = SourceRun(source_id=source.id, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        fetched_count = 0
        stored_count = 0
        for ticker in tickers:
            points = await connector.fetch_prices(ticker)
            fetched_count += len(points)
            stored_count += store_stock_price_points(db, points)
        run.status = "success"
        run.items_fetched = fetched_count
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
        logger.exception(
            "Connector ingestion failed",
            extra={"source_id": source.id, "source_name": source.name},
        )
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


async def run_sec_filings_ingestion(
    db: Session,
    limit: int = 25,
    settings: Settings | None = None,
) -> IngestionResult:
    resolved_settings = settings or get_settings()
    source = get_or_create_source(
        db,
        name="SEC Filings",
        source_type="finance_filings",
        access_method="official_api",
        base_url="https://data.sec.gov/submissions",
        auth_required=False,
        rate_limit="Official SEC submissions API; use descriptive User-Agent and poll daily.",
        polling_interval="daily",
        enabled=True,
        priority=15,
        terms_notes="Uses SEC EDGAR submissions metadata for recent 8-K, 10-Q, and 10-K filings.",
    )
    connector = SecFilingsConnector(
        tickers=list_price_watchlist_tickers(db),
        limit=limit,
        user_agent=resolved_settings.sec_user_agent,
        forms=parse_sec_forms(resolved_settings.sec_forms),
    )
    return await run_connector_ingestion(db=db, connector=connector, source=source)


REGISTERED_SOURCE_RUNNERS = (
    RegisteredSourceRunner("Hacker News", run_hacker_news_ingestion, 30),
    RegisteredSourceRunner("Alpha Vantage News", run_alpha_vantage_news_ingestion, 25),
    RegisteredSourceRunner("Alpha Vantage Prices", run_alpha_vantage_price_ingestion, 30),
    RegisteredSourceRunner("SEC Filings", run_sec_filings_ingestion, 25),
    RegisteredSourceRunner("arXiv", run_arxiv_ingestion, 25),
    RegisteredSourceRunner("Chinese RSS Feeds", run_chinese_rss_ingestion, 25),
    RegisteredSourceRunner("GitHub", run_github_ingestion, 25),
    RegisteredSourceRunner("Hugging Face", run_hugging_face_ingestion, 25),
    RegisteredSourceRunner("Product Hunt", run_product_hunt_ingestion, 25),
    RegisteredSourceRunner("Selected RSS Feeds", run_rss_ingestion, 25),
)
REGISTERED_SOURCE_RUNNERS_BY_NAME = {
    item.source_name: item for item in REGISTERED_SOURCE_RUNNERS
}


async def run_source_ingestion_by_id(
    db: Session,
    source_id: int,
    limit: int | None = None,
    runners_by_name: Mapping[str, RegisteredSourceRunner] = REGISTERED_SOURCE_RUNNERS_BY_NAME,
) -> IngestionResult:
    source = db.get(Source, source_id)
    if source is None:
        raise SourceNotFoundError(f"Source {source_id} was not found.")

    registered = runners_by_name.get(source.name)
    if registered is None:
        if source.type == "product_topic":
            settings = get_settings()
            if not settings.product_hunt_api_token:
                return record_skipped_run(
                    db=db,
                    source=source,
                    message="PRODUCT_HUNT_API_TOKEN is not configured.",
                )
            connector = ProductHuntConnector(
                api_token=settings.product_hunt_api_token,
                limit=limit or 25,
                source_name=source.name,
                topic_terms=product_hunt_topic_terms_for_source(source),
            )
            return await run_connector_ingestion(db=db, connector=connector, source=source)
        if source.type == "social_keyword":
            feeds = parse_custom_rss_feeds(source.base_url, default_name=source.name)
            if not feeds:
                return record_skipped_run(
                    db=db,
                    source=source,
                    message="Social keyword source needs at least one public RSS/Atom feed URL.",
                )
            connector = RssConnector(
                limit=limit or 25,
                feeds=feeds,
                source_name=source.name,
                source_type=source.type,
                include_terms=social_keyword_terms_for_source(source),
            )
            return await run_connector_ingestion(db=db, connector=connector, source=source)
        if source.type == "github_repository" and source.base_url:
            repository = parse_github_repository(source.base_url)
            if repository is None:
                raise SourceRunnerNotFoundError(
                    f"{source.name} does not have a valid GitHub repository URL."
                )
            connector = GitHubConnector(
                limit=1,
                api_token=get_settings().github_token,
                repositories=[repository],
                source_name=source.name,
            )
            return await run_connector_ingestion(db=db, connector=connector, source=source)
        if source.access_method == "rss" and source.base_url:
            connector = RssConnector(
                limit=limit or 25,
                feeds=[RssFeedSpec(name=source.name, url=source.base_url)],
                source_name=source.name,
                source_type=source.type,
            )
            return await run_connector_ingestion(db=db, connector=connector, source=source)
        raise SourceRunnerNotFoundError(
            f"No runnable connector is registered for source {source.name}."
        )

    return await registered.runner(db, limit or registered.default_limit)


def product_hunt_topic_terms_for_source(source: Source) -> list[str]:
    values = [
        source.terms_notes,
        product_hunt_topic_from_url(source.base_url),
        cleaned_product_hunt_source_name(source.name),
        source.name,
    ]
    terms: list[str] = []
    seen: set[str] = set()
    for value in values:
        for term in split_product_hunt_terms(value):
            normalized = normalize_topic_term(term)
            if normalized and normalized not in seen:
                seen.add(normalized)
                terms.append(term.strip())
    return terms


def product_hunt_topic_from_url(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"/topics/([^/?#]+)", value)
    if not match:
        return None
    return match.group(1).replace("-", " ")


def cleaned_product_hunt_source_name(value: str) -> str:
    return re.sub(r"^product\s+hunt\s*", "", value.strip(), flags=re.IGNORECASE).strip()


def split_product_hunt_terms(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in re.split(r"[,;\n|]+", value) if part.strip()]


def normalize_topic_term(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def social_keyword_terms_for_source(source: Source) -> list[str]:
    values = [source.terms_notes, cleaned_social_source_name(source.name), source.name]
    terms: list[str] = []
    seen: set[str] = set()
    for value in values:
        for term in split_product_hunt_terms(value):
            normalized = normalize_social_keyword_term(term)
            if normalized and normalized not in seen:
                seen.add(normalized)
                terms.append(term.strip())
    return terms


def cleaned_social_source_name(value: str) -> str:
    return re.sub(
        r"^(social|chinese|xiaohongshu|xhs|twitter|x)\s+",
        "",
        value.strip(),
        flags=re.IGNORECASE,
    ).strip()


def normalize_social_keyword_term(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", value.lower()).strip()


async def run_connector_ingestion(
    db: Session,
    connector: SourceConnector,
    source: Source,
) -> IngestionResult:
    if not source.enabled:
        return record_skipped_run(
            db=db,
            source=source,
            message=f"{source.name} is disabled.",
        )

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
        logger.exception(
            "Connector ingestion failed",
            extra={"source_id": source.id, "source_name": source.name},
        )
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


def record_skipped_run(db: Session, source: Source, message: str) -> IngestionResult:
    run = SourceRun(
        source_id=source.id,
        status="skipped",
        items_fetched=0,
        items_stored=0,
        error_message=message,
        finished_at=datetime.now(UTC),
    )
    db.add(run)
    db.commit()
    return IngestionResult(
        source_name=source.name,
        status=run.status,
        items_fetched=0,
        items_stored=0,
        error_message=message,
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
        canonical_url = canonical_ingestion_url(item.url)
        content_hash = compute_content_hash(item)
        if raw_item_exists(
            db,
            source_id=source.id,
            external_id=item.external_id,
            content_hash=content_hash,
            canonical_url=canonical_url,
            title=item.raw_title,
            published_at=item.published_at,
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
            normalized.novelty_score = compute_ingestion_novelty_score(
                db=db,
                raw=raw,
                source=source,
            )
            db.add(normalized)
            stored_count += 1

    db.commit()
    return stored_count


def store_stock_price_points(db: Session, points) -> int:
    stored_count = 0
    for point in points:
        existing = (
            db.query(StockPricePoint)
            .filter(
                StockPricePoint.ticker == point.ticker,
                StockPricePoint.price_date == point.price_date,
            )
            .one_or_none()
        )
        price_point = existing or StockPricePoint(
            ticker=point.ticker,
            price_date=point.price_date,
        )
        if existing is None:
            stored_count += 1
        price_point.open_price = point.open_price
        price_point.high_price = point.high_price
        price_point.low_price = point.low_price
        price_point.close_price = point.close_price
        price_point.adjusted_close = point.adjusted_close
        price_point.volume = point.volume
        price_point.source_name = "Alpha Vantage"
        db.add(price_point)

    db.commit()
    return stored_count


def raw_item_exists(
    db: Session,
    source_id: int,
    external_id: str | None,
    content_hash: str,
    canonical_url: str | None = None,
    title: str | None = None,
    published_at: datetime | None = None,
) -> bool:
    query = db.query(RawItem).filter(RawItem.content_hash == content_hash)
    if db.query(query.exists()).scalar():
        return True
    if canonical_url and raw_item_canonical_url_exists(db, canonical_url):
        return True
    if title and near_duplicate_title_exists(
        db=db,
        source_id=source_id,
        title=title,
        published_at=published_at,
    ):
        return True
    if external_id:
        external_query = db.query(RawItem).filter(
            RawItem.source_id == source_id,
            RawItem.external_id == external_id,
        )
        return bool(db.query(external_query.exists()).scalar())
    return False


def raw_item_canonical_url_exists(db: Session, canonical_url: str) -> bool:
    return any(canonical_ingestion_url(raw.url) == canonical_url for raw in db.query(RawItem).all())


def near_duplicate_title_exists(
    db: Session,
    source_id: int,
    title: str,
    published_at: datetime | None,
) -> bool:
    signature = normalized_title_signature(title)
    if not signature:
        return False
    candidates = db.query(RawItem).filter(RawItem.source_id == source_id).all()
    for raw in candidates:
        if not same_publication_day(raw.published_at, published_at):
            continue
        candidate_signature = normalized_title_signature(raw.raw_title)
        if (
            candidate_signature
            and title_similarity(signature, candidate_signature)
            >= NEAR_DUPLICATE_TITLE_THRESHOLD
        ):
            return True
    return False


def normalized_title_signature(title: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", title.casefold())
    tokens = [token for token in normalized.split() if token not in TITLE_DEDUPE_STOPWORDS]
    return " ".join(tokens)


def title_similarity(left: str, right: str) -> float:
    if left == right:
        return 1
    return SequenceMatcher(None, left, right).ratio()


def compute_ingestion_novelty_score(db: Session, raw: RawItem, source: Source) -> float:
    signature = normalized_title_signature(raw.raw_title)
    if not signature:
        return 1

    score = 1.0
    candidates = (
        db.query(RawItem, Source)
        .join(Source, Source.id == RawItem.source_id)
        .filter(RawItem.id != raw.id)
        .all()
    )
    for candidate, candidate_source in candidates:
        if not within_novelty_lookback(raw, candidate):
            continue
        candidate_signature = normalized_title_signature(candidate.raw_title)
        if not candidate_signature:
            continue
        if title_similarity(signature, candidate_signature) < NOVELTY_TITLE_SIMILARITY_THRESHOLD:
            continue
        if candidate_source.id == source.id:
            score = min(score, SAME_SOURCE_FOLLOWUP_NOVELTY)
        else:
            score = min(score, CROSS_SOURCE_CONFIRMATION_NOVELTY)
    return round(score, 3)


def within_novelty_lookback(raw: RawItem, candidate: RawItem) -> bool:
    raw_time = raw.published_at or raw.fetched_at
    candidate_time = candidate.published_at or candidate.fetched_at
    if raw_time is None or candidate_time is None:
        return True
    left = normalize_ingestion_datetime(raw_time)
    right = normalize_ingestion_datetime(candidate_time)
    return abs(left - right) <= timedelta(days=NOVELTY_LOOKBACK_DAYS)


def same_publication_day(left: datetime | None, right: datetime | None) -> bool:
    if left is None or right is None:
        return left is None and right is None
    return normalize_ingestion_datetime(left).date() == normalize_ingestion_datetime(right).date()


def normalize_ingestion_datetime(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def compute_content_hash(item: RawItemInput) -> str:
    hash_input = "|".join(
        [
            canonical_ingestion_url(item.url),
            item.raw_title,
            item.raw_text or "",
        ]
    )
    return sha256(hash_input.encode("utf-8")).hexdigest()


def canonical_ingestion_url(url: str) -> str:
    try:
        parsed = urlsplit(url.strip())
    except ValueError:
        return url.strip()
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key.casefold() not in TRACKING_QUERY_PARAMS
        )
    )
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/") or parsed.path,
            query,
            "",
        )
    )


def normalize_item(raw: RawItem, source: Source) -> NormalizedItem | None:
    combined_text = " ".join(part for part in [raw.raw_title, raw.raw_text or ""] if part)
    if not is_ai_relevant(combined_text) and source.name != "SEC Filings":
        return None

    language = detect_language(combined_text)
    topics = detect_topics(combined_text)
    tickers = detect_tickers(combined_text)
    if raw.raw_metadata.get("ticker_sentiment"):
        tickers = sorted(
            {
                *tickers,
                *[
                    str(item.get("ticker", "")).strip().upper()
                    for item in raw.raw_metadata["ticker_sentiment"]
                    if str(item.get("ticker", "")).strip()
                ],
            }
    )
    companies = sorted({*detect_companies(combined_text), *company_names_for_tickers(tickers)})
    products = sorted(
        {
            *detect_products(combined_text),
            *([raw.raw_metadata["product_name"]] if raw.raw_metadata.get("product_name") else []),
        }
    )
    source_quality = source_quality_score_for_source(source)
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
        hf_kind = raw.raw_metadata.get("hf_kind")
        if hf_kind == "space":
            category = "product"
            subcategory = infer_product_use_case(combined_text)
            summary_prefix = "Hugging Face Space"
            why_it_matters = (
                "This Space metadata matched AI product or demo signals on Hugging Face."
            )
        elif hf_kind == "dataset":
            category = "research"
            subcategory = "dataset_release"
            summary_prefix = "Hugging Face dataset"
            why_it_matters = (
                "This dataset metadata matched AI research or benchmark signals on Hugging Face."
            )
        else:
            category = "research"
            subcategory = "model_release"
            summary_prefix = "Hugging Face model"
            why_it_matters = (
                "This model metadata matched the AI relevance prefilter from Hugging Face."
            )
    elif source.name == "Selected RSS Feeds":
        category = "technical_trend"
        subcategory = "company_blog"
        summary_prefix = "RSS item"
        why_it_matters = "This RSS item matched the AI relevance prefilter from selected feeds."
    elif source.name == "Chinese RSS Feeds":
        category = "social_trend"
        subcategory = "chinese_rss"
        summary_prefix = "Chinese AI social signal"
        why_it_matters = (
            "This Chinese-language item matched the AI relevance prefilter "
            "from configured RSS feeds."
        )
    elif source.type == "social_keyword":
        category = "social_trend"
        subcategory = "chinese_social_keyword" if language == "zh" else "social_keyword"
        summary_prefix = "Experimental social keyword signal"
        why_it_matters = (
            "This item matched a followed social keyword source using public RSS/Atom "
            "metadata only."
        )
    elif source.name == "Product Hunt":
        category = "product"
        subcategory = infer_product_use_case(combined_text)
        summary_prefix = "Product Hunt launch"
        why_it_matters = (
            "This product launch matched the AI relevance prefilter from Product Hunt metadata."
        )
    elif source.name == "Alpha Vantage News":
        category = "stock_company_event"
        subcategory = "finance_news"
        summary_prefix = "Stock-linked AI news"
        why_it_matters = (
            "This finance item matched watched AI tickers or AI themes in Alpha Vantage news."
        )
    elif source.name == "SEC Filings":
        category = "stock_company_event"
        subcategory = "sec_filing"
        summary_prefix = "SEC filing"
        why_it_matters = (
            "This filing matched a watched ticker and may contain company-specific "
            "financial, risk, or event disclosures."
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

    if category == "social_trend":
        products = sorted({*products, *infer_social_product_names(combined_text)})

    return NormalizedItem(
        raw_item_id=raw.id,
        title=raw.raw_title,
        url=raw.url,
        source_name=source.name,
        author=raw.raw_author,
        language=language,
        published_at=raw.published_at,
        text=raw.raw_text,
        category=category,
        subcategory=subcategory,
        tickers=tickers,
        companies=companies,
        products=products,
        topics=topics,
        sentiment="neutral",
        relevance_score=relevance,
        classification_confidence=0.62,
        importance_score=importance,
        novelty_score=1.0,
        source_quality_score=source_quality,
        stock_impact_score=stock_impact_score_for_source(source=source, tickers=tickers),
        summary_short=f"{summary_prefix}: {raw.raw_title}",
        summary_detailed=build_initial_detailed_summary(
            raw=raw,
            category=category,
            topics=topics,
            products=products,
            source=source,
            language=language,
            subcategory=subcategory,
        ),
        why_it_matters=why_it_matters,
    )


def build_initial_detailed_summary(
    raw: RawItem,
    category: str,
    topics: list[str],
    products: list[str] | None = None,
    source: Source | None = None,
    language: str | None = None,
    subcategory: str | None = None,
) -> str | None:
    source_excerpt = first_sentence(raw.raw_text or raw.raw_title)
    topic_text = ", ".join(topics[:5]) if topics else "AI relevance prefilter"
    product_names = products or []

    if category == "research":
        parts = [
            f"Research contribution: {source_excerpt}",
            (
                "Research method: Not explicit in source metadata; review the source "
                "abstract for method and evaluation details."
            ),
            f"Technical relevance: Matched watched research topics: {topic_text}.",
        ]
        traction = build_source_traction_signal(raw.raw_metadata)
        if traction:
            parts.append(f"Engagement signal: {traction}")
        return "\n".join(parts)

    if category == "social_trend":
        return build_social_trend_summary(
            raw=raw,
            source_excerpt=source_excerpt,
            topics=topics,
            products=product_names,
            language=language,
            subcategory=subcategory,
            source=source,
        )

    if category == "product":
        traction = build_source_traction_signal(raw.raw_metadata)
        product_category = format_product_use_case(subcategory)
        parts = [
            f"Product category: {product_category}",
            f"Product use case: {source_excerpt}",
            f"Product audience: {infer_product_audience(raw.raw_text or raw.raw_title)}",
        ]
        if traction:
            parts.append(f"Traction signal: {traction}")
        return "\n".join(parts)

    if source and source.name == "Hacker News":
        return build_hacker_news_discussion_summary(raw, source_excerpt, topics)

    if source and source.name == "SEC Filings":
        return build_sec_filing_summary(raw)

    return None


def build_hacker_news_discussion_summary(
    raw: RawItem,
    source_excerpt: str,
    topics: list[str],
) -> str:
    metadata = raw.raw_metadata or {}
    score = metadata.get("score")
    descendants = metadata.get("descendants")
    top_comments = [
        comment
        for comment in metadata.get("top_comments", [])
        if isinstance(comment, dict) and comment.get("text")
    ]
    topic_text = ", ".join(topics[:5]) if topics else "AI technical discussion"
    signals = []
    if score is not None:
        signals.append(f"{score} HN points")
    if descendants is not None:
        signals.append(f"{descendants} comments")
    if top_comments:
        comment_label = "comment" if len(top_comments) == 1 else "comments"
        signals.append(f"{len(top_comments)} sampled top {comment_label}")

    lines = [
        f"Discussion summary: {source_excerpt}",
        f"Technical relevance: Matched watched topics: {topic_text}.",
    ]
    if signals:
        lines.append(f"Discussion signal: {', '.join(signals)}.")
    for comment in top_comments[:2]:
        author = comment.get("by") or "unknown"
        text = first_sentence(str(comment["text"]), limit=180)
        lines.append(f"Top comment by {author}: {text}")
    return "\n".join(lines)


def build_sec_filing_summary(raw: RawItem) -> str:
    metadata = raw.raw_metadata or {}
    company = metadata.get("company_name") or "Watched company"
    ticker = metadata.get("ticker") or "watched ticker"
    form = metadata.get("form") or "SEC filing"
    filing_date = metadata.get("filing_date")
    report_date = metadata.get("report_date")
    description = metadata.get("primary_doc_description") or metadata.get("description") or form

    lines = [
        f"Filing summary: {company} ({ticker}) filed {form}.",
        f"Disclosure type: {description}.",
    ]
    if filing_date:
        lines.append(f"Filing date: {filing_date}.")
    if report_date:
        lines.append(f"Report date: {report_date}.")
    lines.append(
        "Stock-watch relevance: official SEC disclosure for a watched company; "
        "review the filing before drawing market conclusions."
    )
    return "\n".join(lines)


def build_social_trend_summary(
    raw: RawItem,
    source_excerpt: str,
    topics: list[str],
    products: list[str],
    language: str | None,
    subcategory: str | None,
    source: Source | None,
) -> str:
    feed_name = raw.raw_metadata.get("feed_name") or (source.name if source else "public feed")
    topic_text = ", ".join(topics[:5]) if topics else "AI product discussion"
    product_text = (
        ", ".join(products[:4])
        if products
        else infer_social_use_case(raw.raw_text or raw.raw_title)
    )
    if subcategory == "manual_social_signal":
        access_note = (
            "Manual source: user-submitted public URL or user-provided context only; "
            "no login-protected or anti-bot-protected pages are accessed."
        )
    elif subcategory in {"chinese_social_keyword", "social_keyword"}:
        access_note = (
            "Experimental source: public RSS/Atom metadata only; no login-protected "
            "or anti-bot-protected pages are accessed."
        )
    else:
        access_note = "Source access: configured public Chinese RSS/Atom feed."
    language_note = (
        "Chinese-language source summarized in English."
        if language == "zh"
        else "Social source summarized in English."
    )
    return "\n".join(
        [
            f"English summary: {language_note} The item discusses {product_text} "
            "and related AI adoption signals.",
            f"Source excerpt: {source_excerpt}",
            f"Product/use case: {product_text}",
            f"Adoption signal: Mentioned in {feed_name} with topics: {topic_text}.",
            access_note,
        ]
    )


def infer_social_product_names(text: str) -> list[str]:
    lowered = text.lower()
    candidates: list[tuple[str, str]] = [
        ("AI photo tool", r"(写真|修图|图片|图像|photo|image)"),
        ("AI video tool", r"(视频|剪辑|video)"),
        ("AI writing tool", r"(写作|文案|文章|writing|copywriting)"),
        ("AI coding tool", r"(编程|代码|coding|code)"),
        ("AI search assistant", r"(搜索|浏览|search|browser)"),
        ("AI education tool", r"(教育|学习|课程|education|study)"),
        ("AI productivity tool", r"(办公|效率|工作流|workflow|productivity)"),
        ("AI agent product", r"(智能体|agent|agents)"),
    ]
    return [name for name, pattern in candidates if re.search(pattern, lowered)]


def infer_social_use_case(text: str) -> str:
    product_names = infer_social_product_names(text)
    if product_names:
        return ", ".join(product_names[:4])
    return "AI consumer or productivity product"


def build_source_traction_signal(metadata: dict) -> str | None:
    explicit_signal = metadata.get("traction_signal")
    if explicit_signal:
        return str(explicit_signal)

    votes = metadata.get("votes_count")
    comments = metadata.get("comments_count")
    signals = []
    if votes is not None:
        signals.append(f"{votes} Product Hunt votes")
    if comments is not None:
        signals.append(f"{comments} comments")
    return ", ".join(signals) if signals else None


def build_product_traction_signal(metadata: dict) -> str | None:
    return build_source_traction_signal(metadata)


def source_quality_score_for_source(source: Source) -> float:
    source_name = normalize_quality_key(source.name)
    if source_name in SOURCE_QUALITY_BY_NAME:
        return SOURCE_QUALITY_BY_NAME[source_name]

    source_type = normalize_quality_key(source.type)
    if source_type == "social keyword":
        return SOURCE_QUALITY_BY_TYPE[source_type]

    access_method = normalize_quality_key(source.access_method)
    if access_method in SOURCE_QUALITY_BY_ACCESS_METHOD:
        return SOURCE_QUALITY_BY_ACCESS_METHOD[access_method]

    if source_type in SOURCE_QUALITY_BY_TYPE:
        return SOURCE_QUALITY_BY_TYPE[source_type]

    return 0.65


def normalize_quality_key(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def infer_product_audience(text: str) -> str:
    lowered = text.lower()
    if re.search(r"\b(developer|developers|coding|code|engineer|software)\b", lowered):
        return "developers and software teams"
    if re.search(r"\b(product teams?|product managers?|pm|launch)\b", lowered):
        return "product and growth teams"
    if re.search(r"\b(marketing|sales|customer|business)\b", lowered):
        return "business teams"
    if re.search(r"\b(student|education|learn|study)\b", lowered):
        return "learners and educators"
    if re.search(r"\b(photo|video|image|media|creative)\b", lowered):
        return "creative and media users"
    return "AI product evaluators"


def format_product_use_case(subcategory: str | None) -> str:
    labels = {
        "product_coding": "coding",
        "product_productivity": "productivity",
        "product_media": "media",
        "product_search": "search",
        "product_education": "education",
        "product_business": "business",
        "product_entertainment": "entertainment",
        "product_general": "general AI product",
    }
    return labels.get(subcategory or "", "general AI product")


def first_sentence(text: str, limit: int = 260) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return "Source metadata describes an AI-related item."
    match = re.search(r"(.+?[.!?。！？])", cleaned)
    sentence = match.group(1) if match else cleaned
    return sentence[:limit].rstrip()


def default_finance_news_tickers() -> list[str]:
    return sorted(TICKER_ALIASES)


def list_price_watchlist_tickers(db: Session) -> list[str]:
    watchlist_rows = db.query(StockWatchlistItem.ticker).all()
    tickers = [row[0] for row in watchlist_rows if row[0]]
    return sorted(set(tickers or ["MU", "MRVL", "SNDK"]))


def stock_impact_score_for_source(source: Source, tickers: list[str]) -> float:
    if not tickers:
        return 0
    if source.name == "Alpha Vantage News":
        return 0.55
    if source.name == "SEC Filings":
        return 0.6
    return 0.2


def parse_chinese_rss_feeds(value: str | None) -> list[RssFeedSpec]:
    return parse_custom_rss_feeds(value, default_name="Chinese Feed")


def parse_custom_rss_feeds(value: str | None, default_name: str) -> list[RssFeedSpec]:
    if not value:
        return []

    feeds: list[RssFeedSpec] = []
    for index, chunk in enumerate(value.split(","), start=1):
        entry = chunk.strip()
        if not entry:
            continue
        if "|" in entry:
            name, url = [part.strip() for part in entry.split("|", 1)]
        else:
            name, url = f"{default_name} {index}", entry
        if url:
            feeds.append(RssFeedSpec(name=name or f"{default_name} {index}", url=url))
    return feeds


def detect_language(text: str) -> str:
    return "zh" if re.search(r"[\u4e00-\u9fff]", text) else "en"
