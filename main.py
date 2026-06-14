"""Entry point for the scan + alert engine process.

Run with:  python main.py

Runs the hybrid scanner across all configured venues, caches the live spreads
in PostgreSQL and dispatches Telegram alerts to users whose filters match.
Configuration comes from environment variables (see arbitrage/config.py).
"""

from __future__ import annotations

import asyncio
import logging
import signal

from arbitrage.alerting import AlertEngine
from arbitrage.config import (
    load_db_settings,
    load_settings,
    load_telegram_settings,
)
from arbitrage.database import Database
from arbitrage.engine import ArbitrageEngine
from arbitrage.exchanges import ExchangePool


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("ccxt").setLevel(logging.WARNING)


def _install_signal_handlers(
    loop: asyncio.AbstractEventLoop, stop: asyncio.Event
) -> None:
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass


async def main() -> None:
    _setup_logging()
    log = logging.getLogger("main")

    settings = load_settings()
    tg_settings = load_telegram_settings()

    db = Database(load_db_settings())
    await db.connect()
    await db.init_schema()

    if not tg_settings.enabled:
        log.warning("TELEGRAM_BOT_TOKEN not set — alerts are disabled")

    pool = ExchangePool(settings)
    alert_engine = AlertEngine(db, tg_settings)
    engine = ArbitrageEngine(settings, pool, db, alert_engine)

    stop = asyncio.Event()
    _install_signal_handlers(asyncio.get_running_loop(), stop)

    try:
        await engine.run(stop_event=stop)
    finally:
        await db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
