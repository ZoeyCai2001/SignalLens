from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import (
    Alert,
    AlertRule,
    Base,
    DailyDigestSnapshot,
    LlmUsageEvent,
    NormalizedItem,
    RawItem,
    Source,
    UserItemAction,
)
from app.schemas.feed import FeedItem
from app.schemas.preferences import RankingWeights
from app.services.feed_actions import (
    FeedInterestProfile,
    build_feed_interest_profile,
    build_feed_module_conditions,
    build_feed_topic_filter_terms,
    build_feed_uncertainty_notes,
    build_feed_why_it_matters,
    build_personalization_notes,
    build_score_explanation,
    delete_feed_item,
    export_saved_items_markdown,
    feed_interest_bonus,
    feedback_interest_adjustment,
    freshness_score,
    infer_market_impact_type,
    list_visible_feed_items,
    normalize_feed_module_filter,
    normalize_feed_topic_filter,
    normalize_language_codes,
    normalize_source_names,
    rank_feed_items,
    serialize_feed_item,
    serialize_feed_item_detail,
    social_signal_score_for_item,
    update_item_action,
    update_item_personal_metadata,
    weighted_feed_score,
)


def test_serialize_feed_item_includes_user_action_flags() -> None:
    item = NormalizedItem(
        id=1,
        raw_item_id=1,
        title="AI agent item",
        url="https://example.com",
        source_name="Manual Submission",
        language="en",
        category="manual_submission",
        tickers=[],
        companies=[],
        products=[],
        topics=["agent"],
        sentiment="neutral",
        relevance_score=0.5,
        importance_score=0.4,
        novelty_score=1.0,
        source_quality_score=0.6,
        stock_impact_score=0,
    )
    action = UserItemAction(
        item_id=1,
        user_id="local",
        is_saved=True,
        is_hidden=False,
        is_important=True,
    )

    serialized = serialize_feed_item(item, action)

    assert serialized.is_saved is True
    assert serialized.is_hidden is False
    assert serialized.is_important is True
    assert serialized.why_it_matters == (
        "This user-submitted link may need review for the personal intelligence archive. "
        "It is linked to agent and shows lower classifier confidence."
    )


def test_serialize_feed_item_preserves_existing_why_it_matters() -> None:
    item = NormalizedItem(
        id=1,
        raw_item_id=1,
        title="Agent release",
        url="https://example.com",
        source_name="Official Blog",
        language="en",
        category="technical_trend",
        tickers=[],
        companies=[],
        products=[],
        topics=["agent"],
        sentiment="neutral",
        relevance_score=0.8,
        importance_score=0.8,
        novelty_score=0.6,
        source_quality_score=0.9,
        stock_impact_score=0,
        why_it_matters="  Existing LLM explanation.  ",
    )

    serialized = serialize_feed_item(item)

    assert serialized.why_it_matters == "Existing LLM explanation."


def test_serialize_feed_item_adds_market_impact_type() -> None:
    item = NormalizedItem(
        id=1,
        raw_item_id=1,
        title="Micron HBM demand rises with AI data center capex",
        url="https://example.com",
        source_name="Finance News",
        language="en",
        category="stock_company_event",
        tickers=["MU"],
        companies=["Micron"],
        products=[],
        topics=["hbm", "ai data center"],
        sentiment="positive",
        relevance_score=0.85,
        importance_score=0.82,
        novelty_score=0.7,
        source_quality_score=0.82,
        stock_impact_score=0.62,
    )

    serialized = serialize_feed_item(item)

    assert serialized.market_impact_type == "demand_signal"


def test_infer_market_impact_type_ignores_low_impact_non_stock_items() -> None:
    item = make_feed_item(1, "Agent release", relevance_score=0.8, importance_score=0.8)

    assert infer_market_impact_type(item) == "none"


def test_build_feed_why_it_matters_uses_entities_and_trust_signals() -> None:
    item = make_feed_item(1, "Micron HBM demand", relevance_score=0.82, importance_score=0.84)
    item.category = "stock_company_event"
    item.tickers = ["MU"]
    item.companies = ["Micron"]
    item.source_quality_score = 0.85
    item.stock_impact_score = 0.55

    why = build_feed_why_it_matters(item)

    assert why == (
        "This may matter for AI-linked company and stock monitoring. "
        "It is linked to MU, Micron and shows high importance, strong AI relevance, "
        "possible stock-watchlist impact."
    )


