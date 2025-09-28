from __future__ import annotations

from fastapi import Depends, FastAPI, Query
from fastapi.responses import ORJSONResponse
from mangum import Mangum

from fastpi.http_client import shutdown_http_client
from fastpi.services import MarketDataService, NewsService

app = FastAPI(
    title="FastPI Crypto Intelligence API",
    version="0.1.0",
    description=(
        "Aggregated crypto market metrics and curated news feeds built for serverless deployment."
    ),
    default_response_class=ORJSONResponse,
)


def get_market_service() -> MarketDataService:
    return MarketDataService()


def get_news_service() -> NewsService:
    return NewsService()


@app.get("/health", tags=["system"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/market/summary", tags=["market"])
async def market_summary(
    base: str = Query(
        "BTC", pattern=r"^[A-Z0-9]{1,10}$", description="Base symbol (e.g. BTC)"
    ),
    quote: str = Query(
        "USDT", pattern=r"^[A-Z0-9]{1,10}$", description="Quote symbol (e.g. USDT)"
    ),
    service: MarketDataService = Depends(get_market_service),
):
    return await service.fetch_symbol(base, quote)


@app.get("/news/aggregate", tags=["news"])
async def news_aggregate(
    limit: int = Query(
        6,
        ge=1,
        le=12,
        description="Maximum articles to pull per source",
    ),
    service: NewsService = Depends(get_news_service),
):
    return await service.fetch_all(limit_per_source=limit)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await shutdown_http_client()


handler = Mangum(app)
