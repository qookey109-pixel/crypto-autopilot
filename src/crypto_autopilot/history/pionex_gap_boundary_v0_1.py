"""Conservative Pionex kline adapter for historical provider-quality boundaries.

The validation dataset contract allows verified contiguous Pionex-native history
to be stored as partial coverage. This adapter converts two narrowly-defined
historical provider defects into explicit boundaries without interpolation or
cross-provider splicing:

* a page containing only an internal time gap; or
* finite, positive-price candles whose only validity defect is that high/low
  fails to contain the candle's OHLC values.

For the second case, the adapter keeps only the clean contiguous suffix after
the most recent invalid candle. A subsequent boundary probe that lands on the
invalid candle raises a typed exception so the existing materializer stops at
that provider boundary while preserving already-verified newer history.

All other audit defects remain untouched and are still rejected by the core
materializer.
"""
from __future__ import annotations

import math
from typing import Protocol

from ..historical import audit_candles
from ..models import Candle


class KlineDelegate(Protocol):
    def get_klines(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        end_time_ms: int | None = None,
    ) -> list[Candle]: ...


class PionexInternalGapBoundary(RuntimeError):
    """A provider page has a historical time gap but no other audit defect."""


class PionexInvalidCandleBoundary(RuntimeError):
    """A provider page reaches a bounds-only invalid historical candle."""


def _bounds_only_invalid(candle: Candle) -> bool:
    values = (candle.open, candle.high, candle.low, candle.close, candle.volume)
    if not all(math.isfinite(value) for value in values):
        return False
    if min(candle.open, candle.high, candle.low, candle.close) <= 0:
        return False
    if candle.volume < 0:
        return False
    if candle.low > candle.high:
        return False
    return (
        candle.high < max(candle.open, candle.close, candle.low)
        or candle.low > min(candle.open, candle.close, candle.high)
    )


class GapBoundaryKlineClient:
    """Convert approved provider defects into conservative partial boundaries."""

    def __init__(self, delegate: KlineDelegate) -> None:
        self.delegate = delegate

    def get_klines(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        end_time_ms: int | None = None,
    ) -> list[Candle]:
        page = self.delegate.get_klines(
            symbol,
            interval,
            limit=limit,
            end_time_ms=end_time_ms,
        )
        if not page:
            return page

        audit = audit_candles(tuple(page), interval)
        non_gap_defect = any(
            (
                audit.duplicate_timestamps,
                audit.out_of_order_pairs,
                audit.misaligned_timestamps,
                audit.invalid_candle_timestamps,
            )
        )
        if audit.gaps and not non_gap_defect:
            gap = audit.gaps[-1]
            raise PionexInternalGapBoundary(
                "provider page contains internal historical gap "
                f"previous={gap.previous_time_ms} next={gap.next_time_ms} "
                f"missing_bars={gap.missing_bars}"
            )

        time_structure_defect = any(
            (
                audit.duplicate_timestamps,
                audit.out_of_order_pairs,
                audit.gaps,
                audit.misaligned_timestamps,
            )
        )
        if audit.invalid_candle_timestamps and not time_structure_defect:
            invalid_times = set(audit.invalid_candle_timestamps)
            invalid_rows = [row for row in page if row.time_ms in invalid_times]
            if invalid_rows and all(_bounds_only_invalid(row) for row in invalid_rows):
                boundary_time_ms = max(invalid_times)
                suffix = [row for row in page if row.time_ms > boundary_time_ms]
                if not suffix:
                    raise PionexInvalidCandleBoundary(
                        "provider page reached bounds-only invalid historical candle "
                        f"boundary_time_ms={boundary_time_ms}"
                    )
                if audit_candles(tuple(suffix), interval).ok:
                    return suffix

        return page
