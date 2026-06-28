from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.db.models import Source
from app.services.alerts import generate_alerts
from app.services.daily_digest import save_daily_digest_snapshot
from app.services.ingestion import (
    REGISTERED_SOURCE_RUNNERS_BY_NAME,
    IngestionResult,
    SourceRunnerNotFoundError,
    record_skipped_run,
    run_alpha_vantage_news_ingestion,
    run_alpha_vantage_price_ingestion,
    run_arxiv_ingestion,
    run_chinese_rss_ingestion,
    run_github_ingestion,
    run_hacker_news_ingestion,
    run_hugging_face_ingestion,
    run_product_hunt_ingestion,
    run_rss_ingestion,
    run_source_ingestion_by_id,
)
from app.services.watchlist import (
    seed_initial_company_watchlist,
    seed_initial_product_watchlist,
    seed_initial_stock_watchlist,
    seed_initial_topic_watchlist,
)

IngestionJob = Callable[[Session, int], Awaitable[IngestionResult]]
WatchlistSeeder = Callable[[Session], tuple[int, int, int, int]]
AlertGenerator = Callable[[Session], int]
DigestSnapshotSaver = Callable[[Session], date]
CustomSourceLister = Callable[[Session], list[Source]]
CustomSourceRunner = Callable[[Session, int], Awaitable[IngestionResult]]


@dataclass(frozen=True)
class ScheduledIngestionJob:
    name: str
    runner: IngestionJob
    limit: int


@dataclass(frozen=True)
class ScheduledCycleResult:
    started_at: datetime
    finished_at: datetime
    seeded_stock_count: int
    seeded_company_count: int
    seeded_topic_count: int
    seeded_product_count: int
    generated_alert_count: int
    saved_digest_date: date | None
    ingestion_results: list[IngestionResult]


DEFAULT_INGESTION_JOBS = [
    ScheduledIngestionJob(name="hacker-news", runner=run_hacker_news_ingestion, limit=30),
    ScheduledIngestionJob(
        name="alpha-vantage-news",
        runner=run_alpha_vantage_news_ingestion,
        limit=25,
    ),
    ScheduledIngestionJob(
        name="alpha-vantage-prices",
        runner=run_alpha_vantage_price_ingestion,
        limit=30,
    ),
    ScheduledIngestionJob(name="arxiv", runner=run_arxiv_ingestion, limit=25),
    ScheduledIngestionJob(name="chinese-rss", runner=run_chinese_rss_ingestion, limit=25),
    ScheduledIngestionJob(name="github", runner=run_github_ingestion, limit=25),
    ScheduledIngestionJob(name="hugging-face", runner=run_hugging_face_ingestion, limit=25),
    ScheduledIngestionJob(name="product-hunt", runner=run_product_hunt_ingestion, limit=25),
    ScheduledIngestionJob(name="rss", runner=run_rss_ingestion, limit=25),
]


def seed_default_watchlists(db: Session) -> tuple[int, int, int, int]:
    stocks = seed_initial_stock_watchlist(db)
    companies = seed_initial_company_watchlist(db)
    topics = seed_initial_topic_watchlist(db)
    products = seed_initial_product_watchlist(db)
    return len(stocks), len(companies), len(topics), len(products)


def generate_cycle_alerts(db: Session) -> int:
    return generate_alerts(db).alerts_created


def save_cycle_digest_snapshot(db: Session) -> date:
    return save_daily_digest_snapshot(db).digest_date


def list_enabled_custom_sources(db: Session) -> list[Source]:
    registered_names = set(REGISTERED_SOURCE_RUNNERS_BY_NAME)
    return (
        db.query(Source)
        .filter(Source.enabled.is_(True), ~Source.name.in_(registered_names))
        .order_by(Source.priority.asc(), Source.name.asc())
        .all()
    )


async def run_ingestion_cycle(
    db: Session,
    jobs: list[ScheduledIngestionJob] | None = None,
    seed_watchlists: WatchlistSeeder = seed_default_watchlists,
    generate_cycle_alerts_fn: AlertGenerator = generate_cycle_alerts,
    save_digest_snapshot_fn: DigestSnapshotSaver = save_cycle_digest_snapshot,
    list_custom_sources_fn: CustomSourceLister = list_enabled_custom_sources,
    run_custom_source_fn: CustomSourceRunner = run_source_ingestion_by_id,
) -> ScheduledCycleResult:
    started_at = datetime.now(UTC)
    (
        seeded_stock_count,
        seeded_company_count,
        seeded_topic_count,
        seeded_product_count,
    ) = seed_watchlists(db)
    ingestion_results: list[IngestionResult] = []

    for job in DEFAULT_INGESTION_JOBS if jobs is None else jobs:
        result = await job.runner(db, job.limit)
        ingestion_results.append(result)
    for source in list_custom_sources_fn(db):
        try:
            result = await run_custom_source_fn(db, source.id)
        except SourceRunnerNotFoundError as exc:
            result = record_skipped_run(db=db, source=source, message=str(exc))
        ingestion_results.append(result)
    generated_alert_count = generate_cycle_alerts_fn(db)
    saved_digest_date = save_digest_snapshot_fn(db)

    return ScheduledCycleResult(
        started_at=started_at,
        finished_at=datetime.now(UTC),
        seeded_stock_count=seeded_stock_count,
        seeded_company_count=seeded_company_count,
        seeded_topic_count=seeded_topic_count,
        seeded_product_count=seeded_product_count,
        generated_alert_count=generated_alert_count,
        saved_digest_date=saved_digest_date,
        ingestion_results=ingestion_results,
    )


def scheduled_cycle_to_log_dict(result: ScheduledCycleResult) -> dict[str, object]:
    return {
        "started_at": result.started_at.isoformat(),
        "finished_at": result.finished_at.isoformat(),
        "seeded_stock_count": result.seeded_stock_count,
        "seeded_company_count": result.seeded_company_count,
        "seeded_topic_count": result.seeded_topic_count,
        "seeded_product_count": result.seeded_product_count,
        "generated_alert_count": result.generated_alert_count,
        "saved_digest_date": result.saved_digest_date.isoformat()
        if result.saved_digest_date
        else None,
        "ingestion_results": [
            {
                "source_name": item.source_name,
                "status": item.status,
                "items_fetched": item.items_fetched,
                "items_stored": item.items_stored,
                "error_message": item.error_message,
            }
            for item in result.ingestion_results
        ],
    }
