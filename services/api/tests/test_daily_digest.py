from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes import digest as digest_routes
from app.db.models import (
    Alert,
    AlertRule,
    Base,
    CompanyWatchlistItem,
    NormalizedItem,
    ProductWatchlistItem,
    UserItemAction,
    UserPreference,
)
from app.db.models import DailyDigestSnapshot as DailyDigestSnapshotModel
from app.schemas.digest import DailyDigest
from app.schemas.feed import FeedItem
from app.services.daily_digest import (
    build_digest_overview_metrics,
    build_digest_item_labels,
    build_digest_sections,
    build_headline,
    build_source_coverage,
    digest_rank_score,
    delete_daily_digest_snapshot,
    filter_items_by_excluded_topics,
    generate_daily_digest,
    list_active_digest_alerts,
    list_excluded_digest_company_terms,
    list_excluded_digest_product_terms,
    list_visible_items_for_digest_date,
    list_watchlist_companies,
    render_digest_markdown,
    select_latest_digest_date,
    serialize_daily_digest_snapshot,
    sort_for_digest,
)


def test_daily_digest_sections_group_items() -> None:
    items = [
        make_item(1, "Research", "research", 0.9, topics=["llm"]),
        make_item(2, "Product", "product", 0.8, products=["Tool"]),
        make_item(3, "Stock", "stock_company_event", 0.7, tickers=["MU"]),
        make_item(4, "Repo", "technical_trend", 0.6, source_name="GitHub"),
        make_item(5, "Saved", "technical_trend", 0.5, is_saved=True),
        make_item(7, "Read saved", "technical_trend", 0.4, is_saved=True, is_read=True),
        make_item(6, "Company", "technical_trend", 0.65, companies=["OpenAI"]),
    ]

    sections = build_digest_sections(items, limit_per_section=3)

    section_map = {section.key: section for section in sections}
    assert section_map["top_signals"].items[0].title == "Research"
    assert section_map["research"].items[0].title == "Research"
    assert section_map["products"].items[0].title == "Product"
    assert section_map["company_watchlist"].items[0].title == "Company"
    assert section_map["stock_watchlist"].items[0].title == "Stock"
    assert section_map["developer_highlights"].items[0].title == "Repo"
    assert section_map["read_later"].items[0].title == "Saved"
    assert "Read saved" not in {item.title for item in section_map["read_later"].items}


def test_daily_digest_source_coverage_counts_sources() -> None:
    items = [
        make_item(1, "A", "research", 0.9, source_name="arXiv"),
        make_item(2, "B", "research", 0.8, source_name="arXiv"),
        make_item(3, "C", "product", 0.7, source_name="Hacker News"),
    ]

    coverage = build_source_coverage(items)

    assert coverage[0].source_name == "arXiv"
    assert coverage[0].item_count == 2
    assert coverage[1].source_name == "Hacker News"


def test_daily_digest_overview_metrics_count_key_triage_groups() -> None:
    items = [
        make_item(1, "Research", "research", 0.9, source_name="arXiv"),
        make_item(2, "Stock", "stock_company_event", 0.8, source_name="Finance", tickers=["MU"]),
        make_item(3, "Saved", "technical_trend", 0.6, source_name="Hacker News", is_saved=True),
        make_item(
            4,
            "Read saved",
            "technical_trend",
            0.5,
            source_name="Hacker News",
            is_saved=True,
            is_read=True,
        ),
    ]

    metrics = build_digest_overview_metrics(items, build_source_coverage(items))

    assert metrics == {
        "high_impact_count": 2,
        "stock_signal_count": 1,
        "read_later_count": 1,
        "source_count": 3,
    }


def test_sort_for_digest_uses_source_quality_and_confidence() -> None:
    lower_trust = make_item(
        1,
        "Slightly higher importance rumor",
        "technical_trend",
        0.74,
        source_quality_score=0.55,
        classification_confidence=0.5,
    )
    trusted = make_item(
        2,
        "Trusted source confirmation",
        "technical_trend",
        0.7,
        source_quality_score=0.9,
        classification_confidence=0.85,
    )

    ranked = sort_for_digest([lower_trust, trusted])

    assert ranked[0].title == "Trusted source confirmation"
    assert digest_rank_score(trusted) > digest_rank_score(lower_trust)


