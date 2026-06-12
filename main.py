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

from arbitrage.config import load_settings
from arbitrage.engine import ArbitrageEngine


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

    stop = asyncio.Event()
    _install_signal_handlers(asyncio.get_running_loop(), stop)

    engine = ArbitrageEngine.from_settings(settings)
    await engine.run(stop_event=stop)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
