from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.db.models import NormalizedItem, Source, SourceRun, StockPricePoint
from app.schemas.manual_submissions import ManualSubmissionRequest
from app.services.alerts import generate_alerts
from app.services.daily_digest import save_daily_digest_snapshot
from app.services.ingestion import get_or_create_source, store_raw_items
from app.services.manual_submissions import create_manual_submission_result
from app.sources.base import RawItemInput


@dataclass(frozen=True)
class DemoSourceSpec:
    name: str
    source_type: str
    access_method: str
    base_url: str
    rate_limit: str
    polling_interval: str
    priority: int
    terms_notes: str


@dataclass(frozen=True)
class DemoPricePoint:
    ticker: str
    price_date: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    adjusted_close: float | None
    volume: int


DEMO_SOURCES = [
    DemoSourceSpec(
        name="arXiv",
        source_type="research",
        access_method="official_api",
        base_url="https://export.arxiv.org/api/query",
        rate_limit="Public API; demo rows are local examples only.",
        polling_interval="6 hours",
        priority=10,
        terms_notes="Demo rows mirror arXiv metadata fields without fetching external data.",
    ),
    DemoSourceSpec(
        name="Hacker News",
        source_type="developer_community",
        access_method="official_api",
        base_url="https://hacker-news.firebaseio.com/v0",
        rate_limit="Public API; demo rows are local examples only.",
        polling_interval="6 hours",
        priority=12,
        terms_notes="Demo rows mirror public Hacker News discussion metadata without fetching.",
    ),
    DemoSourceSpec(
        name="GitHub",
        source_type="developer",
        access_method="official_api",
        base_url="https://api.github.com/search/repositories",
        rate_limit="Public API; demo rows are local examples only.",
        polling_interval="6 hours",
        priority=15,
        terms_notes="Demo rows mirror public repository metadata without fetching external data.",
    ),
    DemoSourceSpec(
        name="Hugging Face",
        source_type="model_hub",
        access_method="official_api",
        base_url="https://huggingface.co/api",
        rate_limit="Public API; demo rows are local examples only.",
        polling_interval="6 hours",
        priority=18,
        terms_notes="Demo rows mirror public Hub model, dataset, and Space metadata.",
    ),
    DemoSourceSpec(
        name="Selected RSS Feeds",
        source_type="company_blog",
        access_method="rss",
        base_url="configured RSS/Atom feeds",
        rate_limit="Public RSS/Atom feeds; demo rows are local examples only.",
        polling_interval="6 hours",
        priority=20,
        terms_notes="Demo rows represent selected public AI company or research RSS feeds.",
    ),
    DemoSourceSpec(
        name="Product Hunt",
        source_type="product_launch",
        access_method="official_graphql_api",
        base_url="https://api.producthunt.com/v2/api/graphql",
        rate_limit="Official API token required for live runs; demo rows are local examples only.",
        polling_interval="daily",
        priority=25,
        terms_notes="Demo rows use public launch-style metadata without calling Product Hunt.",
    ),
    DemoSourceSpec(
        name="Alpha Vantage News",
        source_type="finance_news",
        access_method="official_api",
        base_url="https://www.alphavantage.co/query",
        rate_limit="Official API key required for live runs; demo rows are local examples only.",
        polling_interval="daily",
        priority=30,
        terms_notes="Demo rows use stock-news-style metadata without calling Alpha Vantage.",
    ),
    DemoSourceSpec(
        name="Chinese RSS Feeds",
        source_type="chinese_social",
        access_method="rss",
        base_url="configured via CHINESE_RSS_FEEDS",
        rate_limit="Public RSS/Atom feeds only; demo rows are local examples only.",
        polling_interval="6 hours",
        priority=19,
        terms_notes="Demo rows represent compliant public-feed metadata, not scraped posts.",
    ),
]


def seed_demo_data(db: Session, now: datetime | None = None) -> dict[str, int]:
    generated_at = now or datetime.now(UTC)
    item_count = seed_demo_feed_items(db=db, now=generated_at)
    manual_submission_count = seed_demo_manual_submission(db)
    mark_demo_items_as_curated_classifications(db)
    price_count = seed_demo_stock_prices(db=db, today=generated_at.date())
    alert_result = generate_alerts(db)
    digest_snapshot = save_daily_digest_snapshot(db=db, digest_date=generated_at.date())
    return {
        "seeded_demo_item_count": item_count + manual_submission_count,
        "seeded_demo_manual_submission_count": manual_submission_count,
        "seeded_demo_price_count": price_count,
        "seeded_demo_alert_count": alert_result.alerts_created,
        "seeded_demo_alert_rule_count": alert_result.rules_seeded,
        "seeded_demo_digest_snapshot_count": 1,
        "seeded_demo_digest_item_count": digest_snapshot.total_items,
    }


