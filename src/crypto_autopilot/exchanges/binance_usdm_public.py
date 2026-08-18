from __future__ import annotations

import json
import math
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..models import Candle


class BinanceUSDMAPIError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class BinanceFundingRate:
    symbol: str
    funding_time_ms: int
    rate: float
    mark_price: float | None
    rate_type: str | None = None

    def __post_init__(self) -> None:
        if not self.symbol.strip() or self.funding_time_ms < 0 or not math.isfinite(self.rate):
            raise ValueError("invalid Binance funding-rate record")
        if self.mark_price is not None and (not math.isfinite(self.mark_price) or self.mark_price <= 0):
            raise ValueError("mark_price must be finite and positive when supplied")


@dataclass(frozen=True, slots=True)
class BinanceMarkPriceCandle:
    symbol: str
    interval: str
    open_time_ms: int
    close_time_ms: int
    open: float
    high: float
    low: float
    close: float

    def __post_init__(self) -> None:
        if not self.symbol.strip() or not self.interval.strip():
            raise ValueError("symbol and interval are required")
        if self.open_time_ms < 0 or self.close_time_ms < self.open_time_ms:
            raise ValueError("invalid mark-price candle timestamps")
        values = (self.open, self.high, self.low, self.close)
        if not all(math.isfinite(value) and value > 0 for value in values):
            raise ValueError("mark-price OHLC must be finite and positive")
        if self.low > min(self.open, self.close, self.high) or self.high < max(self.open, self.close, self.low):
            raise ValueError("invalid mark-price candle range")

    @property
    def available_at_ms(self) -> int:
        return self.close_time_ms + 1


@dataclass(frozen=True, slots=True)
class BinanceOpenInterestPoint:
    symbol: str
    period: str
    timestamp_ms: int
    sum_open_interest: float
    sum_open_interest_value: float

    def __post_init__(self) -> None:
        if not self.symbol.strip() or not self.period.strip() or self.timestamp_ms < 0:
            raise ValueError("invalid Binance open-interest record")
        if not math.isfinite(self.sum_open_interest) or self.sum_open_interest < 0:
            raise ValueError("sum_open_interest must be finite and non-negative")
        if not math.isfinite(self.sum_open_interest_value) or self.sum_open_interest_value < 0:
            raise ValueError("sum_open_interest_value must be finite and non-negative")


