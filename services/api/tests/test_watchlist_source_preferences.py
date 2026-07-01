from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import (
    Base,
    CompanyWatchlistItem,
    NormalizedItem,
    ProductWatchlistItem,
    StockWatchlistItem,
    TopicWatchlistItem,
)
from app.services.watchlist import (
    get_company_briefing,
    get_product_briefing,
    get_stock_signals,
    get_topic_briefing,
)


def test_company_briefing_excludes_blocked_sources() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add(
            CompanyWatchlistItem(
                user_id="local",
                company_key="nvidia",
                company_name="NVIDIA",
                ticker="NVDA",
                category="semiconductor",
                related_terms=["GPU"],
            )
        )
        db.add_all(
            [
                make_item(1, "Blocked NVIDIA GPU note", "Noisy Blog", companies=["NVIDIA"]),
                make_item(2, "Visible NVIDIA GPU note", "Trusted Blog", companies=["NVIDIA"]),
            ]
        )
        db.commit()

        briefing = get_company_briefing(
            db,
            company_key="nvidia",
            blocked_sources=["Noisy Blog"],
        )

    assert briefing is not None
    assert [item.title for item in briefing.recent_timeline] == ["Visible NVIDIA GPU note"]
    assert [source.source_name for source in briefing.trending_sources] == ["Trusted Blog"]


def test_product_briefing_excludes_blocked_sources() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add(
            ProductWatchlistItem(
                user_id="local",
                category="ai-coding-tools",
                label="AI coding tools",
                related_terms=["agent"],
            )
        )
        db.add_all(
            [
                make_item(
                    1,
                    "Blocked coding agent note",
                    "Noisy Blog",
                    products=["AgentDesk"],
                ),
                make_item(
                    2,
                    "Visible coding agent note",
                    "Trusted Blog",
                    products=["AgentDesk"],
                ),
            ]
        )
        db.commit()

        briefing = get_product_briefing(
            db,
            category="ai-coding-tools",
            blocked_sources=["Noisy Blog"],
        )

    assert briefing is not None
    assert [item.title for item in briefing.recent_timeline] == ["Visible coding agent note"]
    assert [source.source_name for source in briefing.trending_sources] == ["Trusted Blog"]


def test_product_briefing_matches_product_use_case_subcategory() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add(
            ProductWatchlistItem(
                user_id="local",
                category="ai-coding-tools",
                label="AI coding tools",
                related_terms=[],
            )
        )
        db.add_all(
            [
                make_item(
                    1,
                    "Generic launch",
                    "Product Hunt",
                    category="product",
                    subcategory="product_coding",
                    text="New workspace for software teams.",
                ),
                make_item(
                    2,
                    "Creative studio launch",
                    "Product Hunt",
                    category="product",
                    subcategory="product_media",
                    text="New workspace for creators.",
                ),
            ]
        )
        db.commit()

        briefing = get_product_briefing(db, category="ai-coding-tools")

    assert briefing is not None
    assert [item.title for item in briefing.recent_timeline] == ["Generic launch"]
    assert [(bucket.source_name, bucket.item_count) for bucket in briefing.use_case_counts] == [
        ("Coding", 1)
    ]


def test_topic_briefing_excludes_blocked_sources() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add(
            TopicWatchlistItem(
                user_id="local",
                topic="ai-coding-agents",
                label="AI coding agents",
                category="technical_trend",
                related_terms=["coding agent"],
            )
        )
        db.add_all(
            [
                make_item(
                    1,
                    "Blocked coding agent trend",
                    "Noisy Blog",
                    topics=["ai-coding-agents"],
                ),
                make_item(
                    2,
                    "Visible coding agent trend",
                    "Trusted Blog",
                    topics=["ai-coding-agents"],
                ),
            ]
        )
        db.commit()

        briefing = get_topic_briefing(
            db,
            topic="ai-coding-agents",
            blocked_sources=["Noisy Blog"],
        )

    assert briefing is not None
    assert [item.title for item in briefing.recent_timeline] == ["Visible coding agent trend"]
    assert [source.source_name for source in briefing.trending_sources] == ["Trusted Blog"]


def test_stock_signals_exclude_blocked_sources() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as db:
        db.add(
            StockWatchlistItem(
                user_id="local",
                ticker="MU",
                company_name="Micron",
                exchange="NASDAQ",
                sector="Technology",
                industry="Semiconductors",
                related_keywords=["HBM"],
            )
        )
        db.add_all(
            [
                make_item(1, "Blocked Micron HBM note", "Noisy Blog", tickers=["MU"]),
                make_item(2, "Visible Micron HBM note", "Trusted Blog", tickers=["MU"]),
            ]
        )
        db.commit()

        summary = get_stock_signals(
            db,
            ticker="MU",
            blocked_sources=["Noisy Blog"],
        )

    assert summary is not None
    assert summary.signal_count == 1
    assert [item.title for item in summary.top_signals] == ["Visible Micron HBM note"]


def make_item(
    item_id: int,
    title: str,
    source_name: str,
    companies: list[str] | None = None,
    products: list[str] | None = None,
    topics: list[str] | None = None,
    tickers: list[str] | None = None,
    category: str = "technical_trend",
    subcategory: str | None = None,
    text: str | None = None,
) -> NormalizedItem:
    return NormalizedItem(
        id=item_id,
        raw_item_id=item_id,
        title=title,
        url=f"https://example.com/{item_id}",
        source_name=source_name,
        author=None,
        language="en",
        published_at=datetime(2026, 6, 25, 12, item_id, tzinfo=UTC),
        text=text or title,
        category=category,
        subcategory=subcategory,
        tickers=tickers or [],
        companies=companies or [],
        products=products or [],
        topics=topics or [],
        sentiment="neutral",
        relevance_score=0.8,
        classification_confidence=0.8,
        importance_score=0.75,
        novelty_score=0.6,
        source_quality_score=0.7,
        stock_impact_score=0.4 if tickers else 0,
    )