def test_build_feed_why_it_matters_includes_product_use_case_focus() -> None:
    item = make_feed_item(1, "AI coding workspace", relevance_score=0.82, importance_score=0.8)
    item.category = "product"
    item.subcategory = "product_coding"
    item.products = ["CodePilot"]
    item.source_quality_score = 0.82

    why = build_feed_why_it_matters(item)

    assert why == (
        "This may help identify AI products gaining traction. "
        "It is linked to CodePilot, Coding and shows high importance, strong AI relevance, "
        "high source credibility."
    )


def test_build_score_explanation_includes_product_use_case() -> None:
    item = make_feed_item(1, "AI media workspace")
    item.category = "product"
    item.subcategory = "product_media"

    explanation = build_score_explanation(item)

    assert "classified as product / Media" in explanation


def test_serialize_feed_item_computes_social_signal_from_raw_metadata() -> None:
    item = NormalizedItem(
        id=1,
        raw_item_id=1,
        title="Popular repository",
        url="https://github.com/example/agent",
        source_name="GitHub",
        language="en",
        category="technical_trend",
        tickers=[],
        companies=[],
        products=[],
        topics=["agent"],
        sentiment="neutral",
        relevance_score=0.5,
        importance_score=0.4,
        novelty_score=1.0,
        source_quality_score=0.75,
        stock_impact_score=0,
        raw_item=RawItem(
            id=1,
            source_id=1,
            url="https://github.com/example/agent",
            raw_title="Popular repository",
            raw_metadata={"stars": 5000, "stars_per_day": 50, "forks": 1000},
            content_hash="hash",
        ),
    )

    serialized = serialize_feed_item(item)

    assert serialized.social_signal_score == 1
    assert social_signal_score_for_item(item) == 1


def test_hugging_face_social_signal_uses_downloads_and_likes() -> None:
    item = NormalizedItem(
        id=1,
        raw_item_id=1,
        title="Popular model",
        url="https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct",
        source_name="Hugging Face",
        language="en",
        category="research",
        tickers=[],
        companies=[],
        products=[],
        topics=["llm"],
        sentiment="neutral",
        relevance_score=0.5,
        importance_score=0.4,
        novelty_score=1.0,
        source_quality_score=0.78,
        stock_impact_score=0,
        raw_item=RawItem(
            id=1,
            source_id=1,
            url="https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct",
            raw_title="Popular model",
            raw_metadata={
                "hf_kind": "model",
                "downloads": 120000,
                "likes": 4200,
            },
            content_hash="hash",
        ),
    )

    assert social_signal_score_for_item(item) == 1


def test_serialize_feed_item_detail_includes_text_actions_and_explanation() -> None:
    item = NormalizedItem(
        id=1,
        raw_item_id=1,
        title="Micron HBM demand",
        url="https://example.com",
        source_name="Alpha Vantage News",
        author=None,
        language="en",
        published_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
        text="Source article text.",
        category="stock_company_event",
        tickers=["MU"],
        companies=["Micron"],
        products=[],
        topics=["HBM"],
        sentiment="positive",
        relevance_score=0.8,
        classification_confidence=0.82,
        importance_score=0.82,
        novelty_score=0.7,
        source_quality_score=0.82,
        stock_impact_score=0.9,
        summary_short="Micron demand signal\n- HBM demand is rising.\n- AI servers need memory.",
        summary_detailed=(
            "Micron demand signal.\n"
            "Market relevance: This is relevant to watched memory tickers.\n"
            "Technical relevance: HBM supply affects AI accelerator deployment."
        ),
    )
    action = UserItemAction(
        item_id=1,
        user_id="local",
        is_saved=True,
        is_hidden=False,
        is_important=True,
        is_read=True,
        read_at=datetime(2026, 6, 25, 13, 0, tzinfo=UTC),
    )

    detail = serialize_feed_item_detail(item, action)

    assert detail.text == "Source article text."
    assert detail.one_line_summary == "Micron demand signal"
    assert detail.card_summary == ["HBM demand is rising.", "AI servers need memory."]
    assert detail.technical_summary == "HBM supply affects AI accelerator deployment."
    assert detail.market_watch_summary == "This is relevant to watched memory tickers."
    assert detail.summary_source == "stored_summary"
    assert detail.action_state == {
        "is_saved": True,
        "is_hidden": False,
        "is_important": True,
        "is_read": True,
    }
    assert "matched tickers MU" in detail.score_explanation
    assert "high source credibility" in detail.score_explanation
    assert "high stock-impact score" in detail.score_explanation
    assert "saved by you" in detail.score_explanation
    assert "marked important by you" in detail.score_explanation
    assert detail.uncertainty_notes == ["No major uncertainty flags from the stored item signals."]
    assert detail.personalization_notes == []


