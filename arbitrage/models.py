"""Data models shared across the engine.

These are deliberately transport-agnostic: whether a metric arrives via REST
polling or a WebSocket stream, it lands in the same structure so the engine
and reporter never need to know the source.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class MarketSnapshot:
    """A point-in-time view of a single exchange's futures market."""

    exchange: str
    symbol: str
    last_price: Optional[float] = None
    funding_rate: Optional[float] = None
    # Reserved for the upcoming WebSocket order-book integration.
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    timestamp: float = field(default_factory=time.time)
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        """True when we have enough data to participate in spread calc."""
        return self.error is None and self.last_price is not None


@dataclass(slots=True)
class SpreadReport:
    """The computed cross-exchange result for one polling cycle."""

    pair: str
    primary: MarketSnapshot
    secondary: MarketSnapshot
    spread_pct: Optional[float] = None
    timestamp: float = field(default_factory=time.time)
