"""A pool of ccxt async clients, one per venue.

The pool centralises lifecycle (load markets / close), and exposes the three
network primitives the scanner needs: ``fetch_tickers``, ``fetch_order_book``
and ``fetch_funding_rate``. Every public method tolerates per-exchange failure
so one flaky venue never takes the whole cycle down.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

import ccxt.async_support as ccxt

from ..config import ExchangeSpec, Settings
from ..models import Ticker

log = logging.getLogger(__name__)


class ExchangePool:
    """Owns one ccxt client per configured exchange."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._clients: dict[str, Any] = {}
        self._specs: dict[str, ExchangeSpec] = {}
        for spec in settings.exchanges:
            klass = getattr(ccxt, spec.id, None)
            if klass is None:
                log.warning("ccxt has no exchange %r; skipping", spec.id)
                continue
            self._clients[spec.name] = klass(
                {
                    "enableRateLimit": True,
                    "timeout": int(settings.request_timeout * 1000),
                    "options": dict(spec.options),
                }
            )
            self._specs[spec.name] = spec

    @property
    def names(self) -> list[str]:
        return list(self._clients)

    def client(self, name: str):
        return self._clients[name]

    async def load(self) -> None:
        """Load markets for every client concurrently, tolerating failures."""
        async def _load(name: str, client: Any) -> None:
            try:
                await client.load_markets()
                log.info("%s: %d markets loaded", name, len(client.markets))
            except Exception as exc:  # noqa: BLE001
                log.warning("%s: load_markets failed: %s", name, exc)

        await asyncio.gather(
            *(_load(n, c) for n, c in self._clients.items())
        )

    async def close(self) -> None:
        await asyncio.gather(
            *(c.close() for c in self._clients.values()),
            return_exceptions=True,
        )

    # ------------------------------------------------------------------ #
    # Step 1: bulk tickers
    # ------------------------------------------------------------------ #
    async def fetch_all_tickers(self) -> dict[str, list[Ticker]]:
        """Concurrently pull tickers from every venue.

        Returns a mapping of exchange name -> list of normalized
        :class:`Ticker`, restricted to active linear perpetuals quoted in the
        configured currencies.
        """

        async def _one(name: str, client: Any) -> tuple[str, list[Ticker]]:
            try:
                raw = await client.fetch_tickers()
            except Exception as exc:  # noqa: BLE001
                log.warning("%s: fetch_tickers failed: %s", name, exc)
                return name, []
            return name, self._normalize_tickers(name, client, raw)

        results = await asyncio.gather(
            *(_one(n, c) for n, c in self._clients.items())
        )
        return {name: tickers for name, tickers in results}

    def _normalize_tickers(
        self, name: str, client: Any, raw: dict[str, dict]
    ) -> list[Ticker]:
        out: list[Ticker] = []
        markets = getattr(client, "markets", {}) or {}
        quotes = self._settings.quote_currencies
        for symbol, t in raw.items():
            market = markets.get(symbol)
            if not market:
                continue
            if not (market.get("swap") and market.get("linear")):
                continue
            if not market.get("active", True):
                continue
            if market.get("quote") not in quotes:
                continue
            last = _as_float(t.get("last") or t.get("close"))
            bid = _as_float(t.get("bid"))
            ask = _as_float(t.get("ask"))
            if last is None and bid is None and ask is None:
                continue
            out.append(
                Ticker(
                    exchange=name,
                    symbol=symbol,
                    base=market.get("base", symbol.split("/")[0]),
                    last=last,
                    bid=bid,
                    ask=ask,
                )
            )
        return out

    # ------------------------------------------------------------------ #
    # Step 2: order books + funding
    # ------------------------------------------------------------------ #
    async def fetch_order_book(
        self, name: str, symbol: str, limit: int = 50
    ) -> Optional[dict]:
        client = self._clients.get(name)
        if client is None:
            return None
        try:
            return await client.fetch_order_book(symbol, limit=limit)
        except Exception as exc:  # noqa: BLE001
            log.debug("%s: fetch_order_book(%s) failed: %s", name, symbol, exc)
            return None

    async def fetch_funding_rate(
        self, name: str, symbol: str
    ) -> Optional[dict]:
        client = self._clients.get(name)
        if client is None:
            return None
        try:
            return await client.fetch_funding_rate(symbol)
        except Exception as exc:  # noqa: BLE001
            log.debug("%s: fetch_funding_rate(%s) failed: %s", name, symbol, exc)
            return None

    async def fetch_ohlcv(
        self,
        name: str,
        symbol: str,
        timeframe: str = "1h",
        since: Optional[int] = None,
        limit: int = 72,
    ) -> list[list[float]]:
        client = self._clients.get(name)
        if client is None:
            return []
        try:
            return await client.fetch_ohlcv(
                symbol, timeframe=timeframe, since=since, limit=limit
            )
        except Exception as exc:  # noqa: BLE001
            log.debug("%s: fetch_ohlcv(%s) failed: %s", name, symbol, exc)
            return []


def _as_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
