from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .backtest import FundingPoint
from .historical import CandleAudit, audit_candles
from .models import Candle
from .exchanges.binance_usdm_public import (
    BinanceFundingRate,
    BinanceMarkPriceCandle,
    BinanceOpenInterestPoint,
)


BINANCE_TO_PROJECT_INTERVAL = {"15m": "15M", "1h": "60M", "4h": "4H"}
BINANCE_INTERVAL_MS = {
    "15m": 15 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
}
# Binance documents OI history as "latest 1 month". V0.1 deliberately
# adopts a conservative 30-day project window instead of assuming 31 days.
OPEN_INTEREST_PROJECT_WINDOW_MS = 30 * 24 * 60 * 60 * 1000


class BinanceHistoricalEvidenceError(RuntimeError):
    pass


class BinanceHistoricalClient(Protocol):
    def get_klines(
        self,
        symbol: str,
        interval: str,
        *,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
        limit: int = 1500,
    ) -> list[Candle]: ...

    def get_mark_price_klines(
        self,
        symbol: str,
        interval: str,
        *,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
        limit: int = 1500,
    ) -> list[BinanceMarkPriceCandle]: ...

    def get_funding_rates(
        self,
        symbol: str,
        *,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
        limit: int = 1000,
    ) -> list[BinanceFundingRate]: ...

    def get_open_interest_history(
        self,
        symbol: str,
        period: str,
        *,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
        limit: int = 500,
    ) -> list[BinanceOpenInterestPoint]: ...


@dataclass(frozen=True, slots=True)
class BinanceSourceProvenance:
    provider: str = "binance_usdm"
    execution_exchange: str = "pionex"
    native_to_execution_exchange: bool = False
    may_authorize_pionex_native_history: bool = False
    requires_equivalence_gate: bool = True


@dataclass(frozen=True, slots=True)
class BinanceKlineBackfillResult:
    symbol: str
    interval: str
    requested_start_ms: int
    requested_end_ms: int
    pages_fetched: int
    candles: tuple[Candle, ...]
    audit: CandleAudit
    provenance: BinanceSourceProvenance = BinanceSourceProvenance()


@dataclass(frozen=True, slots=True)
class BinanceMarkPriceBackfillResult:
    symbol: str
    interval: str
    requested_start_ms: int
    requested_end_ms: int
    pages_fetched: int
    candles: tuple[BinanceMarkPriceCandle, ...]
    provenance: BinanceSourceProvenance = BinanceSourceProvenance()


@dataclass(frozen=True, slots=True)
class BinanceFundingBackfillResult:
    symbol: str
    requested_start_ms: int
    requested_end_ms: int
    pages_fetched: int
    points: tuple[BinanceFundingRate, ...]
    provenance: BinanceSourceProvenance = BinanceSourceProvenance()


@dataclass(frozen=True, slots=True)
class BinanceOpenInterestBackfillResult:
    symbol: str
    period: str
    requested_start_ms: int
    requested_end_ms: int
    pages_fetched: int
    points: tuple[BinanceOpenInterestPoint, ...]
    provenance: BinanceSourceProvenance = BinanceSourceProvenance()


def pionex_perp_to_binance_usdm(symbol: str) -> str:
    suffix = "_USDT_PERP"
    if not symbol.endswith(suffix):
        raise ValueError("only Pionex _USDT_PERP symbols have a V0.1 Binance mapping")
    base = symbol[: -len(suffix)]
    if not base or not base.replace("_", "").isalnum():
        raise ValueError("invalid Pionex perpetual symbol")
    return f"{base.replace('_', '')}USDT"


def binance_usdm_to_pionex_perp(symbol: str) -> str:
    if not symbol.endswith("USDT") or len(symbol) <= 4:
        raise ValueError("only Binance USDT symbols have a V0.1 Pionex mapping")
    return f"{symbol[:-4]}_USDT_PERP"


def _validate_request_range(start_time_ms: int, end_time_ms: int, max_pages: int) -> None:
    if start_time_ms < 0 or end_time_ms < 0:
        raise ValueError("request timestamps cannot be negative")
    if start_time_ms > end_time_ms:
        raise ValueError("start_time_ms must be <= end_time_ms")
    if max_pages < 1:
        raise ValueError("max_pages must be positive")


def _validate_unique_monotonic(times: list[int], *, label: str) -> None:
    if len(times) != len(set(times)):
        raise BinanceHistoricalEvidenceError(f"duplicate {label} timestamps")
    if times != sorted(times):
        raise BinanceHistoricalEvidenceError(f"out-of-order {label} timestamps")


