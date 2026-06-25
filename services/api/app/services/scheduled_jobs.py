from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.services.alerts import generate_alerts
from app.services.ingestion import (
    IngestionResult,
    run_alpha_vantage_news_ingestion,
    run_arxiv_ingestion,
    run_github_ingestion,
    run_hacker_news_ingestion,
    run_hugging_face_ingestion,
    run_product_hunt_ingestion,
    run_rss_ingestion,
)
from app.services.watchlist import seed_initial_stock_watchlist, seed_initial_topic_watchlist

IngestionJob = Callable[[Session, int], Awaitable[IngestionResult]]
WatchlistSeeder = Callable[[Session], tuple[int, int]]
AlertGenerator = Callable[[Session], int]


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
    seeded_topic_count: int
    generated_alert_count: int
    ingestion_results: list[IngestionResult]


DEFAULT_INGESTION_JOBS = [
    ScheduledIngestionJob(name="hacker-news", runner=run_hacker_news_ingestion, limit=30),
    ScheduledIngestionJob(
        name="alpha-vantage-news",
        runner=run_alpha_vantage_news_ingestion,
        limit=25,
    ),
    ScheduledIngestionJob(name="arxiv", runner=run_arxiv_ingestion, limit=25),
    ScheduledIngestionJob(name="github", runner=run_github_ingestion, limit=25),
    ScheduledIngestionJob(name="hugging-face", runner=run_hugging_face_ingestion, limit=25),
    ScheduledIngestionJob(name="product-hunt", runner=run_product_hunt_ingestion, limit=25),
    ScheduledIngestionJob(name="rss", runner=run_rss_ingestion, limit=25),
]


def seed_default_watchlists(db: Session) -> tuple[int, int]:
    stocks = seed_initial_stock_watchlist(db)
    topics = seed_initial_topic_watchlist(db)
    return len(stocks), len(topics)


def generate_cycle_alerts(db: Session) -> int:
    return generate_alerts(db).alerts_created


async def run_ingestion_cycle(
    db: Session,
    jobs: list[ScheduledIngestionJob] | None = None,
    seed_watchlists: WatchlistSeeder = seed_default_watchlists,
    generate_cycle_alerts_fn: AlertGenerator = generate_cycle_alerts,
) -> ScheduledCycleResult:
    started_at = datetime.now(UTC)
    seeded_stock_count, seeded_topic_count = seed_watchlists(db)
    ingestion_results: list[IngestionResult] = []

    for job in jobs or DEFAULT_INGESTION_JOBS:
        result = await job.runner(db, job.limit)
        ingestion_results.append(result)
    generated_alert_count = generate_cycle_alerts_fn(db)

    return ScheduledCycleResult(
        started_at=started_at,
        finished_at=datetime.now(UTC),
        seeded_stock_count=seeded_stock_count,
        seeded_topic_count=seeded_topic_count,
        generated_alert_count=generated_alert_count,
        ingestion_results=ingestion_results,
    )


def scheduled_cycle_to_log_dict(result: ScheduledCycleResult) -> dict[str, object]:
    return {
        "started_at": result.started_at.isoformat(),
        "finished_at": result.finished_at.isoformat(),
        "seeded_stock_count": result.seeded_stock_count,
        "seeded_topic_count": result.seeded_topic_count,
        "generated_alert_count": result.generated_alert_count,
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
