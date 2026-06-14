"""Transport-agnostic data models shared across the engine, API and bot."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class Ticker:
    """A lightweight ticker row distilled from ccxt ``fetch_tickers``."""

    exchange: str
    symbol: str
    base: str
    last: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None

    @property
    def mid(self) -> Optional[float]:
        """Best available mid price: (bid+ask)/2, falling back to last."""
        if self.bid is not None and self.ask is not None and self.bid > 0:
            return (self.bid + self.ask) / 2.0
        return self.last


@dataclass(slots=True)
class FundingLeg:
    """Funding state for one leg of a position.

    ``rate`` is a fraction (e.g. 0.0001 == 0.01%) charged each interval.
    ``interval_hours`` and ``next_funding_ms`` are extracted dynamically and
    never hardcoded to 8h.
    """

    rate: Optional[float] = None
    interval_hours: float = 8.0
    next_funding_ms: Optional[int] = None

    def per_24h(self) -> Optional[float]:
        """Funding accrued over 24h as a fraction, given this leg's interval."""
        if self.rate is None or self.interval_hours <= 0:
            return None
        return self.rate * (24.0 / self.interval_hours)


@dataclass(slots=True)
class Opportunity:
    """A single delta-neutral arbitrage opportunity for one asset.

    Convention: you BUY (go long) the cheaper ``long_exchange`` and SELL (go
    short) the richer ``short_exchange``; the price spread is captured on
    convergence while funding is farmed for the holding period.
    """

    asset: str
    long_exchange: str
    short_exchange: str
    long_symbol: str
    short_symbol: str

    long_price: float
    short_price: float

    # Step 1: naive mid-to-mid spread used for ranking before order books.
    raw_spread_pct: float
    # Step 2: spread after walking L2 books for a fixed-notional order.
    real_spread_pct: Optional[float] = None

    long_funding: Optional[float] = None
    short_funding: Optional[float] = None
    # Funding charge interval per leg, in hours (e.g. 8.0 or 4.0). Derived from
    # the exchange payload, never assumed.
    long_funding_interval_h: Optional[float] = None
    short_funding_interval_h: Optional[float] = None
    # Net funding you keep per 24h (short income minus long cost), as percent.
    net_funding_24h_pct: Optional[float] = None
    farm_24h_pct: Optional[float] = None
    farm_72h_pct: Optional[float] = None
    next_funding_ms: Optional[int] = None

    timestamp: float = field(default_factory=time.time)

    @property
    def key(self) -> str:
        """Stable identity for de-duplicating alerts."""
        return f"{self.asset}:{self.long_exchange}->{self.short_exchange}"

    def to_dict(self) -> dict:
        return {
            "asset": self.asset,
            "long_exchange": self.long_exchange,
            "short_exchange": self.short_exchange,
            "long_symbol": self.long_symbol,
            "short_symbol": self.short_symbol,
            "long_price": self.long_price,
            "short_price": self.short_price,
            "raw_spread_pct": self.raw_spread_pct,
            "real_spread_pct": self.real_spread_pct,
            "long_funding": self.long_funding,
            "short_funding": self.short_funding,
            "long_funding_interval_h": self.long_funding_interval_h,
            "short_funding_interval_h": self.short_funding_interval_h,
            "net_funding_24h_pct": self.net_funding_24h_pct,
            "farm_24h_pct": self.farm_24h_pct,
            "farm_72h_pct": self.farm_72h_pct,
            "next_funding_ms": self.next_funding_ms,
            "timestamp": self.timestamp,
        }