def test_sort_for_digest_uses_social_signal() -> None:
    quiet = make_item(
        1,
        "Quiet product signal",
        "product",
        0.7,
        source_quality_score=0.7,
        classification_confidence=0.7,
    )
    popular = make_item(
        2,
        "Popular product signal",
        "product",
        0.7,
        source_quality_score=0.7,
        classification_confidence=0.7,
    )
    popular.social_signal_score = 0.9

    ranked = sort_for_digest([quiet, popular])

    assert ranked[0].title == "Popular product signal"
    assert digest_rank_score(popular) > digest_rank_score(quiet)


def test_build_digest_item_labels_includes_product_names_and_use_case() -> None:
    item = make_item(
        1,
        "AI product launch",
        "product",
        0.8,
        products=["CodePilot", "Coding"],
        topics=["ai coding"],
        subcategory="product_coding",
    )

    assert build_digest_item_labels(item) == ["CodePilot", "Coding", "ai coding"]


def test_daily_digest_headline_handles_empty_day() -> None:
    headline = build_headline([], datetime(2026, 6, 25, tzinfo=UTC).date())

    assert headline == "No collected AI signals for 2026-06-25."


@pytest.mark.anyio
async def test_generate_daily_digest_route_uses_explicit_generation(monkeypatch) -> None:
    digest = DailyDigest(
        digest_date=datetime(2026, 6, 25, tzinfo=UTC).date(),
        generated_at=datetime(2026, 6, 25, 13, 0, tzinfo=UTC),
        headline="Generated digest",
        total_items=0,
        sections=[],
        source_coverage=[],
        disclaimer="For information organization only.",
    )
    calls = []

    def fake_generate_daily_digest(db, digest_date=None, limit_per_section=5):
        calls.append((db, digest_date, limit_per_section))
        return digest

    monkeypatch.setattr(
        digest_routes,
        "generate_daily_digest",
        fake_generate_daily_digest,
    )

    result = await digest_routes.generate_daily_digest_now(
        db="db-session",
        digest_date=datetime(2026, 6, 25, tzinfo=UTC).date(),
        limit_per_section=3,
    )

    assert result.headline == "Generated digest"
    assert calls == [
        ("db-session", datetime(2026, 6, 25, tzinfo=UTC).date(), 3),
    ]


def test_filter_items_by_excluded_topics_removes_digest_excluded_terms() -> None:
    items = [
        make_item(1, "Keep", "technical_trend", 0.8, topics=["agent"]),
        make_item(2, "Exclude", "technical_trend", 0.9, topics=["model routing"]),
        make_item(3, "Product Exclude", "product", 0.7, products=["AI search"]),
        make_item(4, "Coding Product Exclude", "product", 0.7, subcategory="product_coding"),
    ]

    filtered = filter_items_by_excluded_topics(
        items,
        {"model routing", "ai search", "product_coding"},
    )

    assert [item.title for item in filtered] == ["Keep"]


def test_list_excluded_digest_product_terms_includes_use_case_terms() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                ProductWatchlistItem(
                    user_id="local",
                    category="ai-coding-tools",
                    label="AI coding tools",
                    include_in_digest=False,
                    related_terms=["developer agent"],
                ),
                ProductWatchlistItem(
                    user_id="local",
                    category="ai-productivity",
                    label="AI productivity",
                    include_in_digest=True,
                    related_terms=["meeting notes"],
                ),
            ]
        )
        db.commit()

        terms = list_excluded_digest_product_terms(db)

    assert {"ai-coding-tools", "ai coding tools", "developer agent", "product_coding"}.issubset(
        terms
    )
    assert "product_productivity" not in terms


def test_filter_items_by_excluded_topics_checks_companies_and_tickers() -> None:
    items = [
        make_item(1, "OpenAI", "technical_trend", 0.8, companies=["OpenAI"]),
        make_item(2, "NVIDIA", "stock_company_event", 0.9, tickers=["NVDA"]),
        make_item(3, "Keep", "research", 0.7, companies=["Anthropic"]),
    ]

    filtered = filter_items_by_excluded_topics(items, {"openai", "nvda"})

    assert [item.title for item in filtered] == ["Keep"]


