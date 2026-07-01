import re
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from typing import TypedDict
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Query
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.api.deps import DbSession
from app.core.config import DEFAULT_SEC_USER_AGENT, Settings, get_settings
from app.db.models import (
    Alert,
    CompanyWatchlistItem,
    DailyDigestSnapshot,
    LlmUsageEvent,
    NormalizedItem,
    ProductWatchlistItem,
    SourceRun,
    StockPricePoint,
    StockWatchlistItem,
    TopicWatchlistItem,
    UserItemAction,
)
from app.schemas.health import (
    HealthResponse,
    IntegrationStatus,
    LlmOperationUsage,
    QualityFinding,
    QualityMetricsResponse,
    SetupItem,
    SetupSummary,
)
from app.services.feed_actions import LOCAL_USER_ID

router = APIRouter()

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

PRD_FEED_MODULES = ("trends", "research", "products", "stocks", "chinese")


class LlmUsageSummary(TypedDict):
    call_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    operation_usage: list[LlmOperationUsage]


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    settings = get_settings()
    integrations = IntegrationStatus(
        kimi_coding_api=has_config_value(settings.moonshot_api_key),
        github_api=has_config_value(settings.github_token),
        product_hunt_api=has_config_value(settings.product_hunt_api_token),
        alpha_vantage_api=has_config_value(settings.alpha_vantage_api_key),
        sec_user_agent=has_custom_sec_user_agent(settings.sec_user_agent),
        chinese_rss_feeds=has_config_value(settings.chinese_rss_feeds),
    )
    setup_items = build_setup_items(settings=settings, integrations=integrations)
    return HealthResponse(
        status="ok",
        service="signallens-api",
        environment=settings.environment,
        llm_provider=settings.llm_provider,
        llm_model=settings.moonshot_model,
        llm_configured=has_config_value(settings.moonshot_api_key),
        integrations=integrations,
        setup_items=setup_items,
        setup_summary=build_setup_summary(setup_items),
        missing_env_template=build_missing_env_template(setup_items),
    )


@router.get("/quality-metrics", response_model=QualityMetricsResponse)
async def quality_metrics(
    db: DbSession,
    window_days: int = Query(default=7, ge=1, le=90),
) -> QualityMetricsResponse:
    return build_quality_metrics(db=db, window_days=window_days)


