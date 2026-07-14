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
    Source,
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
    MvpChecklistItem,
    MvpChecklistResponse,
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

PRD_SOURCE_FAMILIES = {
    "arxiv": "arXiv",
    "hacker_news": "Hacker News",
    "rss": "selected RSS",
    "alpha_vantage": "Alpha Vantage",
    "product_hunt": "Product Hunt",
    "github": "GitHub",
    "hugging_face": "Hugging Face",
    "chinese_rss": "Chinese RSS",
}


class LlmUsageSummary(TypedDict):
    call_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float
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


@router.get("/mvp-checklist", response_model=MvpChecklistResponse)
async def mvp_checklist(
    db: DbSession,
    window_days: int = Query(default=7, ge=1, le=90),
) -> MvpChecklistResponse:
    settings = get_settings()
    integrations = IntegrationStatus(
        kimi_coding_api=has_config_value(settings.moonshot_api_key),
        github_api=has_config_value(settings.github_token),
        product_hunt_api=has_config_value(settings.product_hunt_api_token),
        alpha_vantage_api=has_config_value(settings.alpha_vantage_api_key),
        sec_user_agent=has_custom_sec_user_agent(settings.sec_user_agent),
        chinese_rss_feeds=has_config_value(settings.chinese_rss_feeds),
    )
    setup_summary = build_setup_summary(
        build_setup_items(settings=settings, integrations=integrations)
    )
    metrics = build_quality_metrics(db=db, window_days=window_days, settings=settings)
    source_count, enabled_source_count = count_sources_by_enabled_state(db)
    source_family_coverage = summarize_prd_source_family_coverage(db)
    return build_mvp_checklist_response(
        metrics=metrics,
        setup_summary=setup_summary,
        llm_configured=has_config_value(settings.moonshot_api_key),
        source_count=source_count,
        enabled_source_count=enabled_source_count,
        source_family_coverage=source_family_coverage,
    )


