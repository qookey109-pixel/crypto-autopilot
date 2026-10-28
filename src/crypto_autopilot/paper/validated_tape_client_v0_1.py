"""Validate lifecycle market observations before lossy parsing or aggregation."""
from __future__ import annotations

import math
from collections.abc import Mapping

from crypto_autopilot.exchanges.pionex_public import PionexPublicClient
from crypto_autopilot.paper.cloud_loop_v0_1 import CloudLoopReviewRequired
from crypto_autopilot.paper.cloud_pionex_client_v0_1 import CloudPaperPionexPublicClient


def _positive_finite(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return False
    try:
        converted = float(value)
        return math.isfinite(converted) and converted > 0
    except (ValueError, OverflowError):
        return False


class _RawTapeBridge:
    """Reuse bounded Cloud Paper transport and existing parsers after validation."""

    def __init__(self, client: CloudPaperPionexPublicClient):
        self._client = client

    def _get_json(self, path: str, params: dict[str, object]):
        payload = self._client._get_json(path, params)
        data = payload.get("data")
        if not isinstance(data, Mapping):
            raise CloudLoopReviewRequired("MARKET_RAW_INVALID")
        if path == "/api/v1/market/depth":
            for side in ("bids", "asks"):
                rows = data.get(side)
                if not isinstance(rows, list) or any(
                    not isinstance(row, (list, tuple)) or len(row) < 2
                    or not _positive_finite(row[0]) or not _positive_finite(row[1])
                    for row in rows
                ):
                    raise CloudLoopReviewRequired("ORDER_BOOK_INVALID")
        elif path == "/api/v1/market/trades":
            rows = data.get("trades")
            if not isinstance(rows, list) or any(
                not isinstance(row, Mapping)
                or not _positive_finite(row.get("price"))
                or not _positive_finite(row.get("size"))
                or isinstance(row.get("timestamp"), bool)
                for row in rows
            ):
                raise CloudLoopReviewRequired("TRADE_TAPE_INVALID")
        return payload


class ValidatedTapeClient:
    """Transparent adapter for bounded Cloud Paper lifecycle inputs."""

    def __init__(self, client: object):
        self._client = client

    def __getattr__(self, name: str):
        return getattr(self._client, name)

    def get_recent_trades(self, symbol: str, *, limit: int):
        if isinstance(self._client, CloudPaperPionexPublicClient):
            trades = PionexPublicClient.get_recent_trades(
                _RawTapeBridge(self._client), symbol, limit=limit,
            )
        else:
            trades = self._client.get_recent_trades(symbol, limit=limit)
        if any(
            not _positive_finite(trade.price) or not _positive_finite(trade.size)
            for trade in trades
        ):
            raise CloudLoopReviewRequired("TRADE_TAPE_INVALID")
        prices_at_time: dict[int, float] = {}
        for trade in trades:
            prior = prices_at_time.setdefault(trade.time_ms, trade.price)
            if prior != trade.price:
                raise CloudLoopReviewRequired("TRADE_TAPE_ORDER_AMBIGUOUS")
        return trades

    def get_order_book(self, symbol: str, *, limit: int):
        if isinstance(self._client, CloudPaperPionexPublicClient):
            book = PionexPublicClient.get_order_book(
                _RawTapeBridge(self._client), symbol, limit=limit,
            )
        else:
            book = self._client.get_order_book(symbol, limit=limit)
        if any(
            not _positive_finite(price) or not _positive_finite(size)
            for price, size in (*book.bids, *book.asks)
        ):
            raise CloudLoopReviewRequired("ORDER_BOOK_INVALID")
        return book