def test_serialize_feed_item_detail_derives_summary_profile_without_stored_summary() -> None:
    item = make_normalized_item(
        1,
        "Research note",
        language="en",
        category="research",
        summary_short=None,
    )
    item.summary_detailed = None
    item.why_it_matters = "This informs AI evaluation work. It should be reviewed later."

    detail = serialize_feed_item_detail(item)

    assert detail.one_line_summary == "This informs AI evaluation work."
    assert detail.card_summary == [
        "This informs AI evaluation work.",
    ]
    assert detail.technical_summary == "This informs AI evaluation work."
    assert detail.market_watch_summary is None
    assert detail.summary_source == "why_it_matters"


def test_serialize_feed_item_detail_includes_personalization_notes() -> None:
    item = make_normalized_item(
        1,
        "Future coding agent",
        language="en",
        topics=["coding agent"],
        products=["IDE agent"],
        source_name="GitHub",
    )
    profile = FeedInterestProfile(
        liked_terms=frozenset({"coding agent", "ide agent"}),
        liked_sources=frozenset({"github"}),
        disliked_terms=frozenset({"crypto trading bot"}),
    )

    detail = serialize_feed_item_detail(item, interest_profile=profile)

    assert detail.personalization_notes == [
        "Source matches items you saved or marked important: GitHub.",
        "Topic/product matches items you saved or marked important: coding agent, ide agent.",
    ]


def test_build_personalization_notes_reports_hidden_feedback_matches() -> None:
    item = make_feed_item(1, "Noisy crypto bot")
    item.source_name = "Noisy RSS"
    item.topics = ["crypto trading bot"]
    profile = FeedInterestProfile(
        disliked_terms=frozenset({"crypto trading bot"}),
        disliked_sources=frozenset({"noisy rss"}),
    )

    notes = build_personalization_notes(item, profile)

    assert notes == [
        "Source matches items you previously hid: Noisy RSS.",
        "Topic/product matches items you previously hid: crypto trading bot.",
    ]


def test_update_item_personal_metadata_saves_note_and_normalized_tags() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        item = make_normalized_item(1, "Saved reading item", language="en")
        db.add(item)
        db.commit()

        detail = update_item_personal_metadata(
            db=db,
            item=item,
            personal_note="  Review for weekend digest.  ",
            manual_tags=[" Agent ", "agent", "market impact", ""],
        )

        assert detail.personal_note == "Review for weekend digest."
        assert detail.manual_tags == ["Agent", "market impact"]
    assert detail.action_state == {
        "is_saved": False,
        "is_hidden": False,
        "is_important": False,
        "is_read": False,
    }


def test_export_saved_items_markdown_includes_notes_tags_and_read_status() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        saved = make_normalized_item(
            1,
            "Agent framework launch",
            language="en",
            topics=["coding agent"],
            summary_short="New local coding agent framework.",
            products=["IDE agent"],
            source_name="GitHub",
        )
        read = make_normalized_item(
            2,
            "Read research note",
            language="en",
            topics=["research"],
        )
        hidden = make_normalized_item(
            3,
            "Hidden saved item",
            language="en",
            topics=["hidden"],
        )
        db.add_all([saved, read, hidden])
        db.add_all(
            [
                UserItemAction(
                    user_id="local",
                    item_id=1,
                    is_saved=True,
                    personal_note="Follow up before Monday.",
                    manual_tags=["Agent", "Weekend"],
                ),
                UserItemAction(
                    user_id="local",
                    item_id=2,
                    is_saved=True,
                    is_read=True,
                    read_at=datetime(2026, 6, 26, 9, 0, tzinfo=UTC),
                ),
                UserItemAction(
                    user_id="local",
                    item_id=3,
                    is_saved=True,
                    is_hidden=True,
                ),
            ]
        )
        db.commit()

        export = export_saved_items_markdown(db=db, limit=10)
        unread_export = export_saved_items_markdown(db=db, include_read=False, limit=10)

    assert export.item_count == 2
    assert "# SignalLens Saved Items" in export.markdown
    assert "Agent framework launch" in export.markdown
    assert "- Source: GitHub | 2026-06-25T12:00:00+00:00 | read later" in export.markdown
    assert "- Labels: IDE agent, coding agent" in export.markdown
    assert "- Manual tags: Agent, Weekend" in export.markdown
    assert "- Personal note: Follow up before Monday." in export.markdown
    assert "- Summary: New local coding agent framework." in export.markdown
    assert "Read research note" in export.markdown
    assert "Hidden saved item" not in export.markdown
    assert unread_export.item_count == 1
    assert "Agent framework launch" in unread_export.markdown
    assert "Read research note" not in unread_export.markdown