def test_list_excluded_digest_company_terms_uses_company_watchlist_toggles() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                CompanyWatchlistItem(
                    user_id="local",
                    company_key="nvidia",
                    company_name="NVIDIA",
                    ticker="NVDA",
                    category="semiconductor",
                    include_in_digest=False,
                    related_terms=["GPU", "AI accelerator"],
                ),
                CompanyWatchlistItem(
                    user_id="local",
                    company_key="openai",
                    company_name="OpenAI",
                    category="ai_lab",
                    include_in_digest=True,
                    related_terms=["ChatGPT"],
                ),
            ]
        )
        db.commit()

        terms = list_excluded_digest_company_terms(db)

    assert {"nvidia", "nvda", "semiconductor", "gpu", "ai accelerator"}.issubset(terms)
    assert "openai" not in terms


def test_list_watchlist_companies_returns_digest_included_companies() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                CompanyWatchlistItem(
                    user_id="local",
                    company_key="openai",
                    company_name="OpenAI",
                    category="ai_lab",
                    priority="High",
                    is_pinned=True,
                    include_in_digest=True,
                ),
                CompanyWatchlistItem(
                    user_id="local",
                    company_key="nvidia",
                    company_name="NVIDIA",
                    ticker="NVDA",
                    category="semiconductor",
                    priority="Medium",
                    include_in_digest=False,
                ),
            ]
        )
        db.commit()

        companies = list_watchlist_companies(db)

    assert companies == ["OpenAI"]


def test_render_digest_markdown_includes_sections_links_and_disclaimer() -> None:
    items = [
        make_item(1, "Research", "research", 0.9, topics=["llm"]),
        make_item(2, "Stock", "stock_company_event", 0.8, tickers=["MU"]),
        make_item(
            3,
            "Product",
            "product",
            0.85,
            products=["CodePilot"],
            subcategory="product_coding",
        ),
    ]
    digest = DailyDigest(
        digest_date=datetime(2026, 6, 25, tzinfo=UTC).date(),
        generated_at=datetime(2026, 6, 25, 13, 0, tzinfo=UTC),
        headline="2 AI signals for 2026-06-25.",
        total_items=2,
        sections=build_digest_sections(items, limit_per_section=2),
        source_coverage=build_source_coverage(items),
        watchlist_tickers=["MU", "MRVL"],
        watchlist_companies=["OpenAI", "Anthropic"],
        disclaimer="Informational only.",
    )

    markdown = render_digest_markdown(digest)

    assert markdown.startswith("# SignalLens Daily Digest - 2026-06-25")
    assert "Ticker watchlist: MU, MRVL" in markdown
    assert "Company watchlist: OpenAI, Anthropic" in markdown
    assert "## AI Research" in markdown
    assert "- [Research](https://example.com/1) - Test Source" in markdown
    assert "- [Product](https://example.com/3) - Test Source (CodePilot, Coding)" in markdown
    assert "## Disclaimer" in markdown
    assert markdown.endswith("Informational only.\n")


def test_render_digest_markdown_includes_active_alerts() -> None:
    digest = DailyDigest(
        digest_date=datetime(2026, 6, 25, tzinfo=UTC).date(),
        generated_at=datetime(2026, 6, 25, 13, 0, tzinfo=UTC),
        headline="1 AI signal for 2026-06-25.",
        total_items=1,
        active_alert_count=1,
        sections=[],
        active_alerts=[
            {
                "id": 9,
                "title": "Urgent stock signal",
                "reason": "High-impact stock signal: importance 90",
                "severity": "high",
                "rule_name": "High-impact stock signal",
                "created_at": datetime(2026, 6, 25, 13, 5, tzinfo=UTC),
                "item": make_item(9, "Urgent stock signal", "stock_company_event", 0.9),
            }
        ],
        source_coverage=[],
        disclaimer="Informational only.",
    )

    markdown = render_digest_markdown(digest)

    assert "## Active Alerts" in markdown
    assert "- [Urgent stock signal](https://example.com/9) - high via High-impact stock signal" in markdown
    assert "High-impact stock signal: importance 90" in markdown


