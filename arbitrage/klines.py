"""On-demand spread history via ccxt OHLCV.

Used by the ``/api/v1/spread-history`` endpoint. Builds two short-lived ccxt
clients, pulls ~3 days of hourly candles from each venue, aligns them by
timestamp and returns the per-candle price spread. Nothing is persisted.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

import ccxt.async_support as ccxt

from .config import EXCHANGE_SPECS

log = logging.getLogger(__name__)

_NAME_TO_SPEC = {s.name.lower(): s for s in EXCHANGE_SPECS}
_ID_TO_SPEC = {s.id.lower(): s for s in EXCHANGE_SPECS}

_QUOTES = ("USDT", "USDC")
_HOUR_MS = 3_600_000


def _resolve_spec(key: str):
    k = key.lower()
    return _NAME_TO_SPEC.get(k) or _ID_TO_SPEC.get(k)


def _candidate_symbols(asset: str) -> list[str]:
    base = asset.upper()
    return [f"{base}/{q}:{q}" for q in _QUOTES]


async def _client_for(key: str):
    spec = _resolve_spec(key)
    if spec is None:
        raise ValueError(f"unknown exchange '{key}'")
    klass = getattr(ccxt, spec.id, None)
    if klass is None:
        raise ValueError(f"ccxt has no exchange '{spec.id}'")
    client = klass(
        {
            "enableRateLimit": True,
            "timeout": 20_000,
            "options": dict(spec.options),
        }
    )
    await client.load_markets()
    return client


async def _ohlcv_map(client, asset: str, since: int, limit: int) -> dict[int, float]:
    """Return {candle_open_ms: close_price} for the first resolvable symbol."""
    markets = getattr(client, "markets", {}) or {}
    for symbol in _candidate_symbols(asset):
        if symbol not in markets:
            continue
        try:
            rows = await client.fetch_ohlcv(
                symbol, timeframe="1h", since=since, limit=limit
            )
        except Exception as exc:  # noqa: BLE001
            log.debug("ohlcv failed for %s: %s", symbol, exc)
            continue
        # row = [ts, open, high, low, close, volume]
        return {int(r[0]): float(r[4]) for r in rows if r[4] is not None}
    return {}


async def fetch_spread_history(
    asset: str, ex1: str, ex2: str, days: int = 3
) -> list[dict]:
    """Return aligned per-hour spread points over the last ``days`` days.

    Each point: ``{time, ex1_price, ex2_price, spread_pct}`` where
    ``spread_pct = (ex1 - ex2) / ex2 * 100``.
    """
    limit = days * 24
    since = int(time.time() * 1000) - limit * _HOUR_MS

    client1: Optional[object] = None
    client2: Optional[object] = None
    try:
        client1, client2 = await asyncio.gather(
            _client_for(ex1), _client_for(ex2)
        )
        map1, map2 = await asyncio.gather(
            _ohlcv_map(client1, asset, since, limit),
            _ohlcv_map(client2, asset, since, limit),
        )
    finally:
        for c in (client1, client2):
            if c is not None:
                try:
                    await c.close()  # type: ignore[attr-defined]
                except Exception:  # noqa: BLE001
                    pass

    common = sorted(set(map1) & set(map2))
    points: list[dict] = []
    for ts in common:
        p1, p2 = map1[ts], map2[ts]
        if p2 <= 0:
            continue
        points.append(
            {
                "time": ts,
                "ex1_price": p1,
                "ex2_price": p2,
                "spread_pct": (p1 - p2) / p2 * 100.0,
            }
        )
    return points