def test_build_score_explanation_flags_lower_confidence_and_source_credibility() -> None:
    item = make_feed_item(1, "Manual rumor", relevance_score=0.6, importance_score=0.5)
    item.category = "manual_submission"
    item.source_quality_score = 0.55
    item.classification_confidence = 0.45

    explanation = build_score_explanation(item)

    assert "lower source credibility; review the original source" in explanation
    assert "lower classifier confidence" in explanation


def test_build_feed_uncertainty_notes_flags_review_risks() -> None:
    item = make_feed_item(1, "Manual stock rumor", relevance_score=0.6, importance_score=0.5)
    item.source_name = "Manual Submission"
    item.source_quality_score = 0.55
    item.classification_confidence = 0.45
    item.stock_impact_score = 0.45
    item.sentiment = "neutral"
    item.tickers = []
    item.summary_short = None
    item.summary_detailed = None

    notes = build_feed_uncertainty_notes(item)

    assert "Classifier confidence is low, so category and entity labels may need review." in notes
    assert "Source credibility is lower than the preferred-source threshold." in notes
    assert "Stock impact was inferred, but no explicit ticker was extracted." in notes
    assert "Market direction is unclear from the available signal." in notes
    assert "No generated summary is stored yet; review the original source text." in notes
    assert "Manual submissions depend on the supplied URL and note context." in notes


def test_build_score_explanation_has_default_reason() -> None:
    item = make_feed_item(1, "Fallback")
    item.category = ""
    item.source_quality_score = 0.65
    item.classification_confidence = 0.7

    assert build_score_explanation(item) == "Shown because it matched the AI relevance prefilter."


def test_rank_feed_items_keeps_important_saved_flags() -> None:
    now = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    important = make_feed_item(1, "Important", relevance_score=0.1, importance_score=0.1)
    important.is_important = True
    high_score = make_feed_item(2, "High score", relevance_score=1, importance_score=1)

    ranked = rank_feed_items([high_score, important], now=now)

    assert [item.title for item in ranked] == ["Important", "High score"]


def test_rank_feed_items_uses_saved_feedback_as_soft_boost() -> None:
    now = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    generic = make_feed_item(1, "Generic", relevance_score=0.5, importance_score=0.5)
    saved = make_feed_item(2, "Saved", relevance_score=0.5, importance_score=0.5)
    saved.is_saved = True

    ranked = rank_feed_items(
        [generic, saved],
        ranking_weights=RankingWeights(
            relevance=1,
            importance=0,
            novelty=0,
            source_quality=0,
            stock_impact=0,
            freshness=0,
        ),
        now=now,
    )

    assert [item.title for item in ranked] == ["Saved", "Generic"]


def test_rank_feed_items_uses_configurable_weights() -> None:
    now = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    relevance_item = make_feed_item(1, "Relevant", relevance_score=0.95, importance_score=0.1)
    importance_item = make_feed_item(2, "Important", relevance_score=0.1, importance_score=0.95)

    ranked = rank_feed_items(
        [importance_item, relevance_item],
        ranking_weights=RankingWeights(
            relevance=1,
            importance=0,
            novelty=0,
            source_quality=0,
            stock_impact=0,
            freshness=0,
        ),
        now=now,
    )

    assert [item.title for item in ranked] == ["Relevant", "Important"]


def test_rank_feed_items_uses_social_signal_weight() -> None:
    now = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    quiet = make_feed_item(1, "Quiet launch", relevance_score=0.5, importance_score=0.5)
    popular = make_feed_item(2, "Popular launch", relevance_score=0.5, importance_score=0.5)
    popular.social_signal_score = 0.9

    ranked = rank_feed_items(
        [quiet, popular],
        ranking_weights=RankingWeights(
            relevance=0,
            importance=0,
            novelty=0,
            source_quality=0,
            social_signal=1,
            stock_impact=0,
            freshness=0,
        ),
        now=now,
    )

    assert [item.title for item in ranked] == ["Popular launch", "Quiet launch"]


