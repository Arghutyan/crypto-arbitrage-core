"""Console reporting of spread results.

Kept separate from the engine so the output channel can be swapped (e.g. a
metrics exporter, database writer, or alerting sink) without changing the
computation logic.
"""

from __future__ import annotations

from .models import SpreadReport


def _fmt_price(value: float | None) -> str:
    return f"{value:,.5f}" if value is not None else "   n/a   "


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "  n/a  "
    return f"{value:+.4f}%"


def _fmt_funding(value: float | None) -> str:
    # Funding rates come as fractions (e.g. 0.0001 == 0.01%).
    if value is None:
        return "  n/a  "
    return f"{value * 100:+.4f}%"


def header(report: SpreadReport) -> str:
    """One-time header describing the columns."""
    a, b = report.primary.exchange, report.secondary.exchange
    return (
        f"{'Time':<10} | "
        f"{a + ' Price':<14} | {b + ' Price':<14} | "
        f"{'Spread':<10} | "
        f"{a + ' Fund':<11} | {b + ' Fund':<11}"
    )


def format_line(report: SpreadReport) -> str:
    """Render a single report as an aligned, human-readable log line."""

    import time

    clock = time.strftime("%H:%M:%S", time.localtime(report.timestamp))
    p, s = report.primary, report.secondary
    return (
        f"{clock:<10} | "
        f"{_fmt_price(p.last_price):<14} | {_fmt_price(s.last_price):<14} | "
        f"{_fmt_pct(report.spread_pct):<10} | "
        f"{_fmt_funding(p.funding_rate):<11} | {_fmt_funding(s.funding_rate):<11}"
    )
