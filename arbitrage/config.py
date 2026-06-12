"""Static configuration for the arbitrage engine.

Everything that is likely to change between deployments lives here so the
rest of the code can stay declarative. Values can be overridden via
environment variables to keep the service container-friendly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExchangeConfig:
    """Identifies a single exchange/market we want to monitor.

    ``id`` is the ccxt exchange id (e.g. ``"binance"``, ``"gate"``).
    ``symbol`` is the unified ccxt symbol for the perpetual futures market.
    For USDT-margined perpetuals ccxt uses the ``BASE/QUOTE:SETTLE`` form,
    e.g. ``"ACE/USDT:USDT"``.
    """

    name: str
    id: str
    symbol: str
    # Passed straight through to the ccxt constructor (e.g. defaultType).
    options: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Settings:
    """Top-level runtime settings for the engine."""

    # The pair we are arbitraging, used only for display/logging.
    pair: str = "ACE/USDT"

    # How often (seconds) we poll the REST endpoints and emit a log line.
    poll_interval: float = 5.0

    # Per-request network timeout in seconds.
    request_timeout: float = 10.0

    exchanges: tuple[ExchangeConfig, ...] = (
        ExchangeConfig(
            name="Binance",
            id="binance",
            symbol="ACE/USDT:USDT",
            options={"defaultType": "swap"},
        ),
        ExchangeConfig(
            name="Gate",
            id="gate",
            symbol="ACE/USDT:USDT",
            options={"defaultType": "swap"},
        ),
    )


@dataclass(frozen=True)
class DbSettings:
    """Connection parameters for the PostgreSQL persistence layer."""

    host: str = "postgres-service"
    port: int = 5432
    user: str = "db_user"
    password: str = "changeme"
    name: str = "crypto_analytics"


def load_db_settings() -> DbSettings:
    """Build :class:`DbSettings` from environment variables."""
    return DbSettings(
        host=os.getenv("DB_HOST", "postgres-service"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "db_user"),
        password=os.getenv("DB_PASSWORD", "changeme"),
        name=os.getenv("DB_NAME", "crypto_analytics"),
    )


def load_settings() -> Settings:
    """Build :class:`Settings`, applying environment-variable overrides."""

    return Settings(
        pair=os.getenv("ARB_PAIR", "ACE/USDT"),
        poll_interval=float(os.getenv("ARB_POLL_INTERVAL", "5")),
        request_timeout=float(os.getenv("ARB_REQUEST_TIMEOUT", "10")),
    )
