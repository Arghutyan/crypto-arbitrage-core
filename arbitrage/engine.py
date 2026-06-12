"""The arbitrage monitoring engine.

Responsibilities:
  * own the set of exchange connectors,
  * poll them concurrently on a fixed cadence,
  * compute the cross-exchange spread,
  * hand each :class:`SpreadReport` to a sink (default: console).

The engine is intentionally agnostic about *how* a connector obtains data,
which is what makes the future WebSocket order-book feed a drop-in addition.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Optional, Sequence

from . import reporter
from .config import Settings
from .exchanges import ExchangeConnector, build_connector
from .models import MarketSnapshot, SpreadReport

log = logging.getLogger(__name__)

# A sink consumes finished reports. Sync or async callables are accepted.
ReportSink = Callable[[SpreadReport], Awaitable[None] | None]


def compute_spread(primary: MarketSnapshot, secondary: MarketSnapshot) -> Optional[float]:
    """Percentage difference of primary vs secondary last price.

    Defined as ``(primary - secondary) / secondary * 100``. A positive value
    means the primary exchange (Binance) is trading richer than the secondary
    (Gate). Returns ``None`` when either price is missing or non-positive.
    """

    a, b = primary.last_price, secondary.last_price
    if a is None or b is None or b <= 0:
        return None
    return (a - b) / b * 100.0


class ArbitrageEngine:
    """Coordinates connectors and runs the polling loop."""

    def __init__(
        self,
        settings: Settings,
        connectors: Sequence[ExchangeConnector],
        sink: Optional[ReportSink] = None,
    ) -> None:
        if len(connectors) < 2:
            raise ValueError("ArbitrageEngine requires at least two connectors")
        self.settings = settings
        self.connectors = list(connectors)
        self._sink: ReportSink = sink or self._default_sink
        self._header_printed = False

    @classmethod
    def from_settings(
        cls, settings: Settings, sink: Optional[ReportSink] = None
    ) -> "ArbitrageEngine":
        """Build an engine and its connectors straight from configuration."""
        connectors = [
            build_connector(cfg, settings.request_timeout)
            for cfg in settings.exchanges
        ]
        return cls(settings, connectors, sink=sink)

    async def start(self) -> None:
        """Load all connectors before polling begins."""
        await asyncio.gather(*(c.load() for c in self.connectors))
        log.info("Engine started: monitoring %s on %s", self.settings.pair,
                 ", ".join(c.name for c in self.connectors))

    async def close(self) -> None:
        """Close every connector, ignoring individual close failures."""
        await asyncio.gather(
            *(c.close() for c in self.connectors), return_exceptions=True
        )

    async def poll_once(self) -> SpreadReport:
        """Fetch all snapshots concurrently and build a single report."""
        snapshots = await asyncio.gather(
            *(c.fetch_snapshot() for c in self.connectors)
        )
        primary, secondary = snapshots[0], snapshots[1]
        report = SpreadReport(
            pair=self.settings.pair,
            primary=primary,
            secondary=secondary,
            spread_pct=compute_spread(primary, secondary),
        )
        return report

    async def run(self, stop_event: Optional[asyncio.Event] = None) -> None:
        """Run the polling loop forever, until ``stop_event`` is set.

        This loop is designed to NEVER exit on its own. Every failure mode is
        contained:
          * startup (loading exchange markets) is retried instead of crashing,
          * each polling cycle is wrapped so a bad tick is logged and skipped.

        The only way out is ``stop_event`` being set (e.g. by SIGINT/SIGTERM),
        which is the deliberate "interrupted" path. The loop targets a steady
        cadence: the sleep is adjusted by how long the fetch took, so a slow
        cycle does not drift the schedule.
        """

        stop_event = stop_event or asyncio.Event()
        interval = self.settings.poll_interval
        try:
            # Resilient startup: a network hiccup while loading markets must
            # not terminate the service. Keep retrying until it succeeds or we
            # are asked to stop.
            await self._start_with_retry(stop_event, interval)

            while not stop_event.is_set():
                loop = asyncio.get_running_loop()
                started = loop.time()
                try:
                    report = await self.poll_once()
                    await self._emit(report)
                except Exception:  # noqa: BLE001 - keep the loop alive
                    log.exception("Polling cycle failed")

                elapsed = loop.time() - started
                delay = max(0.0, interval - elapsed)
                await self._sleep_or_stop(stop_event, delay)
        finally:
            await self.close()

    async def _start_with_retry(
        self, stop_event: asyncio.Event, interval: float
    ) -> None:
        """Load connectors, retrying on failure until ready or stopped.

        Without this guard a failed ``load_markets()`` would propagate out of
        ``run()`` and silently kill the process right after startup.
        """
        while not stop_event.is_set():
            try:
                await self.start()
                return
            except Exception:  # noqa: BLE001 - never crash on startup
                log.exception(
                    "Engine startup failed; retrying in %.0fs", interval
                )
                await self._sleep_or_stop(stop_event, interval)

    @staticmethod
    async def _sleep_or_stop(stop_event: asyncio.Event, delay: float) -> None:
        """Sleep up to ``delay`` seconds, waking early if ``stop_event`` fires."""
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=delay)
        except asyncio.TimeoutError:
            pass  # normal: interval elapsed, carry on

    async def _emit(self, report: SpreadReport) -> None:
        result = self._sink(report)
        if asyncio.iscoroutine(result):
            await result

    def _default_sink(self, report: SpreadReport) -> None:
        if not self._header_printed:
            print(reporter.header(report))
            print("-" * len(reporter.header(report)))
            self._header_printed = True
        print(reporter.format_line(report))