def backfill_binance_klines(
    client: BinanceHistoricalClient,
    symbol: str,
    interval: str,
    *,
    start_time_ms: int,
    end_time_ms: int,
    page_limit: int = 1500,
    max_pages: int = 10_000,
) -> BinanceKlineBackfillResult:
    if interval not in BINANCE_TO_PROJECT_INTERVAL:
        raise ValueError("V0.1 Binance historical klines support 15m, 1h and 4h")
    if not 1 <= page_limit <= 1500:
        raise ValueError("page_limit must be between 1 and 1500")
    _validate_request_range(start_time_ms, end_time_ms, max_pages)

    cursor = start_time_ms
    pages = 0
    collected: dict[int, Candle] = {}
    step = BINANCE_INTERVAL_MS[interval]
    while cursor <= end_time_ms:
        if pages >= max_pages:
            raise BinanceHistoricalEvidenceError("Binance kline pagination exceeded max_pages")
        page = client.get_klines(
            symbol,
            interval,
            start_time_ms=cursor,
            end_time_ms=end_time_ms,
            limit=page_limit,
        )
        pages += 1
        if not page:
            break
        ordered = sorted(page, key=lambda candle: candle.time_ms)
        if ordered != page:
            raise BinanceHistoricalEvidenceError("Binance kline page was not ascending")
        for candle in ordered:
            if candle.time_ms < start_time_ms or candle.time_ms > end_time_ms:
                raise BinanceHistoricalEvidenceError("Binance kline escaped requested range")
            existing = collected.get(candle.time_ms)
            if existing is not None and existing != candle:
                raise BinanceHistoricalEvidenceError("conflicting duplicate Binance kline")
            collected[candle.time_ms] = candle
        next_cursor = ordered[-1].time_ms + step
        if next_cursor <= cursor:
            raise BinanceHistoricalEvidenceError("Binance kline pagination did not advance")
        cursor = next_cursor
        if len(ordered) < page_limit:
            break

    candles = tuple(collected[key] for key in sorted(collected))
    audit = audit_candles(candles, BINANCE_TO_PROJECT_INTERVAL[interval])
    if candles and not audit.ok:
        raise BinanceHistoricalEvidenceError("Binance kline audit failed")
    return BinanceKlineBackfillResult(
        symbol=symbol,
        interval=interval,
        requested_start_ms=start_time_ms,
        requested_end_ms=end_time_ms,
        pages_fetched=pages,
        candles=candles,
        audit=audit,
    )


def backfill_binance_mark_price(
    client: BinanceHistoricalClient,
    symbol: str,
    interval: str,
    *,
    start_time_ms: int,
    end_time_ms: int,
    page_limit: int = 1500,
    max_pages: int = 10_000,
) -> BinanceMarkPriceBackfillResult:
    if interval not in BINANCE_INTERVAL_MS:
        raise ValueError("V0.1 Binance mark-price history supports 15m, 1h and 4h")
    if not 1 <= page_limit <= 1500:
        raise ValueError("page_limit must be between 1 and 1500")
    _validate_request_range(start_time_ms, end_time_ms, max_pages)

    cursor = start_time_ms
    pages = 0
    collected: dict[int, BinanceMarkPriceCandle] = {}
    step = BINANCE_INTERVAL_MS[interval]
    while cursor <= end_time_ms:
        if pages >= max_pages:
            raise BinanceHistoricalEvidenceError("Binance mark-price pagination exceeded max_pages")
        page = client.get_mark_price_klines(
            symbol,
            interval,
            start_time_ms=cursor,
            end_time_ms=end_time_ms,
            limit=page_limit,
        )
        pages += 1
        if not page:
            break
        ordered = sorted(page, key=lambda candle: candle.open_time_ms)
        if ordered != page:
            raise BinanceHistoricalEvidenceError("Binance mark-price page was not ascending")
        for candle in ordered:
            if candle.open_time_ms < start_time_ms or candle.open_time_ms > end_time_ms:
                raise BinanceHistoricalEvidenceError("Binance mark-price candle escaped requested range")
            if candle.close_time_ms + 1 != candle.open_time_ms + step:
                raise BinanceHistoricalEvidenceError("Binance mark-price candle has unexpected close boundary")
            existing = collected.get(candle.open_time_ms)
            if existing is not None and existing != candle:
                raise BinanceHistoricalEvidenceError("conflicting duplicate Binance mark-price candle")
            collected[candle.open_time_ms] = candle
        next_cursor = ordered[-1].open_time_ms + step
        if next_cursor <= cursor:
            raise BinanceHistoricalEvidenceError("Binance mark-price pagination did not advance")
        cursor = next_cursor
        if len(ordered) < page_limit:
            break

    candles = tuple(collected[key] for key in sorted(collected))
    times = [candle.open_time_ms for candle in candles]
    _validate_unique_monotonic(times, label="mark-price")
    for left, right in zip(times, times[1:]):
        if right - left != step:
            raise BinanceHistoricalEvidenceError("gap in Binance mark-price history")
    return BinanceMarkPriceBackfillResult(
        symbol=symbol,
        interval=interval,
        requested_start_ms=start_time_ms,
        requested_end_ms=end_time_ms,
        pages_fetched=pages,
        candles=candles,
    )


