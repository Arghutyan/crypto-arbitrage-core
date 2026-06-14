"""Dynamic funding-rate parsing and farm projections.

Funding intervals differ across venues (1h, 2h, 4h, 8h, ...). We never assume
8h: the interval is derived from the exchange payload, either from an explicit
``interval`` field or from the gap between the current and next funding
timestamps.
"""

from __future__ import annotations

from typing import Optional

from .models import FundingLeg

_HOUR_MS = 3_600_000


def _parse_interval_field(value: object) -> Optional[float]:
    """Parse ccxt's ``interval`` (e.g. ``"8h"``, ``"1h"``) into hours."""
    if not value:
        return None
    text = str(value).strip().lower()
    try:
        if text.endswith("h"):
            return float(text[:-1])
        if text.endswith("m"):
            return float(text[:-1]) / 60.0
        return float(text)
    except ValueError:
        return None


def parse_funding(payload: Optional[dict]) -> FundingLeg:
    """Turn a ccxt ``fetch_funding_rate`` result into a :class:`FundingLeg`."""
    leg = FundingLeg()
    if not payload:
        return leg

    rate = payload.get("fundingRate")
    if rate is not None:
        try:
            leg.rate = float(rate)
        except (TypeError, ValueError):
            leg.rate = None

    next_ms = payload.get("nextFundingTimestamp") or payload.get(
        "fundingTimestamp"
    )
    if next_ms:
        try:
            leg.next_funding_ms = int(next_ms)
        except (TypeError, ValueError):
            leg.next_funding_ms = None

    # Prefer an explicit interval; otherwise derive it from the timestamps.
    interval = _parse_interval_field(payload.get("interval"))
    if interval is None:
        info = payload.get("info") or {}
        interval = _parse_interval_field(
            info.get("fundingInterval")
            or info.get("funding_interval")
            or info.get("fundingIntervalHours")
        )
    if interval is None:
        cur = payload.get("fundingTimestamp")
        nxt = payload.get("nextFundingTimestamp")
        if cur and nxt and nxt > cur:
            interval = round((int(nxt) - int(cur)) / _HOUR_MS, 4)

    if interval and interval > 0:
        leg.interval_hours = interval
    return leg


def net_funding_24h(long: FundingLeg, short: FundingLeg) -> Optional[float]:
    """Net funding kept over 24h for a delta-neutral book, as a percent.

    A short position *receives* funding when the rate is positive; a long
    position *pays* it. Net = short income − long cost, each scaled to 24h by
    its own interval.
    """
    short_24h = short.per_24h()
    long_24h = long.per_24h()
    if short_24h is None and long_24h is None:
        return None
    return ((short_24h or 0.0) - (long_24h or 0.0)) * 100.0


def project_farm(net_24h_pct: Optional[float], hours: float) -> Optional[float]:
    """Linearly project the 24h net funding to an arbitrary horizon."""
    if net_24h_pct is None:
        return None
    return net_24h_pct * (hours / 24.0)