def seed_demo_feed_items(db: Session, now: datetime | None = None) -> int:
    generated_at = now or datetime.now(UTC)
    total_stored = 0
    for spec in DEMO_SOURCES:
        source = get_or_create_demo_source(db=db, spec=spec)
        items = demo_items_for_source(source_name=spec.name, now=generated_at)
        stored_count = store_raw_items(db=db, source=source, items=items)
        if stored_count:
            record_demo_source_run(
                db=db,
                source=source,
                now=generated_at,
                items_fetched=len(items),
                items_stored=stored_count,
        )
        total_stored += stored_count
    mark_demo_items_as_curated_classifications(db)
    return total_stored


def seed_demo_manual_submission(db: Session) -> int:
    result = create_manual_submission_result(
        db=db,
        request=ManualSubmissionRequest(
            title="Manual capture: AI coding agent note",
            url="https://example.com/demo/manual-ai-coding-agent-note",
            source_name="Demo Manual Capture",
            text=(
                "A manually captured AI coding agent note mentions MCP routing, RAG memory, "
                "long-context planning, and developer automation signals for later review."
            ),
            save_item=True,
            personal_note="Demo manual capture saved into the read-later queue.",
            manual_tags=["demo", "manual", "coding-agent"],
        ),
    )
    return 1 if result.created else 0


def mark_demo_items_as_curated_classifications(db: Session) -> None:
    curated_relevance_by_source = {
        "Alpha Vantage News": 0.74,
        "Chinese RSS Feeds": 0.66,
        "Demo Manual Capture": 0.75,
        "Product Hunt": 0.68,
    }
    demo_source_names = [spec.name for spec in DEMO_SOURCES] + ["Demo Manual Capture"]
    rows = (
        db.query(NormalizedItem)
        .filter(NormalizedItem.source_name.in_(demo_source_names))
        .all()
    )
    for item in rows:
        item.classification_confidence = max(item.classification_confidence or 0, 0.82)
        curated_relevance = curated_relevance_by_source.get(item.source_name)
        if curated_relevance is not None:
            item.relevance_score = max(item.relevance_score or 0, curated_relevance)
        db.add(item)
    if rows:
        db.commit()


def get_or_create_demo_source(db: Session, spec: DemoSourceSpec) -> Source:
    return get_or_create_source(
        db=db,
        name=spec.name,
        source_type=spec.source_type,
        access_method=spec.access_method,
        base_url=spec.base_url,
        auth_required=False,
        rate_limit=spec.rate_limit,
        polling_interval=spec.polling_interval,
        enabled=True,
        priority=spec.priority,
        terms_notes=spec.terms_notes,
    )


def record_demo_source_run(
    db: Session,
    source: Source,
    now: datetime,
    items_fetched: int,
    items_stored: int,
) -> None:
    db.add(
        SourceRun(
            source_id=source.id,
            status="success",
            items_fetched=items_fetched,
            items_stored=items_stored,
            error_message=None,
            started_at=now - timedelta(seconds=8),
            finished_at=now,
        )
    )
    db.commit()


def seed_demo_stock_prices(db: Session, today: date | None = None) -> int:
    reference_date = today or datetime.now(UTC).date()
    points = demo_price_points(reference_date)
    created = 0
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
            created += 1
        price_point.open_price = point.open_price
        price_point.high_price = point.high_price
        price_point.low_price = point.low_price
        price_point.close_price = point.close_price
        price_point.adjusted_close = point.adjusted_close
        price_point.volume = point.volume
        price_point.source_name = "Demo Market Data"
        db.add(price_point)
    db.commit()
    return created


def demo_items_for_source(source_name: str, now: datetime) -> list[RawItemInput]:
    return [item for item in demo_feed_items(now) if item.source_name == source_name]


