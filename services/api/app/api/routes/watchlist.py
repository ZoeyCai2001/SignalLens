from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import DbSession
from app.schemas.watchlist import (
    ProductBriefing,
    ProductWatchlistItem,
    ProductWatchlistItemCreate,
    ProductWatchlistItemUpdate,
    StockBriefing,
    StockMarketSnapshot,
    StockSignalSummary,
    StockWatchlistItem,
    StockWatchlistItemCreate,
    StockWatchlistItemUpdate,
    TopicBriefing,
    TopicWatchlistItem,
    TopicWatchlistItemCreate,
    TopicWatchlistItemUpdate,
)
from app.services.seed_data import (
    initial_product_watchlist,
    initial_stock_watchlist,
    initial_topic_watchlist,
)
from app.services.watchlist import (
    build_stock_market_snapshot,
    create_product_watchlist_item,
    create_stock_watchlist_item,
    create_topic_watchlist_item,
    delete_product_watchlist_item,
    delete_stock_watchlist_item,
    delete_topic_watchlist_item,
    get_stock_briefing,
    get_stock_signals,
    get_product_briefing,
    get_topic_briefing,
    list_product_watchlist,
    list_topic_watchlist,
    seed_initial_product_watchlist,
    seed_initial_stock_watchlist,
    seed_initial_topic_watchlist,
    summarize_stock_signals,
    update_product_watchlist_item,
    update_stock_watchlist_item,
    update_topic_watchlist_item,
)
from app.services.watchlist import (
    list_stock_watchlist as list_stock_watchlist_items,
)

router = APIRouter()


@router.get("/stocks", response_model=list[StockWatchlistItem])
async def list_stock_watchlist(db: DbSession) -> list[StockWatchlistItem]:
    items = list_stock_watchlist_items(db)
    if not items:
        return initial_stock_watchlist()
    return [StockWatchlistItem.model_validate(item) for item in items]


@router.post("/stocks/seed", response_model=list[StockWatchlistItem])
async def seed_stock_watchlist(db: DbSession) -> list[StockWatchlistItem]:
    items = seed_initial_stock_watchlist(db)
    return [StockWatchlistItem.model_validate(item) for item in items]


