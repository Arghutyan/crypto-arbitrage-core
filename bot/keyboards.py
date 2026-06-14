"""Inline keyboard layouts, tuned for narrow phone screens."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from arbitrage.config import EXCHANGE_SPECS


def main_menu(alerts_enabled: bool = True) -> InlineKeyboardMarkup:
    bell = "🔔 Alerts: ON" if alerts_enabled else "🔕 Alerts: OFF"
    builder = InlineKeyboardBuilder()
    builder.button(text="🔥 Live Top", callback_data="live_top")
    builder.button(text="⚙️ Set Filters", callback_data="set_filters")
    builder.button(text=bell, callback_data="toggle_alerts")
    builder.button(text="📊 My Filters", callback_data="my_filters")
    builder.adjust(2, 2)
    return builder.as_markup()


def back_to_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Back to menu", callback_data="menu")
    return builder.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✖️ Cancel", callback_data="menu")
    return builder.as_markup()


def excluded_exchanges_keyboard(excluded: list[str]) -> InlineKeyboardMarkup:
    """Toggle grid of every venue; excluded ones are marked."""
    excluded_lower = {e.lower() for e in excluded}
    builder = InlineKeyboardBuilder()
    for spec in EXCHANGE_SPECS:
        on = spec.name.lower() in excluded_lower
        mark = "🚫" if on else "✅"
        builder.button(
            text=f"{mark} {spec.name}",
            callback_data=f"exch_toggle:{spec.name}",
        )
    builder.button(text="⬅️ Back to menu", callback_data="menu")
    builder.adjust(2, 2, 2, 2, 2, 1)
    return builder.as_markup()
