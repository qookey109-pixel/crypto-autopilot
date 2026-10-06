from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from crypto_autopilot.historical import INTERVAL_MS, audit_candles
from crypto_autopilot.models import Candle
from crypto_autopilot.technical import (
    TechnicalDataError,
    TechnicalSnapshot,
    build_technical_series,
)

_HARMONIC_TEMPLATES: Final[dict[str, dict[str, tuple[float, float]]]] = {
    "GARTLEY": {
        "ab_xa": (0.568, 0.668),
        "bc_ab": (0.382, 0.886),
        "cd_bc": (1.272, 1.618),
        "ad_xa": (0.736, 0.836),
    },
    "BAT": {
        "ab_xa": (0.382, 0.500),
        "bc_ab": (0.382, 0.886),
        "cd_bc": (1.618, 2.618),
        "ad_xa": (0.836, 0.936),
    },
    "BUTTERFLY": {
        "ab_xa": (0.736, 0.836),
        "bc_ab": (0.382, 0.886),
        "cd_bc": (1.618, 2.240),
        "ad_xa": (1.220, 1.668),
    },
    "CRAB": {
        "ab_xa": (0.382, 0.618),
        "bc_ab": (0.382, 0.886),
        "cd_bc": (2.240, 3.618),
        "ad_xa": (1.568, 1.668),
    },
}


@dataclass(frozen=True, slots=True)
class DetectorPolicy:
    liquidity_lookback: int = 20
    order_block_lookback: int = 10
    order_block_body_fraction_floor: float = 0.60
    swing_left: int = 2
    swing_right: int = 2

    def __post_init__(self) -> None:
        if self.liquidity_lookback < 2 or self.order_block_lookback < 2:
            raise ValueError("detector lookbacks must be at least 2")
        if not 0.0 < self.order_block_body_fraction_floor <= 1.0:
            raise ValueError("order-block body fraction must be within (0, 1]")
        if self.swing_left < 1 or self.swing_right < 1:
            raise ValueError("swing confirmation windows must be positive")


@dataclass(frozen=True, slots=True)
class ConfirmedPivot:
    index: int
    kind: str
    price: float


@dataclass(frozen=True, slots=True)
class TechnicalPatternSnapshot:
    bar_time_ms: int
    available_at_ms: int
    liquidity_event: str
    fvg_bias: str
    fvg_zone_low: float | None
    fvg_zone_high: float | None
    order_block_bias: str
    order_block_zone_low: float | None
    order_block_zone_high: float | None
    harmonic_prz: str
    harmonic_pattern: str | None
    macd_divergence: str

    def to_confluence_row(self, timeframe: str, structure_state: str) -> dict[str, object]:
        return {
            "timeframe": timeframe,
            "available_at_ms": self.available_at_ms,
            "structure_state": structure_state,
            "liquidity_event": self.liquidity_event,
            "fvg_bias": self.fvg_bias,
            "order_block_bias": self.order_block_bias,
            "harmonic_prz": self.harmonic_prz,
            "macd_divergence": self.macd_divergence,
        }


def _strict_pivot_high(
    candles: tuple[Candle, ...],
    pivot: int,
    left: int,
    right: int,
) -> bool:
    value = candles[pivot].high
    neighbors = candles[pivot - left : pivot] + candles[pivot + 1 : pivot + right + 1]
    return bool(neighbors) and all(value > candle.high for candle in neighbors)


def _strict_pivot_low(
    candles: tuple[Candle, ...],
    pivot: int,
    left: int,
    right: int,
) -> bool:
    value = candles[pivot].low
    neighbors = candles[pivot - left : pivot] + candles[pivot + 1 : pivot + right + 1]
    return bool(neighbors) and all(value < candle.low for candle in neighbors)


def _append_pivot(pivots: list[ConfirmedPivot], candidate: ConfirmedPivot) -> None:
    if not pivots or pivots[-1].kind != candidate.kind:
        pivots.append(candidate)
        return
    previous = pivots[-1]
    more_extreme = (
        candidate.price > previous.price
        if candidate.kind == "HIGH"
        else candidate.price < previous.price
    )
    if more_extreme:
        pivots[-1] = candidate


