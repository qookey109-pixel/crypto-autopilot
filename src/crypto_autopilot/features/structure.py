from __future__ import annotations

from dataclasses import dataclass

from crypto_autopilot.historical import INTERVAL_MS, audit_candles
from crypto_autopilot.models import Candle
from crypto_autopilot.technical import TechnicalDataError, TechnicalSnapshot


@dataclass(frozen=True, slots=True)
class MarketStructureSnapshot:
    """Causally available market-structure evidence for one closed candle."""

    bar_time_ms: int
    available_at_ms: int
    rolling_previous_high: float | None
    rolling_previous_low: float | None
    breakout_above_previous_range: bool | None
    breakdown_below_previous_range: bool | None
    distance_to_previous_high_atr: float | None
    distance_to_previous_low_atr: float | None
    confirmed_swing_high: bool
    confirmed_swing_low: bool
    most_recent_confirmed_swing_high: float | None
    most_recent_confirmed_swing_low: float | None
    market_structure_state: str

    @property
    def ready(self) -> bool:
        return (
            self.rolling_previous_high is not None
            and self.rolling_previous_low is not None
            and self.breakout_above_previous_range is not None
            and self.breakdown_below_previous_range is not None
        )


def _strict_pivot_high(candles: tuple[Candle, ...], pivot: int, left: int, right: int) -> bool:
    value = candles[pivot].high
    neighbors = candles[pivot - left : pivot] + candles[pivot + 1 : pivot + right + 1]
    return bool(neighbors) and all(value > candle.high for candle in neighbors)


def _strict_pivot_low(candles: tuple[Candle, ...], pivot: int, left: int, right: int) -> bool:
    value = candles[pivot].low
    neighbors = candles[pivot - left : pivot] + candles[pivot + 1 : pivot + right + 1]
    return bool(neighbors) and all(value < candle.low for candle in neighbors)


def _structure_state(
    confirmed_highs: list[float], confirmed_lows: list[float]
) -> str:
    if len(confirmed_highs) < 2 or len(confirmed_lows) < 2:
        return "INDETERMINATE"
    higher_high = confirmed_highs[-1] > confirmed_highs[-2]
    higher_low = confirmed_lows[-1] > confirmed_lows[-2]
    lower_high = confirmed_highs[-1] < confirmed_highs[-2]
    lower_low = confirmed_lows[-1] < confirmed_lows[-2]
    if higher_high and higher_low:
        return "UP"
    if lower_high and lower_low:
        return "DOWN"
    return "RANGE"


def build_market_structure_series(
    candles: list[Candle] | tuple[Candle, ...],
    interval: str,
    *,
    rolling_window: int = 20,
    swing_left: int = 2,
    swing_right: int = 2,
    technical_series: list[TechnicalSnapshot] | tuple[TechnicalSnapshot, ...] | None = None,
) -> tuple[MarketStructureSnapshot, ...]:
    """Build a trailing range and delayed swing-confirmation series.

    A pivot at index ``N`` is only inspected at index ``N + swing_right``.
    Therefore no output at index ``N`` or earlier can depend on a future bar.
    Ties are deliberately not classified as pivots: highs/lows must be strict
    relative to every bar in the left and right confirmation windows.
    """

    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported market-structure interval: {interval}")
    if rolling_window < 1:
        raise ValueError("rolling_window must be positive")
    if swing_left < 1 or swing_right < 1:
        raise ValueError("swing confirmation windows must be positive")

    source = tuple(candles)
    audit = audit_candles(source, interval)
    if not audit.ok:
        raise TechnicalDataError(f"Candle audit failed: {audit}")
    if technical_series is not None and len(technical_series) != len(source):
        raise ValueError("technical_series must align one-to-one with candles")

    step_ms = INTERVAL_MS[interval]
    confirmed_highs: list[float] = []
    confirmed_lows: list[float] = []
    latest_high: float | None = None
    latest_low: float | None = None
    output: list[MarketStructureSnapshot] = []

    for index, candle in enumerate(source):
        previous_high = None
        previous_low = None
        if index >= rolling_window:
            previous_window = source[index - rolling_window : index]
            previous_high = max(item.high for item in previous_window)
            previous_low = min(item.low for item in previous_window)

        high_confirmed = False
        low_confirmed = False
        pivot = index - swing_right
        if pivot >= swing_left and pivot + swing_right < len(source):
            high_confirmed = _strict_pivot_high(source, pivot, swing_left, swing_right)
            low_confirmed = _strict_pivot_low(source, pivot, swing_left, swing_right)
            if high_confirmed:
                latest_high = source[pivot].high
                confirmed_highs.append(latest_high)
            if low_confirmed:
                latest_low = source[pivot].low
                confirmed_lows.append(latest_low)

        current_atr = None
        if technical_series is not None:
            current_atr = technical_series[index].atr14

        distance_high = None
        distance_low = None
        if current_atr is not None and current_atr > 0:
            if previous_high is not None:
                distance_high = (candle.close - previous_high) / current_atr
            if previous_low is not None:
                distance_low = (candle.close - previous_low) / current_atr

        breakout = None if previous_high is None else candle.close > previous_high
        breakdown = None if previous_low is None else candle.close < previous_low

        output.append(
            MarketStructureSnapshot(
                bar_time_ms=candle.time_ms,
                available_at_ms=candle.time_ms + step_ms,
                rolling_previous_high=previous_high,
                rolling_previous_low=previous_low,
                breakout_above_previous_range=breakout,
                breakdown_below_previous_range=breakdown,
                distance_to_previous_high_atr=distance_high,
                distance_to_previous_low_atr=distance_low,
                confirmed_swing_high=high_confirmed,
                confirmed_swing_low=low_confirmed,
                most_recent_confirmed_swing_high=latest_high,
                most_recent_confirmed_swing_low=latest_low,
                market_structure_state=_structure_state(confirmed_highs, confirmed_lows),
            )
        )

    return tuple(output)


def latest_market_structure_as_of(
    series: list[MarketStructureSnapshot] | tuple[MarketStructureSnapshot, ...],
    as_of_ms: int,
    *,
    require_ready: bool = False,
) -> MarketStructureSnapshot | None:
    if as_of_ms < 0:
        raise ValueError("as_of_ms cannot be negative")
    available = tuple(item for item in series if item.available_at_ms <= as_of_ms)
    if require_ready:
        available = tuple(item for item in available if item.ready)
    return available[-1] if available else None