def build_quality_metrics(db: Session, window_days: int = 7) -> QualityMetricsResponse:
    generated_at = datetime.now(UTC)
    since = generated_at - timedelta(days=window_days)
    total_rows = list_visible_quality_items(db)
    recent_rows = [
        item for item in total_rows if quality_item_timestamp(item, generated_at) >= since
    ]
    save_count = count_user_actions(db=db, field_name="is_saved")
    hide_count = count_user_actions(db=db, field_name="is_hidden")
    feedback_action_count = save_count + hide_count
    saved_read_count, saved_read_later_count = count_saved_read_statuses(db)
    alert_counts = count_alerts_by_status(db)
    source_run_count, source_failure_count = count_recent_source_runs(db=db, since=since)
    llm_usage = summarize_recent_llm_usage(db=db, since=since)
    recent_item_count = len(recent_rows)
    recent_module_counts = build_recent_module_counts(recent_rows)
    covered_module_count = sum(1 for count in recent_module_counts.values() if count > 0)
    recent_source_counts = Counter(item.source_name for item in recent_rows)
    recent_source_count = len(recent_source_counts)
    dominant_source_share = ratio(
        max(recent_source_counts.values()) if recent_source_counts else 0,
        recent_item_count,
    )
    trusted_source_item_count = sum(
        1 for item in recent_rows if (item.source_quality_score or 0) >= 0.7
    )
    trusted_source_coverage = ratio(trusted_source_item_count, recent_item_count)
    low_quality_item_count = recent_item_count - trusted_source_item_count
    faceted_item_count = sum(
        1 for item in recent_rows if quality_item_has_search_facets(item)
    )
    search_facet_coverage = ratio(faceted_item_count, recent_item_count)
    unfaceted_item_count = recent_item_count - faceted_item_count
    recent_manual_rows = [item for item in recent_rows if quality_item_is_manual_submission(item)]
    manual_submission_count = len(recent_manual_rows)
    manual_enrichment_gap_count = sum(
        1 for item in recent_manual_rows if quality_item_needs_manual_enrichment(item)
    )
    relevance_precision_proxy = ratio(
        sum(1 for item in recent_rows if item.relevance_score >= 0.5),
        recent_item_count,
    )
    duplicate_rate = duplicate_rate_for_items(recent_rows)
    high_confidence_item_count = sum(
        1 for item in recent_rows if (item.classification_confidence or 0) >= 0.7
    )
    classification_coverage = ratio(high_confidence_item_count, recent_item_count)
    low_confidence_item_count = recent_item_count - high_confidence_item_count
    high_value_item_count = sum(1 for item in recent_rows if item.importance_score >= 0.75)
    high_value_unsummarized_count = sum(
        1
        for item in recent_rows
        if item.importance_score >= 0.75 and not (item.summary_short or item.summary_detailed)
    )
    summary_coverage = ratio(
        sum(1 for item in recent_rows if item.summary_short or item.summary_detailed),
        recent_item_count,
    )
    source_failure_rate = ratio(source_failure_count, source_run_count)
    alert_dismissal_rate = ratio(
        alert_counts["dismissed"],
        alert_counts["active"] + alert_counts["dismissed"],
    )
    digest_snapshot_count = count_recent_digest_snapshots(db=db, since=since)
    latest_digest_snapshot = get_latest_digest_snapshot(db)
    latest_digest_snapshot_date = (
        latest_digest_snapshot.digest_date if latest_digest_snapshot else None
    )
    latest_digest_snapshot_item_count = (
        latest_digest_snapshot.total_items if latest_digest_snapshot else None
    )
    latest_digest_age_days = digest_age_days(
        latest_digest_snapshot_date=latest_digest_snapshot_date,
        current_date=generated_at.date(),
    )
    stock_watchlist_count = count_stock_watchlist_items(db)
    company_watchlist_count = count_company_watchlist_items(db)
    topic_watchlist_count = count_topic_watchlist_items(db)
    product_watchlist_count = count_product_watchlist_items(db)
    watchlist_area_count = count_populated_watchlist_areas(
        stock_watchlist_count=stock_watchlist_count,
        company_watchlist_count=company_watchlist_count,
        topic_watchlist_count=topic_watchlist_count,
        product_watchlist_count=product_watchlist_count,
    )
    latest_stock_price_date = get_latest_stock_price_date(db)
    latest_stock_price_age_days = stock_price_age_days(
        latest_stock_price_date=latest_stock_price_date,
        current_date=generated_at.date(),
    )
    llm_calls_per_recent_item = ratio(llm_usage["call_count"], recent_item_count)

    return QualityMetricsResponse(
        generated_at=generated_at,
        window_days=window_days,
        total_item_count=len(total_rows),
        recent_item_count=recent_item_count,
        recent_module_counts=recent_module_counts,
        covered_module_count=covered_module_count,
        recent_source_count=recent_source_count,
        dominant_source_share=dominant_source_share,
        trusted_source_coverage=trusted_source_coverage,
        low_quality_item_count=low_quality_item_count,
        search_facet_coverage=search_facet_coverage,
        unfaceted_item_count=unfaceted_item_count,
        high_value_item_count=high_value_item_count,
        high_value_unsummarized_count=high_value_unsummarized_count,
        classification_coverage=classification_coverage,
        low_confidence_item_count=low_confidence_item_count,
        relevance_precision_proxy=relevance_precision_proxy,
        duplicate_rate=duplicate_rate,
        summary_coverage=summary_coverage,
        source_failure_rate=source_failure_rate,
        save_count=save_count,
        hide_count=hide_count,
        feedback_action_count=feedback_action_count,
        manual_submission_count=manual_submission_count,
        manual_enrichment_gap_count=manual_enrichment_gap_count,
        stock_watchlist_count=stock_watchlist_count,
        company_watchlist_count=company_watchlist_count,
        topic_watchlist_count=topic_watchlist_count,
        product_watchlist_count=product_watchlist_count,
        watchlist_area_count=watchlist_area_count,
        saved_read_count=saved_read_count,
        saved_read_later_count=saved_read_later_count,
        save_hide_ratio=round(save_count / hide_count, 3) if hide_count else None,
        active_alert_count=alert_counts["active"],
        dismissed_alert_count=alert_counts["dismissed"],
        alert_dismissal_rate=alert_dismissal_rate,
        digest_snapshot_count=digest_snapshot_count,
        latest_digest_snapshot_date=latest_digest_snapshot_date,
        latest_digest_age_days=latest_digest_age_days,
        latest_digest_snapshot_item_count=latest_digest_snapshot_item_count,
        latest_stock_price_date=latest_stock_price_date,
        latest_stock_price_age_days=latest_stock_price_age_days,
        llm_call_count=llm_usage["call_count"],
        llm_input_tokens=llm_usage["input_tokens"],
        llm_output_tokens=llm_usage["output_tokens"],
        llm_total_tokens=llm_usage["total_tokens"],
        llm_calls_per_recent_item=llm_calls_per_recent_item,
        llm_operation_usage=llm_usage["operation_usage"],
        quality_findings=build_quality_findings(
            recent_item_count=recent_item_count,
            covered_module_count=covered_module_count,
            total_module_count=len(PRD_FEED_MODULES),
            recent_source_count=recent_source_count,
            dominant_source_share=dominant_source_share,
            trusted_source_coverage=trusted_source_coverage,
            low_quality_item_count=low_quality_item_count,
            search_facet_coverage=search_facet_coverage,
            unfaceted_item_count=unfaceted_item_count,
            high_value_item_count=high_value_item_count,
            relevance_precision_proxy=relevance_precision_proxy,
            duplicate_rate=duplicate_rate,
            summary_coverage=summary_coverage,
            classification_coverage=classification_coverage,
            low_confidence_item_count=low_confidence_item_count,
            high_value_unsummarized_count=high_value_unsummarized_count,
            source_failure_rate=source_failure_rate,
            saved_read_later_count=saved_read_later_count,
            save_count=save_count,
            feedback_action_count=feedback_action_count,
            manual_submission_count=manual_submission_count,
            manual_enrichment_gap_count=manual_enrichment_gap_count,
            watchlist_area_count=watchlist_area_count,
            active_alert_count=alert_counts["active"],
            dismissed_alert_count=alert_counts["dismissed"],
            alert_dismissal_rate=alert_dismissal_rate,
            digest_snapshot_count=digest_snapshot_count,
            latest_digest_snapshot_date=latest_digest_snapshot_date,
            latest_digest_snapshot_item_count=latest_digest_snapshot_item_count,
            latest_stock_price_date=latest_stock_price_date,
            stock_watchlist_count=stock_watchlist_count,
            current_date=generated_at.date(),
            llm_calls_per_recent_item=llm_calls_per_recent_item,
        ),
    )