def _ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0.0:
        return None
    return abs(numerator) / abs(denominator)


def classify_harmonic_pattern(
    pivots: tuple[ConfirmedPivot, ...] | list[ConfirmedPivot],
) -> tuple[str, str] | None:
    """Classify the latest five alternating pivots against preregistered ratios."""

    if len(pivots) < 5:
        return None
    x, a, b, c, d = pivots[-5:]
    kinds = tuple(item.kind for item in (x, a, b, c, d))
    if kinds not in {
        ("LOW", "HIGH", "LOW", "HIGH", "LOW"),
        ("HIGH", "LOW", "HIGH", "LOW", "HIGH"),
    }:
        return None

    xa = a.price - x.price
    ab = b.price - a.price
    bc = c.price - b.price
    cd = d.price - c.price
    ad = d.price - a.price
    ratios = {
        "ab_xa": _ratio(ab, xa),
        "bc_ab": _ratio(bc, ab),
        "cd_bc": _ratio(cd, bc),
        "ad_xa": _ratio(ad, xa),
    }
    if any(value is None for value in ratios.values()):
        return None

    for name, bounds in _HARMONIC_TEMPLATES.items():
        if all(
            bounds[key][0] <= float(ratios[key]) <= bounds[key][1]
            for key in bounds
        ):
            direction = "BULLISH" if d.kind == "LOW" else "BEARISH"
            return name, direction
    return None


def _liquidity_event(
    source: tuple[Candle, ...],
    index: int,
    lookback: int,
) -> str:
    if index < lookback:
        return "NONE"
    previous = source[index - lookback : index]
    previous_high = max(item.high for item in previous)
    previous_low = min(item.low for item in previous)
    candle = source[index]
    high_reclaim = candle.high > previous_high and candle.close <= previous_high
    low_reclaim = candle.low < previous_low and candle.close >= previous_low
    if high_reclaim == low_reclaim:
        return "NONE"
    return "HIGH_SWEEP_RECLAIM" if high_reclaim else "LOW_SWEEP_RECLAIM"


def _fvg(
    source: tuple[Candle, ...],
    index: int,
) -> tuple[str, float | None, float | None]:
    if index < 2:
        return "NONE", None, None
    first = source[index - 2]
    third = source[index]
    if third.low > first.high:
        return "BULLISH", first.high, third.low
    if third.high < first.low:
        return "BEARISH", third.high, first.low
    return "NONE", None, None


def _order_block(
    source: tuple[Candle, ...],
    index: int,
    *,
    lookback: int,
    body_fraction_floor: float,
) -> tuple[str, float | None, float | None]:
    if index < max(lookback, 1):
        return "NONE", None, None
    candle = source[index]
    previous = source[index - 1]
    candle_range = candle.high - candle.low
    if candle_range <= 0.0:
        return "NONE", None, None
    body_fraction = abs(candle.close - candle.open) / candle_range
    if body_fraction < body_fraction_floor:
        return "NONE", None, None

    range_window = source[index - lookback : index]
    previous_high = max(item.high for item in range_window)
    previous_low = min(item.low for item in range_window)
    bullish_displacement = candle.close > candle.open and candle.close > previous_high
    bearish_displacement = candle.close < candle.open and candle.close < previous_low

    if bullish_displacement and previous.close < previous.open:
        return "BULLISH", previous.low, previous.high
    if bearish_displacement and previous.close > previous.open:
        return "BEARISH", previous.low, previous.high
    return "NONE", None, None


