"""Entry point for the crypto arbitrage monitoring service.

Run with:  python main.py

Configuration is read from environment variables (see arbitrage/config.py);
sensible defaults monitor ACE/USDT perpetuals on Binance and Gate.io every
5 seconds.
"""

from __future__ import annotations

import asyncio
import logging
import signal

from arbitrage.config import load_db_settings, load_settings
from arbitrage.database import Database
from arbitrage.engine import ArbitrageEngine
from arbitrage.models import SpreadReport
from arbitrage.reporter import ConsoleSink


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # ccxt is chatty at INFO during market loading; keep our output clean.
    logging.getLogger("ccxt").setLevel(logging.WARNING)


def _install_signal_handlers(loop: asyncio.AbstractEventLoop, stop: asyncio.Event) -> None:
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            # Signal handlers are unavailable on some platforms (e.g. Windows).
            pass


async def main() -> None:
    _setup_logging()
    settings = load_settings()

    db = Database(load_db_settings())
    await db.connect()
    await db.init_schema()

    console = ConsoleSink()

    async def _sink(report: SpreadReport) -> None:
        console(report)
        await db.insert_spread(report)

    stop = asyncio.Event()
    _install_signal_handlers(asyncio.get_running_loop(), stop)

    engine = ArbitrageEngine.from_settings(settings, sink=_sink)
    try:
        await engine.run(stop_event=stop)
    finally:
        await db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
