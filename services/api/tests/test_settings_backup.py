from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import (
    AlertRule,
    Base,
    CompanyWatchlistItem,
    ProductWatchlistItem,
    Source,
    StockWatchlistItem,
    TopicWatchlistItem,
)
from app.schemas.alerts import AlertRuleCreate
from app.schemas.preferences import RankingWeights, UserPreferencesUpdate
from app.schemas.settings_backup import PersonalSettingsBackup
from app.schemas.sources import SourceCreate
from app.schemas.watchlist import (
    CompanyWatchlistItemCreate,
    ProductWatchlistItemCreate,
    StockWatchlistItemCreate,
    TopicWatchlistItemCreate,
)
from app.services.preferences import get_user_preferences, update_user_preferences
from app.services.settings_backup import (
    export_personal_settings_backup,
    restore_personal_settings_backup,
)


def test_export_personal_settings_backup_contains_only_local_configuration() -> None:
    SessionLocal = build_session()
    with SessionLocal() as db:
        update_user_preferences(
            db,
            UserPreferencesUpdate(
                ranking_weights=RankingWeights(importance=0.4),
                preferred_sources=["arXiv"],
                blocked_sources=["Noisy RSS"],
                language_preferences=["en"],
            ),
        )
        db.add(
            Source(
                name="AI Blog",
                type="rss",
                access_method="rss",
                base_url="https://example.com/feed.xml",
                enabled=True,
                priority=25,
                terms_notes="Public feed only.",
            )
        )
        db.add(
            AlertRule(
                user_id="local",
                name="Agent alert",
                description="Watch agent news.",
                category="technical_trend",
                severity="medium",
                min_importance_score=0.7,
                min_stock_impact_score=0,
                tickers=[],
                topics=["agents"],
                enabled=True,
            )
        )
        db.add(
            StockWatchlistItem(
                user_id="local",
                ticker="MU",
                company_name="Micron",
                exchange="NASDAQ",
                sector="Technology",
                industry="Semiconductors",
                market_cap_usd=100_000_000_000,
                priority="High",
                group_name="Watch Only",
                display_order=10,
                related_ai_themes=["HBM"],
            )
        )
        db.commit()

        backup = export_personal_settings_backup(db)
        backup_dict = backup.model_dump()

        assert backup.version == 1
        assert backup.preferences is not None
        assert backup.preferences.preferred_sources == ["arXiv"]
        assert backup.sources[0].name == "AI Blog"
        assert backup.alert_rules[0].name == "Agent alert"
        assert backup.stock_watchlist[0].ticker == "MU"
        assert backup.stock_watchlist[0].market_cap_usd == 100_000_000_000
        assert "moonshot" not in str(backup_dict).lower()
        assert "api_key" not in str(backup_dict).lower()
        assert "raw_items" not in str(backup_dict).lower()
        assert "normalized_items" not in str(backup_dict).lower()


