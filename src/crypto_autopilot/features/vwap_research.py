from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Sequence

from crypto_autopilot.historical import INTERVAL_MS, audit_candles
from crypto_autopilot.models import Candle


DAY_MS = 24 * 60 * 60 * 1000
TRAILING_WINDOWS_MS = {
    "trailing_7d": 7 * DAY_MS,
    "trailing_30d": 30 * DAY_MS,
}


class VwapResearchDataError(RuntimeError):
    """Raised when the offline VWAP input is not safe for causal research."""


@dataclass(frozen=True, slots=True)
class VwapResearchValue:
    bar_count: int
    vwap: float | None
    distance_fraction: float | None
    weighted_stddev: float | None
    stddev_position: float | None
    ready: bool
    reason: str | None


@dataclass(frozen=True, slots=True)
class VwapResearchSnapshot:
    provider: str
    instrument: str
    volume_unit: str
    bar_time_ms: int
    available_at_ms: int
    day: VwapResearchValue
    week: VwapResearchValue
    month: VwapResearchValue
    trailing_7d: VwapResearchValue
    trailing_30d: VwapResearchValue


def _nonempty(value: str, name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must be non-empty")
    return normalized


def _utc_anchor_ms(time_ms: int, anchor: str) -> int:
    instant = datetime.fromtimestamp(time_ms / 1000.0, tz=UTC)
    midnight = instant.replace(hour=0, minute=0, second=0, microsecond=0)
    if anchor == "day":
        start = midnight
    elif anchor == "week":
        start = midnight - timedelta(days=midnight.weekday())
    elif anchor == "month":
        start = midnight.replace(day=1)
    else:
        raise ValueError(f"Unsupported VWAP anchor: {anchor}")
    return int(start.timestamp() * 1000)


def _not_ready(bar_count: int, reason: str) -> VwapResearchValue:
    return VwapResearchValue(
        bar_count=bar_count,
        vwap=None,
        distance_fraction=None,
        weighted_stddev=None,
        stddev_position=None,
        ready=False,
        reason=reason,
    )


def _window_value(
    candles: Sequence[Candle],
    *,
    current_close: float,
) -> VwapResearchValue:
    if not candles:
        return _not_ready(0, "INSUFFICIENT_HISTORY")

    total_volume = sum(candle.volume for candle in candles)
    if total_volume <= 0:
        return _not_ready(len(candles), "ZERO_VOLUME")

    prices = tuple(
        (candle.high + candle.low + candle.close) / 3.0
        for candle in candles
    )
    vwap = sum(
        price * candle.volume
        for price, candle in zip(prices, candles)
    ) / total_volume
    distance_fraction = (current_close - vwap) / vwap

    variance = sum(
        candle.volume * (price - vwap) ** 2
        for price, candle in zip(prices, candles)
    ) / total_volume
    weighted_stddev = math.sqrt(max(0.0, variance))
    if weighted_stddev == 0:
        return VwapResearchValue(
            bar_count=len(candles),
            vwap=vwap,
            distance_fraction=distance_fraction,
            weighted_stddev=0.0,
            stddev_position=None,
            ready=False,
            reason="ZERO_VARIANCE",
        )

    return VwapResearchValue(
        bar_count=len(candles),
        vwap=vwap,
        distance_fraction=distance_fraction,
        weighted_stddev=weighted_stddev,
        stddev_position=(current_close - vwap) / weighted_stddev,
        ready=True,
        reason=None,
    )


def build_vwap_research_series(
    candles: Sequence[Candle],
    interval: str,
    *,
    provider: str,
    instrument: str,
    volume_unit: str,
) -> tuple[VwapResearchSnapshot, ...]:
    """Build causal offline VWAP research features without touching model inputs.

    Anchored windows are assigned by the source bar's UTC open timestamp. Every
    emitted snapshot is available only at the source bar close. Trailing
    windows contain bars whose close is inside (T-window, T] and stay not-ready
    until the full interval-aligned window is present.
    """

    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported VWAP research interval: {interval}")

    provider_name = _nonempty(provider, "provider")
    instrument_name = _nonempty(instrument, "instrument")
    volume_name = _nonempty(volume_unit, "volume_unit")

    interval_ms = INTERVAL_MS[interval]
    for name, window_ms in TRAILING_WINDOWS_MS.items():
        if window_ms % interval_ms != 0:
            raise ValueError(
                f"{interval} does not divide {name} exactly; partial-bar "
                "trailing windows are not supported"
            )

    source = tuple(candles)
    audit = audit_candles(source, interval)
    if not audit.ok:
        raise VwapResearchDataError(f"Candle audit failed: {audit}")
    if not source:
        return ()

    available_times = tuple(candle.time_ms + interval_ms for candle in source)
    anchor_starts = {
        anchor: tuple(_utc_anchor_ms(candle.time_ms, anchor) for candle in source)
        for anchor in ("day", "week", "month")
    }

    output: list[VwapResearchSnapshot] = []
    anchor_first_index = {"day": 0, "week": 0, "month": 0}

    for index, candle in enumerate(source):
        anchored: dict[str, VwapResearchValue] = {}
        for anchor in ("day", "week", "month"):
            if index > 0 and anchor_starts[anchor][index] != anchor_starts[anchor][index - 1]:
                anchor_first_index[anchor] = index
            start = anchor_first_index[anchor]
            anchored[anchor] = _window_value(
                source[start : index + 1],
                current_close=candle.close,
            )

        trailing: dict[str, VwapResearchValue] = {}
        current_available_at = available_times[index]
        for name, window_ms in TRAILING_WINDOWS_MS.items():
            lower_bound = current_available_at - window_ms
            start = bisect_right(available_times, lower_bound, 0, index + 1)
            window = source[start : index + 1]
            expected_bars = window_ms // interval_ms
            if len(window) != expected_bars:
                trailing[name] = _not_ready(len(window), "INSUFFICIENT_HISTORY")
            else:
                trailing[name] = _window_value(
                    window,
                    current_close=candle.close,
                )

        output.append(
            VwapResearchSnapshot(
                provider=provider_name,
                instrument=instrument_name,
                volume_unit=volume_name,
                bar_time_ms=candle.time_ms,
                available_at_ms=current_available_at,
                day=anchored["day"],
                week=anchored["week"],
                month=anchored["month"],
                trailing_7d=trailing["trailing_7d"],
                trailing_30d=trailing["trailing_30d"],
            )
        )

    return tuple(output)