def demo_feed_items(now: datetime) -> list[RawItemInput]:
    return [
        RawItemInput(
            source_name="arXiv",
            external_id="demo-arxiv-agent-memory",
            url="https://example.com/demo/arxiv-agent-memory",
            raw_title="Agent Memory Bench evaluates long-running coding agents",
            raw_text=(
                "A research paper introduces Agent Memory Bench for evaluating coding agent "
                "memory, tool use, retrieval, and multi-agent workflows across long software "
                "engineering tasks."
            ),
            raw_author="Demo Research Lab",
            raw_metadata={"traction_signal": "benchmark and agent-memory evaluation demo"},
            published_at=now - timedelta(hours=8),
        ),
        RawItemInput(
            source_name="Hacker News",
            external_id="demo-hn-agent-discussion",
            url="https://example.com/demo/hn-agent-discussion",
            raw_title="Show HN: local AI agent runner for coding workflows",
            raw_text=(
                "Developer discussion compares a local AI agent runner, MCP tools, code "
                "review automation, and retrieval memory for long software engineering tasks."
            ),
            raw_author="demo_hn_user",
            raw_metadata={"score": 438, "descendants": 96},
            published_at=now - timedelta(hours=7),
        ),
        RawItemInput(
            source_name="GitHub",
            external_id="demo-github-coding-agent",
            url="https://example.com/demo/github-coding-agent",
            raw_title="Open-source coding agent framework adds MCP tool routing",
            raw_text=(
                "The repository for an AI coding agent adds Model Context Protocol tool "
                "routing, agent harness templates, RAG memory, and evaluation workflows."
            ),
            raw_author="demo-builder",
            raw_metadata={"stars": 4200, "stars_per_day": 64, "forks": 520},
            published_at=now - timedelta(hours=5),
        ),
        RawItemInput(
            source_name="Hugging Face",
            external_id="demo-hf-research-space",
            url="https://example.com/demo/hf-research-space",
            raw_title="Hugging Face Space demos multimodal agent evaluation",
            raw_text=(
                "A Hugging Face Space launches an AI demo for multimodal agent evaluation, "
                "benchmark comparison, and open-source model inspection."
            ),
            raw_author="demo-hf-lab",
            raw_metadata={
                "hf_kind": "space",
                "likes": 1320,
                "downloads": 42000,
                "product_name": "AgentEval Space",
            },
            published_at=now - timedelta(hours=9),
        ),
        RawItemInput(
            source_name="Selected RSS Feeds",
            external_id="demo-rss-lab-agent-release",
            url="https://example.com/demo/rss-lab-agent-release",
            raw_title="AI lab blog details new agent skill routing architecture",
            raw_text=(
                "A public AI lab RSS post explains agent skill routing, model selection, "
                "tool-use evaluation, and inference infrastructure updates."
            ),
            raw_author="Demo AI Lab",
            raw_metadata={"feed_name": "Demo AI Lab Blog"},
            published_at=now - timedelta(hours=10),
        ),
        RawItemInput(
            source_name="Product Hunt",
            external_id="demo-product-research-browser",
            url="https://example.com/demo/product-research-browser",
            raw_title="ScoutTab launches an AI browser for research workflows",
            raw_text=(
                "ScoutTab is an AI search and browser product that summarizes sources, "
                "builds research briefs, and automates multi-step web workflows for teams."
            ),
            raw_author="ScoutTab",
            raw_metadata={
                "product_name": "ScoutTab",
                "votes_count": 760,
                "comments_count": 84,
            },
            published_at=now - timedelta(hours=11),
        ),
        RawItemInput(
            source_name="Alpha Vantage News",
            external_id="demo-alpha-micron-hbm",
            url="https://example.com/demo/alpha-micron-hbm",
            raw_title="Micron raises AI HBM demand commentary after cloud capex update",
            raw_text=(
                "Micron Technology discussed HBM, DRAM demand, data center revenue, and AI "
                "server memory demand after a cloud capex update from major customers."
            ),
            raw_author="Demo Markets",
            raw_metadata={
                "ticker_sentiment": [
                    {"ticker": "MU", "relevance_score": "0.86", "ticker_sentiment_label": "Bullish"}
                ]
            },
            published_at=now - timedelta(hours=4),
        ),
        RawItemInput(
            source_name="Chinese RSS Feeds",
            external_id="demo-chinese-ai-video",
            url="https://example.com/demo/chinese-ai-video",
            raw_title="AI视频工具在小红书创作者中走红",
            raw_text=(
                "一款AI视频和AI修图工作流工具在创作者中流行，用户讨论智能体、AI办公、"
                "AI学习和短视频生产效率。"
            ),
            raw_author="Demo Chinese Feed",
            raw_metadata={
                "feed_name": "Demo Chinese AI Feed",
                "likes": 1800,
                "comments": 260,
                "views": 88000,
            },
            published_at=now - timedelta(hours=6),
        ),
    ]


def demo_price_points(reference_date: date) -> list[DemoPricePoint]:
    return [
        DemoPricePoint(
            "MU",
            reference_date - timedelta(days=2),
            121.20,
            124.10,
            120.80,
            122.40,
            122.40,
            18400000,
        ),
        DemoPricePoint(
            "MU",
            reference_date - timedelta(days=1),
            122.80,
            130.20,
            122.10,
            129.60,
            129.60,
            28600000,
        ),
        DemoPricePoint(
            "MRVL",
            reference_date - timedelta(days=2),
            72.10,
            73.40,
            70.90,
            71.80,
            71.80,
            9400000,
        ),
        DemoPricePoint(
            "MRVL",
            reference_date - timedelta(days=1),
            72.20,
            76.80,
            71.90,
            76.10,
            76.10,
            15100000,
        ),
        DemoPricePoint(
            "SNDK",
            reference_date - timedelta(days=2),
            58.40,
            59.20,
            57.80,
            58.10,
            58.10,
            4200000,
        ),
        DemoPricePoint(
            "SNDK",
            reference_date - timedelta(days=1),
            58.50,
            60.60,
            58.20,
            60.20,
            60.20,
            6100000,
        ),
    ]
