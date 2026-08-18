from __future__ import annotations

from dataclasses import asdict, dataclass

from .historical import INTERVAL_MS, audit_candles
from .models import Candle


class TechnicalDataError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class TechnicalSnapshot:
    """Raw technical values for one candle, usable only after that candle closes."""

    bar_time_ms: int
    available_at_ms: int
    close: float
    volume: float
    ema20: float | None
    ema50: float | None
    ema20_slope: float | None
    atr14: float | None
    volume_sma20: float | None
    volume_ratio: float | None
    previous_high: float | None
    extension_from_ema20_atr: float | None

    @property
    def ready(self) -> bool:
        return all(
            value is not None
            for value in (
                self.ema20,
                self.ema50,
                self.ema20_slope,
                self.atr14,
                self.volume_sma20,
                self.volume_ratio,
                self.previous_high,
            )
        )


def _ema(values: tuple[float, ...], period: int) -> tuple[float | None, ...]:
    if period < 1:
        raise ValueError("period must be positive")
    output: list[float | None] = [None] * len(values)
    if len(values) < period:
        return tuple(output)

    seed = sum(values[:period]) / period
    output[period - 1] = seed
    alpha = 2.0 / (period + 1.0)
    previous = seed
    for index in range(period, len(values)):
        previous = (values[index] - previous) * alpha + previous
        output[index] = previous
    return tuple(output)


def _rolling_sma(values: tuple[float, ...], period: int) -> tuple[float | None, ...]:
    if period < 1:
        raise ValueError("period must be positive")
    output: list[float | None] = [None] * len(values)
    if len(values) < period:
        return tuple(output)

    running = sum(values[:period])
    output[period - 1] = running / period
    for index in range(period, len(values)):
        running += values[index] - values[index - period]
        output[index] = running / period
    return tuple(output)


def _true_ranges(candles: tuple[Candle, ...]) -> tuple[float, ...]:
    values: list[float] = []
    for index, candle in enumerate(candles):
        if index == 0:
            values.append(candle.high - candle.low)
            continue
        previous_close = candles[index - 1].close
        values.append(
            max(
                candle.high - candle.low,
                abs(candle.high - previous_close),
                abs(candle.low - previous_close),
            )
        )
    return tuple(values)


def _wilder(values: tuple[float, ...], period: int) -> tuple[float | None, ...]:
    if period < 1:
        raise ValueError("period must be positive")
    output: list[float | None] = [None] * len(values)
    if len(values) < period:
        return tuple(output)

    previous = sum(values[:period]) / period
    output[period - 1] = previous
    for index in range(period, len(values)):
        previous = (previous * (period - 1) + values[index]) / period
        output[index] = previous
    return tuple(output)


def build_technical_series(
    candles: list[Candle] | tuple[Candle, ...],
    interval: str,
) -> tuple[TechnicalSnapshot, ...]:
    """Build deterministic raw indicators from audited candles only.

    No missing candle is filled or repaired. `available_at_ms` is the earliest
    timestamp at which the corresponding closed-bar values may be consumed.
    """

    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported technical interval: {interval}")

    source = tuple(candles)
    audit = audit_candles(source, interval)
    if not audit.ok:
        raise TechnicalDataError(f"Candle audit failed: {asdict(audit)}")
    if not source:
        return ()

    closes = tuple(candle.close for candle in source)
    volumes = tuple(candle.volume for candle in source)
    ema20 = _ema(closes, 20)
    ema50 = _ema(closes, 50)
    atr14 = _wilder(_true_ranges(source), 14)
    volume_sma20 = _rolling_sma(volumes, 20)
    interval_ms = INTERVAL_MS[interval]

    output: list[TechnicalSnapshot] = []
    for index, candle in enumerate(source):
        slope = None
        if index > 0 and ema20[index] is not None and ema20[index - 1] is not None:
            slope = ema20[index] - ema20[index - 1]  # type: ignore[operator]

        volume_ratio = None
        current_volume_sma = volume_sma20[index]
        if current_volume_sma is not None and current_volume_sma > 0:
            volume_ratio = candle.volume / current_volume_sma

        extension = None
        current_ema20 = ema20[index]
        current_atr14 = atr14[index]
        if current_ema20 is not None and current_atr14 is not None and current_atr14 > 0:
            extension = (candle.close - current_ema20) / current_atr14

        output.append(
            TechnicalSnapshot(
                bar_time_ms=candle.time_ms,
                available_at_ms=candle.time_ms + interval_ms,
                close=candle.close,
                volume=candle.volume,
                ema20=current_ema20,
                ema50=ema50[index],
                ema20_slope=slope,
                atr14=current_atr14,
                volume_sma20=current_volume_sma,
                volume_ratio=volume_ratio,
                previous_high=source[index - 1].high if index > 0 else None,
                extension_from_ema20_atr=extension,
            )
        )
    return tuple(output)


def closed_snapshots_as_of(
    series: list[TechnicalSnapshot] | tuple[TechnicalSnapshot, ...],
    as_of_ms: int,
) -> tuple[TechnicalSnapshot, ...]:
    if as_of_ms < 0:
        raise ValueError("as_of_ms cannot be negative")
    return tuple(snapshot for snapshot in series if snapshot.available_at_ms <= as_of_ms)


def latest_closed_snapshot(
    series: list[TechnicalSnapshot] | tuple[TechnicalSnapshot, ...],
    as_of_ms: int,
    *,
    require_ready: bool = False,
) -> TechnicalSnapshot | None:
    available = closed_snapshots_as_of(series, as_of_ms)
    if require_ready:
        available = tuple(snapshot for snapshot in available if snapshot.ready)
    return available[-1] if available else None
