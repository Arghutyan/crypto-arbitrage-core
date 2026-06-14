"""The alerting engine.

After each scan cycle the engine receives the fresh opportunities, loads every
user with alerts enabled, and pushes a Telegram notification for each
opportunity that satisfies that user's stored filters. A per-(user, asset-pair)
cooldown prevents the same signal from spamming the user every cycle.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from .config import TelegramSettings
from .database import Database
from .models import Opportunity
from .telegram_client import TelegramClient

log = logging.getLogger(__name__)


def matches_filters(opp: Opportunity, user: dict) -> bool:
    """Whether an opportunity passes a single user's filter set."""
    real = opp.real_spread_pct
    if real is None:
        return False
    if real < float(user.get("min_spread", 0.0) or 0.0):
        return False

    min_funding = float(user.get("min_funding", 0.0) or 0.0)
    net = opp.net_funding_24h_pct or 0.0
    if net < min_funding:
        return False

    excluded = {e.lower() for e in user.get("excluded_exchanges", [])}
    if (
        opp.long_exchange.lower() in excluded
        or opp.short_exchange.lower() in excluded
    ):
        return False
    return True


def blacklist_markup(opp: Opportunity) -> dict:
    """Inline keyboard letting an admin blacklist this asset straight from the
    alert. The callback is handled by the bot process (shared DB + token)."""
    return {
        "inline_keyboard": [
            [
                {
                    "text": f"🚫 Blacklist {opp.asset}",
                    "callback_data": f"bl:add:{opp.asset}",
                }
            ]
        ]
    }


def format_alert(opp: Opportunity) -> str:
    """Compact, emoji-rich push body."""
    spread = opp.real_spread_pct if opp.real_spread_pct is not None else opp.raw_spread_pct
    funding = opp.net_funding_24h_pct or 0.0
    farm = opp.farm_24h_pct
    lines = [
        f"🚨 <b>{opp.asset}</b>  Spread: <b>{spread:.2f}%</b>",
        f"📈 {opp.long_exchange} → {opp.short_exchange}",
        f"💰 Funding 24h: <b>{funding:+.3f}%</b>",
    ]
    if farm is not None:
        lines.append(f"🌾 Farm 24h: {farm:+.3f}%  |  72h: {opp.farm_72h_pct:+.3f}%")
    return "\n".join(lines)


class AlertEngine:
    """Evaluates opportunities against user filters and dispatches alerts."""

    def __init__(
        self,
        db: Database,
        settings: TelegramSettings,
        client: Optional[TelegramClient] = None,
    ) -> None:
        self._db = db
        self._settings = settings
        self._client = client or (
            TelegramClient(settings.token) if settings.enabled else None
        )
        # (telegram_id, opp.key) -> last sent monotonic timestamp.
        self._last_sent: dict[tuple[int, str], float] = {}

    async def process(self, opps: list[Opportunity]) -> None:
        if self._client is None or not opps:
            return
        try:
            users = await self._db.get_alert_users()
        except Exception:  # noqa: BLE001
            log.exception("Alert engine: failed to load users")
            return
        if not users:
            return

        now = time.monotonic()
        cooldown = self._settings.alert_cooldown
        sent = 0
        for user in users:
            chat_id = user["telegram_id"]
            for opp in opps:
                if not matches_filters(opp, user):
                    continue
                cache_key = (chat_id, opp.key)
                last = self._last_sent.get(cache_key, 0.0)
                if now - last < cooldown:
                    continue
                markup = (
                    blacklist_markup(opp)
                    if self._settings.is_admin(chat_id)
                    else None
                )
                if await self._client.send_message(
                    chat_id, format_alert(opp), reply_markup=markup
                ):
                    self._last_sent[cache_key] = now
                    sent += 1
        if sent:
            log.info("Alert engine: dispatched %d notifications", sent)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
