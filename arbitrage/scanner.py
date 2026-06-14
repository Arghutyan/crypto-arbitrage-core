"""The hybrid two-step scanner.

Step 1 (cheap, anti-ban): one ``fetch_tickers`` call per venue, run
concurrently. Group by asset, compute the best mid-to-mid spread per asset and
keep those above the raw threshold.

Step 2 (expensive, throttled): for only the widest ``top_n`` candidates, pull
L2 order books for both legs and the funding rates, then recompute the *real*
spread accounting for slippage on a fixed-notional order.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from .config import Settings
from .exchanges import ExchangePool
from .funding import net_funding_24h, parse_funding, project_farm
from .models import Opportunity, Ticker

log = logging.getLogger(__name__)


def vwap_for_notional(
    levels: list[list[float]], target_usd: float
) -> Optional[float]:
    """Volume-weighted average fill price to trade ``target_usd`` of notional.

    ``levels`` are ``[price, amount]`` order-book rows (asks for a buy, bids
    for a sell). Returns ``None`` when the book is too thin to fill the order.
    """
    if not levels or target_usd <= 0:
        return None
    spent = 0.0
    base_filled = 0.0
    for level in levels:
        if len(level) < 2:
            continue
        price = float(level[0])
        amount = float(level[1])
        if price <= 0 or amount <= 0:
            continue
        level_value = price * amount
        if spent + level_value >= target_usd:
            remaining = target_usd - spent
            base_filled += remaining / price
            spent = target_usd
            break
        spent += level_value
        base_filled += amount
    if spent < target_usd or base_filled <= 0:
        return None
    return target_usd / base_filled


class Scanner:
    """Runs one full hybrid scan cycle against the exchange pool."""

    def __init__(self, settings: Settings, pool: ExchangePool) -> None:
        self.settings = settings
        self.pool = pool

    async def scan(
        self, blacklist: Optional[set[str]] = None
    ) -> list[Opportunity]:
        candidates = await self._raw_candidates(blacklist or set())
        if not candidates:
            return []
        top = candidates[: self.settings.top_n_orderbooks]
        log.info(
            "Scan: %d raw candidates > %.2f%%, refining top %d via L2 books",
            len(candidates),
            self.settings.min_raw_spread_pct,
            len(top),
        )
        refined = await self._refine(top)
        refined.sort(
            key=lambda o: (o.real_spread_pct is None, -(o.real_spread_pct or 0))
        )
        return refined

    # ------------------------------------------------------------------ #
    # Step 1
    # ------------------------------------------------------------------ #
    async def _raw_candidates(
        self, blacklist: set[str]
    ) -> list[Opportunity]:
        by_exchange = await self.pool.fetch_all_tickers()

        # asset -> list[Ticker] across venues (best mid kept per exchange).
        by_asset: dict[str, dict[str, Ticker]] = {}
        for tickers in by_exchange.values():
            for t in tickers:
                if t.mid is None or t.mid <= 0:
                    continue
                # Drop admin-blacklisted base assets before any processing.
                if t.base.upper() in blacklist:
                    continue
                slot = by_asset.setdefault(t.base, {})
                # If the same exchange lists multiple quotes, keep first seen.
                slot.setdefault(t.exchange, t)

        candidates: list[Opportunity] = []
        for asset, venues in by_asset.items():
            if len(venues) < 2:
                continue
            cheap = min(venues.values(), key=lambda t: t.mid)  # type: ignore[arg-type]
            rich = max(venues.values(), key=lambda t: t.mid)  # type: ignore[arg-type]
            if cheap.exchange == rich.exchange:
                continue
            low, high = cheap.mid, rich.mid
            if low is None or high is None or low <= 0:
                continue
            raw = (high - low) / low * 100.0
            if raw < self.settings.min_raw_spread_pct:
                continue
            candidates.append(
                Opportunity(
                    asset=asset,
                    long_exchange=cheap.exchange,
                    short_exchange=rich.exchange,
                    long_symbol=cheap.symbol,
                    short_symbol=rich.symbol,
                    long_price=low,
                    short_price=high,
                    raw_spread_pct=raw,
                )
            )
        candidates.sort(key=lambda o: o.raw_spread_pct, reverse=True)
        return candidates

    # ------------------------------------------------------------------ #
    # Step 2
    # ------------------------------------------------------------------ #
    async def _refine(self, opps: list[Opportunity]) -> list[Opportunity]:
        sem = asyncio.Semaphore(self.settings.orderbook_concurrency)

        async def _refine_one(opp: Opportunity) -> Opportunity:
            async with sem:
                return await self._refine_opportunity(opp)

        return await asyncio.gather(*(_refine_one(o) for o in opps))

    async def _refine_opportunity(self, opp: Opportunity) -> Opportunity:
        size = self.settings.order_size_usd
        long_ob, short_ob, long_fr, short_fr = await asyncio.gather(
            self.pool.fetch_order_book(opp.long_exchange, opp.long_symbol),
            self.pool.fetch_order_book(opp.short_exchange, opp.short_symbol),
            self.pool.fetch_funding_rate(opp.long_exchange, opp.long_symbol),
            self.pool.fetch_funding_rate(opp.short_exchange, opp.short_symbol),
        )

        # Real spread: buy into asks on the long leg, sell into bids on short.
        if long_ob and short_ob:
            buy_vwap = vwap_for_notional(long_ob.get("asks", []), size)
            sell_vwap = vwap_for_notional(short_ob.get("bids", []), size)
            if buy_vwap and sell_vwap and buy_vwap > 0:
                opp.real_spread_pct = (sell_vwap - buy_vwap) / buy_vwap * 100.0
                opp.long_price = buy_vwap
                opp.short_price = sell_vwap

        long_leg = parse_funding(long_fr)
        short_leg = parse_funding(short_fr)
        opp.long_funding = long_leg.rate
        opp.short_funding = short_leg.rate
        opp.next_funding_ms = _soonest(
            long_leg.next_funding_ms, short_leg.next_funding_ms
        )
        net_24h = net_funding_24h(long_leg, short_leg)
        opp.net_funding_24h_pct = net_24h
        opp.farm_24h_pct = project_farm(net_24h, 24.0)
        opp.farm_72h_pct = project_farm(net_24h, 72.0)
        return opp


def _soonest(a: Optional[int], b: Optional[int]) -> Optional[int]:
    candidates = [x for x in (a, b) if x]
    return min(candidates) if candidates else None
