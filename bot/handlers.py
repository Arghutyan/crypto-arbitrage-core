"""Command, callback and FSM handlers for the screener bot.

The ``Database`` instance is injected by aiogram from the dispatcher's
workflow data (see ``bot/main.py``), so every handler simply declares a ``db``
parameter.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from arbitrage.database import Database, normalize_symbol

from . import formatting, keyboards
from .states import FilterSetup

log = logging.getLogger(__name__)
router = Router()


def _is_admin(telegram_id: int, admin_ids: frozenset[int] | None) -> bool:
    return bool(admin_ids) and telegram_id in admin_ids


def _parse_pct(text: str) -> float | None:
    try:
        return float(text.strip().replace("%", "").replace(",", "."))
    except (ValueError, AttributeError):
        return None


# --------------------------------------------------------------------------- #
# /start and main menu
# --------------------------------------------------------------------------- #
@router.message(Command("start"))
async def cmd_start(message: Message, db: Database, state: FSMContext) -> None:
    await state.clear()
    user_in = message.from_user
    user = await db.upsert_user(user_in.id, user_in.username)
    await message.answer(
        formatting.WELCOME,
        reply_markup=keyboards.main_menu(user.get("alerts_enabled", True)),
    )


@router.callback_query(F.data == "menu")
async def cb_menu(query: CallbackQuery, db: Database, state: FSMContext) -> None:
    await state.clear()
    user = await db.get_user(query.from_user.id) or {}
    await query.message.edit_text(
        formatting.WELCOME,
        reply_markup=keyboards.main_menu(user.get("alerts_enabled", True)),
    )
    await query.answer()


# --------------------------------------------------------------------------- #
# Live Top
# --------------------------------------------------------------------------- #
@router.callback_query(F.data == "live_top")
async def cb_live_top(query: CallbackQuery, db: Database) -> None:
    await query.answer("Fetching live spreads…")
    rows = await db.get_live_spreads(limit=10)
    await query.message.edit_text(
        formatting.format_top(rows),
        reply_markup=keyboards.back_to_menu(),
    )


# --------------------------------------------------------------------------- #
# My filters / toggle alerts
# --------------------------------------------------------------------------- #
@router.callback_query(F.data == "my_filters")
async def cb_my_filters(query: CallbackQuery, db: Database) -> None:
    user = await db.get_user(query.from_user.id) or {}
    await query.message.edit_text(
        formatting.format_filters(user),
        reply_markup=keyboards.excluded_exchanges_keyboard(
            user.get("excluded_exchanges", [])
        ),
    )
    await query.answer()


@router.callback_query(F.data == "toggle_alerts")
async def cb_toggle_alerts(query: CallbackQuery, db: Database) -> None:
    user = await db.get_user(query.from_user.id) or {}
    new_state = not user.get("alerts_enabled", True)
    await db.update_filters(query.from_user.id, alerts_enabled=new_state)
    await query.message.edit_text(
        formatting.WELCOME,
        reply_markup=keyboards.main_menu(new_state),
    )
    await query.answer("Alerts " + ("enabled 🔔" if new_state else "disabled 🔕"))


@router.callback_query(F.data.startswith("exch_toggle:"))
async def cb_exch_toggle(query: CallbackQuery, db: Database) -> None:
    name = query.data.split(":", 1)[1]
    user = await db.get_user(query.from_user.id) or {}
    excluded = list(user.get("excluded_exchanges", []))
    lower = {e.lower() for e in excluded}
    if name.lower() in lower:
        excluded = [e for e in excluded if e.lower() != name.lower()]
    else:
        excluded.append(name)
    user = await db.update_filters(
        query.from_user.id, excluded_exchanges=excluded
    )
    await query.message.edit_text(
        formatting.format_filters(user),
        reply_markup=keyboards.excluded_exchanges_keyboard(excluded),
    )
    await query.answer()


# --------------------------------------------------------------------------- #
# Set Filters — FSM
# --------------------------------------------------------------------------- #
@router.callback_query(F.data == "set_filters")
async def cb_set_filters(query: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FilterSetup.min_spread)
    await query.message.edit_text(
        "⚙️ <b>Step 1/2 — Minimum Real Spread</b>\n\n"
        "Send the minimum spread % to alert on (e.g. <code>0.8</code>).",
        reply_markup=keyboards.cancel_keyboard(),
    )
    await query.answer()


@router.message(FilterSetup.min_spread)
async def fsm_min_spread(message: Message, state: FSMContext) -> None:
    value = _parse_pct(message.text or "")
    if value is None or value < 0:
        await message.answer(
            "❌ Please send a valid number, e.g. <code>0.8</code>.",
            reply_markup=keyboards.cancel_keyboard(),
        )
        return
    await state.update_data(min_spread=value)
    await state.set_state(FilterSetup.min_funding)
    await message.answer(
        "⚙️ <b>Step 2/2 — Minimum 24h Funding</b>\n\n"
        "Send the minimum net funding % over 24h (e.g. <code>0.1</code>, "
        "or <code>0</code> to ignore funding).",
        reply_markup=keyboards.cancel_keyboard(),
    )


@router.message(FilterSetup.min_funding)
async def fsm_min_funding(
    message: Message, state: FSMContext, db: Database
) -> None:
    value = _parse_pct(message.text or "")
    if value is None:
        await message.answer(
            "❌ Please send a valid number, e.g. <code>0.1</code>.",
            reply_markup=keyboards.cancel_keyboard(),
        )
        return
    data = await state.get_data()
    await state.clear()
    user = await db.update_filters(
        message.from_user.id,
        min_spread=data.get("min_spread", 0.0),
        min_funding=value,
    )
    await message.answer(
        "✅ <b>Filters saved!</b>\n\n" + formatting.format_filters(user),
        reply_markup=keyboards.main_menu(user.get("alerts_enabled", True)),
    )


# --------------------------------------------------------------------------- #
# Admin — symbol blacklist
# --------------------------------------------------------------------------- #
_BLACKLIST_USAGE = (
    "🚫 <b>Symbol Blacklist</b> (admin)\n\n"
    "Garbage cross-listings filtered out of every scan and alert.\n\n"
    "<b>Usage:</b>\n"
    "<code>/blacklist ADD HK50</code>\n"
    "<code>/blacklist ADD BTC/USDT</code>\n"
    "<code>/blacklist REMOVE OPENAI</code>\n"
    "<code>/blacklist LIST</code>"
)


@router.message(Command("blacklist"))
async def cmd_blacklist(
    message: Message, db: Database, admin_ids: frozenset[int]
) -> None:
    if not _is_admin(message.from_user.id, admin_ids):
        await message.answer("⛔️ This command is restricted to admins.")
        return

    parts = (message.text or "").split()
    args = parts[1:]
    action = args[0].upper() if args else ""

    if action == "LIST" or not action:
        rows = await db.list_blacklist()
        if not rows:
            await message.answer(
                "✅ Blacklist is empty.\n\n" + _BLACKLIST_USAGE
            )
            return
        listed = "\n".join(f"• <code>{r['symbol']}</code>" for r in rows)
        await message.answer(
            f"🚫 <b>Blacklisted symbols ({len(rows)})</b>\n\n{listed}"
        )
        return

    if action == "ADD":
        if len(args) < 2:
            await message.answer(_BLACKLIST_USAGE)
            return
        norm = normalize_symbol(args[1])
        if not norm:
            await message.answer("❌ Could not parse a symbol from that input.")
            return
        await db.add_to_blacklist(norm, added_by=message.from_user.id)
        log.info("Admin %s blacklisted %s", message.from_user.id, norm)
        await message.answer(
            f"🚫 <b>{norm}</b> added to the blacklist. "
            "It will be filtered from the next scan cycle."
        )
        return

    if action in {"REMOVE", "RM", "DEL", "DELETE"}:
        if len(args) < 2:
            await message.answer(_BLACKLIST_USAGE)
            return
        norm = normalize_symbol(args[1])
        removed = await db.remove_from_blacklist(norm)
        if removed:
            log.info("Admin %s un-blacklisted %s", message.from_user.id, norm)
            await message.answer(f"✅ <b>{norm}</b> removed from the blacklist.")
        else:
            await message.answer(f"ℹ️ <b>{norm}</b> was not on the blacklist.")
        return

    await message.answer(_BLACKLIST_USAGE)


@router.callback_query(F.data.startswith("bl:add:"))
async def cb_blacklist_add(
    query: CallbackQuery, db: Database, admin_ids: frozenset[int]
) -> None:
    if not _is_admin(query.from_user.id, admin_ids):
        await query.answer("⛔️ Admins only.", show_alert=True)
        return
    symbol = query.data.split(":", 2)[2]
    norm = normalize_symbol(symbol)
    if not norm:
        await query.answer("❌ Bad symbol.", show_alert=True)
        return
    await db.add_to_blacklist(norm, added_by=query.from_user.id)
    log.info("Admin %s blacklisted %s via alert button", query.from_user.id, norm)
    # Drop the button so it can't be tapped twice; keep the alert text intact.
    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except Exception:  # noqa: BLE001 - message may be too old to edit
        pass
    await query.answer(f"🚫 {norm} blacklisted", show_alert=True)
