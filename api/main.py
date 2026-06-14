"""FastAPI service for the delta-neutral funding arbitrage SaaS.

Endpoints
---------
* ``GET /health`` — liveness/readiness (verifies the DB is reachable).
* ``GET /api/v1/spreads/live`` — the latest cached scan cycle for the UI.
* ``GET /api/v1/spread-history/{asset}/{ex1}/{ex2}`` — 3 days of hourly spread
  history computed on demand from ccxt OHLCV. Nothing is stored.

The app imports the shared ``arbitrage`` package, so it must run from the repo
root (the container sets ``WORKDIR /app`` with the package on the path).

Run locally:
    uvicorn api.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from arbitrage.config import load_db_settings
from arbitrage.database import Database
from arbitrage.klines import fetch_spread_history

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _parse_cors_origins() -> list[str]:
    """Allowed browser origins, comma-separated. Defaults to the local
    Next.js dev server so the dashboard works out of the box."""
    raw = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    return [o.strip() for o in raw.split(",") if o.strip()]


_CORS_ORIGINS = _parse_cors_origins()
# A wildcard origin is invalid alongside credentials per the CORS spec, so we
# only advertise credentials support when the origins are explicit.
_ALLOW_ALL_ORIGINS = "*" in _CORS_ORIGINS


# --------------------------------------------------------------------------- #
# Response models
# --------------------------------------------------------------------------- #
class LiveSpread(BaseModel):
    asset: str
    long_exchange: str
    short_exchange: str
    long_symbol: Optional[str] = None
    short_symbol: Optional[str] = None
    long_price: Optional[float] = None
    short_price: Optional[float] = None
    raw_spread_pct: Optional[float] = None
    real_spread_pct: Optional[float] = None
    long_funding: Optional[float] = None
    short_funding: Optional[float] = None
    long_funding_interval_h: Optional[float] = None
    short_funding_interval_h: Optional[float] = None
    net_funding_24h_pct: Optional[float] = None
    farm_24h_pct: Optional[float] = None
    farm_72h_pct: Optional[float] = None
    next_funding_ms: Optional[int] = None


class SpreadHistoryPoint(BaseModel):
    time: int
    ex1_price: float
    ex2_price: float
    spread_pct: float


class SpreadHistoryResponse(BaseModel):
    asset: str
    ex1: str
    ex2: str
    points: list[SpreadHistoryPoint]


class BlacklistResponse(BaseModel):
    symbol: str
    status: str = "blacklisted"


# --------------------------------------------------------------------------- #
# Lifespan
# --------------------------------------------------------------------------- #
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    db = Database(load_db_settings())
    await db.connect()
    await db.init_schema()
    app.state.db = db
    log.info("API ready")
    try:
        yield
    finally:
        await db.close()


app = FastAPI(
    title="Delta-Neutral Funding Arbitrage API",
    version="2.0.0",
    description="Live cross-exchange spreads, funding farm estimates and history.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=not _ALLOW_ALL_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
log.info("CORS allowed origins: %s", _CORS_ORIGINS)


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.get("/health", tags=["meta"])
async def health(request: Request) -> dict:
    db: Database = request.app.state.db
    try:
        async with db.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ok"}


@app.get(
    "/api/v1/spreads/live",
    response_model=list[LiveSpread],
    tags=["spreads"],
)
async def live_spreads(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
) -> list[LiveSpread]:
    """Return the latest cached scan cycle, widest real spread first."""
    db: Database = request.app.state.db
    try:
        rows = await db.get_live_spreads(limit=limit)
    except Exception as exc:  # noqa: BLE001
        log.exception("Failed to read live_spreads")
        raise HTTPException(status_code=503, detail="database query failed") from exc
    return [LiveSpread(**{k: row.get(k) for k in LiveSpread.model_fields}) for row in rows]


@app.get(
    "/api/v1/spread-history/{asset}/{ex1}/{ex2}",
    response_model=SpreadHistoryResponse,
    tags=["spreads"],
)
async def spread_history(
    asset: str,
    ex1: str,
    ex2: str,
    days: int = Query(3, ge=1, le=14),
) -> SpreadHistoryResponse:
    """Compute hourly spread history on demand via ccxt (not persisted)."""
    try:
        points = await fetch_spread_history(asset, ex1, ex2, days=days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        log.exception("Failed to build spread history")
        raise HTTPException(status_code=502, detail="exchange data unavailable") from exc
    return SpreadHistoryResponse(
        asset=asset.upper(),
        ex1=ex1,
        ex2=ex2,
        points=[SpreadHistoryPoint(**p) for p in points],
    )


@app.post(
    "/api/v1/blacklist/{symbol}",
    response_model=BlacklistResponse,
    status_code=201,
    tags=["blacklist"],
)
async def blacklist_symbol(symbol: str, request: Request) -> BlacklistResponse:
    """Add a base asset to the shared ``symbol_blacklist`` table.

    The engine reads this table every scan cycle, so the asset stops being
    scanned/served from the next cycle onward. Idempotent: re-adding an
    existing symbol just refreshes it.
    """
    db: Database = request.app.state.db
    try:
        normalized = await db.add_to_blacklist(symbol, reason="web-ui")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        log.exception("Failed to blacklist %s", symbol)
        raise HTTPException(status_code=503, detail="database write failed") from exc
    log.info("Blacklisted %s via web UI", normalized)
    return BlacklistResponse(symbol=normalized)
