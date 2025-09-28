from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from ..config import Settings, get_settings
from ..http_client import get_http_client
from ..models.market import MarketAggregate, MarketPricePoint


@dataclass(slots=True)
class MarketDataService:
    settings: Settings | None = None
    client: httpx.AsyncClient | None = None

    def __post_init__(self) -> None:
        if self.settings is None:
            self.settings = get_settings()

    async def fetch_symbol(
        self, base_symbol: str, quote_symbol: str = "USDT"
    ) -> MarketAggregate:
        base = base_symbol.upper()
        quote = quote_symbol.upper()
        symbol = f"{base}{quote}"
        client = self.client or await get_http_client()

        tasks = [
            self._fetch_binance(client, base, quote),
            self._fetch_bybit(client, base, quote),
            self._fetch_coincap(client, base, quote),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        price_points: list[MarketPricePoint] = []
        for result in results:
            if isinstance(result, MarketPricePoint):
                price_points.append(result)
            else:
                price_points.append(
                    MarketPricePoint(
                        source="error",
                        symbol=symbol,
                        price=None,
                        change_24h=None,
                        volume_24h=None,
                        raw={"message": str(result)},
                    )
                )

        return MarketAggregate(
            base_symbol=base,
            quote_symbol=quote,
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            prices=price_points,
        )

    async def _fetch_binance(
        self, client: httpx.AsyncClient, base: str, quote: str
    ) -> MarketPricePoint:
        symbol = f"{base}{quote}"
        url = f"{self.settings.binance_base_url}/api/v3/ticker/24hr"
        response = await client.get(url, params={"symbol": symbol})
        response.raise_for_status()
        payload = response.json()
        price = _to_float(payload.get("lastPrice"))
        change = _to_float(payload.get("priceChangePercent"))
        volume = _to_float(payload.get("quoteVolume"))
        return MarketPricePoint(
            source="binance",
            symbol=symbol,
            price=price,
            change_24h=change,
            volume_24h=volume,
            raw=payload,
        )

    async def _fetch_bybit(
        self, client: httpx.AsyncClient, base: str, quote: str
    ) -> MarketPricePoint:
        symbol = f"{base}{quote}"
        url = f"{self.settings.bybit_base_url}/v5/market/tickers"
        params = {"category": "spot", "symbol": symbol}
        response = await client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()
        items = payload.get("result", {}).get("list", [])
        first: dict[str, Any] | None = items[0] if items else None
        if not first:
            raise ValueError(f"Bybit returned no ticker data for {symbol}")
        price = _to_float(first.get("lastPrice"))
        change = None
        if "price24hPcnt" in first:
            pct = _to_float(first.get("price24hPcnt"))
            change = pct * 100 if pct is not None else None
        volume = _to_float(first.get("turnover24h"))
        return MarketPricePoint(
            source="bybit",
            symbol=symbol,
            price=price,
            change_24h=change,
            volume_24h=volume,
            raw=first,
        )

    async def _fetch_coincap(
        self, client: httpx.AsyncClient, base: str, quote: str
    ) -> MarketPricePoint:
        # CoinCap returns USD denominated data; quote is ignored but captured for context
        url = f"{self.settings.coincap_base_url}/assets"
        headers: dict[str, str] | None = None
        if self.settings.coincap_api_key:
            headers = {"Authorization": f"Bearer {self.settings.coincap_api_key}"}
        response = await client.get(url, params={"search": base}, headers=headers)
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data", [])
        match = None
        base_upper = base.upper()
        for entry in data:
            if entry.get("symbol", "").upper() == base_upper:
                match = entry
                break
        if match is None and data:
            match = data[0]
        if match is None:
            raise ValueError(f"CoinCap returned no asset data for {base}")
        price = _to_float(match.get("priceUsd"))
        change = _to_float(match.get("changePercent24Hr"))
        volume = _to_float(match.get("volumeUsd24Hr"))
        return MarketPricePoint(
            source="coincap",
            symbol=f"{base}{quote}",
            price=price,
            change_24h=change,
            volume_24h=volume,
            raw=match,
        )


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
