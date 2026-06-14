"""Minimal Telegram Bot API sender.

The alerting engine (running inside the scanner process) pushes notifications
directly through the Bot API over HTTP. This deliberately avoids importing
aiogram in the engine: the bot process owns interactive command handling, while
the engine only needs to fire ``sendMessage`` calls. Both share one token.
"""

from __future__ import annotations

import logging
from typing import Optional

import aiohttp

log = logging.getLogger(__name__)


class TelegramClient:
    """Thin async wrapper over ``sendMessage``."""

    def __init__(self, token: str) -> None:
        self._base = f"https://api.telegram.org/bot{token}"
        self._session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15)
            )
        return self._session

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[dict] = None,
    ) -> bool:
        session = await self._ensure_session()
        payload: dict = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        try:
            async with session.post(
                f"{self._base}/sendMessage", json=payload
            ) as resp:
                if resp.status == 200:
                    return True
                body = await resp.text()
                log.warning(
                    "Telegram sendMessage failed (%s): %s", resp.status, body
                )
                return False
        except Exception as exc:  # noqa: BLE001
            log.warning("Telegram sendMessage error: %s", exc)
            return False

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()
