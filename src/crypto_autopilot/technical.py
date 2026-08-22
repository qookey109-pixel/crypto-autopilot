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
    ema200: float | None = None
    ema20_ema50_distance_fraction: float | None = None
    ema50_ema200_distance_fraction: float | None = None
    ema20_slope_atr: float | None = None
    rsi14: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    atr14_fraction: float | None = None
    bollinger_mid: float | None = None
    bollinger_upper: float | None = None
    bollinger_lower: float | None = None
    bollinger_bandwidth: float | None = None
    bollinger_position: float | None = None

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

    @property
    def ready_v0_2(self) -> bool:
        """Whether the full V0.2 indicator set is genuinely warmed up."""
        return self.ready and all(
            value is not None
            for value in (
                self.ema200,
                self.ema20_ema50_distance_fraction,
                self.ema50_ema200_distance_fraction,
                self.ema20_slope_atr,
                self.rsi14,
                self.macd,
                self.macd_signal,
                self.macd_histogram,
                self.atr14_fraction,
                self.bollinger_mid,
                self.bollinger_upper,
                self.bollinger_lower,
                self.bollinger_bandwidth,
                self.bollinger_position,
            )
        )

    @property
    def normalized_features(self) -> dict[str, float | None]:
        """Feature-only view for downstream research consumers.

        This intentionally contains no strategy or order decision fields.
        """
        return {
            "ema20_ema50_distance_fraction": self.ema20_ema50_distance_fraction,
            "ema50_ema200_distance_fraction": self.ema50_ema200_distance_fraction,
            "ema20_slope_atr": self.ema20_slope_atr,
            "atr14_fraction": self.atr14_fraction,
            "rsi14": self.rsi14,
            "macd_histogram": self.macd_histogram,
            "bollinger_bandwidth": self.bollinger_bandwidth,
            "bollinger_position": self.bollinger_position,
            "volume_ratio": self.volume_ratio,
        }


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


def _rolling_population_stddev(
    values: tuple[float, ...], period: int
) -> tuple[float | None, ...]:
    if period < 1:
        raise ValueError("period must be positive")
    output: list[float | None] = [None] * len(values)
    if len(values) < period:
        return tuple(output)

    for index in range(period - 1, len(values)):
        window = values[index - period + 1 : index + 1]
        mean = sum(window) / period
        variance = sum((value - mean) ** 2 for value in window) / period
        output[index] = variance**0.5
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


def _rsi_wilder(values: tuple[float, ...], period: int) -> tuple[float | None, ...]:
    """Return RSI using Wilder's smoothed gains/losses.

    The first value is available after ``period`` price changes, therefore at
    candle index ``period``. A flat series is defined as RSI 50.
    """
    if period < 1:
        raise ValueError("period must be positive")
    output: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return tuple(output)

    gains: list[float] = []
    losses: list[float] = []
    for index in range(1, period + 1):
        change = values[index] - values[index - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    average_gain = sum(gains) / period
    average_loss = sum(losses) / period

    def calculate(gain: float, loss: float) -> float:
        if loss == 0.0:
            return 50.0 if gain == 0.0 else 100.0
        relative_strength = gain / loss
        return 100.0 - (100.0 / (1.0 + relative_strength))

    output[period] = calculate(average_gain, average_loss)
    for index in range(period + 1, len(values)):
        change = values[index] - values[index - 1]
        gain = max(change, 0.0)
        loss = max(-change, 0.0)
        average_gain = (average_gain * (period - 1) + gain) / period
        average_loss = (average_loss * (period - 1) + loss) / period
        output[index] = calculate(average_gain, average_loss)
    return tuple(output)


def _macd_series(
    values: tuple[float, ...],
    *,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[tuple[float | None, ...], tuple[float | None, ...], tuple[float | None, ...]]:
    if not 1 <= fast_period <= slow_period:
        raise ValueError("MACD periods must satisfy 1 <= fast_period <= slow_period")
    fast = _ema(values, fast_period)
    slow = _ema(values, slow_period)
    macd: list[float | None] = [None] * len(values)
    for index, (fast_value, slow_value) in enumerate(zip(fast, slow)):
        if fast_value is not None and slow_value is not None:
            macd[index] = fast_value - slow_value

    signal_values = tuple(value for value in macd if value is not None)
    signal_ema = _ema(signal_values, signal_period)
    signal: list[float | None] = [None] * len(values)
    signal_offset = next((index for index, value in enumerate(macd) if value is not None), len(values))
    for offset, value in enumerate(signal_ema):
        if signal_offset + offset < len(signal):
            signal[signal_offset + offset] = value

    histogram: list[float | None] = [None] * len(values)
    for index, (macd_value, signal_value) in enumerate(zip(macd, signal)):
        if macd_value is not None and signal_value is not None:
            histogram[index] = macd_value - signal_value
    return tuple(macd), tuple(signal), tuple(histogram)


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
    ema200 = _ema(closes, 200)
    rsi14 = _rsi_wilder(closes, 14)
    macd, macd_signal, macd_histogram = _macd_series(closes)
    bollinger_mid = _rolling_sma(closes, 20)
    bollinger_stddev = _rolling_population_stddev(closes, 20)
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

        distance_20_50 = None
        current_ema50 = ema50[index]
        if current_ema20 is not None and current_ema50 is not None and candle.close != 0:
            distance_20_50 = (current_ema20 - current_ema50) / candle.close

        distance_50_200 = None
        current_ema200 = ema200[index]
        if current_ema50 is not None and current_ema200 is not None and candle.close != 0:
            distance_50_200 = (current_ema50 - current_ema200) / candle.close

        slope_atr = None
        if slope is not None and current_atr14 is not None and current_atr14 > 0:
            slope_atr = slope / current_atr14

        atr_fraction = None
        if current_atr14 is not None and candle.close != 0:
            atr_fraction = current_atr14 / candle.close

        current_bollinger_mid = bollinger_mid[index]
        current_bollinger_stddev = bollinger_stddev[index]
        bollinger_upper = None
        bollinger_lower = None
        bollinger_bandwidth = None
        bollinger_position = None
        if current_bollinger_mid is not None and current_bollinger_stddev is not None:
            bollinger_upper = current_bollinger_mid + 2.0 * current_bollinger_stddev
            bollinger_lower = current_bollinger_mid - 2.0 * current_bollinger_stddev
            if current_bollinger_mid != 0:
                bollinger_bandwidth = (bollinger_upper - bollinger_lower) / current_bollinger_mid
            band_range = bollinger_upper - bollinger_lower
            if band_range != 0:
                bollinger_position = (candle.close - bollinger_lower) / band_range

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
                ema200=current_ema200,
                ema20_ema50_distance_fraction=distance_20_50,
                ema50_ema200_distance_fraction=distance_50_200,
                ema20_slope_atr=slope_atr,
                rsi14=rsi14[index],
                macd=macd[index],
                macd_signal=macd_signal[index],
                macd_histogram=macd_histogram[index],
                atr14_fraction=atr_fraction,
                bollinger_mid=current_bollinger_mid,
                bollinger_upper=bollinger_upper,
                bollinger_lower=bollinger_lower,
                bollinger_bandwidth=bollinger_bandwidth,
                bollinger_position=bollinger_position,
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