def list_visible_quality_items(db: Session) -> list[NormalizedItem]:
    rows = (
        db.query(NormalizedItem)
        .outerjoin(
            UserItemAction,
            (UserItemAction.item_id == NormalizedItem.id)
            & (UserItemAction.user_id == LOCAL_USER_ID),
        )
        .filter((UserItemAction.is_hidden.is_(False)) | (UserItemAction.id.is_(None)))
        .all()
    )
    return list(rows)


def quality_item_timestamp(item: NormalizedItem, fallback: datetime) -> datetime:
    timestamp = item.published_at or item.created_at or fallback
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)
    return timestamp


def count_user_actions(db: Session, field_name: str) -> int:
    field = getattr(UserItemAction, field_name)
    return (
        db.query(UserItemAction)
        .filter(UserItemAction.user_id == LOCAL_USER_ID, field.is_(True))
        .count()
    )


def count_saved_read_statuses(db: Session) -> tuple[int, int]:
    rows = (
        db.query(UserItemAction.is_read)
        .filter(
            UserItemAction.user_id == LOCAL_USER_ID,
            UserItemAction.is_saved.is_(True),
            UserItemAction.is_hidden.is_(False),
        )
        .all()
    )
    read_count = sum(1 for row in rows if unwrap_bool(row))
    return read_count, len(rows) - read_count


def unwrap_bool(row) -> bool:
    if isinstance(row, bool):
        return row
    if hasattr(row, "is_read"):
        return bool(row.is_read)
    if isinstance(row, tuple) and row:
        return bool(row[0])
    try:
        return bool(row[0])
    except (IndexError, KeyError, TypeError):
        return False
    return False


def count_alerts_by_status(db: Session) -> dict[str, int]:
    active_count = (
        db.query(Alert)
        .filter(Alert.user_id == LOCAL_USER_ID, Alert.status == "active")
        .count()
    )
    dismissed_count = (
        db.query(Alert)
        .filter(Alert.user_id == LOCAL_USER_ID, Alert.status == "dismissed")
        .count()
    )
    return {"active": active_count, "dismissed": dismissed_count}


def count_recent_source_runs(db: Session, since: datetime) -> tuple[int, int]:
    query = db.query(SourceRun).filter(
        or_(
            SourceRun.started_at >= since,
            and_(SourceRun.finished_at.is_not(None), SourceRun.finished_at >= since),
        )
    )
    run_count = query.count()
    failure_count = query.filter(SourceRun.status == "failed").count()
    return run_count, failure_count


def count_recent_digest_snapshots(db: Session, since: datetime) -> int:
    return (
        db.query(DailyDigestSnapshot)
        .filter(
            DailyDigestSnapshot.user_id == LOCAL_USER_ID,
            DailyDigestSnapshot.generated_at >= since,
        )
        .count()
    )


def get_latest_digest_snapshot(db: Session) -> DailyDigestSnapshot | None:
    return (
        db.query(DailyDigestSnapshot)
        .filter(DailyDigestSnapshot.user_id == LOCAL_USER_ID)
        .order_by(
            DailyDigestSnapshot.digest_date.desc(),
            DailyDigestSnapshot.generated_at.desc(),
        )
        .first()
    )