def test_weighted_feed_score_boosts_preferred_sources() -> None:
    now = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    item = make_feed_item(1, "Preferred")
    item.source_name = "GitHub"

    score = weighted_feed_score(
        item,
        RankingWeights(),
        now=now,
        preferred_sources={"GitHub"},
    )
    baseline = weighted_feed_score(item, RankingWeights(), now=now)

    assert score == baseline + 0.08


def test_weighted_feed_score_boosts_saved_items() -> None:
    now = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    item = make_feed_item(1, "Saved")
    item.is_saved = True

    score = weighted_feed_score(item, RankingWeights(), now=now)
    item.is_saved = False
    baseline = weighted_feed_score(item, RankingWeights(), now=now)

    assert score == baseline + 0.05


def test_weighted_feed_score_boosts_watchlist_interest_matches() -> None:
    now = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    item = make_feed_item(1, "Micron HBM demand")
    item.tickers = ["MU"]
    item.topics = ["HBM memory"]
    profile = FeedInterestProfile(
        symbols=frozenset({"MU"}),
        terms=frozenset({"hbm memory"}),
    )

    score = weighted_feed_score(
        item,
        RankingWeights(),
        now=now,
        interest_profile=profile,
    )
    baseline = weighted_feed_score(item, RankingWeights(), now=now)

    assert score == baseline + 0.08


def test_freshness_score_treats_naive_datetimes_as_utc() -> None:
    item = make_feed_item(1, "Naive timestamp")
    item.published_at = datetime(2026, 6, 25, 6, 0)

    score = freshness_score(item, now=datetime(2026, 6, 25, 12, 0, tzinfo=UTC))

    assert score == 0.9167


def test_rank_feed_items_uses_watchlist_interest_profile() -> None:
    now = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    generic = make_feed_item(1, "Generic item", relevance_score=0.5, importance_score=0.5)
    watched = make_feed_item(2, "Agent coding launch", relevance_score=0.5, importance_score=0.5)
    watched.topics = ["coding agent"]

    ranked = rank_feed_items(
        [generic, watched],
        ranking_weights=RankingWeights(
            relevance=1,
            importance=0,
            novelty=0,
            source_quality=0,
            stock_impact=0,
            freshness=0,
        ),
        interest_profile=FeedInterestProfile(
            symbols=frozenset(),
            terms=frozenset({"coding agent"}),
        ),
        now=now,
    )

    assert [item.title for item in ranked] == ["Agent coding launch", "Generic item"]


def test_feed_interest_bonus_caps_multiple_matches() -> None:
    item = make_feed_item(1, "Agent coding launch for Micron HBM")
    item.tickers = ["MU"]
    item.topics = ["coding agent", "HBM memory"]
    item.products = ["IDE agent"]
    profile = FeedInterestProfile(
        symbols=frozenset({"MU"}),
        terms=frozenset({"coding agent", "hbm memory", "ide agent", "micron"}),
    )

    assert feed_interest_bonus(item, profile) == 0.12


def test_feedback_interest_adjustment_uses_positive_and_negative_feedback() -> None:
    liked = make_feed_item(1, "Future coding agent")
    liked.source_name = "GitHub"
    liked.topics = ["coding agent"]
    disliked = make_feed_item(2, "Noisy crypto bot")
    disliked.source_name = "Noisy RSS"
    disliked.topics = ["crypto trading bot"]
    profile = FeedInterestProfile(
        liked_terms=frozenset({"coding agent"}),
        liked_sources=frozenset({"github"}),
        disliked_terms=frozenset({"crypto trading bot"}),
        disliked_sources=frozenset({"noisy rss"}),
    )

    assert feedback_interest_adjustment(liked, profile) == 0.07
    assert feedback_interest_adjustment(disliked, profile) == -0.08


