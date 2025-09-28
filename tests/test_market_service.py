import httpx
import pytest
import respx

from fastpi.config import Settings
from fastpi.services.market import MarketDataService


@pytest.mark.asyncio
async def test_fetch_symbol_aggregates_all_sources() -> None:
    settings = Settings()
    async with httpx.AsyncClient() as client:
        service = MarketDataService(settings=settings, client=client)
        with respx.mock(assert_all_called=False) as mock:
            mock.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                params={"symbol": "BTCUSDT"},
            ).respond(
                200,
                json={
                    "lastPrice": "64000.12",
                    "priceChangePercent": "2.5",
                    "quoteVolume": "450000000.0",
                },
            )
            mock.get(
                "https://api.bybit.com/v5/market/tickers",
                params={"category": "spot", "symbol": "BTCUSDT"},
            ).respond(
                200,
                json={
                    "result": {
                        "list": [
                            {
                                "lastPrice": "63950.55",
                                "price24hPcnt": "0.025",
                                "turnover24h": "420000000.0",
                            }
                        ]
                    }
                },
            )
            mock.get(
                "https://api.coincap.io/v2/assets",
                params={"search": "BTC"},
            ).respond(
                200,
                json={
                    "data": [
                        {
                            "symbol": "BTC",
                            "priceUsd": "63975.10",
                            "changePercent24Hr": "2.45",
                            "volumeUsd24Hr": "410000000.0",
                        }
                    ]
                },
            )

            snapshot = await service.fetch_symbol("BTC", "USDT")

    assert snapshot.symbol == "BTCUSDT"
    assert snapshot.base_symbol == "BTC"
    assert snapshot.quote_symbol == "USDT"
    assert len(snapshot.prices) == 3
    assert snapshot.median_price is not None
    sources = {point.source for point in snapshot.prices}
    assert {"binance", "bybit", "coincap"}.issubset(sources)
    bybit_point = next(point for point in snapshot.prices if point.source == "bybit")
    assert bybit_point.change_24h == pytest.approx(2.5)


@pytest.mark.asyncio
async def test_fetch_symbol_uses_coincap_token() -> None:
    settings = Settings(coincap_api_key="secret-token")
    async with httpx.AsyncClient() as client:
        service = MarketDataService(settings=settings, client=client)
        with respx.mock(assert_all_called=False) as mock:
            mock.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                params={"symbol": "BTCUSDT"},
            ).respond(200, json={})
            mock.get(
                "https://api.bybit.com/v5/market/tickers",
                params={"category": "spot", "symbol": "BTCUSDT"},
            ).respond(200, json={"result": {"list": [{"lastPrice": "0"}]}})
            mock.get(
                "https://api.coincap.io/v2/assets",
                params={"search": "BTC"},
                headers={"Authorization": "Bearer secret-token"},
            ).respond(
                200,
                json={
                    "data": [
                        {
                            "symbol": "BTC",
                            "priceUsd": "1",
                            "changePercent24Hr": "0",
                            "volumeUsd24Hr": "0",
                        }
                    ]
                },
            )

            snapshot = await service.fetch_symbol("BTC", "USDT")

    assert snapshot.symbol == "BTCUSDT"