def digest_age_days(
    latest_digest_snapshot_date: date | None,
    current_date: date,
) -> int | None:
    if latest_digest_snapshot_date is None:
        return None
    return max(0, (current_date - latest_digest_snapshot_date).days)


def count_stock_watchlist_items(db: Session) -> int:
    return (
        db.query(StockWatchlistItem)
        .filter(StockWatchlistItem.user_id == LOCAL_USER_ID)
        .count()
    )


def count_company_watchlist_items(db: Session) -> int:
    return (
        db.query(CompanyWatchlistItem)
        .filter(CompanyWatchlistItem.user_id == LOCAL_USER_ID)
        .count()
    )


def count_topic_watchlist_items(db: Session) -> int:
    return (
        db.query(TopicWatchlistItem)
        .filter(TopicWatchlistItem.user_id == LOCAL_USER_ID)
        .count()
    )


def count_product_watchlist_items(db: Session) -> int:
    return (
        db.query(ProductWatchlistItem)
        .filter(ProductWatchlistItem.user_id == LOCAL_USER_ID)
        .count()
    )


def count_populated_watchlist_areas(
    *,
    stock_watchlist_count: int,
    company_watchlist_count: int,
    topic_watchlist_count: int,
    product_watchlist_count: int,
) -> int:
    return sum(
        1
        for count in (
            stock_watchlist_count,
            company_watchlist_count,
            topic_watchlist_count,
            product_watchlist_count,
        )
        if count > 0
    )


def get_latest_stock_price_date(db: Session) -> date | None:
    tickers = [
        row[0]
        for row in db.query(StockWatchlistItem.ticker)
        .filter(StockWatchlistItem.user_id == LOCAL_USER_ID)
        .all()
    ]
    if not tickers:
        return None
    return (
        db.query(func.max(StockPricePoint.price_date))
        .filter(StockPricePoint.ticker.in_(tickers))
        .scalar()
    )


def stock_price_age_days(
    latest_stock_price_date: date | None,
    current_date: date,
) -> int | None:
    if latest_stock_price_date is None:
        return None
    return max(0, (current_date - latest_stock_price_date).days)