def test_build_feed_interest_profile_includes_saved_and_hidden_feedback() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_normalized_item(
                    1,
                    "Saved coding agent",
                    language="en",
                    topics=["coding agent"],
                    products=["IDE agent"],
                    source_name="GitHub",
                ),
                make_normalized_item(
                    2,
                    "Hidden crypto bot",
                    language="en",
                    topics=["crypto trading bot"],
                    products=["trading bot"],
                    source_name="Noisy RSS",
                ),
            ]
        )
        db.add_all(
            [
                UserItemAction(user_id="local", item_id=1, is_saved=True),
                UserItemAction(user_id="local", item_id=2, is_hidden=True),
            ]
        )
        db.commit()

        profile = build_feed_interest_profile(db)

    assert "coding agent" in profile.liked_terms
    assert "ide agent" in profile.liked_terms
    assert "github" in profile.liked_sources
    assert "crypto trading bot" in profile.disliked_terms
    assert "trading bot" in profile.disliked_terms
    assert "noisy rss" in profile.disliked_sources


def test_build_feed_interest_profile_includes_default_company_watchlist() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        profile = build_feed_interest_profile(db)

    assert "NVDA" in profile.symbols
    assert "nvidia" in profile.terms
    assert "openai" in profile.terms


def test_normalize_source_names_trims_empty_values() -> None:
    assert normalize_source_names([" GitHub ", "", "RSS"]) == {"GitHub", "RSS"}


def test_normalize_language_codes_maps_aliases() -> None:
    assert normalize_language_codes([" English ", "zh-cn", "", "CN"]) == {"en", "zh"}


def test_normalize_feed_topic_filter_matches_slug_and_spacing() -> None:
    assert normalize_feed_topic_filter(" ai-coding-agents ") == "ai coding agents"
    assert normalize_feed_topic_filter("") is None


def test_build_feed_topic_filter_terms_adds_conservative_variants() -> None:
    assert build_feed_topic_filter_terms("ai-coding-agents") == {
        "ai coding agents",
        "ai coding agent",
        "ai-coding-agents",
        "coding agents",
        "coding agent",
    }


def test_normalize_feed_module_filter_accepts_prd_module_aliases() -> None:
    assert normalize_feed_module_filter("trends") == "trends"
    assert normalize_feed_module_filter("AI Trends") == "trends"
    assert normalize_feed_module_filter("ai-trends") == "trends"
    assert normalize_feed_module_filter("stock_company_event") == "stocks"
    assert normalize_feed_module_filter("benchmark_evaluation") == "research"
    assert normalize_feed_module_filter("policy_regulation") == "trends"
    assert normalize_feed_module_filter("funding_mna") == "stocks"
    assert normalize_feed_module_filter("Chinese Social") == "chinese"
    assert normalize_feed_module_filter("chinese-social") == "chinese"
    assert normalize_feed_module_filter("ignored") is None


def test_build_feed_module_conditions_ignores_unknown_modules() -> None:
    assert build_feed_module_conditions(None) == []
    assert build_feed_module_conditions("ignored") == []


def test_list_visible_feed_items_filters_language_preferences() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_normalized_item(1, "English signal", language="en"),
                make_normalized_item(2, "Chinese signal", language="zh"),
            ]
        )
        db.commit()

        items = list_visible_feed_items(db, limit=10, language_preferences=["zh"])

    assert [item.title for item in items] == ["Chinese signal"]


def test_list_visible_feed_items_filters_by_topic() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_normalized_item(
                    1,
                    "Agent coding launch",
                    language="en",
                    topics=["ai coding agents"],
                ),
                make_normalized_item(
                    2,
                    "Semiconductor capacity",
                    language="en",
                    topics=["semiconductor"],
                ),
                make_normalized_item(
                    3,
                    "Agent product summary",
                    language="en",
                    topics=[],
                    summary_short="New coding agent workflow.",
                ),
            ]
        )
        db.commit()

        items = list_visible_feed_items(db, limit=10, topic="ai-coding-agents")

    assert [item.title for item in items] == [
        "Agent coding launch",
        "Agent product summary",
    ]


def test_list_visible_feed_items_filters_by_research_module() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_normalized_item(1, "Research paper", language="en", category="research"),
                make_normalized_item(
                    2,
                    "Product launch",
                    language="en",
                    category="product",
                    products=["IDE agent"],
                ),
            ]
        )
        db.commit()

        items = list_visible_feed_items(db, limit=10, module="research")

    assert [item.title for item in items] == ["Research paper"]


