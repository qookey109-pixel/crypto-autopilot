from __future__ import annotations

import json
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..models import BookTicker, Candle, MarketTicker
from ..market_features import (
    DerivativeIndexSnapshot,
    FundingRateObservation,
    OrderBookSnapshot,
    PublicTrade,
)


class PionexAPIError(RuntimeError):
    pass


class PionexPublicClient:
    """Public-only Pionex futures client for V0.1.

    No API key, signing, balance, position or order methods are present here.
    """

    BASE_URL = "https://api.pionex.com"
    ALLOWED_INTERVALS = {"1M", "5M", "15M", "30M", "60M", "4H", "8H", "12H", "1D", "1W", "1m"}

    def __init__(
        self,
        *,
        timeout_seconds: float = 15.0,
        requests_per_second: float = 3.0,
    ) -> None:
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        self.timeout_seconds = timeout_seconds
        self.minimum_request_interval_seconds = 1.0 / requests_per_second
        self._last_request_started: float | None = None

    def _pace(self) -> None:
        now = time.monotonic()
        if self._last_request_started is not None:
            remaining = self.minimum_request_interval_seconds - (
                now - self._last_request_started
            )
            if remaining > 0:
                time.sleep(remaining)
        self._last_request_started = time.monotonic()

    def _get_json(self, path: str, params: dict[str, object]) -> dict:
        self._pace()
        query = urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{self.BASE_URL}{path}?{query}" if query else f"{self.BASE_URL}{path}"
        req = Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "qookey-crypto-autopilot/0.1"},
        )
        with urlopen(req, timeout=self.timeout_seconds) as response:  # noqa: S310 - fixed HTTPS host
            payload = json.loads(response.read().decode("utf-8"))
        if not payload.get("result"):
            raise PionexAPIError(
                f"Pionex request failed: {payload.get('code')} {payload.get('message')}"
            )
        return payload

    def list_perpetual_symbols(self) -> list[str]:
        payload = self._get_json(
            "/api/v1/common/symbols",
            {"type": "PERP", "status": "TRADING"},
        )
        rows = payload.get("data", {}).get("symbols", [])
        return sorted({str(row["symbol"]) for row in rows if row.get("symbol")})

    def list_perpetual_tickers(self) -> list[MarketTicker]:
        payload = self._get_json("/api/v1/market/tickers", {"type": "PERP"})
        rows = payload.get("data", {}).get("tickers", [])
        tickers = []
        for row in rows:
            symbol = row.get("symbol")
            if not symbol:
                continue
            tickers.append(
                MarketTicker(
                    symbol=str(symbol),
                    close=float(row.get("close") or 0.0),
                    base_volume=float(row.get("volume") or 0.0),
                    quote_amount=float(row.get("amount") or 0.0),
                    trade_count=int(row.get("count") or 0),
                )
            )
        return sorted(tickers, key=lambda item: item.symbol)

    def list_perpetual_book_tickers(self) -> list[BookTicker]:
        # Runtime verification on 2026-08-17 found the singular /bookTicker route returning 404
        # while Pionex's public-permission reference and changelog list /bookTickers.
        payload = self._get_json("/api/v1/market/bookTickers", {"type": "PERP"})
        rows = payload.get("data", {}).get("tickers", [])
        books = []
        for row in rows:
            symbol = row.get("symbol")
            if not symbol:
                continue
            books.append(
                BookTicker(
                    symbol=str(symbol),
                    bid_price=float(row.get("bidPrice") or 0.0),
                    bid_size=float(row.get("bidSize") or 0.0),
                    ask_price=float(row.get("askPrice") or 0.0),
                    ask_size=float(row.get("askSize") or 0.0),
                    timestamp_ms=int(row.get("timestamp") or 0),
                )
            )
        return sorted(books, key=lambda item: item.symbol)

    def get_klines(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        end_time_ms: int | None = None,
    ) -> list[Candle]:
        if interval not in self.ALLOWED_INTERVALS:
            raise ValueError(f"Unsupported Pionex interval: {interval}")
        if not 1 <= limit <= 500:
            raise ValueError("Pionex futures kline limit must be between 1 and 500")

        payload = self._get_json(
            "/api/v1/market/klines",
            {
                "symbol": symbol,
                "interval": interval,
                "limit": limit,
                "endTime": end_time_ms,
            },
        )
        candles = [
            Candle(
                time_ms=int(row["time"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
            for row in payload.get("data", {}).get("klines", [])
        ]
        return sorted(candles, key=lambda candle: candle.time_ms)

    def get_recent_trades(self, symbol: str, *, limit: int = 500) -> list[PublicTrade]:
        if not 10 <= limit <= 500:
            raise ValueError("Pionex recent-trade limit must be between 10 and 500")
        payload = self._get_json("/api/v1/market/trades", {"symbol": symbol, "limit": limit})
        rows = payload.get("data", {}).get("trades", [])
        return sorted(
            (
                PublicTrade(
                    symbol=str(row.get("symbol") or symbol),
                    trade_id=str(row.get("tradeId") or ""),
                    price=float(row.get("price") or 0.0),
                    size=float(row.get("size") or 0.0),
                    side=str(row.get("side") or "").upper(),
                    time_ms=int(row.get("timestamp") or 0),
                )
                for row in rows
            ),
            key=lambda item: (item.time_ms, item.trade_id),
        )

    def get_order_book(self, symbol: str, *, limit: int = 20) -> OrderBookSnapshot:
        if not 1 <= limit <= 1_000:
            raise ValueError("Pionex depth limit must be between 1 and 1000")
        payload = self._get_json("/api/v1/market/depth", {"symbol": symbol, "limit": limit})
        data = payload.get("data", {})

        def levels(name: str) -> tuple[tuple[float, float], ...]:
            output = []
            for row in data.get(name, []):
                if not isinstance(row, (list, tuple)) or len(row) < 2:
                    continue
                output.append((float(row[0]), float(row[1])))
            return tuple(output)

        return OrderBookSnapshot(
            symbol=symbol,
            bids=levels("bids"),
            asks=levels("asks"),
            update_time_ms=int(data.get("updateTime") or payload.get("timestamp") or 0),
        )

    def get_funding_rates(
        self, symbol: str, *, limit: int = 100, end_time_ms: int | None = None
    ) -> list[FundingRateObservation]:
        if not 1 <= limit <= 500:
            raise ValueError("Pionex funding-rate limit must be between 1 and 500")
        payload = self._get_json(
            "/api/v1/market/fundingRates",
            {"symbol": symbol, "limit": limit, "endTime": end_time_ms},
        )
        rows = payload.get("data", {}).get("rates", [])
        return sorted(
            (
                FundingRateObservation(
                    symbol=symbol,
                    funding_time_ms=int(row.get("fundingTime") or 0),
                    funding_rate=float(row.get("fundingRate") or 0.0),
                )
                for row in rows
            ),
            key=lambda item: item.funding_time_ms,
        )

    def list_derivative_indexes(self) -> list[DerivativeIndexSnapshot]:
        payload = self._get_json("/api/v1/market/indexes", {})
        rows = payload.get("data", {}).get("indexes", [])
        return sorted(
            (
                DerivativeIndexSnapshot(
                    symbol=str(row.get("symbol") or ""),
                    index_price=float(row.get("indexPrice") or 0.0),
                    mark_price=float(row.get("markPrice") or 0.0),
                    next_funding_rate=float(row.get("nextFundingRate") or 0.0),
                    next_funding_time_ms=int(row.get("nextFundingTime") or 0),
                    update_time_ms=int(row.get("updateTime") or payload.get("timestamp") or 0),
                )
                for row in rows
                if row.get("symbol")
            ),
            key=lambda item: item.symbol,
        )

    def list_open_interests(self) -> dict[str, float]:
        payload = self._get_json("/api/v1/market/openInterests", {})
        rows = payload.get("data", {}).get("openInterests", [])
        return {
            str(row["symbol"]): float(row.get("openInterest") or 0.0)
            for row in rows
            if row.get("symbol")
        }

    def get_price_klines(
        self,
        symbol: str,
        interval: str,
        *,
        price_type: str,
        limit: int = 100,
    ) -> list[Candle]:
        if interval not in self.ALLOWED_INTERVALS:
            raise ValueError(f"Unsupported Pionex interval: {interval}")
        if not 1 <= limit <= 2_000:
            raise ValueError("Pionex price-kline limit must be between 1 and 2000")
        paths = {"mark": "/api/v1/market/markKlines", "index": "/api/v1/market/indexKlines"}
        if price_type not in paths:
            raise ValueError("price_type must be mark or index")
        payload = self._get_json(
            paths[price_type],
            {"symbol": symbol, "interval": interval, "limit": limit},
        )
        rows = payload.get("data", {}).get("klines", [])
        return sorted(
            (
                Candle(
                    time_ms=int(row["time"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=0.0,
                )
                for row in rows
            ),
            key=lambda item: item.time_ms,
        )