def summarize_recent_llm_usage(db: Session, since: datetime) -> LlmUsageSummary:
    rows = (
        db.query(LlmUsageEvent)
        .filter(LlmUsageEvent.user_id == LOCAL_USER_ID, LlmUsageEvent.created_at >= since)
        .all()
    )
    operation_totals: dict[str, dict[str, int]] = {}
    for row in rows:
        totals = operation_totals.setdefault(
            row.operation,
            {"call_count": 0, "input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        )
        totals["call_count"] += 1
        totals["input_tokens"] += row.input_tokens
        totals["output_tokens"] += row.output_tokens
        totals["total_tokens"] += row.total_tokens

    operation_usage = [
        LlmOperationUsage(operation=operation, **totals)
        for operation, totals in sorted(
            operation_totals.items(),
            key=lambda item: (-item[1]["total_tokens"], item[0]),
        )
    ]
    return {
        "call_count": len(rows),
        "input_tokens": sum(row.input_tokens for row in rows),
        "output_tokens": sum(row.output_tokens for row in rows),
        "total_tokens": sum(row.total_tokens for row in rows),
        "operation_usage": operation_usage,
    }


def duplicate_rate_for_items(items: list[NormalizedItem]) -> float:
    if not items:
        return 0
    seen: set[str] = set()
    duplicate_count = 0
    for item in items:
        keys = quality_duplicate_keys(item)
        if keys and seen.intersection(keys):
            duplicate_count += 1
        seen.update(keys)
    return ratio(duplicate_count, len(items))


def quality_duplicate_keys(item: NormalizedItem) -> set[str]:
    keys: set[str] = set()
    url = canonical_quality_url(item.url)
    if url:
        keys.add(f"url:{url}")
    title = normalize_quality_title(item.title)
    if title:
        keys.add(f"title:{title}")
    return keys


def canonical_quality_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parsed = urlsplit(url.strip())
    except ValueError:
        return url.strip().casefold() or None
    if not parsed.scheme and not parsed.netloc:
        return url.strip().casefold() or None
    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.casefold() not in TRACKING_QUERY_PARAMS
    ]
    return urlunsplit(
        (
            parsed.scheme.casefold(),
            parsed.netloc.casefold(),
            parsed.path.rstrip("/"),
            urlencode(sorted(filtered_query)),
            "",
        )
    )


def normalize_quality_title(title: str | None) -> str | None:
    normalized = re.sub(r"\s+", " ", title or "").strip().casefold()
    return normalized if len(normalized) >= 20 else None


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0
    return round(numerator / denominator, 3)


def build_recent_module_counts(items: list[NormalizedItem]) -> dict[str, int]:
    return {
        module: sum(1 for item in items if quality_item_matches_module(item, module))
        for module in PRD_FEED_MODULES
    }


def quality_item_matches_module(item: NormalizedItem, module: str) -> bool:
    source_name = (item.source_name or "").casefold()
    products = item.products or []
    tickers = item.tickers or []
    if module == "trends":
        return item.category == "technical_trend"
    if module == "research":
        return item.category == "research"
    if module == "products":
        return item.category == "product" or bool(products) or "product hunt" in source_name
    if module == "stocks":
        return (
            item.category == "stock_company_event"
            or bool(tickers)
            or item.stock_impact_score >= 0.35
        )
    if module == "chinese":
        return (
            item.category == "social_trend"
            or item.language == "zh"
            or "chinese" in source_name
        )
    return False


def quality_item_has_search_facets(item: NormalizedItem) -> bool:
    return bool(item.topics or item.companies or item.products or item.tickers)


def quality_item_is_manual_submission(item: NormalizedItem) -> bool:
    if item.category == "manual_submission":
        return True
    raw_item = getattr(item, "raw_item", None)
    if raw_item is None:
        return item.source_name == "Manual Submission"
    source = getattr(raw_item, "source", None)
    metadata = raw_item.raw_metadata or {}
    return (
        getattr(source, "type", None) == "manual"
        or metadata.get("submission_type") == "manual"
        or item.source_name == "Manual Submission"
    )


def quality_item_needs_manual_enrichment(item: NormalizedItem) -> bool:
    return (
        item.category == "manual_submission"
        or (item.classification_confidence or 0) < 0.7
        or not quality_item_has_search_facets(item)
    )


def build_quality_findings(
    *,
    recent_item_count: int,
    high_value_item_count: int,
    relevance_precision_proxy: float,
    duplicate_rate: float,
    summary_coverage: float,
    high_value_unsummarized_count: int,
    source_failure_rate: float,
    saved_read_later_count: int,
    save_count: int,
    active_alert_count: int,
    dismissed_alert_count: int,
    alert_dismissal_rate: float,
    digest_snapshot_count: int,
    latest_digest_snapshot_date: date | None,
    latest_digest_snapshot_item_count: int | None,
    llm_calls_per_recent_item: float,
    feedback_action_count: int | None = None,
    manual_submission_count: int = 0,
    manual_enrichment_gap_count: int = 0,
    watchlist_area_count: int | None = None,
    classification_coverage: float = 0,
    low_confidence_item_count: int = 0,
    covered_module_count: int | None = None,
    total_module_count: int = len(PRD_FEED_MODULES),
    recent_source_count: int = 0,
    dominant_source_share: float = 0,
    trusted_source_coverage: float = 0,
    low_quality_item_count: int = 0,
    search_facet_coverage: float = 0,
    unfaceted_item_count: int = 0,
    latest_stock_price_date: date | None = None,
    stock_watchlist_count: int = 0,
    current_date: date | None = None,
) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    today = current_date or latest_digest_snapshot_date or datetime.now(UTC).date()
    if recent_item_count == 0:
        findings.append(
            QualityFinding(
                severity="warning",
                title="No recent items",
                metric="0 recent items",
                recommendation=(
                    "Seed local demo data to evaluate the dashboard, or run a full ingestion "
                    "cycle after source credentials are configured."
                ),
                action_label="Seed Demo Data",
                action_module="dashboard",
                action_operation="demo-data:seed",
            )
        )
    elif relevance_precision_proxy < 0.6:
        findings.append(
            QualityFinding(
                severity="warning",
                title="Low relevance precision",
                metric=f"{format_quality_percent(relevance_precision_proxy)} relevant",
                recommendation="Tune followed sources, blocked sources, and watchlist terms.",
                action_label="Tune Settings",
                action_module="settings",
            )
        )
    if (
        recent_item_count >= 5
        and covered_module_count is not None
        and total_module_count > 0
        and covered_module_count < 3
    ):
        findings.append(
            QualityFinding(
                severity="info",
                title="Module coverage is thin",
                metric=f"{covered_module_count}/{total_module_count} modules active",
                recommendation=(
                    "Run a full ingestion cycle and review Source Health so the PRD modules "
                    "do not silently collapse into one feed."
                ),
                action_label="Run Full Cycle",
                action_module="sources",
                action_operation="cycle",
                action_source_filter="attention",
            )
        )
    if (
        recent_item_count >= 5
        and recent_source_count > 0
        and (recent_source_count < 2 or dominant_source_share >= 0.8)
    ):
        findings.append(
            QualityFinding(
                severity="info",
                title="Source diversity is thin",
                metric=(
                    f"{recent_source_count} recent sources, "
                    f"{format_quality_percent(dominant_source_share)} dominant"
                ),
                recommendation=(
                    "Run a full ingestion cycle and review Source Health so the dashboard "
                    "keeps cross-source context instead of over-weighting one feed."
                ),
                action_label="Review Sources",
                action_module="sources",
                action_operation="cycle",
                action_source_filter="attention",
            )
        )
    if (
        recent_item_count >= 5
        and low_quality_item_count > 0
        and trusted_source_coverage < 0.6
    ):
        findings.append(
            QualityFinding(
                severity="warning",
                title="Trusted source coverage is thin",
                metric=f"{format_quality_percent(trusted_source_coverage)} trusted",
                recommendation=(
                    "Review Source Health, block noisy sources, and prioritize official, RSS, "
                    "or API-backed sources before relying on rankings."
                ),
                action_label="Review Sources",
                action_module="sources",
                action_source_filter="attention",
            )
        )
    if duplicate_rate >= 0.25:
        findings.append(
            QualityFinding(
                severity="warning",
                title="Duplicate pressure",
                metric=f"{format_quality_percent(duplicate_rate)} duplicate rate",
                recommendation=(
                    "Review noisy sources and canonical URL handling before LLM batches."
                ),
                action_label="Open Source Health",
                action_module="sources",
                action_source_filter="attention",
            )
        )
    if recent_item_count > 0 and summary_coverage < 0.5:
        findings.append(
            QualityFinding(
                severity="info",
                title="Summary coverage is thin",
                metric=f"{format_quality_percent(summary_coverage)} summarized",
                recommendation="Run capped LLM summarization for high-signal unsummarized items.",
                action_label="Run Summaries",
                action_module="dashboard",
                action_operation="llm:summarize",
            )
        )
    if (
        recent_item_count >= 5
        and low_confidence_item_count > 0
        and classification_coverage < 0.6
    ):
        findings.append(
            QualityFinding(
                severity="info",
                title="Classification confidence is thin",
                metric=f"{round(classification_coverage * 100)}% high-confidence",
                recommendation=(
                    "Run capped LLM classification so ranking, alerts, digest sections, "
                    "and uncertainty notes have stronger labels."
                ),
                action_label="Run Classification",
                action_module="dashboard",
                action_operation="llm:classify",
            )
        )
    if (
        recent_item_count >= 5
        and unfaceted_item_count > 0
        and search_facet_coverage < 0.6
    ):
        findings.append(
            QualityFinding(
                severity="info",
                title="Search facets are thin",
                metric=f"{format_quality_percent(search_facet_coverage)} faceted",
                recommendation=(
                    "Run capped LLM classification so topics, companies, products, and tickers "
                    "improve search filters and drill-downs."
                ),
                action_label="Run Classification",
                action_module="dashboard",
                action_operation="llm:classify",
            )
        )
    if high_value_unsummarized_count > 0:
        findings.append(
            QualityFinding(
                severity="info",
                title="High-value summaries missing",
                metric=f"{high_value_unsummarized_count} high-value unsummarized",
                recommendation="Run capped LLM summarization before relying on the daily digest.",
                action_label="Run Summaries",
                action_module="dashboard",
                action_operation="llm:summarize",
            )
        )
    if saved_read_later_count >= 5 and ratio(saved_read_later_count, save_count) >= 0.8:
        findings.append(
            QualityFinding(
                severity="info",
                title="Read-later backlog is high",
                metric=f"{saved_read_later_count} saved unread",
                recommendation="Use the Daily Digest read-later section to clear saved items.",
                action_label="Open Daily Digest",
                action_module="digest",
            )
        )
    if recent_item_count >= 10 and feedback_action_count == 0:
        findings.append(
            QualityFinding(
                severity="info",
                title="Personal feedback is empty",
                metric="0 save or hide actions",
                recommendation=(
                    "Save useful items and hide noisy ones so SignalLens can tune ranking, "
                    "digest read-later context, and personalization notes."
                ),
                action_label="Open Dashboard",
                action_module="dashboard",
            )
        )
    if manual_submission_count >= 3 and ratio(
        manual_enrichment_gap_count,
        manual_submission_count,
    ) >= 0.5:
        findings.append(
            QualityFinding(
                severity="info",
                title="Manual submissions need enrichment",
                metric=(
                    f"{manual_enrichment_gap_count}/{manual_submission_count} "
                    "manual items need review"
                ),
                recommendation=(
                    "Run capped LLM classification so user-submitted links become searchable, "
                    "ranked, and digest-ready."
                ),
                action_label="Run Classification",
                action_module="dashboard",
                action_operation="llm:classify",
            )
        )
    if (
        watchlist_area_count is not None
        and recent_item_count >= 5
        and watchlist_area_count < 3
    ):
        findings.append(
            QualityFinding(
                severity="info",
                title="Watchlist coverage is thin",
                metric=f"{watchlist_area_count}/4 watchlist areas",
                recommendation=(
                    "Seed or edit stock, company, topic, and product watchlists so ranking, "
                    "search, alerts, and digests have enough personal context."
                ),
                action_label="Open Dashboard",
                action_module="dashboard",
            )
        )
    if recent_item_count > 0 and high_value_item_count > 0 and active_alert_count == 0:
        findings.append(
            QualityFinding(
                severity="info",
                title="Alert coverage is empty",
                metric=f"{high_value_item_count} high-value recent signals",
                recommendation=(
                    "Generate dashboard alerts so urgent stock, product, and cross-source signals "
                    "are visible before the daily digest."
                ),
                action_label="Generate Alerts",
                action_module="dashboard",
                action_operation="alerts:generate",
            )
        )
    if dismissed_alert_count >= 5 and alert_dismissal_rate >= 0.8:
        findings.append(
            QualityFinding(
                severity="info",
                title="Alerts may be noisy",
                metric=(
                    f"{format_quality_percent(alert_dismissal_rate)} dismissed "
                    f"across {active_alert_count + dismissed_alert_count} alerts"
                ),
                recommendation=(
                    "Tune alert rules, watched tickers, and minimum importance thresholds."
                ),
                action_label="Review Settings",
                action_module="settings",
            )
        )
    if source_failure_rate >= 0.25:
        findings.append(
            QualityFinding(
                severity="warning",
                title="Source failures need review",
                metric=f"{format_quality_percent(source_failure_rate)} failure rate",
                recommendation=(
                    "Open Source Health, filter failed runs, and update credentials or feeds."
                ),
                action_label="Show Failed Runs",
                action_module="sources",
                action_source_filter="failed",
            )
        )
    if stock_watchlist_count > 0 and latest_stock_price_date is None:
        findings.append(
            QualityFinding(
                severity="warning",
                title="Stock prices are missing",
                metric=f"{stock_watchlist_count} watched tickers need price data",
                recommendation=(
                    "Refresh Alpha Vantage price snapshots so stock alerts and briefings "
                    "can compare AI signals with market moves."
                ),
                action_label="Refresh Prices",
                action_module="stocks",
                action_operation="stock-prices:refresh",
            )
        )
    elif latest_stock_price_date and latest_stock_price_date < today - timedelta(days=1):
        findings.append(
            QualityFinding(
                severity="info",
                title="Stock prices are stale",
                metric=f"latest close {latest_stock_price_date.isoformat()}",
                recommendation=(
                    "Refresh Alpha Vantage price snapshots before reviewing stock-sensitive alerts."
                ),
                action_label="Refresh Prices",
                action_module="stocks",
                action_operation="stock-prices:refresh",
            )
        )
    if latest_digest_snapshot_date and latest_digest_snapshot_date < today:
        findings.append(
            QualityFinding(
                severity="info",
                title="Digest snapshot is stale",
                metric=f"last saved {latest_digest_snapshot_date.isoformat()}",
                recommendation="Generate and save a fresh daily digest snapshot after ingestion.",
                action_label="Save Digest",
                action_module="digest",
                action_operation="digest:save-snapshot",
            )
        )
    elif latest_digest_snapshot_date is None:
        findings.append(
            QualityFinding(
                severity="info",
                title="No saved digest snapshot",
                metric="0 saved digests",
                recommendation="Generate and save a daily digest snapshot after ingestion.",
                action_label="Save Digest",
                action_module="digest",
                action_operation="digest:save-snapshot",
            )
        )
    elif recent_item_count >= 5 and (latest_digest_snapshot_item_count or 0) < 3:
        findings.append(
            QualityFinding(
                severity="info",
                title="Digest snapshot is thin",
                metric=f"{latest_digest_snapshot_item_count or 0} saved digest items",
                recommendation=(
                    "Regenerate and save the daily digest after the latest ingestion so the "
                    "morning briefing reflects the available feed."
                ),
                action_label="Save Digest",
                action_module="digest",
                action_operation="digest:save-snapshot",
            )
        )
    if llm_calls_per_recent_item > 1.5:
        findings.append(
            QualityFinding(
                severity="warning",
                title="LLM spend is high",
                metric=f"{llm_calls_per_recent_item:.2f} calls per recent item",
                recommendation="Use module-scoped batches and skip already enriched items.",
                action_label="Review Settings",
                action_module="settings",
            )
        )
    return findings


def format_quality_percent(value: float) -> str:
    return f"{round(value * 100)}%"


def has_config_value(value: str | None) -> bool:
    return bool(value and value.strip())


def has_custom_sec_user_agent(value: str | None) -> bool:
    if not value or not value.strip():
        return False
    text = value.strip()
    return text != DEFAULT_SEC_USER_AGENT and "configure SEC_USER_AGENT" not in text


def build_setup_items(settings: Settings, integrations: IntegrationStatus) -> list[SetupItem]:
    return [
        SetupItem(
            key="kimi_coding_api",
            label="Kimi Coding API",
            configured=integrations.kimi_coding_api,
            importance="core",
            required_for="LLM summarization, classification, and digest enrichment",
            env_var="MOONSHOT_API_KEY",
            setup_hint=(
                f"Set MOONSHOT_API_KEY in .env; current provider is "
                f"{settings.llm_provider} using {settings.moonshot_model}."
            ),
        ),
        SetupItem(
            key="github_api",
            label="GitHub API",
            configured=integrations.github_api,
            importance="recommended",
            required_for="higher-rate public repository search and open-source AI signal ingestion",
            env_var="GITHUB_TOKEN",
            setup_hint=(
                "Set GITHUB_TOKEN in .env to raise GitHub public API limits; "
                "unauthenticated search still works at a lower limit."
            ),
        ),
        SetupItem(
            key="alpha_vantage_api",
            label="Alpha Vantage",
            configured=integrations.alpha_vantage_api,
            importance="recommended",
            required_for="watched-stock news and daily price snapshots",
            env_var="ALPHA_VANTAGE_API_KEY",
            setup_hint="Set ALPHA_VANTAGE_API_KEY in .env for stock news and prices.",
        ),
        SetupItem(
            key="sec_user_agent",
            label="SEC User-Agent",
            configured=integrations.sec_user_agent,
            importance="recommended",
            required_for="official SEC EDGAR filings ingestion",
            env_var="SEC_USER_AGENT",
            setup_hint=(
                "Set SEC_USER_AGENT in .env to a descriptive app/contact string "
                "for SEC EDGAR requests."
            ),
        ),
        SetupItem(
            key="product_hunt_api",
            label="Product Hunt",
            configured=integrations.product_hunt_api,
            importance="optional",
            required_for="AI product launch ingestion",
            env_var="PRODUCT_HUNT_API_TOKEN",
            setup_hint="Set PRODUCT_HUNT_API_TOKEN in .env to collect public launch metadata.",
        ),
        SetupItem(
            key="chinese_rss_feeds",
            label="Chinese RSS Feeds",
            configured=integrations.chinese_rss_feeds,
            importance="recommended",
            required_for="Chinese-language AI trend ingestion from public feeds",
            env_var="CHINESE_RSS_FEEDS",
            setup_hint=(
                "Set CHINESE_RSS_FEEDS as comma-separated Name|URL entries; "
                "use public RSS/Atom feeds only."
            ),
        ),
    ]


def build_missing_env_template(items: list[SetupItem]) -> str:
    missing_items = [item for item in items if not item.configured]
    if not missing_items:
        return ""

    lines = ["# SignalLens missing optional/core setup values"]
    for item in missing_items:
        lines.append(f"# {item.label}: {item.required_for}")
        lines.append(f"{item.env_var}={placeholder_for_env_var(item.env_var)}")
    return "\n".join(lines)


def build_setup_summary(items: list[SetupItem]) -> SetupSummary:
    missing_items = [item for item in items if not item.configured]
    return SetupSummary(
        total=len(items),
        configured=len(items) - len(missing_items),
        missing=len(missing_items),
        core_missing=count_missing_by_importance(missing_items, "core"),
        recommended_missing=count_missing_by_importance(missing_items, "recommended"),
        optional_missing=count_missing_by_importance(missing_items, "optional"),
        core_ready=not any(item.importance == "core" for item in missing_items),
    )


def count_missing_by_importance(
    items: list[SetupItem],
    importance: str,
) -> int:
    return sum(1 for item in items if item.importance == importance)


def placeholder_for_env_var(env_var: str) -> str:
    placeholders = {
        "MOONSHOT_API_KEY": "sk-...",
        "GITHUB_TOKEN": "ghp_...",
        "ALPHA_VANTAGE_API_KEY": "your-alpha-vantage-key",
        "SEC_USER_AGENT": "SignalLens/0.1 your-email@example.com",
        "PRODUCT_HUNT_API_TOKEN": "your-product-hunt-token",
        "CHINESE_RSS_FEEDS": "Name|https://example.com/feed.xml",
    }
    return placeholders.get(env_var, "replace-me")
