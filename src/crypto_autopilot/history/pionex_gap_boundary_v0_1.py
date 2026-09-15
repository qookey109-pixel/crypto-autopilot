"""Conservative Pionex kline adapter for historical internal gaps.

The validation dataset contract allows verified contiguous Pionex-native history
to be stored as partial coverage. This adapter turns a page containing only an
internal time gap into a provider boundary exception so the existing
materializer can keep already-verified newer pages without interpolation or
cross-provider splicing.

All other audit defects remain untouched and are still rejected by the core
materializer.
"""
from __future__ import annotations

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


class GapBoundaryKlineClient:
    """Convert gap-only provider pages into conservative partial boundaries."""

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
        return page
