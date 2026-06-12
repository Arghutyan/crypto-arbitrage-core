"""Exchange connector package.

Provides a uniform async interface (:class:`base.ExchangeConnector`) and a
factory to build connectors from configuration.
"""

from __future__ import annotations

from ..config import ExchangeConfig
from .base import ExchangeConnector


def build_connector(cfg: ExchangeConfig, request_timeout: float) -> ExchangeConnector:
    """Create the appropriate connector for the given exchange config.

    Today every exchange is served by the generic ``CCXTConnector``. When a
    venue needs bespoke handling (or a native WebSocket order-book feed),
    register a specialized connector here without touching callers.

    The ccxt-backed connector is imported lazily so the engine core can be
    imported and unit-tested without the (heavy) ccxt dependency installed.
    """

    from .ccxt_connector import CCXTConnector

    return CCXTConnector(cfg, request_timeout=request_timeout)


__all__ = ["ExchangeConnector", "build_connector"]
