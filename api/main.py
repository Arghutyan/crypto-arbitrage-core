"""FastAPI microservice exposing crypto-arbitrage spread data.

Reads from the same PostgreSQL ``spread_history`` table the engine writes to.
Connection details come from environment variables (matching the engine and
the K8s manifests):

    DB_HOST  (default: postgres-service)
    DB_PORT  (default: 5432)
    DB_USER  (default: db_user)
    DB_PASSWORD (default: changeme)
    DB_NAME  (default: crypto_analytics)

Run locally with:
    uvicorn api.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncIterator, Optional

import asyncpg
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #


def _build_dsn() -> str:
    host = os.getenv("DB_HOST", "postgres-service")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "db_user")
    password = os.getenv("DB_PASSWORD", "changeme")
    name = os.getenv("DB_NAME", "crypto_analytics")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


# Comma-separated list of allowed origins; "*" by default for early dev.
_CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")


# --------------------------------------------------------------------------- #
# Response models
# --------------------------------------------------------------------------- #


class SpreadRecord(BaseModel):
    """One row of the ``spread_history`` table."""

    id: int
    timestamp: datetime
    pair: str
    binance_price: Optional[float] = None
    gate_price: Optional[float] = None
    spread_pct: Optional[float] = None
    binance_funding: Optional[float] = None
    gate_funding: Optional[float] = None


# --------------------------------------------------------------------------- #
# Lifespan: own the asyncpg pool for the app's lifetime
# --------------------------------------------------------------------------- #


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the connection pool on startup, drain it on shutdown."""
    pool = await asyncpg.create_pool(
        dsn=_build_dsn(),
        min_size=1,
        max_size=10,
        command_timeout=10,
    )
    app.state.pool = pool
    log.info("DB pool created")
    try:
        yield
    finally:
        await pool.close()
        log.info("DB pool closed")


app = FastAPI(
    title="Crypto Arbitrage API",
    version="1.0.0",
    description="Read-only access to cross-exchange spread history.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _CORS_ORIGINS if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #

_LATEST_QUERY = """
SELECT id, timestamp, pair, binance_price, gate_price,
       spread_pct, binance_funding, gate_funding
FROM spread_history
ORDER BY timestamp DESC
LIMIT 50
"""


@app.get("/health", tags=["meta"])
async def health(request: Request) -> dict:
    """Liveness/readiness probe target: verifies the DB is reachable."""
    pool: asyncpg.Pool = request.app.state.pool
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ok"}


@app.get(
    "/api/v1/spreads/latest",
    response_model=list[SpreadRecord],
    tags=["spreads"],
)
async def latest_spreads(request: Request) -> list[SpreadRecord]:
    """Return the 50 most recent spread records, newest first."""
    pool: asyncpg.Pool = request.app.state.pool
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(_LATEST_QUERY)
    except Exception as exc:  # noqa: BLE001
        log.exception("Failed to query spread_history")
        raise HTTPException(status_code=503, detail="database query failed") from exc

    return [SpreadRecord(**dict(row)) for row in rows]