def test_list_active_digest_alerts_excludes_blocked_hidden_and_dismissed_items() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        rule = make_alert_rule(1, "High-impact stock signal", severity="high")
        disabled_rule = make_alert_rule(2, "Disabled rule", enabled=False)
        db.add_all([rule, disabled_rule])
        db.add_all(
            [
                make_normalized_item(1, "Blocked alert item", source_name="Noisy Blog"),
                make_normalized_item(2, "Hidden alert item", source_name="Trusted Blog"),
                make_normalized_item(3, "Dismissed alert item", source_name="Trusted Blog"),
                make_normalized_item(4, "Disabled-rule alert item", source_name="Trusted Blog"),
                make_normalized_item(5, "Visible high alert", source_name="Trusted Blog"),
                make_normalized_item(6, "Visible medium alert", source_name="Trusted Blog"),
            ]
        )
        db.flush()
        dismissed_alert = make_alert(3, rule.id, "Dismissed alert item", severity="high")
        dismissed_alert.status = "dismissed"
        db.add_all(
            [
                make_alert(1, rule.id, "Blocked alert item", severity="high"),
                make_alert(2, rule.id, "Hidden alert item", severity="high"),
                dismissed_alert,
                make_alert(4, disabled_rule.id, "Disabled-rule alert item", severity="high"),
                make_alert(5, rule.id, "Visible high alert", severity="high"),
                make_alert(6, rule.id, "Visible medium alert", severity="medium"),
            ]
        )
        db.add(
            UserPreference(
                user_id="local",
                ranking_weights={},
                preferred_sources=[],
                blocked_sources=["Noisy Blog"],
            )
        )
        db.add(UserPreference(user_id="other", ranking_weights={}, preferred_sources=[]))
        db.add(UserItemAction(user_id="local", item_id=2, is_hidden=True))
        db.commit()

        alerts = list_active_digest_alerts(db, blocked_sources=["Noisy Blog"])
        digest = generate_daily_digest(
            db,
            digest_date=datetime(2026, 6, 25, tzinfo=UTC).date(),
        )

    assert [alert.title for alert in alerts] == ["Visible high alert", "Visible medium alert"]
    assert digest.active_alert_count == 2
    assert [alert.title for alert in digest.active_alerts] == [
        "Visible high alert",
        "Visible medium alert",
    ]


def test_serialize_daily_digest_snapshot_round_trips_payload() -> None:
    digest = DailyDigest(
        digest_date=datetime(2026, 6, 25, tzinfo=UTC).date(),
        generated_at=datetime(2026, 6, 25, 13, 0, tzinfo=UTC),
        headline="Snapshot headline",
        total_items=0,
        sections=[],
        source_coverage=[],
        watchlist_tickers=[],
        watchlist_companies=[],
        disclaimer="Informational only.",
    )
    timestamp = datetime(2026, 6, 25, 13, 5, tzinfo=UTC)
    snapshot = DailyDigestSnapshotModel(
        id=7,
        user_id="local",
        digest_date=digest.digest_date,
        generated_at=digest.generated_at,
        headline=digest.headline,
        total_items=digest.total_items,
        limit_per_section=5,
        payload=digest.model_dump(mode="json"),
        markdown="# Snapshot\n",
        created_at=timestamp,
        updated_at=timestamp,
    )

    serialized = serialize_daily_digest_snapshot(snapshot)

    assert serialized.id == 7
    assert serialized.digest.headline == "Snapshot headline"
    assert serialized.markdown == "# Snapshot\n"


def test_serialize_daily_digest_snapshot_handles_legacy_payload_without_companies() -> None:
    timestamp = datetime(2026, 6, 25, 13, 5, tzinfo=UTC)
    legacy_payload = {
        "digest_date": "2026-06-25",
        "generated_at": "2026-06-25T13:00:00Z",
        "headline": "Legacy snapshot",
        "total_items": 0,
        "sections": [],
        "source_coverage": [],
        "watchlist_tickers": ["MU"],
        "disclaimer": "Informational only.",
    }
    snapshot = DailyDigestSnapshotModel(
        id=8,
        user_id="local",
        digest_date=datetime(2026, 6, 25, tzinfo=UTC).date(),
        generated_at=datetime(2026, 6, 25, 13, 0, tzinfo=UTC),
        headline="Legacy snapshot",
        total_items=0,
        limit_per_section=5,
        payload=legacy_payload,
        markdown="# Legacy\n",
        created_at=timestamp,
        updated_at=timestamp,
    )

    serialized = serialize_daily_digest_snapshot(snapshot)

    assert serialized.digest.watchlist_tickers == ["MU"]
    assert serialized.digest.watchlist_companies == []


