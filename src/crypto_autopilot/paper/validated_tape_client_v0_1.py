"""Validate all lifecycle market observations before aggregation."""
from __future__ import annotations

import math

from crypto_autopilot.paper.cloud_loop_v0_1 import CloudLoopReviewRequired


def _positive_finite(value: object) -> bool:
    return (
        isinstance(value, (int, float)) and not isinstance(value, bool)
        and math.isfinite(value) and value > 0
    )


class ValidatedTapeClient:
    """Transparent client adapter for complete-tape lifecycle inputs."""

    def __init__(self, client: object):
        self._client = client

    def __getattr__(self, name: str):
        return getattr(self._client, name)

    def get_recent_trades(self, symbol: str, *, limit: int):
        trades = self._client.get_recent_trades(symbol, limit=limit)
        if any(
            not _positive_finite(trade.price) or not _positive_finite(trade.size)
            for trade in trades
        ):
            raise CloudLoopReviewRequired("TRADE_TAPE_INVALID")
        return trades

    def get_order_book(self, symbol: str, *, limit: int):
        book = self._client.get_order_book(symbol, limit=limit)
        if any(
            not _positive_finite(price) or not _positive_finite(size)
            for price, size in (*book.bids, *book.asks)
        ):
            raise CloudLoopReviewRequired("ORDER_BOOK_INVALID")
        return book
