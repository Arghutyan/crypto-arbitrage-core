"""Runtime configuration for the delta-neutral funding arbitrage engine.

Everything that changes between deployments is centralised here and can be
overridden through environment variables so the same image runs unchanged in
docker-compose and Kubernetes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExchangeSpec:
    """Describes one venue we scan.

    ``id`` is the ccxt exchange id. ``options`` are passed straight to the ccxt
    constructor (mainly ``defaultType`` so we load perpetual-swap markets).
    """

    name: str
    id: str
    options: dict = field(default_factory=lambda: {"defaultType": "swap"})


# The eleven venues requested. ccxt id notes:
#   * ``gate``           — Gate.io (the old ``gateio`` alias was dropped in ccxt 4.5).
#   * ``kucoinfutures``  — KuCoin perpetuals (the spot ``kucoin`` id has no swaps).
#   * ``htx``            — Huobi/HTX.
#   * ``aster``/``xt``   — Aster DEX perps and XT.com perpetuals.
EXCHANGE_SPECS: tuple[ExchangeSpec, ...] = (
    ExchangeSpec("Binance", "binance"),
    ExchangeSpec("Bybit", "bybit"),
    ExchangeSpec("OKX", "okx"),
    ExchangeSpec("Gate.io", "gate"),
    ExchangeSpec("MEXC", "mexc"),
    ExchangeSpec("KuCoin", "kucoinfutures", options={}),
    ExchangeSpec("HTX", "htx"),
    ExchangeSpec("Bitget", "bitget"),
    ExchangeSpec("Hyperliquid", "hyperliquid", options={}),
    ExchangeSpec("Aster", "aster", options={}),
    ExchangeSpec("XT", "xt"),
)


@dataclass(frozen=True)
class Settings:
    """Top-level engine settings."""

    # Quote/settle currencies considered comparable across venues. USDT and
    # USDC perpetuals trade close enough to 1:1 to arbitrage on price spread.
    quote_currencies: tuple[str, ...] = ("USDT", "USDC")

    # Step 1 — discard anything below this raw (mid-price) spread, in percent.
    min_raw_spread_pct: float = 0.2

    # Step 2 — how many of the widest raw spreads get the expensive L2 /
    # order-book + funding treatment each cycle.
    top_n_orderbooks: int = 50

    # Notional used when walking the order book to estimate realistic slippage.
    order_size_usd: float = 1000.0

    # Seconds between full scan cycles.
    poll_interval: float = 30.0

    # Per-request ccxt network timeout, seconds.
    request_timeout: float = 20.0

    # Maximum exchanges hit concurrently for the heavy (order-book) phase.
    orderbook_concurrency: int = 20

    exchanges: tuple[ExchangeSpec, ...] = EXCHANGE_SPECS


@dataclass(frozen=True)
class DbSettings:
    """PostgreSQL connection parameters."""

    host: str = "postgres-service"
    port: int = 5432
    user: str = "db_user"
    password: str = "changeme"
    name: str = "crypto_analytics"

    @property
    def dsn(self) -> str:
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


@dataclass(frozen=True)
class TelegramSettings:
    """Telegram bot credentials shared by the bot and the alerting engine."""

    token: str = ""
    # Cooldown (seconds) before the same opportunity can alert a user again.
    alert_cooldown: float = 900.0
    # Telegram user ids allowed to manage the symbol blacklist. Admins also get
    # an inline "blacklist this pair" button on every alert they receive.
    admin_ids: frozenset[int] = frozenset()

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    def is_admin(self, telegram_id: int) -> bool:
        return telegram_id in self.admin_ids


def _parse_admin_ids(raw: str) -> frozenset[int]:
    """Parse a comma/space separated list of Telegram ids into a set."""
    ids: set[int] = set()
    for chunk in raw.replace(",", " ").split():
        try:
            ids.add(int(chunk))
        except ValueError:
            continue
    return frozenset(ids)


def load_settings() -> Settings:
    """Build :class:`Settings` applying environment overrides."""
    return Settings(
        min_raw_spread_pct=float(os.getenv("ARB_MIN_RAW_SPREAD", "0.2")),
        top_n_orderbooks=int(os.getenv("ARB_TOP_N", "50")),
        order_size_usd=float(os.getenv("ARB_ORDER_SIZE_USD", "1000")),
        poll_interval=float(os.getenv("ARB_POLL_INTERVAL", "30")),
        request_timeout=float(os.getenv("ARB_REQUEST_TIMEOUT", "20")),
        orderbook_concurrency=int(os.getenv("ARB_OB_CONCURRENCY", "20")),
    )


def load_db_settings() -> DbSettings:
    """Build :class:`DbSettings` from environment variables."""
    return DbSettings(
        host=os.getenv("DB_HOST", "postgres-service"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "db_user"),
        password=os.getenv("DB_PASSWORD", "changeme"),
        name=os.getenv("DB_NAME", "crypto_analytics"),
    )


def load_telegram_settings() -> TelegramSettings:
    """Build :class:`TelegramSettings` from environment variables."""
    return TelegramSettings(
        token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        alert_cooldown=float(os.getenv("ALERT_COOLDOWN_SECONDS", "900")),
        admin_ids=_parse_admin_ids(os.getenv("TELEGRAM_ADMIN_IDS", "")),
    )
