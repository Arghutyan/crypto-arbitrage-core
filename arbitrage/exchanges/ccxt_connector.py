"""Generic ccxt-backed connector for futures markets.

Uses ``ccxt.async_support`` so all I/O is non-blocking. A single connector
instance wraps one exchange and one symbol, fetching the last price and
funding rate concurrently each cycle.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import ccxt.async_support as ccxt

from ..config import ExchangeConfig
from ..models import MarketSnapshot
from .base import ExchangeConnector

log = logging.getLogger(__name__)


class CCXTConnector(ExchangeConnector):
    """Fetches price + funding rate for a perpetual futures market via ccxt."""

    def __init__(self, cfg: ExchangeConfig, request_timeout: float = 10.0) -> None:
        super().__init__(cfg)
        exchange_class = getattr(ccxt, cfg.id)
        self._client = exchange_class(
            {
                "enableRateLimit": True,
                "timeout": int(request_timeout * 1000),
                "options": dict(cfg.options),
            }
        )
        self._markets_loaded = False

    async def load(self) -> None:
        if not self._markets_loaded:
            await self._client.load_markets()
            self._markets_loaded = True
            log.debug("%s: markets loaded", self.name)

    async def fetch_snapshot(self) -> MarketSnapshot:
        """Fetch price and funding rate concurrently, tolerating partial failure."""

        price_task = asyncio.create_task(self._fetch_last_price())
        funding_task = asyncio.create_task(self._fetch_funding_rate())
        results = await asyncio.gather(
            price_task, funding_task, return_exceptions=True
        )

        snapshot = MarketSnapshot(exchange=self.name, symbol=self.symbol)
        errors: list[str] = []

        price_result, funding_result = results
        if isinstance(price_result, Exception):
            errors.append(f"price: {price_result}")
        else:
            snapshot.last_price = price_result

        if isinstance(funding_result, Exception):
            errors.append(f"funding: {funding_result}")
        else:
            snapshot.funding_rate = funding_result

        if errors:
            snapshot.error = "; ".join(errors)
            log.warning("%s fetch issues: %s", self.name, snapshot.error)

        return snapshot

    async def _fetch_last_price(self) -> Optional[float]:
        ticker = await self._client.fetch_ticker(self.symbol)
        return ticker.get("last") or ticker.get("close")

    async def _fetch_funding_rate(self) -> Optional[float]:
        funding = await self._client.fetch_funding_rate(self.symbol)
        return funding.get("fundingRate")

    async def close(self) -> None:
        await self._client.close()