def test_restore_personal_settings_backup_upserts_configuration_without_deleting() -> None:
    SessionLocal = build_session()
    with SessionLocal() as db:
        db.add(
            Source(
                name="AI Blog",
                type="rss",
                access_method="rss",
                base_url="https://old.example.com/rss.xml",
                enabled=False,
                priority=100,
            )
        )
        db.add(
            Source(
                name="Keep Me",
                type="rss",
                access_method="rss",
                base_url="https://keep.example.com/rss.xml",
                enabled=True,
                priority=10,
            )
        )
        db.add(
            AlertRule(
                user_id="local",
                name="Agent alert",
                category="all",
                severity="low",
                min_importance_score=0.5,
                min_stock_impact_score=0,
                tickers=[],
                topics=[],
                enabled=False,
            )
        )
        db.add(
            StockWatchlistItem(
                user_id="local",
                ticker="MU",
                company_name="Micron",
                exchange="NASDAQ",
                sector="Technology",
                industry="Semiconductors",
                priority="Low",
                group_name="Watch Only",
                display_order=40,
                notes="Old note",
            )
        )
        db.commit()

        backup = PersonalSettingsBackup(
            exported_at=datetime(2026, 7, 2, 9, 0, tzinfo=UTC),
            preferences=UserPreferencesUpdate(
                ranking_weights=RankingWeights(relevance=0.3, importance=0.25),
                preferred_sources=["AI Blog"],
                blocked_sources=["Noisy RSS"],
                language_preferences=["Chinese", "en-us"],
            ),
            sources=[
                SourceCreate(
                    name="AI Blog",
                    type="rss",
                    access_method="rss",
                    base_url="https://new.example.com/rss.xml",
                    enabled=True,
                    priority=5,
                    polling_interval="6 hours",
                )
            ],
            alert_rules=[
                AlertRuleCreate(
                    name="Agent alert",
                    description="Updated agent rule.",
                    category="technical_trend",
                    severity="high",
                    min_importance_score=0.8,
                    topics=["agent workflows"],
                    enabled=True,
                )
            ],
            stock_watchlist=[
                StockWatchlistItemCreate(
                    ticker="MU",
                    company_name="Micron Technology",
                    exchange="NASDAQ",
                    sector="Technology",
                    industry="Semiconductors",
                    market_cap_usd=120_000_000_000,
                    priority="High",
                    group_name="Core AI Stocks",
                    display_order=15,
                    related_ai_themes=["HBM"],
                    notes="Restored note",
                )
            ],
            company_watchlist=[
                CompanyWatchlistItemCreate(
                    company_key="openai",
                    company_name="OpenAI",
                    category="ai_lab",
                    related_terms=["reasoning models"],
                )
            ],
            topic_watchlist=[
                TopicWatchlistItemCreate(
                    topic="agent-workflows",
                    label="Agent workflows",
                    related_terms=["agent harness"],
                )
            ],
            product_watchlist=[
                ProductWatchlistItemCreate(
                    category="ai-coding-tools",
                    label="AI coding tools",
                    related_terms=["coding agents"],
                )
            ],
        )

        result = restore_personal_settings_backup(db, backup)

        preferences = get_user_preferences(db)
        source = db.query(Source).filter(Source.name == "AI Blog").one()
        alert_rule = db.query(AlertRule).filter(AlertRule.name == "Agent alert").one()
        stock = db.query(StockWatchlistItem).filter(StockWatchlistItem.ticker == "MU").one()

        assert result.preferences_updated is True
        assert result.sources_upserted == 1
        assert result.alert_rules_upserted == 1
        assert result.stock_watchlist_upserted == 1
        assert result.company_watchlist_upserted == 1
        assert result.topic_watchlist_upserted == 1
        assert result.product_watchlist_upserted == 1
        assert preferences.blocked_sources == ["Noisy RSS"]
        assert preferences.language_preferences == ["zh", "en"]
        assert source.base_url == "https://new.example.com/rss.xml"
        assert source.enabled is True
        assert source.priority == 5
        assert db.query(Source).filter(Source.name == "Keep Me").count() == 1
        assert alert_rule.severity == "high"
        assert alert_rule.topics == ["agent workflows"]
        assert stock.company_name == "Micron Technology"
        assert stock.market_cap_usd == 120_000_000_000
        assert stock.display_order == 15
        assert stock.notes == "Restored note"
        assert (
            db.query(CompanyWatchlistItem)
            .filter(CompanyWatchlistItem.company_key == "openai")
            .count()
            == 1
        )
        assert (
            db.query(TopicWatchlistItem)
            .filter(TopicWatchlistItem.topic == "agent-workflows")
            .count()
            == 1
        )
        assert (
            db.query(ProductWatchlistItem)
            .filter(ProductWatchlistItem.category == "ai-coding-tools")
            .count()
            == 1
        )


def test_restore_personal_settings_backup_skips_unsupported_versions() -> None:
    SessionLocal = build_session()
    with SessionLocal() as db:
        result = restore_personal_settings_backup(
            db,
            PersonalSettingsBackup(
                version=99,
                exported_at=datetime(2026, 7, 2, 9, 0, tzinfo=UTC),
                sources=[SourceCreate(name="Should Not Import")],
            ),
        )

        assert result.sources_upserted == 0
        assert result.skipped_sections == ["Unsupported backup version 99."]
        assert db.query(Source).count() == 0


def build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)
