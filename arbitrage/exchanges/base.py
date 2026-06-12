"""Abstract exchange connector.

The engine talks to exchanges exclusively through this interface. Each
concrete connector is responsible for translating a venue's API into our
:class:`~arbitrage.models.MarketSnapshot`.

The order-book hooks (``supports_order_book`` / ``watch_order_book``) are
defined here but left unimplemented. This is the seam for the upcoming
WebSocket integration: a connector simply overrides them and the engine can
start consuming the stream without structural changes.
"""

from __future__ import annotations

import abc
from typing import AsyncIterator

from ..config import ExchangeConfig
from ..models import MarketSnapshot


class ExchangeConnector(abc.ABC):
    """Common async contract every exchange adapter must satisfy."""

    def __init__(self, cfg: ExchangeConfig) -> None:
        self.cfg = cfg

    @property
    def name(self) -> str:
        return self.cfg.name

    @property
    def symbol(self) -> str:
        return self.cfg.symbol

    @abc.abstractmethod
    async def load(self) -> None:
        """Perform any one-time setup (e.g. load markets metadata)."""

    @abc.abstractmethod
    async def fetch_snapshot(self) -> MarketSnapshot:
        """Return the latest price + funding rate as a single snapshot.

        Implementations must never raise: network/exchange failures are
        captured in :attr:`MarketSnapshot.error` so one bad exchange cannot
        take down the whole polling loop.
        """

    @abc.abstractmethod
    async def close(self) -> None:
        """Release network resources (sessions, sockets)."""

    # ------------------------------------------------------------------ #
    # Order-book streaming seam (implemented in a later iteration).
    # ------------------------------------------------------------------ #
    @property
    def supports_order_book(self) -> bool:
        """Whether this connector can stream a live order book."""
        return False

    async def watch_order_book(self) -> AsyncIterator[MarketSnapshot]:
        """Yield snapshots enriched with best bid/ask from a WS feed.

        Default implementation signals that streaming is not yet available.
        """
        raise NotImplementedError(
            f"{self.name} connector does not support order-book streaming yet"
        )
        # Makes the function an async generator for type-checking purposes.
        yield  # pragma: no cover

    async def __aenter__(self) -> "ExchangeConnector":
        await self.load()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()
