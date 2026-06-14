"""Async PostgreSQL persistence.

Two tables:

* ``live_spreads`` — a *cache* of the latest scan cycle. It is replaced
  wholesale every cycle so readers always see a consistent snapshot.
* ``telegram_users`` — registered bot users and their per-user alert filters
  (min spread, min funding, excluded exchanges, alerts on/off).
* ``symbol_blacklist`` — admin-curated base assets to drop entirely (garbage
  cross-listings like HK50, OPENAI). The engine filters these every cycle.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import asyncpg

from .config import DbSettings
from .models import Opportunity

log = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS live_spreads (
    id                  BIGSERIAL PRIMARY KEY,
    asset               TEXT NOT NULL,
    long_exchange       TEXT NOT NULL,
    short_exchange      TEXT NOT NULL,
    long_symbol         TEXT,
    short_symbol        TEXT,
    long_price          DOUBLE PRECISION,
    short_price         DOUBLE PRECISION,
    raw_spread_pct      DOUBLE PRECISION,
    real_spread_pct     DOUBLE PRECISION,
    long_funding        DOUBLE PRECISION,
    short_funding       DOUBLE PRECISION,
    net_funding_24h_pct DOUBLE PRECISION,
    farm_24h_pct        DOUBLE PRECISION,
    farm_72h_pct        DOUBLE PRECISION,
    next_funding_ms     BIGINT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_live_spreads_real
    ON live_spreads (real_spread_pct DESC NULLS LAST);

CREATE TABLE IF NOT EXISTS telegram_users (
    telegram_id         BIGINT PRIMARY KEY,
    username            TEXT,
    min_spread          DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    min_funding         DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    excluded_exchanges  JSONB NOT NULL DEFAULT '[]'::jsonb,
    alerts_enabled      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS symbol_blacklist (
    symbol      TEXT PRIMARY KEY,
    reason      TEXT,
    added_by    BIGINT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

_INSERT_SPREAD = """
INSERT INTO live_spreads (
    asset, long_exchange, short_exchange, long_symbol, short_symbol,
    long_price, short_price, raw_spread_pct, real_spread_pct,
    long_funding, short_funding, net_funding_24h_pct,
    farm_24h_pct, farm_72h_pct, next_funding_ms, updated_at
) VALUES (
    $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16
)
"""


class Database:
    """asyncpg connection pool plus domain helpers."""

    def __init__(self, settings: DbSettings) -> None:
        self._settings = settings
        self._pool: Optional[asyncpg.Pool] = None

    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database.connect() has not been called")
        return self._pool

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(
            dsn=self._settings.dsn,
            min_size=1,
            max_size=10,
            command_timeout=15,
        )
        log.info("DB pool connected → %s", self._settings.host)

    async def init_schema(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(_SCHEMA)
        log.info(
            "DB schema ready (live_spreads, telegram_users, symbol_blacklist)"
        )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            log.info("DB pool closed")

    # ------------------------------------------------------------------ #
    # live_spreads cache
    # ------------------------------------------------------------------ #
    async def replace_live_spreads(self, opps: list[Opportunity]) -> None:
        """Atomically swap the cache for the latest scan cycle."""
        now = datetime.now(tz=timezone.utc)
        rows = [
            (
                o.asset,
                o.long_exchange,
                o.short_exchange,
                o.long_symbol,
                o.short_symbol,
                o.long_price,
                o.short_price,
                o.raw_spread_pct,
                o.real_spread_pct,
                o.long_funding,
                o.short_funding,
                o.net_funding_24h_pct,
                o.farm_24h_pct,
                o.farm_72h_pct,
                o.next_funding_ms,
                now,
            )
            for o in opps
        ]
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute("TRUNCATE live_spreads")
                    if rows:
                        await conn.executemany(_INSERT_SPREAD, rows)
        except Exception:  # noqa: BLE001
            log.exception("Failed to replace live_spreads")

    async def get_live_spreads(self, limit: int = 100) -> list[dict]:
        query = """
            SELECT * FROM live_spreads
            ORDER BY real_spread_pct DESC NULLS LAST, raw_spread_pct DESC
            LIMIT $1
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, limit)
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # telegram_users
    # ------------------------------------------------------------------ #
    async def upsert_user(
        self, telegram_id: int, username: Optional[str]
    ) -> dict:
        query = """
            INSERT INTO telegram_users (telegram_id, username)
            VALUES ($1, $2)
            ON CONFLICT (telegram_id) DO UPDATE
                SET username = EXCLUDED.username,
                    updated_at = now()
            RETURNING *
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, telegram_id, username)
        return _user_row(row)

    async def get_user(self, telegram_id: int) -> Optional[dict]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM telegram_users WHERE telegram_id = $1",
                telegram_id,
            )
        return _user_row(row) if row else None

    async def update_filters(
        self,
        telegram_id: int,
        *,
        min_spread: Optional[float] = None,
        min_funding: Optional[float] = None,
        excluded_exchanges: Optional[list[str]] = None,
        alerts_enabled: Optional[bool] = None,
    ) -> Optional[dict]:
        sets: list[str] = []
        args: list = []
        idx = 1
        if min_spread is not None:
            sets.append(f"min_spread = ${idx}")
            args.append(min_spread)
            idx += 1
        if min_funding is not None:
            sets.append(f"min_funding = ${idx}")
            args.append(min_funding)
            idx += 1
        if excluded_exchanges is not None:
            sets.append(f"excluded_exchanges = ${idx}::jsonb")
            args.append(json.dumps(excluded_exchanges))
            idx += 1
        if alerts_enabled is not None:
            sets.append(f"alerts_enabled = ${idx}")
            args.append(alerts_enabled)
            idx += 1
        if not sets:
            return await self.get_user(telegram_id)
        sets.append("updated_at = now()")
        args.append(telegram_id)
        query = (
            f"UPDATE telegram_users SET {', '.join(sets)} "
            f"WHERE telegram_id = ${idx} RETURNING *"
        )
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
        return _user_row(row) if row else None

    async def get_alert_users(self) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM telegram_users WHERE alerts_enabled = TRUE"
            )
        return [_user_row(r) for r in rows]

    # ------------------------------------------------------------------ #
    # symbol_blacklist
    # ------------------------------------------------------------------ #
    async def add_to_blacklist(
        self,
        symbol: str,
        *,
        added_by: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> str:
        """Insert (or update) a base asset on the blacklist; returns the
        normalised symbol that was stored."""
        norm = normalize_symbol(symbol)
        if not norm:
            raise ValueError("empty symbol")
        query = """
            INSERT INTO symbol_blacklist (symbol, reason, added_by)
            VALUES ($1, $2, $3)
            ON CONFLICT (symbol) DO UPDATE
                SET reason = COALESCE(EXCLUDED.reason, symbol_blacklist.reason),
                    added_by = EXCLUDED.added_by
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, norm, reason, added_by)
        return norm

    async def remove_from_blacklist(self, symbol: str) -> bool:
        """Remove a symbol; returns True if a row was deleted."""
        norm = normalize_symbol(symbol)
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM symbol_blacklist WHERE symbol = $1", norm
            )
        return result.endswith("1")

    async def get_blacklist(self) -> set[str]:
        """The set of blacklisted base assets, used by the engine each cycle."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT symbol FROM symbol_blacklist")
        return {r["symbol"] for r in rows}

    async def list_blacklist(self) -> list[dict]:
        """Full blacklist rows for display in the bot."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM symbol_blacklist ORDER BY symbol"
            )
        return [dict(r) for r in rows]


def normalize_symbol(symbol: str) -> str:
    """Reduce any user/exchange symbol to its bare base asset, upper-cased.

    Accepts ``BTC``, ``BTC/USDT``, ``BTC/USDT:USDT`` etc. and returns ``BTC``
    so the blacklist matches the ``asset`` (base) the scanner groups on.
    """
    if not symbol:
        return ""
    token = symbol.strip().upper()
    # Drop ccxt settle suffix (``:USDT``) then the quote (``/USDT``).
    token = token.split(":", 1)[0]
    token = token.split("/", 1)[0]
    return token.strip()


def _user_row(row: Optional[asyncpg.Record]) -> dict:
    if row is None:
        return {}
    data = dict(row)
    raw = data.get("excluded_exchanges")
    if isinstance(raw, str):
        try:
            data["excluded_exchanges"] = json.loads(raw)
        except json.JSONDecodeError:
            data["excluded_exchanges"] = []
    elif raw is None:
        data["excluded_exchanges"] = []
    return data
