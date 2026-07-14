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
    StockWatchlistItem,
    TopicWatchlistItem,
    UserItemAction,
    UserPreference,
)
from app.db.models import DailyDigestSnapshot as DailyDigestSnapshotModel
from app.schemas.digest import DailyDigest
from app.schemas.feed import FeedItem
from app.services.daily_digest import (
    build_digest_item_labels,
    build_digest_overview_metrics,
    build_digest_sections,
    build_headline,
    build_source_coverage,
    delete_daily_digest_snapshot,
    digest_rank_score,
    filter_items_by_excluded_topics,
    generate_daily_digest,
    list_active_digest_alerts,
    list_excluded_digest_company_terms,
    list_excluded_digest_product_terms,
    list_included_digest_product_terms,
    list_included_digest_stock_terms,
    list_included_digest_topic_terms,
    list_visible_items_for_digest_date,
    list_watchlist_companies,
    list_watchlist_products,
    list_watchlist_topics,
    render_digest_markdown,
    select_latest_digest_date,
    serialize_daily_digest_snapshot,
    sort_for_digest,
    update_daily_digest_snapshot_feedback,
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
    assert section_map["top_signals"].metrics.item_count == 3
    assert section_map["top_signals"].metrics.high_impact_count == 2
    assert section_map["top_signals"].metrics.stock_signal_count == 1
    assert section_map["top_signals"].metrics.source_count == 1
    assert section_map["read_later"].metrics.read_later_count == 1


def test_daily_digest_sections_include_topic_watchlist_matches() -> None:
    items = [
        make_item(1, "Agent harness paper", "research", 0.9, topics=["agent"]),
        make_item(2, "Coding agent launch", "product", 0.8, topics=["developer tools"]),
        make_item(3, "Unrelated model note", "technical_trend", 0.7, topics=["multimodal"]),
    ]

    sections = build_digest_sections(
        items,
        topic_watchlist_terms={"agent harness", "coding agent"},
    )
    section_map = {section.key: section for section in sections}

    assert [item.title for item in section_map["topic_watchlist"].items] == [
        "Agent harness paper",
        "Coding agent launch",
    ]
    assert section_map["topic_watchlist"].metrics.item_count == 2


def test_daily_digest_sections_limit_stock_watchlist_to_watched_terms() -> None:
    items = [
        make_item(1, "Micron HBM demand rises", "stock_company_event", 0.9, tickers=["MU"]),
        make_item(2, "HBM memory pricing note", "stock_company_event", 0.8),
        make_item(3, "Unwatched retailer earnings", "stock_company_event", 0.7, tickers=["SHOP"]),
    ]

    sections = build_digest_sections(
        items,
        stock_watchlist_terms={"mu", "micron technology", "hbm memory"},
    )
    section_map = {section.key: section for section in sections}

    assert [item.title for item in section_map["stock_watchlist"].items] == [
        "Micron HBM demand rises",
        "HBM memory pricing note",
    ]


def test_daily_digest_sections_include_product_watchlist_matches() -> None:
    items = [
        make_item(
            1,
            "CodePilot developer agent launch",
            "product",
            0.9,
            products=["CodePilot"],
        ),
        make_item(
            2,
            "AI coding assistant benchmark",
            "technical_trend",
            0.8,
            subcategory="product_coding",
        ),
        make_item(3, "Photo model update", "product", 0.7, products=["AI photo"]),
    ]

    sections = build_digest_sections(
        items,
        product_watchlist_terms={"ai coding tools", "developer agent", "product_coding"},
    )
    section_map = {section.key: section for section in sections}

    assert [item.title for item in section_map["product_watchlist"].items] == [
        "CodePilot developer agent launch",
        "AI coding assistant benchmark",
    ]
    assert section_map["product_watchlist"].metrics.item_count == 2


def test_daily_digest_sections_include_prd_secondary_categories() -> None:
    items = [
        make_item(1, "Benchmark eval", "benchmark_evaluation", 0.9),
        make_item(2, "AI policy update", "policy_regulation", 0.8),
        make_item(3, "Inference infrastructure", "infrastructure", 0.75),
        make_item(4, "Startup acquisition", "funding_mna", 0.7),
        make_item(5, "Open source release", "open_source_release", 0.65),
        make_item(6, "Tutorial essay", "tutorial_opinion", 0.6),
    ]

    section_map = {section.key: section for section in build_digest_sections(items)}

    assert [item.title for item in section_map["research"].items] == ["Benchmark eval"]
    assert {item.title for item in section_map["technical_trends"].items} == {
        "AI policy update",
        "Inference infrastructure",
        "Open source release",
        "Tutorial essay",
    }
    assert [item.title for item in section_map["stock_watchlist"].items] == [
        "Startup acquisition"
    ]
    assert [item.title for item in section_map["developer_highlights"].items] == [
        "Open source release"
    ]


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


def test_build_digest_item_labels_includes_market_impact_type() -> None:
    item = make_item(
        1,
        "Micron HBM demand",
        "stock_company_event",
        0.8,
        tickers=["MU"],
        companies=["Micron"],
        topics=["hbm"],
    )
    item.market_impact_type = "demand_signal"

    assert build_digest_item_labels(item) == ["MU", "Micron", "demand signal", "hbm"]


def test_build_digest_item_labels_includes_technologies() -> None:
    item = make_item(
        1,
        "Inference systems update",
        "technical_trend",
        0.8,
        topics=["inference"],
    )
    item.technologies = ["Inference", "RAG"]

    assert build_digest_item_labels(item) == ["Inference", "RAG"]


def test_build_digest_item_labels_includes_non_ai_relevance_label() -> None:
    item = make_item(
        1,
        "Unrelated saved link",
        "noise_irrelevant",
        0.2,
        topics=["office software"],
    )
    item.is_ai_related = False

    assert build_digest_item_labels(item) == ["not AI-related", "office software"]


def test_build_digest_item_labels_includes_strong_social_signal() -> None:
    item = make_item(
        1,
        "Popular AI workflow",
        "social_trend",
        0.8,
        products=["PhotoFlow"],
        topics=["ai photo"],
    )
    item.social_signal_score = 0.82

    assert build_digest_item_labels(item) == ["social signal 82%", "PhotoFlow", "ai photo"]


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


def test_list_included_digest_product_terms_includes_use_case_terms() -> None:
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
                    include_in_digest=True,
                    related_terms=["developer agent"],
                ),
                ProductWatchlistItem(
                    user_id="local",
                    category="ai-photo",
                    label="AI photo tools",
                    include_in_digest=False,
                    related_terms=["image generation"],
                ),
            ]
        )
        db.commit()

        terms = list_included_digest_product_terms(db)

    assert {"ai-coding-tools", "ai coding tools", "developer agent", "product_coding"}.issubset(
        terms
    )
    assert "ai photo tools" not in terms


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


