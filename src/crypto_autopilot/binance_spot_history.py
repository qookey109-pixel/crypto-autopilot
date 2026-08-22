from __future__ import annotations

import json
import math
import random
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .historical import audit_candles
from .models import Candle


BINANCE_SPOT_KLINES_URL = "https://api.binance.com/api/v3/klines"
BINANCE_SPOT_INTERVAL_MS = {"1d": 24 * 60 * 60 * 1000}
PROJECT_INTERVAL = {"1d": "1D"}
_SYMBOL_RE = re.compile(r"^[A-Z0-9]{5,24}$")


class BinanceSpotHistoryError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class BinanceSpotCandle:
    symbol: str
    open_time_ms: int
    open: float
    high: float
    low: float
    close: float
    base_volume: float
    close_time_ms: int
    quote_volume: float
    trade_count: int

    def as_candle(self) -> Candle:
        return Candle(
            time_ms=self.open_time_ms,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.base_volume,
        )


@dataclass(frozen=True, slots=True)
class BinanceSpotSeries:
    symbol: str
    interval: str
    requested_start_ms: int
    requested_end_ms: int
    pages_fetched: int
    candles: tuple[BinanceSpotCandle, ...]

    @property
    def audit_ok(self) -> bool:
        if not self.candles:
            return False
        audit = audit_candles(
            [candle.as_candle() for candle in self.candles],
            PROJECT_INTERVAL[self.interval],
        )
        return audit.ok


Transport = Callable[[str, float], bytes]


def _validate_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if normalized != symbol or not _SYMBOL_RE.fullmatch(normalized):
        raise ValueError("Binance Spot symbol must be an uppercase alphanumeric market id")
    return normalized


def _finite_non_negative(value: float) -> bool:
    return math.isfinite(value) and value >= 0


def parse_spot_kline(symbol: str, row: object) -> BinanceSpotCandle:
    _validate_symbol(symbol)
    if not isinstance(row, list) or len(row) < 9:
        raise BinanceSpotHistoryError("Binance Spot kline row has too few fields")
    try:
        candle = BinanceSpotCandle(
            symbol=symbol,
            open_time_ms=int(row[0]),
            open=float(row[1]),
            high=float(row[2]),
            low=float(row[3]),
            close=float(row[4]),
            base_volume=float(row[5]),
            close_time_ms=int(row[6]),
            quote_volume=float(row[7]),
            trade_count=int(row[8]),
        )
    except (TypeError, ValueError) as exc:
        raise BinanceSpotHistoryError("invalid Binance Spot kline value") from exc
    prices = (candle.open, candle.high, candle.low, candle.close)
    if not all(math.isfinite(value) and value > 0 for value in prices):
        raise BinanceSpotHistoryError("Binance Spot kline contains invalid price")
    if candle.high < max(prices) or candle.low > min(prices):
        raise BinanceSpotHistoryError("Binance Spot kline violates OHLC bounds")
    if not _finite_non_negative(candle.base_volume) or not _finite_non_negative(
        candle.quote_volume
    ):
        raise BinanceSpotHistoryError("Binance Spot kline contains invalid volume")
    if candle.trade_count < 0 or candle.close_time_ms < candle.open_time_ms:
        raise BinanceSpotHistoryError("Binance Spot kline contains invalid metadata")
    return candle


def public_http_transport(url: str, timeout_seconds: float) -> bytes:
    request = Request(
        url,
        headers={"User-Agent": "qookey-crypto-autopilot-binance-spot-history/0.1"},
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read()


def fetch_spot_history(
    symbol: str,
    *,
    start_time_ms: int,
    end_time_ms: int,
    interval: str = "1d",
    page_limit: int = 1000,
    requests_per_second: float = 5.0,
    timeout_seconds: float = 30.0,
    max_retries: int = 4,
    transport: Transport = public_http_transport,
    sleep_fn: Callable[[float], None] = time.sleep,
    random_fn: Callable[[], float] = random.random,
) -> BinanceSpotSeries:
    symbol = _validate_symbol(symbol)
    if interval not in BINANCE_SPOT_INTERVAL_MS:
        raise ValueError("V0.1 Binance Spot history supports only 1d")
    if start_time_ms > end_time_ms:
        raise ValueError("start_time_ms must be <= end_time_ms")
    if not 1 <= page_limit <= 1000:
        raise ValueError("page_limit must be between 1 and 1000")
    if requests_per_second <= 0 or timeout_seconds <= 0:
        raise ValueError("request pacing and timeout must be positive")
    if max_retries < 0:
        raise ValueError("max_retries cannot be negative")

    step_ms = BINANCE_SPOT_INTERVAL_MS[interval]
    cursor = start_time_ms
    pages = 0
    by_time: dict[int, BinanceSpotCandle] = {}
    minimum_delay = 1.0 / requests_per_second

    while cursor <= end_time_ms:
        query = urlencode(
            {
                "symbol": symbol,
                "interval": interval,
                "startTime": cursor,
                "endTime": end_time_ms,
                "limit": page_limit,
            }
        )
        url = f"{BINANCE_SPOT_KLINES_URL}?{query}"
        payload: bytes | None = None
        for attempt in range(max_retries + 1):
            try:
                payload = transport(url, timeout_seconds)
                break
            except HTTPError as exc:
                if exc.code not in {418, 429, 500, 502, 503, 504} or attempt >= max_retries:
                    raise BinanceSpotHistoryError(
                        f"Binance Spot request failed for {symbol}: HTTP {exc.code}"
                    ) from exc
            except URLError as exc:
                if attempt >= max_retries:
                    raise BinanceSpotHistoryError(
                        f"Binance Spot request failed for {symbol}: {exc.reason}"
                    ) from exc
            sleep_fn(minimum_delay * (2**attempt) + random_fn() * 0.1)
        if payload is None:
            raise BinanceSpotHistoryError(f"Binance Spot request produced no payload: {symbol}")

        try:
            decoded = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BinanceSpotHistoryError("Binance Spot response was not valid JSON") from exc
        if isinstance(decoded, dict):
            raise BinanceSpotHistoryError(
                f"Binance Spot rejected {symbol}: {decoded.get('msg', 'unknown error')}"
            )
        if not isinstance(decoded, list):
            raise BinanceSpotHistoryError("Binance Spot response must be a list")

        pages += 1
        page = [parse_spot_kline(symbol, row) for row in decoded]
        if not page:
            break
        for candle in page:
            if start_time_ms <= candle.open_time_ms <= end_time_ms:
                by_time[candle.open_time_ms] = candle
        latest = max(candle.open_time_ms for candle in page)
        next_cursor = latest + step_ms
        if next_cursor <= cursor:
            raise BinanceSpotHistoryError("Binance Spot pagination cursor did not advance")
        cursor = next_cursor
        if len(page) < page_limit:
            break
        sleep_fn(minimum_delay)

    candles = tuple(sorted(by_time.values(), key=lambda item: item.open_time_ms))
    return BinanceSpotSeries(
        symbol=symbol,
        interval=interval,
        requested_start_ms=start_time_ms,
        requested_end_ms=end_time_ms,
        pages_fetched=pages,
        candles=candles,
    )