def test_delete_daily_digest_snapshot_removes_local_snapshot() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    digest = DailyDigest(
        digest_date=datetime(2026, 6, 25, tzinfo=UTC).date(),
        generated_at=datetime(2026, 6, 25, 13, 0, tzinfo=UTC),
        headline="Snapshot headline",
        total_items=0,
        sections=[],
        source_coverage=[],
        watchlist_tickers=[],
        watchlist_companies=[],
        disclaimer="Informational only.",
    )

    with session_factory() as db:
        db.add(
            DailyDigestSnapshotModel(
                user_id="local",
                digest_date=digest.digest_date,
                generated_at=digest.generated_at,
                headline=digest.headline,
                total_items=digest.total_items,
                limit_per_section=5,
                payload=digest.model_dump(mode="json"),
                markdown="# Snapshot\n",
            )
        )
        db.add(
            DailyDigestSnapshotModel(
                user_id="other",
                digest_date=digest.digest_date,
                generated_at=digest.generated_at,
                headline="Other user snapshot",
                total_items=0,
                limit_per_section=5,
                payload=digest.model_dump(mode="json"),
                markdown="# Other\n",
            )
        )
        db.commit()
        local_snapshot = (
            db.query(DailyDigestSnapshotModel)
            .filter(DailyDigestSnapshotModel.user_id == "local")
            .one()
        )
        other_snapshot = (
            db.query(DailyDigestSnapshotModel)
            .filter(DailyDigestSnapshotModel.user_id == "other")
            .one()
        )

        assert delete_daily_digest_snapshot(db, local_snapshot.id)
        assert not delete_daily_digest_snapshot(db, local_snapshot.id)
        assert not delete_daily_digest_snapshot(db, other_snapshot.id)
        remaining = db.query(DailyDigestSnapshotModel).one()
        assert remaining.user_id == "other"


def test_generate_daily_digest_excludes_blocked_sources_from_preferences() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add(
            UserPreference(
                user_id="local",
                ranking_weights={},
                preferred_sources=[],
                blocked_sources=["Noisy Blog"],
            )
        )
        db.add_all(
            [
                make_normalized_item(1, "Blocked signal", source_name="Noisy Blog"),
                make_normalized_item(2, "Visible signal", source_name="Trusted Blog"),
            ]
        )
        db.commit()

        digest = generate_daily_digest(
            db,
            digest_date=datetime(2026, 6, 25, tzinfo=UTC).date(),
        )

    assert digest.total_items == 1
    assert [item.source_name for item in digest.source_coverage] == ["Trusted Blog"]
    assert [item.title for item in digest.sections[0].items] == ["Visible signal"]


def test_generate_daily_digest_filters_language_preferences() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add(
            UserPreference(
                user_id="local",
                ranking_weights={},
                preferred_sources=[],
                blocked_sources=[],
                language_preferences=["zh"],
            )
        )
        db.add_all(
            [
                make_normalized_item(
                    1,
                    "English signal",
                    source_name="Trusted Blog",
                    language="en",
                ),
                make_normalized_item(
                    2,
                    "Chinese signal",
                    source_name="Trusted Blog",
                    language="zh",
                ),
            ]
        )
        db.commit()

        digest = generate_daily_digest(
            db,
            digest_date=datetime(2026, 6, 25, tzinfo=UTC).date(),
        )

    assert digest.total_items == 1
    assert [item.title for item in digest.sections[0].items] == ["Chinese signal"]


