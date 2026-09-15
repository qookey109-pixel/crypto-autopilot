"""Secret-free page-audit diagnostics for Pionex validation materialization V0.1.

This module does not relax validation. It wraps the existing fail-closed page
validator and adds bounded derived diagnostics when validation rejects a page.
No raw provider payloads are persisted or emitted.
"""
from __future__ import annotations

import math
from typing import Sequence

from ..historical import audit_candles
from ..models import Candle
from . import pionex_validation_materialization_v0_1 as materialization


def _first(values: list[int]) -> int | None:
    return values[0] if values else None


def invalid_candle_reason_diagnostics(page: Sequence[Candle]) -> dict[str, object]:
    """Classify invalid candles without emitting OHLCV provider payload values."""
    nonfinite: list[int] = []
    nonpositive_price: list[int] = []
    negative_volume: list[int] = []
    high_below_ohlc: list[int] = []
    low_above_ohlc: list[int] = []
    inverted_range: list[int] = []

    for candle in page:
        values = (candle.open, candle.high, candle.low, candle.close, candle.volume)
        if not all(math.isfinite(value) for value in values):
            nonfinite.append(candle.time_ms)
            continue
        prices = (candle.open, candle.high, candle.low, candle.close)
        if min(prices) <= 0:
            nonpositive_price.append(candle.time_ms)
        if candle.volume < 0:
            negative_volume.append(candle.time_ms)
        if candle.high < max(candle.open, candle.close, candle.low):
            high_below_ohlc.append(candle.time_ms)
        if candle.low > min(candle.open, candle.close, candle.high):
            low_above_ohlc.append(candle.time_ms)
        if candle.low > candle.high:
            inverted_range.append(candle.time_ms)

    return {
        "invalid_nonfinite_count": len(nonfinite),
        "first_invalid_nonfinite_timestamp_ms": _first(nonfinite),
        "invalid_nonpositive_price_count": len(nonpositive_price),
        "first_invalid_nonpositive_price_timestamp_ms": _first(nonpositive_price),
        "invalid_negative_volume_count": len(negative_volume),
        "first_invalid_negative_volume_timestamp_ms": _first(negative_volume),
        "invalid_high_below_ohlc_count": len(high_below_ohlc),
        "first_invalid_high_below_ohlc_timestamp_ms": _first(high_below_ohlc),
        "invalid_low_above_ohlc_count": len(low_above_ohlc),
        "first_invalid_low_above_ohlc_timestamp_ms": _first(low_above_ohlc),
        "invalid_inverted_range_count": len(inverted_range),
        "first_invalid_inverted_range_timestamp_ms": _first(inverted_range),
    }


def page_audit_diagnostics(
    page: Sequence[Candle], *, interval: str, cursor: int
) -> dict[str, object]:
    audit = audit_candles(tuple(page), interval)
    first_gap = audit.gaps[0] if audit.gaps else None
    first_out_of_order = audit.out_of_order_pairs[0] if audit.out_of_order_pairs else None
    return {
        "page_count": len(page),
        "requested_cursor_ms": cursor,
        "page_first_time_ms": page[0].time_ms if page else None,
        "page_last_time_ms": page[-1].time_ms if page else None,
        "duplicate_timestamp_count": len(audit.duplicate_timestamps),
        "first_duplicate_timestamp_ms": audit.duplicate_timestamps[0]
        if audit.duplicate_timestamps
        else None,
        "out_of_order_pair_count": len(audit.out_of_order_pairs),
        "first_out_of_order_left_ms": first_out_of_order[0]
        if first_out_of_order
        else None,
        "first_out_of_order_right_ms": first_out_of_order[1]
        if first_out_of_order
        else None,
        "gap_count": len(audit.gaps),
        "first_gap_previous_time_ms": first_gap.previous_time_ms if first_gap else None,
        "first_gap_next_time_ms": first_gap.next_time_ms if first_gap else None,
        "first_gap_missing_bars": first_gap.missing_bars if first_gap else None,
        "misaligned_timestamp_count": len(audit.misaligned_timestamps),
        "first_misaligned_timestamp_ms": audit.misaligned_timestamps[0]
        if audit.misaligned_timestamps
        else None,
        "invalid_candle_count": len(audit.invalid_candle_timestamps),
        "first_invalid_candle_timestamp_ms": audit.invalid_candle_timestamps[0]
        if audit.invalid_candle_timestamps
        else None,
        **invalid_candle_reason_diagnostics(page),
    }


def install_page_audit_diagnostics() -> None:
    original = materialization._validate_page
    if getattr(original, "_pionex_page_audit_diagnostics_v0_1", False):
        return

    def wrapped(
        page: Sequence[Candle],
        *,
        interval: str,
        cursor: int,
        limit: int,
        seen: set[int],
    ) -> None:
        try:
            original(page, interval=interval, cursor=cursor, limit=limit, seen=seen)
        except materialization.ValidationMaterializationRejected as exc:
            diagnostics = {
                **exc.diagnostics,
                **page_audit_diagnostics(page, interval=interval, cursor=cursor),
            }
            raise materialization.ValidationMaterializationRejected(
                str(exc), diagnostics=diagnostics
            ) from None

    wrapped._pionex_page_audit_diagnostics_v0_1 = True  # type: ignore[attr-defined]
    materialization._validate_page = wrapped