@router.post("/stocks", response_model=StockWatchlistItem, status_code=201)
async def create_stock(
    payload: StockWatchlistItemCreate,
    db: DbSession,
) -> StockWatchlistItem:
    try:
        item = create_stock_watchlist_item(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return StockWatchlistItem.model_validate(item)


@router.get("/stocks/signals/summary", response_model=list[StockSignalSummary])
async def list_stock_signal_summary(
    db: DbSession,
    limit_per_stock: Annotated[int, Query(ge=0, le=10)] = 3,
) -> list[StockSignalSummary]:
    return summarize_stock_signals(db, limit_per_stock=limit_per_stock)


@router.get("/stocks/{ticker}/signals", response_model=StockSignalSummary)
async def list_stock_signals(
    ticker: str,
    db: DbSession,
    limit: Annotated[int, Query(ge=0, le=100)] = 20,
) -> StockSignalSummary:
    result = get_stock_signals(db, ticker=ticker, limit=limit)
    if result is None:
        raise HTTPException(status_code=404, detail="Stock ticker not found in watchlist.")
    return result


@router.get("/stocks/{ticker}/briefing", response_model=StockBriefing)
async def get_stock_watchlist_briefing(
    ticker: str,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> StockBriefing:
    result = get_stock_briefing(db, ticker=ticker, limit=limit)
    if result is None:
        raise HTTPException(status_code=404, detail="Stock ticker not found in watchlist.")
    return result


@router.get("/stocks/{ticker}/prices", response_model=StockMarketSnapshot | None)
async def get_stock_prices(
    ticker: str,
    db: DbSession,
    limit: Annotated[int, Query(ge=2, le=260)] = 30,
) -> StockMarketSnapshot | None:
    return build_stock_market_snapshot(db=db, ticker=ticker, limit=limit)


@router.patch("/stocks/{ticker}", response_model=StockWatchlistItem)
async def update_stock(
    ticker: str,
    payload: StockWatchlistItemUpdate,
    db: DbSession,
) -> StockWatchlistItem:
    item = update_stock_watchlist_item(db, ticker=ticker, payload=payload)
    if item is None:
        raise HTTPException(status_code=404, detail="Stock ticker not found in watchlist.")
    return StockWatchlistItem.model_validate(item)


@router.delete("/stocks/{ticker}", status_code=204)
async def delete_stock(ticker: str, db: DbSession) -> None:
    deleted = delete_stock_watchlist_item(db, ticker=ticker)
    if not deleted:
        raise HTTPException(status_code=404, detail="Stock ticker not found in watchlist.")


@router.get("/topics", response_model=list[TopicWatchlistItem])
async def list_topics(db: DbSession) -> list[TopicWatchlistItem]:
    items = list_topic_watchlist(db)
    if not items:
        return initial_topic_watchlist()
    return [TopicWatchlistItem.model_validate(item) for item in items]


@router.post("/topics", response_model=TopicWatchlistItem, status_code=201)
async def create_topic(
    payload: TopicWatchlistItemCreate,
    db: DbSession,
) -> TopicWatchlistItem:
    try:
        item = create_topic_watchlist_item(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TopicWatchlistItem.model_validate(item)


@router.post("/topics/seed", response_model=list[TopicWatchlistItem])
async def seed_topics(db: DbSession) -> list[TopicWatchlistItem]:
    items = seed_initial_topic_watchlist(db)
    return [TopicWatchlistItem.model_validate(item) for item in items]


@router.get("/topics/{topic}/briefing", response_model=TopicBriefing)
async def get_topic_watchlist_briefing(
    topic: str,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> TopicBriefing:
    result = get_topic_briefing(db=db, topic=topic, limit=limit)
    if result is None:
        raise HTTPException(status_code=404, detail="Topic not found in watchlist.")
    return result


@router.patch("/topics/{topic}", response_model=TopicWatchlistItem)
async def update_topic(
    topic: str,
    payload: TopicWatchlistItemUpdate,
    db: DbSession,
) -> TopicWatchlistItem:
    item = update_topic_watchlist_item(db, topic=topic, payload=payload)
    if item is None:
        raise HTTPException(status_code=404, detail="Topic not found in watchlist.")
    return TopicWatchlistItem.model_validate(item)


@router.delete("/topics/{topic}", status_code=204)
async def delete_topic(topic: str, db: DbSession) -> None:
    deleted = delete_topic_watchlist_item(db, topic=topic)
    if not deleted:
        raise HTTPException(status_code=404, detail="Topic not found in watchlist.")


@router.get("/products", response_model=list[ProductWatchlistItem])
async def list_products(db: DbSession) -> list[ProductWatchlistItem]:
    items = list_product_watchlist(db)
    if not items:
        return initial_product_watchlist()
    return [ProductWatchlistItem.model_validate(item) for item in items]


@router.post("/products", response_model=ProductWatchlistItem, status_code=201)
async def create_product(
    payload: ProductWatchlistItemCreate,
    db: DbSession,
) -> ProductWatchlistItem:
    try:
        item = create_product_watchlist_item(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ProductWatchlistItem.model_validate(item)


@router.post("/products/seed", response_model=list[ProductWatchlistItem])
async def seed_products(db: DbSession) -> list[ProductWatchlistItem]:
    items = seed_initial_product_watchlist(db)
    return [ProductWatchlistItem.model_validate(item) for item in items]


@router.get("/products/{category}/briefing", response_model=ProductBriefing)
async def get_product_watchlist_briefing(
    category: str,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProductBriefing:
    result = get_product_briefing(db=db, category=category, limit=limit)
    if result is None:
        raise HTTPException(status_code=404, detail="Product category not found in watchlist.")
    return result


@router.patch("/products/{category}", response_model=ProductWatchlistItem)
async def update_product(
    category: str,
    payload: ProductWatchlistItemUpdate,
    db: DbSession,
) -> ProductWatchlistItem:
    item = update_product_watchlist_item(db, category=category, payload=payload)
    if item is None:
        raise HTTPException(status_code=404, detail="Product category not found in watchlist.")
    return ProductWatchlistItem.model_validate(item)


@router.delete("/products/{category}", status_code=204)
async def delete_product(category: str, db: DbSession) -> None:
    deleted = delete_product_watchlist_item(db, category=category)
    if not deleted:
        raise HTTPException(status_code=404, detail="Product category not found in watchlist.")
