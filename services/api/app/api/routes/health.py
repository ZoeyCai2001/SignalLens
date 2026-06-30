import re
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.api.deps import DbSession
from app.core.config import DEFAULT_SEC_USER_AGENT, Settings, get_settings
from app.db.models import Alert, DailyDigestSnapshot, NormalizedItem, SourceRun, UserItemAction
from app.schemas.health import (
    HealthResponse,
    IntegrationStatus,
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
    alert_counts = count_alerts_by_status(db)
    source_run_count, source_failure_count = count_recent_source_runs(db=db, since=since)

    return QualityMetricsResponse(
        generated_at=generated_at,
        window_days=window_days,
        total_item_count=len(total_rows),
        recent_item_count=len(recent_rows),
        high_value_item_count=sum(1 for item in recent_rows if item.importance_score >= 0.75),
        relevance_precision_proxy=ratio(
            sum(1 for item in recent_rows if item.relevance_score >= 0.5),
            len(recent_rows),
        ),
        duplicate_rate=duplicate_rate_for_items(recent_rows),
        summary_coverage=ratio(
            sum(1 for item in recent_rows if item.summary_short or item.summary_detailed),
            len(recent_rows),
        ),
        source_failure_rate=ratio(source_failure_count, source_run_count),
        save_count=save_count,
        hide_count=hide_count,
        save_hide_ratio=round(save_count / hide_count, 3) if hide_count else None,
        active_alert_count=alert_counts["active"],
        dismissed_alert_count=alert_counts["dismissed"],
        alert_dismissal_rate=ratio(
            alert_counts["dismissed"],
            alert_counts["active"] + alert_counts["dismissed"],
        ),
        digest_snapshot_count=count_recent_digest_snapshots(db=db, since=since),
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
