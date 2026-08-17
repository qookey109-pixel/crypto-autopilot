from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from .models import Candle

INTERVAL_MS = {
    "15M": 15 * 60 * 1000,
    "60M": 60 * 60 * 1000,
    "4H": 4 * 60 * 60 * 1000,
}


class KlineClient(Protocol):
    def get_klines(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        end_time_ms: int | None = None,
    ) -> list[Candle]: ...


class HistoricalDataError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CandleGap:
    previous_time_ms: int
    next_time_ms: int
    missing_bars: int


@dataclass(frozen=True, slots=True)
class CandleAudit:
    interval: str
    count: int
    duplicate_timestamps: tuple[int, ...]
    out_of_order_pairs: tuple[tuple[int, int], ...]
    gaps: tuple[CandleGap, ...]
    misaligned_timestamps: tuple[int, ...]
    invalid_candle_timestamps: tuple[int, ...]

    @property
    def ok(self) -> bool:
        return not any(
            (
                self.duplicate_timestamps,
                self.out_of_order_pairs,
                self.gaps,
                self.misaligned_timestamps,
                self.invalid_candle_timestamps,
            )
        )


@dataclass(frozen=True, slots=True)
class BackfillResult:
    symbol: str
    interval: str
    requested_start_ms: int
    requested_end_ms: int
    page_limit: int
    pages_fetched: int
    candles: tuple[Candle, ...]
    audit: CandleAudit


def _valid_candle(candle: Candle) -> bool:
    values = (candle.open, candle.high, candle.low, candle.close, candle.volume)
    if not all(math.isfinite(value) for value in values):
        return False
    if min(candle.open, candle.high, candle.low, candle.close) <= 0:
        return False
    if candle.volume < 0:
        return False
    if candle.high < max(candle.open, candle.close, candle.low):
        return False
    if candle.low > min(candle.open, candle.close, candle.high):
        return False
    return candle.low <= candle.high


def audit_candles(candles: list[Candle] | tuple[Candle, ...], interval: str) -> CandleAudit:
    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported audit interval: {interval}")
    step = INTERVAL_MS[interval]
    times = [candle.time_ms for candle in candles]

    counts: dict[int, int] = {}
    for timestamp in times:
        counts[timestamp] = counts.get(timestamp, 0) + 1
    duplicates = tuple(sorted(timestamp for timestamp, count in counts.items() if count > 1))

    out_of_order = tuple(
        (left, right)
        for left, right in zip(times, times[1:])
        if right < left
    )
    misaligned = tuple(sorted({timestamp for timestamp in times if timestamp % step != 0}))
    invalid = tuple(sorted({candle.time_ms for candle in candles if not _valid_candle(candle)}))

    unique_times = sorted(set(times))
    gaps: list[CandleGap] = []
    for left, right in zip(unique_times, unique_times[1:]):
        delta = right - left
        if delta > step:
            missing = max(1, math.ceil(delta / step) - 1)
            gaps.append(CandleGap(left, right, missing))

    return CandleAudit(
        interval=interval,
        count=len(candles),
        duplicate_timestamps=duplicates,
        out_of_order_pairs=out_of_order,
        gaps=tuple(gaps),
        misaligned_timestamps=misaligned,
        invalid_candle_timestamps=invalid,
    )


def backfill_klines(
    client: KlineClient,
    symbol: str,
    interval: str,
    *,
    start_time_ms: int,
    end_time_ms: int,
    page_limit: int = 500,
    max_pages: int = 10_000,
) -> BackfillResult:
    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported historical interval: {interval}")
    if start_time_ms > end_time_ms:
        raise ValueError("start_time_ms must be <= end_time_ms")
    if not 1 <= page_limit <= 500:
        raise ValueError("page_limit must be between 1 and 500")
    if max_pages < 1:
        raise ValueError("max_pages must be positive")

    by_time: dict[int, Candle] = {}
    cursor = end_time_ms
    pages = 0

    while pages < max_pages:
        page = client.get_klines(
            symbol,
            interval,
            limit=page_limit,
            end_time_ms=cursor,
        )
        pages += 1
        if not page:
            break

        eligible = [candle for candle in page if candle.time_ms <= end_time_ms]
        for candle in eligible:
            if candle.time_ms >= start_time_ms:
                by_time[candle.time_ms] = candle

        earliest = min(candle.time_ms for candle in page)
        if earliest <= start_time_ms:
            break

        next_cursor = earliest - 1
        if next_cursor >= cursor:
            raise HistoricalDataError("Pionex pagination cursor did not move backwards")
        cursor = next_cursor
    else:
        raise HistoricalDataError(f"Historical backfill exceeded max_pages={max_pages}")

    candles = tuple(sorted(by_time.values(), key=lambda candle: candle.time_ms))
    return BackfillResult(
        symbol=symbol,
        interval=interval,
        requested_start_ms=start_time_ms,
        requested_end_ms=end_time_ms,
        page_limit=page_limit,
        pages_fetched=pages,
        candles=candles,
        audit=audit_candles(candles, interval),
    )


def backfill_payload(result: BackfillResult) -> dict[str, object]:
    return {
        "schema_version": 1,
        "source": "pionex_futures_klines",
        "symbol": result.symbol,
        "interval": result.interval,
        "requested_start_ms": result.requested_start_ms,
        "requested_end_ms": result.requested_end_ms,
        "page_limit": result.page_limit,
        "pages_fetched": result.pages_fetched,
        "audit": {
            "ok": result.audit.ok,
            "count": result.audit.count,
            "duplicate_timestamps": list(result.audit.duplicate_timestamps),
            "out_of_order_pairs": [list(pair) for pair in result.audit.out_of_order_pairs],
            "gaps": [asdict(gap) for gap in result.audit.gaps],
            "misaligned_timestamps": list(result.audit.misaligned_timestamps),
            "invalid_candle_timestamps": list(result.audit.invalid_candle_timestamps),
        },
        "candles": [asdict(candle) for candle in result.candles],
    }


def write_backfill_json(path: str | Path, result: BackfillResult) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(backfill_payload(result), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
