"""Entry point for the Telegram screener bot process.

Run with:  python -m bot

Owns interactive command handling (registration, Live Top, filter FSM). Alerts
themselves are pushed by the engine process via the Bot API; both share the
same ``TELEGRAM_BOT_TOKEN`` and PostgreSQL database.
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from arbitrage.config import load_db_settings, load_telegram_settings
from arbitrage.database import Database

from .handlers import router


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


async def main() -> None:
    _setup_logging()
    log = logging.getLogger("bot")
    log.info("Starting Spread+ screener bot…")

    tg = load_telegram_settings()
    if not tg.enabled:
        log.error(
            "TELEGRAM_BOT_TOKEN is not set — the bot cannot start. "
            "Add it to your .env (see .env.example) and restart the service."
        )
        raise SystemExit(1)

    db = Database(load_db_settings())
    await db.connect()
    await db.init_schema()

    bot = Bot(
        token=tg.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    if tg.admin_ids:
        log.info("Bot admins: %s", ", ".join(map(str, sorted(tg.admin_ids))))
    else:
        log.warning(
            "TELEGRAM_ADMIN_IDS not set — blacklist commands are disabled"
        )

    log.info("Bot starting (long polling)…")
    try:
        # ``db`` and ``admin_ids`` are injected into every handler that
        # declares them (aiogram pulls from the dispatcher workflow data).
        await dp.start_polling(bot, db=db, admin_ids=tg.admin_ids)
    finally:
        await bot.session.close()
        await db.close()


if __name__ == "__main__":
    _setup_logging()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.getLogger("bot").info("Bot stopped (keyboard interrupt)")