def build_quality_metrics(
    db: Session,
    window_days: int = 7,
    settings: Settings | None = None,
) -> QualityMetricsResponse:
    settings = settings or get_settings()
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
    llm_usage = summarize_recent_llm_usage(db=db, since=since, settings=settings)
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
    alert_usefulness_proxy = build_alert_usefulness_proxy(
        active_alert_count=alert_counts["active"],
        dismissed_alert_count=alert_counts["dismissed"],
    )
    digest_snapshot_count = count_recent_digest_snapshots(db=db, since=since)
    digest_feedback_counts = count_digest_snapshot_feedback(db=db, since=since)
    digest_feedback_count = sum(digest_feedback_counts.values())
    digest_feedback_usefulness_rate = (
        ratio(digest_feedback_counts["useful"], digest_feedback_count)
        if digest_feedback_count
        else None
    )
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
    digest_usefulness_proxy = build_digest_usefulness_proxy(
        latest_digest_age_days=latest_digest_age_days,
        latest_digest_snapshot_item_count=latest_digest_snapshot_item_count,
        recent_item_count=recent_item_count,
        digest_feedback_useful_count=digest_feedback_counts["useful"],
        digest_feedback_not_useful_count=digest_feedback_counts["not_useful"],
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
    llm_pricing_configured = is_llm_pricing_configured(settings)
    llm_projected_monthly_cost_usd = project_monthly_cost(
        cost_usd=llm_usage["estimated_cost_usd"],
        window_days=window_days,
    )
    llm_monthly_budget_usage = (
        ratio(llm_projected_monthly_cost_usd, settings.llm_monthly_budget_usd)
        if settings.llm_monthly_budget_usd > 0
        else None
    )
    source_api_estimated_cost_usd = estimate_source_api_cost_usd(
        call_count=source_run_count,
        settings=settings,
    )
    source_api_projected_monthly_cost_usd = project_monthly_cost(
        cost_usd=source_api_estimated_cost_usd,
        window_days=window_days,
    )
    source_api_monthly_budget_usage = (
        ratio(source_api_projected_monthly_cost_usd, settings.source_api_monthly_budget_usd)
        if settings.source_api_monthly_budget_usd > 0
        else None
    )

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
        alert_usefulness_proxy=alert_usefulness_proxy,
        digest_snapshot_count=digest_snapshot_count,
        digest_feedback_count=digest_feedback_count,
        digest_useful_feedback_count=digest_feedback_counts["useful"],
        digest_not_useful_feedback_count=digest_feedback_counts["not_useful"],
        digest_feedback_usefulness_rate=digest_feedback_usefulness_rate,
        digest_usefulness_proxy=digest_usefulness_proxy,
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
        llm_pricing_configured=llm_pricing_configured,
        llm_estimated_cost_usd=llm_usage["estimated_cost_usd"],
        llm_projected_monthly_cost_usd=llm_projected_monthly_cost_usd,
        llm_monthly_budget_usd=round(settings.llm_monthly_budget_usd, 6),
        llm_monthly_budget_usage=llm_monthly_budget_usage,
        llm_estimated_cost_per_recent_item_usd=cost_per_unit(
            llm_usage["estimated_cost_usd"],
            recent_item_count,
        ),
        llm_estimated_cost_per_digest_usd=cost_per_unit(
            llm_usage["estimated_cost_usd"],
            digest_snapshot_count,
        ),
        llm_estimated_cost_per_active_alert_usd=cost_per_unit(
            llm_usage["estimated_cost_usd"],
            alert_counts["active"],
        ),
        llm_operation_usage=llm_usage["operation_usage"],
        source_api_call_count=source_run_count,
        source_api_calls_per_recent_item=ratio(source_run_count, recent_item_count),
        source_api_pricing_configured=is_source_api_pricing_configured(settings),
        source_api_estimated_cost_usd=source_api_estimated_cost_usd,
        source_api_projected_monthly_cost_usd=source_api_projected_monthly_cost_usd,
        source_api_monthly_budget_usd=round(settings.source_api_monthly_budget_usd, 6),
        source_api_monthly_budget_usage=source_api_monthly_budget_usage,
        source_api_estimated_cost_per_recent_item_usd=cost_per_unit(
            source_api_estimated_cost_usd,
            recent_item_count,
        ),
        source_api_estimated_cost_per_digest_usd=cost_per_unit(
            source_api_estimated_cost_usd,
            digest_snapshot_count,
        ),
        source_api_estimated_cost_per_active_alert_usd=cost_per_unit(
            source_api_estimated_cost_usd,
            alert_counts["active"],
        ),
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
            llm_pricing_configured=llm_pricing_configured,
            llm_projected_monthly_cost_usd=llm_projected_monthly_cost_usd,
            llm_monthly_budget_usd=settings.llm_monthly_budget_usd,
            source_api_pricing_configured=is_source_api_pricing_configured(settings),
            source_api_projected_monthly_cost_usd=source_api_projected_monthly_cost_usd,
            source_api_monthly_budget_usd=settings.source_api_monthly_budget_usd,
        ),
    )


def count_sources_by_enabled_state(db: Session) -> tuple[int, int]:
    rows = db.query(Source.enabled).all()
    return len(rows), sum(1 for row in rows if unwrap_bool(row))


def summarize_prd_source_family_coverage(db: Session) -> tuple[int, int, list[str], list[str]]:
    covered_keys: set[str] = set()
    for source in db.query(Source).filter(Source.enabled.is_(True)).all():
        covered_keys.update(prd_source_family_keys_for_source(source))

    ordered_keys = list(PRD_SOURCE_FAMILIES)
    covered_labels = [
        PRD_SOURCE_FAMILIES[key] for key in ordered_keys if key in covered_keys
    ]
    missing_labels = [
        PRD_SOURCE_FAMILIES[key] for key in ordered_keys if key not in covered_keys
    ]
    return len(covered_labels), len(PRD_SOURCE_FAMILIES), covered_labels, missing_labels


def prd_source_family_keys_for_source(source: Source) -> set[str]:
    name = normalize_source_family_text(source.name)
    source_type = normalize_source_family_text(source.type)
    access_method = normalize_source_family_text(source.access_method)
    base_url = normalize_source_family_text(source.base_url)
    combined = " ".join([name, source_type, access_method, base_url])

    keys: set[str] = set()
    if "arxiv" in combined:
        keys.add("arxiv")
    if "hacker news" in combined or "firebaseio" in combined:
        keys.add("hacker_news")
    if "github" in combined:
        keys.add("github")
    if "hugging face" in combined or "huggingface" in combined:
        keys.add("hugging_face")
    if "product hunt" in combined or "producthunt" in combined:
        keys.add("product_hunt")
    if "alpha vantage" in combined or "alphavantage" in combined:
        keys.add("alpha_vantage")
    if "chinese rss" in combined or source_type == "chinese social":
        keys.add("chinese_rss")
    if "rss" in combined or "atom" in combined or source_type in {"rss", "company blog"}:
        if "chinese" not in combined:
            keys.add("rss")
    return keys


