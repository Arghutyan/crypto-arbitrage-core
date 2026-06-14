"""HTML message builders shared by the bot handlers.

Compact, emoji-led layout that reads well on a phone in the Telegram client.
"""

from __future__ import annotations

import time
from typing import Optional


def _fmt_pct(value: Optional[float], digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{value:+.{digits}f}%"


def _countdown(next_ms: Optional[int]) -> str:
    if not next_ms:
        return "—"
    remaining = next_ms / 1000 - time.time()
    if remaining <= 0:
        return "now"
    h = int(remaining // 3600)
    m = int((remaining % 3600) // 60)
    return f"{h}h {m}m"


def format_top(rows: list[dict], limit: int = 10) -> str:
    if not rows:
        return (
            "😴 <b>No live opportunities right now.</b>\n"
            "The scanner hasn't found spreads above threshold yet — "
            "try again in a moment."
        )
    lines = ["🔥 <b>Live Top Spreads</b>\n"]
    for i, r in enumerate(rows[:limit], start=1):
        spread = r.get("real_spread_pct")
        if spread is None:
            spread = r.get("raw_spread_pct")
        farm = r.get("farm_24h_pct")
        lines.append(
            f"{i}. <b>{r['asset']}</b>  ·  <b>{_fmt_pct(spread)}</b>\n"
            f"    {r['long_exchange']} → {r['short_exchange']}  ·  "
            f"🌾 {_fmt_pct(farm, 3)}  ·  ⏳ {_countdown(r.get('next_funding_ms'))}"
        )
    lines.append("\n<i>Buy long-leg, short rich-leg. Updated each cycle.</i>")
    return "\n".join(lines)


def format_filters(user: dict) -> str:
    excluded = user.get("excluded_exchanges") or []
    excl_text = ", ".join(excluded) if excluded else "none"
    status = "ON 🔔" if user.get("alerts_enabled", True) else "OFF 🔕"
    return (
        "📊 <b>Your Alert Filters</b>\n\n"
        f"• Min spread: <b>{user.get('min_spread', 0):.2f}%</b>\n"
        f"• Min funding (24h): <b>{user.get('min_funding', 0):.2f}%</b>\n"
        f"• Excluded: <b>{excl_text}</b>\n"
        f"• Alerts: <b>{status}</b>"
    )


WELCOME = (
    "👋 <b>Welcome to Spread+ Screener</b>\n\n"
    "I track delta-neutral funding-arbitrage spreads across 10 exchanges "
    "and ping you when an opportunity matches your filters.\n\n"
    "🔥 <b>Live Top</b> — best spreads right now\n"
    "⚙️ <b>Set Filters</b> — your alert thresholds\n"
    "🔔 <b>Alerts</b> — toggle push notifications\n\n"
    "Pick an option below 👇"
)