def _macd_divergence(
    pivots: list[ConfirmedPivot],
    technical: tuple[TechnicalSnapshot, ...],
) -> str:
    lows = [pivot for pivot in pivots if pivot.kind == "LOW"]
    highs = [pivot for pivot in pivots if pivot.kind == "HIGH"]
    bullish = False
    bearish = False

    if len(lows) >= 2:
        first, second = lows[-2:]
        first_macd = technical[first.index].macd_histogram
        second_macd = technical[second.index].macd_histogram
        bullish = (
            first_macd is not None
            and second_macd is not None
            and second.price < first.price
            and second_macd > first_macd
        )

    if len(highs) >= 2:
        first, second = highs[-2:]
        first_macd = technical[first.index].macd_histogram
        second_macd = technical[second.index].macd_histogram
        bearish = (
            first_macd is not None
            and second_macd is not None
            and second.price > first.price
            and second_macd < first_macd
        )

    if bullish == bearish:
        return "NONE"
    return "BULLISH" if bullish else "BEARISH"


def build_technical_pattern_series(
    candles: list[Candle] | tuple[Candle, ...],
    interval: str,
    *,
    technical_series: list[TechnicalSnapshot] | tuple[TechnicalSnapshot, ...] | None = None,
    policy: DetectorPolicy = DetectorPolicy(),
) -> tuple[TechnicalPatternSnapshot, ...]:
    """Build causal research-only SMC/harmonic/divergence detector evidence."""

    if interval not in INTERVAL_MS:
        raise ValueError(f"unsupported detector interval: {interval}")
    source = tuple(candles)
    audit = audit_candles(source, interval)
    if not audit.ok:
        raise TechnicalDataError(f"Candle audit failed: {audit}")
    if technical_series is None:
        technical = build_technical_series(source, interval)
    else:
        technical = tuple(technical_series)
        if len(technical) != len(source):
            raise ValueError("technical_series must align one-to-one with candles")

    pivots: list[ConfirmedPivot] = []
    output: list[TechnicalPatternSnapshot] = []
    step_ms = INTERVAL_MS[interval]

    for index, candle in enumerate(source):
        pivot_index = index - policy.swing_right
        if pivot_index >= policy.swing_left:
            if _strict_pivot_high(
                source,
                pivot_index,
                policy.swing_left,
                policy.swing_right,
            ):
                _append_pivot(
                    pivots,
                    ConfirmedPivot(pivot_index, "HIGH", source[pivot_index].high),
                )
            if _strict_pivot_low(
                source,
                pivot_index,
                policy.swing_left,
                policy.swing_right,
            ):
                _append_pivot(
                    pivots,
                    ConfirmedPivot(pivot_index, "LOW", source[pivot_index].low),
                )

        liquidity = _liquidity_event(source, index, policy.liquidity_lookback)
        fvg_bias, fvg_low, fvg_high = _fvg(source, index)
        order_bias, order_low, order_high = _order_block(
            source,
            index,
            lookback=policy.order_block_lookback,
            body_fraction_floor=policy.order_block_body_fraction_floor,
        )
        harmonic = classify_harmonic_pattern(pivots)
        harmonic_name = harmonic[0] if harmonic is not None else None
        harmonic_bias = harmonic[1] if harmonic is not None else "NONE"

        output.append(
            TechnicalPatternSnapshot(
                bar_time_ms=candle.time_ms,
                available_at_ms=candle.time_ms + step_ms,
                liquidity_event=liquidity,
                fvg_bias=fvg_bias,
                fvg_zone_low=fvg_low,
                fvg_zone_high=fvg_high,
                order_block_bias=order_bias,
                order_block_zone_low=order_low,
                order_block_zone_high=order_high,
                harmonic_prz=harmonic_bias,
                harmonic_pattern=harmonic_name,
                macd_divergence=_macd_divergence(pivots, technical),
            )
        )

    return tuple(output)


def latest_technical_pattern_as_of(
    series: list[TechnicalPatternSnapshot] | tuple[TechnicalPatternSnapshot, ...],
    as_of_ms: int,
) -> TechnicalPatternSnapshot | None:
    if as_of_ms < 0:
        raise ValueError("as_of_ms cannot be negative")
    available = tuple(item for item in series if item.available_at_ms <= as_of_ms)
    return available[-1] if available else None