def test_list_visible_feed_items_routes_prd_secondary_categories_to_modules() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_normalized_item(
                    1,
                    "Benchmark leaderboard",
                    language="en",
                    category="benchmark_evaluation",
                ),
                make_normalized_item(
                    2,
                    "AI policy update",
                    language="en",
                    category="policy_regulation",
                ),
                make_normalized_item(
                    3,
                    "Startup acquisition",
                    language="en",
                    category="funding_mna",
                ),
                make_normalized_item(
                    4,
                    "Product launch",
                    language="en",
                    category="product",
                ),
            ]
        )
        db.commit()

        research_items = list_visible_feed_items(db, limit=10, module="research")
        trend_items = list_visible_feed_items(db, limit=10, module="trends")
        stock_items = list_visible_feed_items(db, limit=10, module="stocks")

    assert [item.title for item in research_items] == ["Benchmark leaderboard"]
    assert [item.title for item in trend_items] == ["AI policy update"]
    assert [item.title for item in stock_items] == ["Startup acquisition"]


def test_list_visible_feed_items_filters_by_stock_module_entities() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_normalized_item(
                    1,
                    "Micron HBM demand",
                    language="en",
                    category="technical_trend",
                    tickers=["MU"],
                    stock_impact_score=0.7,
                ),
                make_normalized_item(2, "Generic agent item", language="en"),
            ]
        )
        db.commit()

        items = list_visible_feed_items(db, limit=10, module="stocks")

    assert [item.title for item in items] == ["Micron HBM demand"]


def test_list_visible_feed_items_filters_by_chinese_module_language() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_normalized_item(
                    1,
                    "Chinese AI workflow trend",
                    language="zh",
                    category="technical_trend",
                ),
                make_normalized_item(
                    2,
                    "English product launch",
                    language="en",
                    category="product",
                ),
            ]
        )
        db.commit()

        items = list_visible_feed_items(db, limit=10, module="chinese-social")

    assert [item.title for item in items] == ["Chinese AI workflow trend"]


def test_list_visible_feed_items_can_return_hidden_items() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add_all(
            [
                make_normalized_item(1, "Visible signal", language="en"),
                make_normalized_item(2, "Hidden signal", language="en"),
            ]
        )
        db.add(UserItemAction(item_id=2, user_id="local", is_hidden=True))
        db.commit()

        visible_items = list_visible_feed_items(db, limit=10)
        hidden_items = list_visible_feed_items(db, limit=10, hidden_only=True)

    assert [item.title for item in visible_items] == ["Visible signal"]
    assert [item.title for item in hidden_items] == ["Hidden signal"]
    assert hidden_items[0].is_hidden is True


def test_update_item_action_can_unhide_item() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        item = make_normalized_item(1, "Hidden signal", language="en")
        db.add(item)
        db.add(UserItemAction(item_id=1, user_id="local", is_hidden=True))
        db.commit()

        restored = update_item_action(db=db, item=item, action_name="unhide")

        persisted = db.query(UserItemAction).filter(UserItemAction.item_id == 1).one()

    assert restored.is_hidden is False
    assert persisted.is_hidden is False


def test_update_item_action_can_mark_and_unmark_important() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        item = make_normalized_item(1, "Important signal", language="en")
        db.add(item)
        db.commit()

        important_item = update_item_action(db=db, item=item, action_name="mark-important")
        important_action = db.query(UserItemAction).filter(UserItemAction.item_id == 1).one()
        assert important_item.is_important is True
        assert important_action.is_important is True

        normal_item = update_item_action(db=db, item=item, action_name="unmark-important")
        normal_action = db.query(UserItemAction).filter(UserItemAction.item_id == 1).one()

    assert normal_item.is_important is False
    assert normal_action.is_important is False


def test_update_item_action_can_mark_item_read_and_unread() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        item = make_normalized_item(1, "Reading item", language="en")
        db.add(item)
        db.commit()

        read_item = update_item_action(db=db, item=item, action_name="mark-read")
        read_action = db.query(UserItemAction).filter(UserItemAction.item_id == 1).one()
        assert read_item.is_read is True
        assert read_item.read_at is not None
        assert read_action.is_read is True
        assert read_action.read_at is not None

        unread_item = update_item_action(db=db, item=item, action_name="mark-unread")
        unread_action = db.query(UserItemAction).filter(UserItemAction.item_id == 1).one()

    assert unread_item.is_read is False
    assert unread_item.read_at is None
    assert unread_action.is_read is False
    assert unread_action.read_at is None


