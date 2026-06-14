"""The arbitrage engine: the long-running scan + alert loop.

Responsibilities each cycle:
  1. run the hybrid scanner,
  2. replace the ``live_spreads`` cache,
  3. hand the fresh opportunities to the alerting engine.

The loop is designed to never exit on its own: startup is retried and every
cycle is wrapped so a single bad tick is logged and skipped. Only ``stop_event``
(SIGINT/SIGTERM) breaks out.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from .alerting import AlertEngine
from .config import Settings
from .database import Database
from .exchanges import ExchangePool
from .scanner import Scanner

log = logging.getLogger(__name__)


class ArbitrageEngine:
    """Owns the exchange pool, scanner and alert engine."""

    def __init__(
        self,
        settings: Settings,
        pool: ExchangePool,
        db: Database,
        alert_engine: AlertEngine,
    ) -> None:
        self.settings = settings
        self.pool = pool
        self.db = db
        self.scanner = Scanner(settings, pool)
        self.alert_engine = alert_engine

    async def run(self, stop_event: Optional[asyncio.Event] = None) -> None:
        stop_event = stop_event or asyncio.Event()
        interval = self.settings.poll_interval
        try:
            await self._start_with_retry(stop_event, interval)
            while not stop_event.is_set():
                loop = asyncio.get_running_loop()
                started = loop.time()
                try:
                    blacklist = await self._load_blacklist()
                    opps = await self.scanner.scan(blacklist)
                    await self.db.replace_live_spreads(opps)
                    await self.alert_engine.process(opps)
                    log.info(
                        "Cycle done: %d opportunities cached (%d blacklisted)",
                        len(opps),
                        len(blacklist),
                    )
                except Exception:  # noqa: BLE001 - keep the loop alive
                    log.exception("Scan cycle failed")
                elapsed = loop.time() - started
                await self._sleep_or_stop(
                    stop_event, max(0.0, interval - elapsed)
                )
        finally:
            await self.alert_engine.close()
            await self.pool.close()

    async def _load_blacklist(self) -> set[str]:
        """Fetch the admin blacklist; never let a DB hiccup kill the cycle."""
        try:
            return await self.db.get_blacklist()
        except Exception:  # noqa: BLE001
            log.exception("Failed to load symbol blacklist; using empty set")
            return set()

    async def _start_with_retry(
        self, stop_event: asyncio.Event, interval: float
    ) -> None:
        while not stop_event.is_set():
            try:
                await self.pool.load()
                log.info(
                    "Engine started: scanning %s", ", ".join(self.pool.names)
                )
                return
            except Exception:  # noqa: BLE001
                log.exception("Engine startup failed; retrying in %.0fs", interval)
                await self._sleep_or_stop(stop_event, interval)

    @staticmethod
    async def _sleep_or_stop(stop_event: asyncio.Event, delay: float) -> None:
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=delay)
        except asyncio.TimeoutError:
            pass