def test_select_latest_digest_date_skips_blocked_sources() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_normalized_item(
                    1,
                    "Older visible signal",
                    source_name="Trusted Blog",
                    published_at=datetime(2026, 6, 24, 12, 0, tzinfo=UTC),
                ),
                make_normalized_item(
                    2,
                    "Newer blocked signal",
                    source_name="Noisy Blog",
                    published_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
                ),
            ]
        )
        db.commit()

        selected_date = select_latest_digest_date(db, blocked_sources=["Noisy Blog"])

    assert selected_date == datetime(2026, 6, 24, tzinfo=UTC).date()


def test_select_latest_digest_date_uses_language_preferences() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_normalized_item(
                    1,
                    "Older Chinese signal",
                    source_name="Trusted Blog",
                    language="zh",
                    published_at=datetime(2026, 6, 24, 12, 0, tzinfo=UTC),
                ),
                make_normalized_item(
                    2,
                    "Newer English signal",
                    source_name="Trusted Blog",
                    language="en",
                    published_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
                ),
            ]
        )
        db.commit()

        selected_date = select_latest_digest_date(db, language_preferences=["zh"])

    assert selected_date == datetime(2026, 6, 24, tzinfo=UTC).date()


def test_list_visible_items_for_digest_date_excludes_blocked_sources() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_normalized_item(1, "Blocked signal", source_name="Noisy Blog"),
                make_normalized_item(2, "Visible signal", source_name="Trusted Blog"),
            ]
        )
        db.commit()

        rows = list_visible_items_for_digest_date(
            db,
            digest_date=datetime(2026, 6, 25, tzinfo=UTC).date(),
            blocked_sources=["Noisy Blog"],
        )

    assert [item.title for item, _action in rows] == ["Visible signal"]


def make_item(
    item_id: int,
    title: str,
    category: str,
    importance_score: float,
    source_name: str = "Test Source",
    topics: list[str] | None = None,
    products: list[str] | None = None,
    tickers: list[str] | None = None,
    companies: list[str] | None = None,
    is_saved: bool = False,
    is_read: bool = False,
    source_quality_score: float = 0.7,
    classification_confidence: float = 0.5,
    subcategory: str | None = None,
) -> FeedItem:
    return FeedItem(
        id=item_id,
        title=title,
        url=f"https://example.com/{item_id}",
        source_name=source_name,
        author=None,
        language="en",
        published_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
        category=category,
        subcategory=subcategory,
        tickers=tickers or [],
        companies=companies or [],
        products=products or [],
        topics=topics or [],
        sentiment="neutral",
        relevance_score=0.8,
        classification_confidence=classification_confidence,
        importance_score=importance_score,
        novelty_score=0.7,
        source_quality_score=source_quality_score,
        stock_impact_score=0.0,
        summary_short=None,
        summary_detailed=None,
        why_it_matters=None,
        is_saved=is_saved,
        is_read=is_read,
    )


def make_normalized_item(
    item_id: int,
    title: str,
    source_name: str,
    published_at: datetime | None = None,
    language: str = "en",
) -> NormalizedItem:
    return NormalizedItem(
        id=item_id,
        raw_item_id=item_id,
        title=title,
        url=f"https://example.com/{item_id}",
        source_name=source_name,
        author=None,
        language=language,
        published_at=published_at or datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
        text=title,
        category="technical_trend",
        subcategory=None,
        tickers=[],
        companies=[],
        products=[],
        topics=["agent"],
        sentiment="neutral",
        relevance_score=0.8,
        classification_confidence=0.8,
        importance_score=0.7,
        novelty_score=0.6,
        source_quality_score=0.7,
        stock_impact_score=0,
    )


def make_alert_rule(
    rule_id: int,
    name: str,
    severity: str = "medium",
    enabled: bool = True,
) -> AlertRule:
    return AlertRule(
        id=rule_id,
        user_id="local",
        name=name,
        category="all",
        severity=severity,
        min_importance_score=0.7,
        min_stock_impact_score=0,
        tickers=[],
        topics=[],
        enabled=enabled,
    )


def make_alert(item_id: int, rule_id: int, title: str, severity: str = "medium") -> Alert:
    return Alert(
        user_id="local",
        item_id=item_id,
        rule_id=rule_id,
        title=title,
        reason=f"{title}: test reason",
        severity=severity,
        status="active",
    )
