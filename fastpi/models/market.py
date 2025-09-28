from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MarketPricePoint(BaseModel):
    source: str = Field(description="Data provider name")
    symbol: str = Field(description="Trading pair symbol (e.g. BTCUSDT)")
    price: float | None = Field(default=None, description="Last traded price")
    change_24h: float | None = Field(
        default=None, description="24 hour price change percentage"
    )
    volume_24h: float | None = Field(
        default=None, description="24 hour traded volume in quote currency"
    )
    raw: dict[str, Any] | None = Field(
        default=None, description="Provider payload for debugging/tracing"
    )


class MarketAggregate(BaseModel):
    base_symbol: str = Field(description="Base asset symbol, e.g. BTC")
    quote_symbol: str = Field(description="Quote asset symbol, e.g. USDT")
    symbol: str = Field(description="Concatenated symbol built from base+quote")
    timestamp: datetime = Field(description="UTC timestamp when the snapshot was taken")
    prices: list[MarketPricePoint] = Field(
        default_factory=list, description="Market data points per provider"
    )

    @property
    def median_price(self) -> float | None:
        non_null = sorted(
            (point.price for point in self.prices if point.price is not None)
        )
        if not non_null:
            return None
        mid = len(non_null) // 2
        if len(non_null) % 2 == 0:
            return (non_null[mid - 1] + non_null[mid]) / 2
        return non_null[mid]
