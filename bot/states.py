"""FSM state definitions for multi-step bot dialogs."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class FilterSetup(StatesGroup):
    """Two-step flow capturing the user's alert thresholds."""

    min_spread = State()
    min_funding = State()
