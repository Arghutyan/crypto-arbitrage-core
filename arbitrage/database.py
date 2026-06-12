"""Async PostgreSQL persistence layer.

Manages a single asyncpg connection pool. The caller is responsible for
calling :meth:`Database.connect` before first use and :meth:`Database.close`
on shutdown (typically in a ``finally`` block in ``main``).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import asyncpg

from .config import DbSettings
from .models import SpreadReport

log = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS spread_history (
    id              BIGSERIAL    PRIMARY KEY,
    timestamp       TIMESTAMPTZ  NOT NULL,
    pair            TEXT         NOT NULL,
    binance_price   DOUBLE PRECISION,
    gate_price      DOUBLE PRECISION,
    spread_pct      DOUBLE PRECISION,
    binance_funding DOUBLE PRECISION,
    gate_funding    DOUBLE PRECISION
);
"""

_INSERT_ROW = """
INSERT INTO spread_history
    (timestamp, pair, binance_price, gate_price,
     spread_pct, binance_funding, gate_funding)
VALUES ($1, $2, $3, $4, $5, $6, $7)
"""


class Database:
    """Wraps an asyncpg connection pool with domain-level helpers."""

    def __init__(self, settings: DbSettings) -> None:
        self._settings = settings
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Open the connection pool. Must be called before any other method."""
        s = self._settings
        dsn = f"postgresql://{s.user}:{s.password}@{s.host}:{s.port}/{s.name}"
        self._pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=1,
            max_size=5,
            command_timeout=10,
        )
        log.info("DB pool connected → %s:%s/%s", s.host, s.port, s.name)

    async def init_schema(self) -> None:
        """Create the ``spread_history`` table if it does not already exist."""
        if self._pool is None:
            raise RuntimeError("Database.connect() has not been called")
        async with self._pool.acquire() as conn:
            await conn.execute(_CREATE_TABLE)
        log.info("DB schema ready (spread_history)")

    async def close(self) -> None:
        """Drain all connections and release pool resources."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            log.info("DB pool closed")

    async def insert_spread(self, report: SpreadReport) -> None:
        """Persist one :class:`~arbitrage.models.SpreadReport` row.

        Errors are logged and swallowed so a DB hiccup never kills the
        polling loop.
        """
        if self._pool is None:
            return
        p, s = report.primary, report.secondary
        ts = datetime.fromtimestamp(report.timestamp, tz=timezone.utc)
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    _INSERT_ROW,
                    ts,
                    report.pair,
                    p.last_price,
                    s.last_price,
                    report.spread_pct,
                    p.funding_rate,
                    s.funding_rate,
                )
        except Exception:  # noqa: BLE001
            log.exception("Failed to insert spread row into DB")