def test_list_watchlist_topics_returns_included_labels_and_terms() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                TopicWatchlistItem(
                    user_id="local",
                    topic="agent-harness",
                    label="Agent Harness",
                    category="technical_trend",
                    priority="High",
                    is_pinned=True,
                    include_in_digest=True,
                    related_terms=["coding agent"],
                ),
                TopicWatchlistItem(
                    user_id="local",
                    topic="ai-photo",
                    label="AI Photo",
                    category="product",
                    priority="Medium",
                    include_in_digest=False,
                    related_terms=["image generation"],
                ),
            ]
        )
        db.commit()

        topics = list_watchlist_topics(db)
        terms = list_included_digest_topic_terms(db)

    assert topics == ["Agent Harness"]
    assert {"agent-harness", "agent harness", "coding agent"}.issubset(terms)
    assert "ai photo" not in terms


def test_list_watchlist_products_returns_digest_included_labels() -> None:
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
                    priority="High",
                    is_pinned=True,
                    include_in_digest=True,
                    related_terms=["developer agent"],
                ),
                ProductWatchlistItem(
                    user_id="local",
                    category="ai-photo",
                    label="AI photo tools",
                    priority="Medium",
                    include_in_digest=False,
                    related_terms=["image generation"],
                ),
            ]
        )
        db.commit()

        products = list_watchlist_products(db)

    assert products == ["AI coding tools"]


def test_list_included_digest_stock_terms_uses_local_stock_profile() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add(
            StockWatchlistItem(
                user_id="local",
                ticker="MU",
                company_name="Micron Technology",
                exchange="NASDAQ",
                sector="Technology",
                industry="Semiconductors",
                priority="High",
                group_name="Memory",
                related_keywords=["HBM"],
                related_companies=["NVDA"],
                related_ai_themes=["AI server memory"],
            )
        )
        db.commit()

        terms = list_included_digest_stock_terms(db)

    assert {"mu", "micron technology", "hbm", "nvda", "ai server memory"}.issubset(terms)


def test_render_digest_markdown_includes_sections_links_and_disclaimer() -> None:
    items = [
        make_item(1, "Research", "research", 0.9, topics=["llm"], companies=["OpenAI"]),
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
        watchlist_topics=["Agent Harness", "AI Coding"],
        watchlist_products=["AI coding tools", "AI search tools"],
        disclaimer="Informational only.",
    )

    markdown = render_digest_markdown(digest)

    assert markdown.startswith("# SignalLens Daily Digest - 2026-06-25")
    assert "Ticker watchlist: MU, MRVL" in markdown
    assert "Company watchlist: OpenAI, Anthropic" in markdown
    assert "Topic watchlist: Agent Harness, AI Coding" in markdown
    assert "Product watchlist: AI coding tools, AI search tools" in markdown
    assert "## AI Research" in markdown
    assert "Papers, benchmarks, and research discussions." in markdown
    assert "_Section signals: 1 items, 1 sources, 1 high-impact_" in markdown
    assert "- [Research](https://example.com/1) - Test Source (OpenAI, llm)" in markdown
    assert "- [Product](https://example.com/3) - Test Source (CodePilot, Coding)" in markdown
    assert "## Disclaimer" in markdown
    assert markdown.endswith("Informational only.\n")