def test_delete_feed_item_removes_stored_content_and_linked_private_state() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        source = Source(name="Manual Submission", type="manual", access_method="manual_submission")
        db.add(source)
        db.flush()
        raw_item = RawItem(
            id=1,
            source_id=source.id,
            external_id="manual-1",
            url="https://example.com/delete-me",
            raw_title="Delete me",
            raw_text="Stored raw source text",
            raw_metadata={"note": "private"},
            content_hash="delete-feed-item-hash",
            published_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
        )
        item = make_normalized_item(1, "Delete me", language="en")
        rule = AlertRule(
            id=1,
            user_id="local",
            name="Delete rule",
            category="all",
            severity="medium",
            min_importance_score=0,
            min_stock_impact_score=0,
            tickers=[],
            topics=[],
            enabled=True,
        )
        db.add_all([raw_item, item, rule])
        db.flush()
        db.add_all(
            [
                UserItemAction(
                    user_id="local",
                    item_id=item.id,
                    is_saved=True,
                    personal_note="private note",
                    manual_tags=["delete"],
                ),
                Alert(
                    user_id="local",
                    item_id=item.id,
                    rule_id=rule.id,
                    title="Delete me",
                    reason="Delete me matched an alert.",
                    severity="medium",
                    status="active",
                ),
                LlmUsageEvent(
                    user_id="local",
                    operation="summarize_item",
                    provider="kimi_coding",
                    model="kimi-for-coding",
                    item_id=item.id,
                    input_tokens=10,
                    output_tokens=4,
                    total_tokens=14,
                    created_at=datetime(2026, 6, 25, 12, 5, tzinfo=UTC),
                ),
                DailyDigestSnapshot(
                    user_id="local",
                    digest_date=datetime(2026, 6, 25, tzinfo=UTC).date(),
                    generated_at=datetime(2026, 6, 25, 13, 0, tzinfo=UTC),
                    headline="Digest",
                    total_items=1,
                    limit_per_section=5,
                    payload={"items": [{"id": item.id, "title": item.title, "url": item.url}]},
                    markdown=f"- [{item.title}]({item.url})",
                ),
            ]
        )
        db.commit()

        delete_feed_item(db=db, item=item)

        usage_event = db.query(LlmUsageEvent).one()

        assert db.get(NormalizedItem, 1) is None
        assert db.get(RawItem, 1) is None
        assert db.query(UserItemAction).count() == 0
        assert db.query(Alert).count() == 0
        assert db.query(DailyDigestSnapshot).count() == 0
        assert usage_event.item_id is None


def test_freshness_score_decays_over_three_days() -> None:
    now = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
    fresh = make_feed_item(1, "Fresh", published_at=now)
    old = make_feed_item(2, "Old", published_at=now - timedelta(days=4))

    assert freshness_score(fresh, now=now) == 1
    assert freshness_score(old, now=now) == 0


def make_feed_item(
    item_id: int,
    title: str,
    relevance_score: float = 0.5,
    importance_score: float = 0.5,
    published_at: datetime | None = None,
) -> FeedItem:
    return FeedItem(
        id=item_id,
        title=title,
        url=f"https://example.com/{item_id}",
        source_name="Test",
        author=None,
        language="en",
        published_at=published_at,
        category="technical_trend",
        subcategory=None,
        tickers=[],
        companies=[],
        products=[],
        topics=[],
        sentiment="neutral",
        relevance_score=relevance_score,
        importance_score=importance_score,
        novelty_score=0.5,
        source_quality_score=0.5,
        stock_impact_score=0,
        summary_short=None,
        summary_detailed=None,
        why_it_matters=None,
    )


def make_normalized_item(
    item_id: int,
    title: str,
    language: str,
    topics: list[str] | None = None,
    summary_short: str | None = None,
    category: str = "technical_trend",
    tickers: list[str] | None = None,
    products: list[str] | None = None,
    source_name: str = "Test",
    stock_impact_score: float = 0,
) -> NormalizedItem:
    return NormalizedItem(
        id=item_id,
        raw_item_id=item_id,
        title=title,
        url=f"https://example.com/{item_id}",
        source_name=source_name,
        author=None,
        language=language,
        published_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
        text=title,
        category=category,
        subcategory=None,
        tickers=tickers or [],
        companies=[],
        products=products or [],
        topics=topics if topics is not None else ["agent"],
        sentiment="neutral",
        relevance_score=0.8,
        classification_confidence=0.8,
        importance_score=0.7,
        novelty_score=0.5,
        source_quality_score=0.7,
        stock_impact_score=stock_impact_score,
        summary_short=summary_short,
    )