def normalize_source_family_text(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def build_mvp_checklist_response(
    *,
    metrics: QualityMetricsResponse,
    setup_summary: SetupSummary,
    llm_configured: bool,
    source_count: int,
    enabled_source_count: int,
    source_family_coverage: tuple[int, int, list[str], list[str]] | None = None,
) -> MvpChecklistResponse:
    items = build_mvp_checklist_items(
        metrics=metrics,
        setup_summary=setup_summary,
        llm_configured=llm_configured,
        source_count=source_count,
        enabled_source_count=enabled_source_count,
        source_family_coverage=source_family_coverage,
    )
    ready_count = sum(1 for item in items if item.status == "ready")
    partial_count = sum(1 for item in items if item.status == "partial")
    needs_action_count = sum(1 for item in items if item.status == "needs_action")
    return MvpChecklistResponse(
        generated_at=metrics.generated_at,
        total_count=len(items),
        ready_count=ready_count,
        partial_count=partial_count,
        needs_action_count=needs_action_count,
        items=items,
    )


def build_mvp_checklist_items(
    *,
    metrics: QualityMetricsResponse,
    setup_summary: SetupSummary,
    llm_configured: bool,
    source_count: int,
    enabled_source_count: int,
    source_family_coverage: tuple[int, int, list[str], list[str]] | None = None,
) -> list[MvpChecklistItem]:
    recent_items = metrics.recent_item_count
    covered_modules = metrics.covered_module_count
    classification_coverage = metrics.classification_coverage
    summary_coverage = metrics.summary_coverage
    source_family_coverage = source_family_coverage or (0, len(PRD_SOURCE_FAMILIES), [], [])
    (
        covered_source_families,
        total_source_families,
        covered_source_family_labels,
        missing_source_family_labels,
    ) = source_family_coverage
    latest_stock_price = (
        metrics.latest_stock_price_date.isoformat()
        if metrics.latest_stock_price_date
        else "no price"
    )
    latest_digest_age = metrics.latest_digest_age_days

    return [
        MvpChecklistItem(
            key="dashboard-feed",
            label="Ranked Dashboard",
            status=(
                "ready"
                if recent_items > 0 and covered_modules >= 3
                else "partial"
                if recent_items > 0
                else "needs_action"
            ),
            metric=f"{recent_items} recent; {covered_modules}/5 modules",
            note=(
                "Feed data is available across the first-class PRD modules."
                if recent_items > 0
                else "Run a source cycle or seed demo data to populate the ranked feed."
            ),
            action_label="Open Dashboard" if recent_items > 0 else "Seed Demo Data",
            action_module="dashboard",
            action_operation=None if recent_items > 0 else "demo-data:seed",
            action_target_id="ranked-feed-workflow",
        ),
        MvpChecklistItem(
            key="source-ingestion",
            label="Source Ingestion",
            status=(
                "ready"
                if covered_source_families >= 6 and metrics.recent_source_count >= 3
                else "partial"
                if enabled_source_count > 0
                else "needs_action"
            ),
            metric=(
                f"{covered_source_families}/{total_source_families} PRD families; "
                f"{metrics.recent_source_count} recent sources"
            ),
            note=(
                "Covered: "
                f"{', '.join(covered_source_family_labels[:5])}"
                f"{'...' if len(covered_source_family_labels) > 5 else ''}."
                if covered_source_family_labels
                else "Enable followed sources before relying on daily collection."
            )
            + (
                " Missing: " + ", ".join(missing_source_family_labels[:3]) + "."
                if missing_source_family_labels and enabled_source_count > 0
                else ""
            ),
            action_label=(
                "Run Full Cycle"
                if enabled_source_count > 0 and metrics.recent_source_count < 3
                else "Open Sources"
            ),
            action_module="sources",
            action_operation=(
                "cycle"
                if enabled_source_count > 0 and metrics.recent_source_count < 3
                else None
            ),
            action_source_filter=(
                "attention"
                if enabled_source_count > 0 and metrics.recent_source_count < 3
                else None
            ),
            action_target_id="source-health-workflow",
        ),
        MvpChecklistItem(
            key="llm-processing",
            label="LLM Processing",
            status=(
                "ready"
                if llm_configured
                and classification_coverage >= 0.7
                and summary_coverage >= 0.5
                else "partial"
                if llm_configured or metrics.llm_call_count > 0
                else "needs_action"
            ),
            metric=(
                f"{format_quality_percent(classification_coverage)} classified; "
                f"{format_quality_percent(summary_coverage)} summarized"
            ),
            note=(
                "Kimi is configured; coverage depends on running capped "
                "classify/summarize batches."
                if llm_configured
                else "Add an LLM key before expecting model-generated summaries."
            ),
            action_label="Run Classification" if llm_configured else "Open Settings",
            action_module="dashboard" if llm_configured else "settings",
            action_operation="llm:classify" if llm_configured else None,
            action_target_id="ranked-feed-workflow" if llm_configured else "settings-workflow",
        ),
        MvpChecklistItem(
            key="watchlists",
            label="Personal Watchlists",
            status=(
                "ready"
                if metrics.watchlist_area_count >= 4
                else "partial"
                if total_watchlist_count(metrics) > 0
                else "needs_action"
            ),
            metric=(
                f"{metrics.watchlist_area_count}/4 areas; "
                f"{total_watchlist_count(metrics)} rows"
            ),
            note=(
                "Stock, company, topic, and product watchlists shape ranking and digest context."
                if total_watchlist_count(metrics) > 0
                else "Seed or create watchlists so personalization has a profile to use."
            ),
            action_label="Open Watchlists",
            action_module="stocks",
            action_target_id="stock-watchlist-workflow",
        ),
        MvpChecklistItem(
            key="stock-watchlist",
            label="AI Stock Watchlist",
            status=(
                "ready"
                if metrics.stock_watchlist_count > 0 and metrics.latest_stock_price_date
                else "partial"
                if metrics.stock_watchlist_count > 0
                else "needs_action"
            ),
            metric=f"{metrics.stock_watchlist_count} tickers; {latest_stock_price}",
            note=(
                "Ticker monitoring is available; fresh prices improve market-context checks."
                if metrics.stock_watchlist_count > 0
                else "Add or seed watched tickers before relying on stock signals."
            ),
            action_label=(
                "Refresh Prices"
                if metrics.stock_watchlist_count > 0 and not metrics.latest_stock_price_date
                else "Open Stocks"
            ),
            action_module="stocks",
            action_operation=(
                "stock-prices:refresh"
                if metrics.stock_watchlist_count > 0 and not metrics.latest_stock_price_date
                else None
            ),
            action_target_id="stock-watchlist-workflow",
        ),
        MvpChecklistItem(
            key="search",
            label="Searchable Archive",
            status=(
                "ready"
                if recent_items > 0 and metrics.search_facet_coverage >= 0.7
                else "partial"
                if recent_items > 0
                else "needs_action"
            ),
            metric=f"{format_quality_percent(metrics.search_facet_coverage)} faceted",
            note=(
                "Facet coverage indicates whether search can filter by topics, "
                "tickers, sources, and tags."
                if recent_items > 0
                else "Search becomes useful after ingestion creates normalized items."
            ),
            action_label=(
                "Run Classification"
                if recent_items > 0 and metrics.search_facet_coverage < 0.7
                else "Open Dashboard"
            ),
            action_module="dashboard",
            action_operation=(
                "llm:classify"
                if recent_items > 0 and metrics.search_facet_coverage < 0.7
                else None
            ),
            action_target_id="ranked-feed-workflow",
        ),
        MvpChecklistItem(
            key="daily-digest",
            label="Daily Digest",
            status=(
                "ready"
                if latest_digest_age is not None and latest_digest_age <= 1
                else "partial"
                if metrics.digest_snapshot_count > 0
                else "needs_action"
            ),
            metric=(
                f"{metrics.digest_snapshot_count} snapshots"
                if latest_digest_age is None
                else f"{metrics.digest_snapshot_count} snapshots; {latest_digest_age}d old"
            ),
            note=(
                "A saved digest exists; morning readiness depends on keeping the snapshot fresh."
                if metrics.digest_snapshot_count > 0
                else "Generate and save a digest snapshot to lock in a daily brief."
            ),
            action_label=(
                "Open Digest"
                if latest_digest_age is not None and latest_digest_age <= 1
                else "Save Digest"
            ),
            action_module="digest",
            action_operation=(
                None
                if latest_digest_age is not None and latest_digest_age <= 1
                else "digest:save-snapshot"
            ),
            action_target_id="digest-workflow",
        ),
        MvpChecklistItem(
            key="alerts",
            label="Dashboard Alerts",
            status=(
                "ready"
                if metrics.active_alert_count > 0
                else "partial"
                if metrics.dismissed_alert_count > 0
                else "needs_action"
            ),
            metric=f"{metrics.active_alert_count} active",
            note=(
                "Dashboard alert rules are producing active signals."
                if metrics.active_alert_count > 0
                else "Generate alerts after ingestion to validate stock, product, and trend rules."
            ),
            action_label="Open Alerts" if metrics.active_alert_count > 0 else "Generate Alerts",
            action_module="alerts",
            action_operation=None if metrics.active_alert_count > 0 else "alerts:generate",
            action_target_id="alerts-workflow",
        ),
        MvpChecklistItem(
            key="manual-submission",
            label="Manual URL Submission",
            status="ready" if metrics.manual_submission_count > 0 else "partial",
            metric=f"{metrics.manual_submission_count} recent",
            note=(
                "Recent manual submissions are flowing into the same feed pipeline."
                if metrics.manual_submission_count > 0
                else "The submission flow is available; paste a URL when a source has no connector."
            ),
            action_label=(
                "Open Submission"
                if recent_items > 0
                else "Seed Demo Data"
            ),
            action_module="submit" if recent_items > 0 else "dashboard",
            action_operation=None if recent_items > 0 else "demo-data:seed",
            action_target_id="manual-submission-workflow",
        ),
    ]


def total_watchlist_count(metrics: QualityMetricsResponse) -> int:
    return (
        metrics.stock_watchlist_count
        + metrics.company_watchlist_count
        + metrics.topic_watchlist_count
        + metrics.product_watchlist_count
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


def count_digest_snapshot_feedback(db: Session, since: datetime) -> dict[str, int]:
    counts = {"useful": 0, "not_useful": 0}
    snapshots = (
        db.query(DailyDigestSnapshot.payload)
        .filter(
            DailyDigestSnapshot.user_id == LOCAL_USER_ID,
            DailyDigestSnapshot.generated_at >= since,
        )
        .all()
    )
    for (payload,) in snapshots:
        feedback = (payload or {}).get("usefulness_feedback")
        if feedback in counts:
            counts[feedback] += 1
    return counts


def digest_age_days(
    latest_digest_snapshot_date: date | None,
    current_date: date,
) -> int | None:
    if latest_digest_snapshot_date is None:
        return None
    return max(0, (current_date - latest_digest_snapshot_date).days)


def build_digest_usefulness_proxy(
    *,
    latest_digest_age_days: int | None,
    latest_digest_snapshot_item_count: int | None,
    recent_item_count: int,
    digest_feedback_useful_count: int = 0,
    digest_feedback_not_useful_count: int = 0,
) -> float:
    if latest_digest_age_days is None or not latest_digest_snapshot_item_count:
        base_score = 0.0
    else:
        if latest_digest_age_days <= 1:
            freshness_score = 1.0
        elif latest_digest_age_days <= 3:
            freshness_score = 0.65
        elif latest_digest_age_days <= 7:
            freshness_score = 0.35
        else:
            freshness_score = 0.0

        target_items = min(recent_item_count, 8) if recent_item_count > 0 else 3
        item_score = ratio(min(latest_digest_snapshot_item_count, target_items), target_items)
        base_score = round(0.6 * freshness_score + 0.4 * item_score, 3)

    feedback_total = digest_feedback_useful_count + digest_feedback_not_useful_count
    if feedback_total == 0:
        return base_score

    feedback_score = ratio(digest_feedback_useful_count, feedback_total)
    return round(0.65 * feedback_score + 0.35 * base_score, 3)


def build_alert_usefulness_proxy(
    *,
    active_alert_count: int,
    dismissed_alert_count: int,
) -> float | None:
    total_alerts = active_alert_count + dismissed_alert_count
    if total_alerts == 0:
        return None
    return ratio(active_alert_count, total_alerts)


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


def summarize_recent_llm_usage(
    db: Session,
    since: datetime,
    settings: Settings,
) -> LlmUsageSummary:
    rows = (
        db.query(LlmUsageEvent)
        .filter(LlmUsageEvent.user_id == LOCAL_USER_ID, LlmUsageEvent.created_at >= since)
        .all()
    )
    operation_totals: dict[str, dict[str, int | float]] = {}
    for row in rows:
        totals = operation_totals.setdefault(
            row.operation,
            {
                "call_count": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0,
            },
        )
        totals["call_count"] += 1
        totals["input_tokens"] += row.input_tokens
        totals["output_tokens"] += row.output_tokens
        totals["total_tokens"] += row.total_tokens
        totals["estimated_cost_usd"] += estimate_llm_cost_usd(
            input_tokens=row.input_tokens,
            output_tokens=row.output_tokens,
            settings=settings,
        )

    operation_usage = [
        LlmOperationUsage(operation=operation, **totals)
        for operation, totals in sorted(
            normalized_llm_operation_totals(operation_totals).items(),
            key=lambda item: (-int(item[1]["total_tokens"]), item[0]),
        )
    ]
    return {
        "call_count": len(rows),
        "input_tokens": sum(row.input_tokens for row in rows),
        "output_tokens": sum(row.output_tokens for row in rows),
        "total_tokens": sum(row.total_tokens for row in rows),
        "estimated_cost_usd": estimate_llm_cost_usd(
            input_tokens=sum(row.input_tokens for row in rows),
            output_tokens=sum(row.output_tokens for row in rows),
            settings=settings,
        ),
        "operation_usage": operation_usage,
    }


def normalized_llm_operation_totals(
    operation_totals: dict[str, dict[str, int | float]],
) -> dict[str, dict[str, int | float]]:
    return {
        operation: {
            **totals,
            "estimated_cost_usd": round(float(totals["estimated_cost_usd"]), 6),
        }
        for operation, totals in operation_totals.items()
    }


def is_llm_pricing_configured(settings: Settings) -> bool:
    return (
        settings.llm_input_cost_per_1m_tokens > 0
        or settings.llm_output_cost_per_1m_tokens > 0
    )


def estimate_llm_cost_usd(
    *,
    input_tokens: int,
    output_tokens: int,
    settings: Settings,
) -> float:
    input_cost = (input_tokens / 1_000_000) * settings.llm_input_cost_per_1m_tokens
    output_cost = (output_tokens / 1_000_000) * settings.llm_output_cost_per_1m_tokens
    return round(input_cost + output_cost, 6)


def is_source_api_pricing_configured(settings: Settings) -> bool:
    return settings.source_api_cost_per_1k_calls_usd > 0


def estimate_source_api_cost_usd(*, call_count: int, settings: Settings) -> float:
    return round((call_count / 1_000) * settings.source_api_cost_per_1k_calls_usd, 6)


def project_monthly_cost(cost_usd: float, window_days: int) -> float:
    if window_days <= 0:
        return round(cost_usd, 6)
    return round(cost_usd * 30 / window_days, 6)


def cost_per_unit(cost_usd: float, count: int) -> float | None:
    if count <= 0:
        return None
    return round(cost_usd / count, 6)


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
    llm_pricing_configured: bool = False,
    llm_projected_monthly_cost_usd: float = 0,
    llm_monthly_budget_usd: float = 0,
    source_api_pricing_configured: bool = False,
    source_api_projected_monthly_cost_usd: float = 0,
    source_api_monthly_budget_usd: float = 0,
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
                action_label="Open Watchlists",
                action_module="stocks",
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
                action_module="alerts",
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
    if (
        llm_pricing_configured
        and llm_monthly_budget_usd > 0
        and llm_projected_monthly_cost_usd > llm_monthly_budget_usd
    ):
        findings.append(
            QualityFinding(
                severity="warning",
                title="LLM budget projection is high",
                metric=(
                    f"${llm_projected_monthly_cost_usd:.2f}/mo projected "
                    f"vs ${llm_monthly_budget_usd:.2f} budget"
                ),
                recommendation=(
                    "Lower batch limits, run module-scoped enrichment, or skip already enriched "
                    "items before running more cost-bearing LLM actions."
                ),
                action_label="Review Settings",
                action_module="settings",
            )
        )
    if (
        source_api_pricing_configured
        and source_api_monthly_budget_usd > 0
        and source_api_projected_monthly_cost_usd > source_api_monthly_budget_usd
    ):
        findings.append(
            QualityFinding(
                severity="warning",
                title="Source API budget projection is high",
                metric=(
                    f"${source_api_projected_monthly_cost_usd:.2f}/mo projected "
                    f"vs ${source_api_monthly_budget_usd:.2f} budget"
                ),
                recommendation=(
                    "Review Source Health, lower polling frequency, or disable optional paid "
                    "connectors before running more ingestion cycles."
                ),
                action_label="Review Sources",
                action_module="sources",
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
