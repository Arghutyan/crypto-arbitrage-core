"""Allow ``python -m bot`` to launch the screener bot."""

from __future__ import annotations

import asyncio
import logging

# Configure logging at the very top, before anything runs, so even an early
# misconfiguration (e.g. a missing TELEGRAM_BOT_TOKEN) is logged instead of the
# process exiting silently with an empty log.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

from .main import main  # noqa: E402  (import after logging is configured)

log = logging.getLogger("bot")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot stopped (keyboard interrupt)")
