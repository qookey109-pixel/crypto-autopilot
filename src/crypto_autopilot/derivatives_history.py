from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

from .backtest import FundingPoint


_INTERVAL_MS = {
    "1M": 60_000,
    "5M": 300_000,
    "15M": 900_000,
    "30M": 1_800_000,
    "60M": 3_600_000,
    "4H": 14_400_000,
    "8H": 28_800_000,
    "12H": 43_200_000,
    "1D": 86_400_000,
    "1W": 604_800_000,
}


class DerivativesHistoryEvidenceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class FundingRateRecord:
    symbol: str
    funding_time_ms: int
    rate: float
    retrieved_at_ms: int

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.funding_time_ms < 0 or self.retrieved_at_ms < 0:
            raise ValueError("timestamps cannot be negative")
        if not math.isfinite(self.rate):
            raise ValueError("funding rate must be finite")


@dataclass(frozen=True, slots=True)
class MarkPriceCandle:
    symbol: str
    interval: str
    time_ms: int
    open: float
    high: float
    low: float
    close: float
    retrieved_at_ms: int

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.interval not in _INTERVAL_MS:
            raise ValueError(f"unsupported mark-price interval: {self.interval}")
        if self.time_ms < 0 or self.retrieved_at_ms < 0:
            raise ValueError("timestamps cannot be negative")
        values = (self.open, self.high, self.low, self.close)
        if not all(math.isfinite(value) and value > 0 for value in values):
            raise ValueError("mark-price OHLC values must be finite and positive")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("invalid mark-price low")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("invalid mark-price high")

    @property
    def available_at_ms(self) -> int:
        return self.time_ms + _INTERVAL_MS[self.interval]


@dataclass(frozen=True, slots=True)
class OpenInterestSnapshot:
    symbol: str
    open_interest: float
    observed_at_ms: int

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.observed_at_ms < 0:
            raise ValueError("observed_at_ms cannot be negative")
        if not math.isfinite(self.open_interest) or self.open_interest < 0:
            raise ValueError("open_interest must be finite and non-negative")


class FundingRateClient(Protocol):
    def get_funding_rates(
        self,
        symbol: str,
        *,
        limit: int = 500,
        end_time_ms: int | None = None,
    ) -> list[FundingRateRecord]: ...


def audit_funding_rate_records(
    records: list[FundingRateRecord] | tuple[FundingRateRecord, ...],
    *,
    symbol: str | None = None,
) -> tuple[FundingRateRecord, ...]:
    ordered = tuple(sorted(records, key=lambda item: (item.funding_time_ms, item.symbol, item.rate)))
    by_time: dict[tuple[str, int], FundingRateRecord] = {}
    for record in ordered:
        if symbol is not None and record.symbol != symbol:
            raise DerivativesHistoryEvidenceError(
                f"unexpected funding symbol: expected {symbol}, got {record.symbol}"
            )
        key = (record.symbol, record.funding_time_ms)
        existing = by_time.get(key)
        if existing is None:
            by_time[key] = record
            continue
        if existing.rate != record.rate:
            raise DerivativesHistoryEvidenceError(
                f"conflicting funding rate at {record.symbol} {record.funding_time_ms}"
            )
        # Identical historical observations may be returned on adjacent inclusive pages.
        # Keep the earliest retrieval authority deterministically.
        if record.retrieved_at_ms < existing.retrieved_at_ms:
            by_time[key] = record
    return tuple(sorted(by_time.values(), key=lambda item: (item.funding_time_ms, item.symbol)))


def fetch_funding_rate_history(
    client: FundingRateClient,
    *,
    symbol: str,
    start_time_ms: int,
    end_time_ms: int,
    page_limit: int = 500,
    max_pages: int | None = None,
) -> tuple[FundingRateRecord, ...]:
    """Backward-page Pionex historical funding rates over an explicit range.

    The provider endpoint is inclusive/"before this time" oriented, so the next
    request advances with `earliest_funding_time - 1 ms`. No fixed funding
    cadence is assumed because provider funding intervals can vary.
    """

    if not symbol.strip():
        raise ValueError("symbol is required")
    if start_time_ms < 0 or end_time_ms < 0 or start_time_ms > end_time_ms:
        raise ValueError("invalid funding history range")
    if not 1 <= page_limit <= 500:
        raise ValueError("page_limit must be between 1 and 500")
    if max_pages is not None and max_pages <= 0:
        raise ValueError("max_pages must be positive when supplied")

    cursor = end_time_ms
    pages = 0
    collected: list[FundingRateRecord] = []

    while cursor >= start_time_ms:
        if max_pages is not None and pages >= max_pages:
            raise DerivativesHistoryEvidenceError("funding history max_pages limit reached")
        page = tuple(client.get_funding_rates(symbol, limit=page_limit, end_time_ms=cursor))
        pages += 1
        if not page:
            break
        audited_page = audit_funding_rate_records(page, symbol=symbol)
        if not audited_page:
            break
        if any(record.funding_time_ms > cursor for record in audited_page):
            raise DerivativesHistoryEvidenceError("funding page returned data after requested cursor")

        collected.extend(
            record
            for record in audited_page
            if start_time_ms <= record.funding_time_ms <= end_time_ms
        )
        earliest = min(record.funding_time_ms for record in audited_page)
        if earliest <= start_time_ms:
            break
        next_cursor = earliest - 1
        if next_cursor >= cursor:
            raise DerivativesHistoryEvidenceError("funding pagination cursor did not move backward")
        cursor = next_cursor

    return audit_funding_rate_records(collected, symbol=symbol)