def test_render_digest_markdown_includes_strong_social_signal_note() -> None:
    item = make_item(
        1,
        "Popular AI workflow",
        "social_trend",
        0.8,
        products=["PhotoFlow"],
    )
    item.social_signal_score = 0.82
    item.summary_short = "PhotoFlow is spreading through public social posts."
    digest = DailyDigest(
        digest_date=datetime(2026, 6, 25, tzinfo=UTC).date(),
        generated_at=datetime(2026, 6, 25, 13, 0, tzinfo=UTC),
        headline="1 AI signal for 2026-06-25.",
        total_items=1,
        sections=build_digest_sections([item], limit_per_section=1),
        source_coverage=build_source_coverage([item]),
        disclaimer="Informational only.",
    )

    markdown = render_digest_markdown(digest)

    assert "- [Popular AI workflow](https://example.com/1) - Test Source" in markdown
    assert "social signal 82%" in markdown
    assert "Signal: strong public engagement (82/100)" in markdown


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
    assert (
        "- [Urgent stock signal](https://example.com/9) - high via High-impact stock signal"
        in markdown
    )
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


def test_update_daily_digest_snapshot_feedback_round_trips_payload() -> None:
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
    timestamp = datetime(2026, 6, 25, 13, 5, tzinfo=UTC)
    with session_factory() as db:
        snapshot = DailyDigestSnapshotModel(
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
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        updated = update_daily_digest_snapshot_feedback(db, snapshot.id, "useful")
        assert updated is not None
        serialized = serialize_daily_digest_snapshot(updated)
        assert serialized.usefulness_feedback == "useful"
        assert updated.payload["usefulness_feedback_at"]

        cleared = update_daily_digest_snapshot_feedback(db, snapshot.id, None)
        assert cleared is not None
        assert serialize_daily_digest_snapshot(cleared).usefulness_feedback is None
        assert "usefulness_feedback_at" not in cleared.payload


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


def test_generate_daily_digest_includes_topic_watchlist_updates() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add(
            TopicWatchlistItem(
                user_id="local",
                topic="agent-harness",
                label="Agent Harness",
                category="technical_trend",
                priority="High",
                is_pinned=True,
                include_in_digest=True,
                related_terms=["coding agent"],
            )
        )
        db.add_all(
            [
                make_normalized_item(
                    1,
                    "Agent harness reliability signal",
                    source_name="Trusted Blog",
                ),
                make_normalized_item(
                    2,
                    "Multimodal release note",
                    source_name="Trusted Blog",
                ),
            ]
        )
        db.commit()

        digest = generate_daily_digest(
            db,
            digest_date=datetime(2026, 6, 25, tzinfo=UTC).date(),
        )

    section_map = {section.key: section for section in digest.sections}
    assert digest.watchlist_topics == ["Agent Harness"]
    assert [item.title for item in section_map["topic_watchlist"].items] == [
        "Agent harness reliability signal"
    ]


def test_generate_daily_digest_includes_product_watchlist_updates() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add(
            ProductWatchlistItem(
                user_id="local",
                category="ai-coding-tools",
                label="AI coding tools",
                priority="High",
                is_pinned=True,
                include_in_digest=True,
                related_terms=["developer agent"],
            )
        )
        db.add_all(
            [
                make_normalized_item(
                    1,
                    "Developer agent launch for coding teams",
                    source_name="Trusted Blog",
                ),
                make_normalized_item(
                    2,
                    "AI photo workflow update",
                    source_name="Trusted Blog",
                ),
            ]
        )
        db.commit()

        digest = generate_daily_digest(
            db,
            digest_date=datetime(2026, 6, 25, tzinfo=UTC).date(),
        )

    section_map = {section.key: section for section in digest.sections}
    assert digest.watchlist_products == ["AI coding tools"]
    assert [item.title for item in section_map["product_watchlist"].items] == [
        "Developer agent launch for coding teams"
    ]


def test_generate_daily_digest_limits_stock_watchlist_updates_to_watched_terms() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add(
            StockWatchlistItem(
                user_id="local",
                ticker="MU",
                company_name="Micron Technology",
                exchange="NASDAQ",
                sector="Technology",
                industry="Semiconductors",
                priority="High",
                group_name="Memory",
                related_keywords=["HBM"],
                related_companies=[],
                related_ai_themes=["AI server memory"],
            )
        )
        watched = make_normalized_item(
            1,
            "Micron HBM memory demand rises",
            source_name="Trusted Blog",
        )
        watched.category = "stock_company_event"
        watched.tickers = ["MU"]
        unwatched = make_normalized_item(
            2,
            "Retailer earnings beat estimates",
            source_name="Trusted Blog",
        )
        unwatched.category = "stock_company_event"
        unwatched.tickers = ["SHOP"]
        db.add_all([watched, unwatched])
        db.commit()

        digest = generate_daily_digest(
            db,
            digest_date=datetime(2026, 6, 25, tzinfo=UTC).date(),
        )

    section_map = {section.key: section for section in digest.sections}
    assert digest.watchlist_tickers == ["MU"]
    assert [item.title for item in section_map["stock_watchlist"].items] == [
        "Micron HBM memory demand rises"
    ]


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