def backfill_binance_funding_rates(
    client: BinanceHistoricalClient,
    symbol: str,
    *,
    start_time_ms: int,
    end_time_ms: int,
    page_limit: int = 1000,
    max_pages: int = 10_000,
) -> BinanceFundingBackfillResult:
    if not 1 <= page_limit <= 1000:
        raise ValueError("page_limit must be between 1 and 1000")
    _validate_request_range(start_time_ms, end_time_ms, max_pages)

    cursor = start_time_ms
    pages = 0
    collected: dict[tuple[int, str | None], BinanceFundingRate] = {}
    while cursor <= end_time_ms:
        if pages >= max_pages:
            raise BinanceHistoricalEvidenceError("Binance funding pagination exceeded max_pages")
        page = client.get_funding_rates(
            symbol,
            start_time_ms=cursor,
            end_time_ms=end_time_ms,
            limit=page_limit,
        )
        pages += 1
        if not page:
            break
        ordered = sorted(page, key=lambda item: (item.funding_time_ms, item.rate_type or "", item.rate))
        if ordered != page:
            raise BinanceHistoricalEvidenceError("Binance funding page was not ascending")
        for point in ordered:
            if point.funding_time_ms < start_time_ms or point.funding_time_ms > end_time_ms:
                raise BinanceHistoricalEvidenceError("Binance funding point escaped requested range")
            key = (point.funding_time_ms, point.rate_type)
            existing = collected.get(key)
            if existing is not None and existing != point:
                raise BinanceHistoricalEvidenceError("conflicting duplicate Binance funding point")
            collected[key] = point
        next_cursor = max(point.funding_time_ms for point in ordered) + 1
        if next_cursor <= cursor:
            raise BinanceHistoricalEvidenceError("Binance funding pagination did not advance")
        cursor = next_cursor
        if len(ordered) < page_limit:
            break

    points = tuple(collected[key] for key in sorted(collected, key=lambda item: (item[0], item[1] or "")))
    return BinanceFundingBackfillResult(
        symbol=symbol,
        requested_start_ms=start_time_ms,
        requested_end_ms=end_time_ms,
        pages_fetched=pages,
        points=points,
    )


def backfill_binance_open_interest(
    client: BinanceHistoricalClient,
    symbol: str,
    period: str,
    *,
    start_time_ms: int,
    end_time_ms: int,
    now_ms: int,
    page_limit: int = 500,
    max_pages: int = 10_000,
) -> BinanceOpenInterestBackfillResult:
    if not 1 <= page_limit <= 500:
        raise ValueError("page_limit must be between 1 and 500")
    _validate_request_range(start_time_ms, end_time_ms, max_pages)
    if now_ms < 0 or end_time_ms > now_ms:
        raise ValueError("OI request cannot extend beyond now_ms")
    if start_time_ms < now_ms - OPEN_INTEREST_PROJECT_WINDOW_MS:
        raise BinanceHistoricalEvidenceError(
            "Binance documents OI history as latest 1 month; V0.1 conservatively permits only the latest 30 days"
        )

    cursor = start_time_ms
    pages = 0
    collected: dict[int, BinanceOpenInterestPoint] = {}
    while cursor <= end_time_ms:
        if pages >= max_pages:
            raise BinanceHistoricalEvidenceError("Binance open-interest pagination exceeded max_pages")
        page = client.get_open_interest_history(
            symbol,
            period,
            start_time_ms=cursor,
            end_time_ms=end_time_ms,
            limit=page_limit,
        )
        pages += 1
        if not page:
            break
        ordered = sorted(page, key=lambda item: item.timestamp_ms)
        if ordered != page:
            raise BinanceHistoricalEvidenceError("Binance open-interest page was not ascending")
        for point in ordered:
            if point.timestamp_ms < start_time_ms or point.timestamp_ms > end_time_ms:
                raise BinanceHistoricalEvidenceError("Binance open-interest point escaped requested range")
            existing = collected.get(point.timestamp_ms)
            if existing is not None and existing != point:
                raise BinanceHistoricalEvidenceError("conflicting duplicate Binance open-interest point")
            collected[point.timestamp_ms] = point
        next_cursor = ordered[-1].timestamp_ms + 1
        if next_cursor <= cursor:
            raise BinanceHistoricalEvidenceError("Binance open-interest pagination did not advance")
        cursor = next_cursor
        if len(ordered) < page_limit:
            break

    points = tuple(collected[key] for key in sorted(collected))
    _validate_unique_monotonic([point.timestamp_ms for point in points], label="open-interest")
    return BinanceOpenInterestBackfillResult(
        symbol=symbol,
        period=period,
        requested_start_ms=start_time_ms,
        requested_end_ms=end_time_ms,
        pages_fetched=pages,
        points=points,
    )


def to_backtest_funding_points(
    result: BinanceFundingBackfillResult,
    *,
    pionex_symbol: str | None = None,
) -> tuple[FundingPoint, ...]:
    """Convert Binance-native funding evidence for research backtests only.

    Symbol conversion does not change provenance. The caller must retain the
    BinanceFundingBackfillResult/receipt alongside any backtest result.
    """

    target_symbol = pionex_symbol or binance_usdm_to_pionex_perp(result.symbol)
    return tuple(
        FundingPoint(symbol=target_symbol, time_ms=point.funding_time_ms, rate=point.rate)
        for point in result.points
    )