class BinanceUSDMPublicClient:
    """Public-only Binance USDⓈ-M historical market-data client.

    This client is intentionally separate from Pionex. Data returned by this
    adapter is Binance-native research evidence and must never be labelled as
    Pionex-native authority.
    """

    BASE_URL = "https://fapi.binance.com"
    ALLOWED_KLINE_INTERVALS = {
        "1m",
        "3m",
        "5m",
        "15m",
        "30m",
        "1h",
        "2h",
        "4h",
        "6h",
        "8h",
        "12h",
        "1d",
        "3d",
        "1w",
        "1M",
    }
    ALLOWED_OI_PERIODS = {"5m", "15m", "30m", "1h", "2h", "4h", "6h", "12h", "1d"}

    def __init__(self, *, timeout_seconds: float = 15.0) -> None:
        self.timeout_seconds = timeout_seconds

    def _get_json(self, path: str, params: dict[str, object]) -> object:
        query = urlencode({key: value for key, value in params.items() if value is not None})
        url = f"{self.BASE_URL}{path}?{query}" if query else f"{self.BASE_URL}{path}"
        req = Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "qookey-crypto-autopilot/0.1"},
        )
        try:
            with urlopen(req, timeout=self.timeout_seconds) as response:  # noqa: S310 - fixed HTTPS host
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # pragma: no cover - network failures are integration evidence
            raise BinanceUSDMAPIError(f"Binance USD-M request failed: {path}: {exc}") from exc
        if isinstance(payload, dict) and "code" in payload and int(payload.get("code") or 0) < 0:
            raise BinanceUSDMAPIError(
                f"Binance USD-M request failed: {payload.get('code')} {payload.get('msg')}"
            )
        return payload

    @staticmethod
    def _validate_range(start_time_ms: int | None, end_time_ms: int | None) -> None:
        if start_time_ms is not None and start_time_ms < 0:
            raise ValueError("start_time_ms cannot be negative")
        if end_time_ms is not None and end_time_ms < 0:
            raise ValueError("end_time_ms cannot be negative")
        if start_time_ms is not None and end_time_ms is not None and start_time_ms > end_time_ms:
            raise ValueError("start_time_ms must be <= end_time_ms")

    def get_klines(
        self,
        symbol: str,
        interval: str,
        *,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
        limit: int = 1500,
    ) -> list[Candle]:
        if not symbol.strip():
            raise ValueError("symbol is required")
        if interval not in self.ALLOWED_KLINE_INTERVALS:
            raise ValueError(f"unsupported Binance USD-M interval: {interval}")
        if not 1 <= limit <= 1500:
            raise ValueError("Binance USD-M kline limit must be between 1 and 1500")
        self._validate_range(start_time_ms, end_time_ms)
        payload = self._get_json(
            "/fapi/v1/klines",
            {
                "symbol": symbol,
                "interval": interval,
                "startTime": start_time_ms,
                "endTime": end_time_ms,
                "limit": limit,
            },
        )
        if not isinstance(payload, list):
            raise BinanceUSDMAPIError("unexpected Binance kline payload")
        candles = [
            Candle(
                time_ms=int(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
            )
            for row in payload
        ]
        return sorted(candles, key=lambda candle: candle.time_ms)

    def get_mark_price_klines(
        self,
        symbol: str,
        interval: str,
        *,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
        limit: int = 1500,
    ) -> list[BinanceMarkPriceCandle]:
        if not symbol.strip():
            raise ValueError("symbol is required")
        if interval not in self.ALLOWED_KLINE_INTERVALS:
            raise ValueError(f"unsupported Binance USD-M interval: {interval}")
        if not 1 <= limit <= 1500:
            raise ValueError("Binance USD-M mark-price kline limit must be between 1 and 1500")
        self._validate_range(start_time_ms, end_time_ms)
        payload = self._get_json(
            "/fapi/v1/markPriceKlines",
            {
                "symbol": symbol,
                "interval": interval,
                "startTime": start_time_ms,
                "endTime": end_time_ms,
                "limit": limit,
            },
        )
        if not isinstance(payload, list):
            raise BinanceUSDMAPIError("unexpected Binance mark-price kline payload")
        rows = [
            BinanceMarkPriceCandle(
                symbol=symbol,
                interval=interval,
                open_time_ms=int(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                close_time_ms=int(row[6]),
            )
            for row in payload
        ]
        return sorted(rows, key=lambda candle: candle.open_time_ms)

    def get_funding_rates(
        self,
        symbol: str,
        *,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
        limit: int = 1000,
    ) -> list[BinanceFundingRate]:
        if not symbol.strip():
            raise ValueError("symbol is required")
        if not 1 <= limit <= 1000:
            raise ValueError("Binance USD-M funding-rate limit must be between 1 and 1000")
        self._validate_range(start_time_ms, end_time_ms)
        payload = self._get_json(
            "/fapi/v1/fundingRate",
            {
                "symbol": symbol,
                "startTime": start_time_ms,
                "endTime": end_time_ms,
                "limit": limit,
            },
        )
        if not isinstance(payload, list):
            raise BinanceUSDMAPIError("unexpected Binance funding-rate payload")
        rows = [
            BinanceFundingRate(
                symbol=str(row.get("symbol") or symbol),
                funding_time_ms=int(row["fundingTime"]),
                rate=float(row["fundingRate"]),
                mark_price=(float(row["markPrice"]) if row.get("markPrice") not in (None, "") else None),
                rate_type=(str(row["rateType"]) if row.get("rateType") not in (None, "") else None),
            )
            for row in payload
        ]
        return sorted(rows, key=lambda item: (item.funding_time_ms, item.rate_type or "", item.rate))

    def get_open_interest_history(
        self,
        symbol: str,
        period: str,
        *,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
        limit: int = 500,
    ) -> list[BinanceOpenInterestPoint]:
        if not symbol.strip():
            raise ValueError("symbol is required")
        if period not in self.ALLOWED_OI_PERIODS:
            raise ValueError(f"unsupported Binance USD-M open-interest period: {period}")
        if not 1 <= limit <= 500:
            raise ValueError("Binance USD-M open-interest limit must be between 1 and 500")
        self._validate_range(start_time_ms, end_time_ms)
        payload = self._get_json(
            "/futures/data/openInterestHist",
            {
                "symbol": symbol,
                "period": period,
                "startTime": start_time_ms,
                "endTime": end_time_ms,
                "limit": limit,
            },
        )
        if not isinstance(payload, list):
            raise BinanceUSDMAPIError("unexpected Binance open-interest payload")
        rows = [
            BinanceOpenInterestPoint(
                symbol=str(row.get("symbol") or symbol),
                period=period,
                timestamp_ms=int(row["timestamp"]),
                sum_open_interest=float(row["sumOpenInterest"]),
                sum_open_interest_value=float(row["sumOpenInterestValue"]),
            )
            for row in payload
        ]
        return sorted(rows, key=lambda item: item.timestamp_ms)