def funding_points_from_records(
    records: list[FundingRateRecord] | tuple[FundingRateRecord, ...],
) -> tuple[FundingPoint, ...]:
    audited = audit_funding_rate_records(records)
    return tuple(
        FundingPoint(symbol=record.symbol, time_ms=record.funding_time_ms, rate=record.rate)
        for record in audited
    )


def audit_mark_price_candles(
    candles: list[MarkPriceCandle] | tuple[MarkPriceCandle, ...],
    *,
    symbol: str | None = None,
    interval: str | None = None,
    require_contiguous: bool = True,
) -> tuple[MarkPriceCandle, ...]:
    ordered = tuple(sorted(candles, key=lambda item: item.time_ms))
    seen: set[int] = set()
    previous: int | None = None
    expected_step: int | None = None

    if interval is not None:
        if interval not in _INTERVAL_MS:
            raise ValueError(f"unsupported mark-price interval: {interval}")
        expected_step = _INTERVAL_MS[interval]

    for candle in ordered:
        if symbol is not None and candle.symbol != symbol:
            raise DerivativesHistoryEvidenceError(
                f"unexpected mark-price symbol: expected {symbol}, got {candle.symbol}"
            )
        if interval is not None and candle.interval != interval:
            raise DerivativesHistoryEvidenceError(
                f"unexpected mark-price interval: expected {interval}, got {candle.interval}"
            )
        if candle.time_ms in seen:
            raise DerivativesHistoryEvidenceError("duplicate mark-price candle timestamp")
        seen.add(candle.time_ms)
        step = _INTERVAL_MS[candle.interval]
        if expected_step is None:
            expected_step = step
        elif step != expected_step:
            raise DerivativesHistoryEvidenceError("mixed mark-price intervals are not allowed")
        if previous is not None and require_contiguous and candle.time_ms - previous != expected_step:
            raise DerivativesHistoryEvidenceError("mark-price candle gap detected")
        previous = candle.time_ms
    return ordered


def mark_price_candles_available_as_of(
    candles: list[MarkPriceCandle] | tuple[MarkPriceCandle, ...],
    *,
    as_of_ms: int,
) -> tuple[MarkPriceCandle, ...]:
    if as_of_ms < 0:
        raise ValueError("as_of_ms cannot be negative")
    audited = audit_mark_price_candles(candles)
    return tuple(candle for candle in audited if candle.available_at_ms <= as_of_ms)


class OpenInterestIndex:
    """Point-in-time OI snapshots only; never backprojects a later observation."""

    def __init__(self, snapshots: list[OpenInterestSnapshot] | tuple[OpenInterestSnapshot, ...]) -> None:
        grouped: dict[tuple[str, int], OpenInterestSnapshot] = {}
        for snapshot in snapshots:
            key = (snapshot.symbol, snapshot.observed_at_ms)
            existing = grouped.get(key)
            if existing is not None and existing.open_interest != snapshot.open_interest:
                raise DerivativesHistoryEvidenceError(
                    f"conflicting open-interest observation for {snapshot.symbol} at {snapshot.observed_at_ms}"
                )
            grouped[key] = snapshot
        self.snapshots = tuple(
            sorted(grouped.values(), key=lambda item: (item.observed_at_ms, item.symbol))
        )

    def latest_at_or_before(
        self,
        *,
        symbol: str,
        as_of_ms: int,
        max_age_ms: int,
    ) -> OpenInterestSnapshot:
        if not symbol.strip():
            raise ValueError("symbol is required")
        if as_of_ms < 0 or max_age_ms <= 0:
            raise ValueError("invalid OI query")
        eligible = [
            item
            for item in self.snapshots
            if item.symbol == symbol
            and item.observed_at_ms <= as_of_ms
            and as_of_ms - item.observed_at_ms <= max_age_ms
        ]
        if not eligible:
            raise DerivativesHistoryEvidenceError(
                "no non-future fresh open-interest snapshot was available at the requested timestamp"
            )
        return max(eligible, key=lambda item: item.observed_at_ms)
