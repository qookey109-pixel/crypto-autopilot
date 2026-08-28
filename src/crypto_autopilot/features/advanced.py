from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from crypto_autopilot.historical import INTERVAL_MS, audit_candles
from crypto_autopilot.models import Candle
from crypto_autopilot.technical import TechnicalDataError, TechnicalSnapshot, build_technical_series


@dataclass(frozen=True, slots=True)
class AdvancedTechnicalSnapshot:
    """Causal market-state features available only after the source bar closes."""

    bar_time_ms: int
    available_at_ms: int
    adx14: float | None
    plus_di14: float | None
    minus_di14: float | None
    rolling_vwap20: float | None
    vwap_distance_fraction: float | None
    volume_zscore20: float | None
    donchian_position20: float | None
    atr_percentile100: float | None
    bollinger_bandwidth_percentile100: float | None
    realized_volatility20: float | None
    parkinson_volatility20: float | None
    volatility_of_volatility20: float | None
    kaufman_efficiency_ratio10: float | None
    choppiness_index14: float | None
    volatility_adjusted_momentum20: float | None
    stoch_rsi14: float | None
    williams_r14: float | None
    cci20: float | None
    awesome_oscillator: float | None
    ultimate_oscillator: float | None
    hull_ma9_distance_fraction: float | None
    ichimoku_base26_distance_fraction: float | None

    @property
    def ready(self) -> bool:
        return all(
            value is not None
            for value in (
                self.adx14,
                self.plus_di14,
                self.minus_di14,
                self.rolling_vwap20,
                self.vwap_distance_fraction,
                self.volume_zscore20,
                self.donchian_position20,
                self.atr_percentile100,
                self.bollinger_bandwidth_percentile100,
                self.realized_volatility20,
                self.parkinson_volatility20,
                self.volatility_of_volatility20,
                self.kaufman_efficiency_ratio10,
                self.choppiness_index14,
                self.volatility_adjusted_momentum20,
            )
        )

    @property
    def normalized_features(self) -> dict[str, float | None]:
        return {
            "adx14": self.adx14,
            "plus_di14": self.plus_di14,
            "minus_di14": self.minus_di14,
            "vwap_distance_fraction": self.vwap_distance_fraction,
            "volume_zscore20": self.volume_zscore20,
            "donchian_position20": self.donchian_position20,
            "atr_percentile100": self.atr_percentile100,
            "bollinger_bandwidth_percentile100": self.bollinger_bandwidth_percentile100,
            "realized_volatility20": self.realized_volatility20,
            "parkinson_volatility20": self.parkinson_volatility20,
            "volatility_of_volatility20": self.volatility_of_volatility20,
            "kaufman_efficiency_ratio10": self.kaufman_efficiency_ratio10,
            "choppiness_index14": self.choppiness_index14,
            "volatility_adjusted_momentum20": self.volatility_adjusted_momentum20,
            "stoch_rsi14": self.stoch_rsi14,
            "williams_r14": self.williams_r14,
            "cci20": self.cci20,
            "awesome_oscillator": self.awesome_oscillator,
            "ultimate_oscillator": self.ultimate_oscillator,
            "hull_ma9_distance_fraction": self.hull_ma9_distance_fraction,
            "ichimoku_base26_distance_fraction": self.ichimoku_base26_distance_fraction,
        }

    @property
    def extended_ready(self) -> bool:
        """Whether the optional indicator extension is fully warmed up.

        ``ready`` intentionally keeps the original V0.2 contract so existing
        paper signals do not change their admission window.  Challenger
        experiments can opt into this stricter readiness gate explicitly.
        """

        return self.ready and all(
            value is not None
            for value in (
                self.stoch_rsi14,
                self.williams_r14,
                self.cci20,
                self.awesome_oscillator,
                self.ultimate_oscillator,
                self.hull_ma9_distance_fraction,
                self.ichimoku_base26_distance_fraction,
            )
        )


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _population_stddev(values: Sequence[float]) -> float:
    mean = _mean(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def _wma(values: Sequence[float | None], period: int) -> tuple[float | None, ...]:
    """Causal weighted moving average with strict warm-up semantics."""

    if period <= 0:
        raise ValueError("period must be positive")
    output: list[float | None] = [None] * len(values)
    denominator = period * (period + 1) / 2.0
    for index in range(period - 1, len(values)):
        window = values[index - period + 1 : index + 1]
        if any(value is None for value in window):
            continue
        output[index] = sum(
            float(value) * weight
            for weight, value in enumerate(window, start=1)
            if value is not None
        ) / denominator
    return tuple(output)


def _sma(values: Sequence[float], period: int) -> tuple[float | None, ...]:
    output: list[float | None] = [None] * len(values)
    for index in range(period - 1, len(values)):
        output[index] = _mean(values[index - period + 1 : index + 1])
    return tuple(output)


def _hull_ma(values: Sequence[float], period: int) -> tuple[float | None, ...]:
    """Causal Hull moving average, using the standard WMA construction."""

    half_period = max(1, period // 2)
    root_period = max(1, int(math.sqrt(period)))
    half = _wma(values, half_period)
    full = _wma(values, period)
    difference: list[float | None] = [
        None
        if half[index] is None or full[index] is None
        else 2.0 * float(half[index]) - float(full[index])
        for index in range(len(values))
    ]
    return _wma(difference, root_period)


def _stoch_rsi(
    rsi_values: Sequence[float | None], period: int = 14
) -> tuple[float | None, ...]:
    output: list[float | None] = [None] * len(rsi_values)
    for index in range(period - 1, len(rsi_values)):
        window = rsi_values[index - period + 1 : index + 1]
        if any(value is None for value in window):
            continue
        numeric = [float(value) for value in window if value is not None]
        low = min(numeric)
        high = max(numeric)
        output[index] = 0.5 if high == low else (numeric[-1] - low) / (high - low)
    return tuple(output)


def _williams_r(candles: Sequence[Candle], period: int = 14) -> tuple[float | None, ...]:
    output: list[float | None] = [None] * len(candles)
    for index in range(period - 1, len(candles)):
        window = candles[index - period + 1 : index + 1]
        highest = max(item.high for item in window)
        lowest = min(item.low for item in window)
        output[index] = -50.0 if highest == lowest else -100.0 * (highest - candles[index].close) / (highest - lowest)
    return tuple(output)


def _cci(candles: Sequence[Candle], period: int = 20) -> tuple[float | None, ...]:
    typical = tuple((item.high + item.low + item.close) / 3.0 for item in candles)
    output: list[float | None] = [None] * len(candles)
    for index in range(period - 1, len(candles)):
        window = typical[index - period + 1 : index + 1]
        average = _mean(window)
        deviation = _mean(tuple(abs(value - average) for value in window))
        output[index] = 0.0 if deviation == 0 else (typical[index] - average) / (0.015 * deviation)
    return tuple(output)


def _awesome_oscillator(candles: Sequence[Candle]) -> tuple[float | None, ...]:
    median = tuple((item.high + item.low) / 2.0 for item in candles)
    fast = _sma(median, 5)
    slow = _sma(median, 34)
    return tuple(
        None if fast[index] is None or slow[index] is None else float(fast[index]) - float(slow[index])
        for index in range(len(candles))
    )


def _ultimate_oscillator(candles: Sequence[Candle]) -> tuple[float | None, ...]:
    buying_pressure: list[float] = []
    true_range: list[float] = []
    for index, candle in enumerate(candles):
        previous_close = candle.close if index == 0 else candles[index - 1].close
        buying_pressure.append(candle.close - min(candle.low, previous_close))
        true_range.append(max(candle.high, previous_close) - min(candle.low, previous_close))
    output: list[float | None] = [None] * len(candles)
    for index in range(27, len(candles)):
        def ratio(period: int) -> float:
            start = index - period + 1
            pressure = sum(buying_pressure[start : index + 1])
            ranges = sum(true_range[start : index + 1])
            return 0.0 if ranges == 0 else pressure / ranges

        output[index] = 100.0 * (4.0 * ratio(7) + 2.0 * ratio(14) + ratio(28)) / 7.0
    return tuple(output)


def _ichimoku_base_distance(candles: Sequence[Candle], period: int = 26) -> tuple[float | None, ...]:
    output: list[float | None] = [None] * len(candles)
    for index in range(period - 1, len(candles)):
        window = candles[index - period + 1 : index + 1]
        baseline = (max(item.high for item in window) + min(item.low for item in window)) / 2.0
        if baseline != 0:
            output[index] = (candles[index].close - baseline) / baseline
    return tuple(output)


def _wilder(values: Sequence[float], period: int) -> tuple[float | None, ...]:
    output: list[float | None] = [None] * len(values)
    if len(values) < period:
        return tuple(output)
    previous = sum(values[:period]) / period
    output[period - 1] = previous
    for index in range(period, len(values)):
        previous = (previous * (period - 1) + values[index]) / period
        output[index] = previous
    return tuple(output)


def _adx(candles: Sequence[Candle], period: int = 14) -> tuple[
    tuple[float | None, ...],
    tuple[float | None, ...],
    tuple[float | None, ...],
]:
    true_ranges: list[float] = []
    plus_dm: list[float] = []
    minus_dm: list[float] = []
    for index, candle in enumerate(candles):
        if index == 0:
            true_ranges.append(candle.high - candle.low)
            plus_dm.append(0.0)
            minus_dm.append(0.0)
            continue
        previous = candles[index - 1]
        true_ranges.append(
            max(
                candle.high - candle.low,
                abs(candle.high - previous.close),
                abs(candle.low - previous.close),
            )
        )
        up_move = candle.high - previous.high
        down_move = previous.low - candle.low
        plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0.0)

    atr = _wilder(true_ranges, period)
    plus_smoothed = _wilder(plus_dm, period)
    minus_smoothed = _wilder(minus_dm, period)
    plus_di: list[float | None] = [None] * len(candles)
    minus_di: list[float | None] = [None] * len(candles)
    dx: list[float | None] = [None] * len(candles)
    for index in range(len(candles)):
        if atr[index] is None or atr[index] == 0:
            continue
        plus_di[index] = 100.0 * float(plus_smoothed[index] or 0.0) / atr[index]
        minus_di[index] = 100.0 * float(minus_smoothed[index] or 0.0) / atr[index]
        denominator = plus_di[index] + minus_di[index]
        dx[index] = 0.0 if denominator == 0 else 100.0 * abs(plus_di[index] - minus_di[index]) / denominator

    valid_dx = [value for value in dx if value is not None]
    smoothed_dx = _wilder(valid_dx, period)
    first_dx = next((index for index, value in enumerate(dx) if value is not None), len(dx))
    adx: list[float | None] = [None] * len(candles)
    for offset, value in enumerate(smoothed_dx):
        if first_dx + offset < len(adx):
            adx[first_dx + offset] = value
    return tuple(adx), tuple(plus_di), tuple(minus_di)


def _percentile_rank(values: Sequence[float | None], index: int, period: int) -> float | None:
    start = index - period + 1
    if start < 0 or values[index] is None:
        return None
    window = values[start : index + 1]
    if any(value is None for value in window):
        return None
    current = float(values[index])  # type: ignore[arg-type]
    numeric = [float(value) for value in window if value is not None]
    return sum(value <= current for value in numeric) / len(numeric)


def build_advanced_technical_series(
    candles: Sequence[Candle],
    interval: str,
    *,
    technical_series: Sequence[TechnicalSnapshot] | None = None,
) -> tuple[AdvancedTechnicalSnapshot, ...]:
    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported technical interval: {interval}")
    source = tuple(candles)
    audit = audit_candles(source, interval)
    if not audit.ok:
        raise TechnicalDataError(f"Candle audit failed: {audit}")
    if not source:
        return ()

    technical = tuple(technical_series or build_technical_series(source, interval))
    if len(technical) != len(source):
        raise ValueError("technical_series length must match candles")

    adx14, plus_di14, minus_di14 = _adx(source, 14)
    atr_fractions = tuple(item.atr14_fraction for item in technical)
    bandwidths = tuple(item.bollinger_bandwidth for item in technical)
    stoch_rsi14 = _stoch_rsi(tuple(item.rsi14 for item in technical), 14)
    williams_r14 = _williams_r(source, 14)
    cci20 = _cci(source, 20)
    awesome_oscillator = _awesome_oscillator(source)
    ultimate_oscillator = _ultimate_oscillator(source)
    closes = tuple(item.close for item in source)
    hull_ma9 = _hull_ma(closes, 9)
    hull_ma9_distance: tuple[float | None, ...] = tuple(
        None
        if hull_ma9[index] in (None, 0.0)
        else (source[index].close - float(hull_ma9[index])) / float(hull_ma9[index])
        for index in range(len(source))
    )
    ichimoku_base26_distance = _ichimoku_base_distance(source, 26)
    log_returns: list[float | None] = [None]
    for index in range(1, len(source)):
        log_returns.append(math.log(source[index].close / source[index - 1].close))

    realized: list[float | None] = [None] * len(source)
    parkinson: list[float | None] = [None] * len(source)
    for index in range(19, len(source)):
        returns = log_returns[index - 19 : index + 1]
        if all(value is not None for value in returns):
            values = [float(value) for value in returns if value is not None]
            realized[index] = _population_stddev(values) * math.sqrt(20.0)
        window = source[index - 19 : index + 1]
        squared_ranges = [math.log(candle.high / candle.low) ** 2 for candle in window]
        parkinson[index] = math.sqrt(sum(squared_ranges) / (4.0 * math.log(2.0)))

    output: list[AdvancedTechnicalSnapshot] = []
    interval_ms = INTERVAL_MS[interval]
    for index, candle in enumerate(source):
        rolling_vwap = None
        vwap_distance = None
        volume_zscore = None
        donchian_position = None
        if index >= 19:
            window = source[index - 19 : index + 1]
            total_volume = sum(item.volume for item in window)
            if total_volume > 0:
                rolling_vwap = sum(
                    ((item.high + item.low + item.close) / 3.0) * item.volume for item in window
                ) / total_volume
                if rolling_vwap != 0:
                    vwap_distance = (candle.close - rolling_vwap) / rolling_vwap
            volumes = [item.volume for item in window]
            volume_stddev = _population_stddev(volumes)
            volume_zscore = 0.0 if volume_stddev == 0 else (candle.volume - _mean(volumes)) / volume_stddev

        if index >= 20:
            previous_window = source[index - 20 : index]
            highest = max(item.high for item in previous_window)
            lowest = min(item.low for item in previous_window)
            if highest != lowest:
                donchian_position = (candle.close - lowest) / (highest - lowest)

        efficiency = None
        if index >= 10:
            path = sum(
                abs(source[offset].close - source[offset - 1].close)
                for offset in range(index - 9, index + 1)
            )
            efficiency = 0.0 if path == 0 else abs(candle.close - source[index - 10].close) / path

        choppiness = None
        if index >= 13:
            window = source[index - 13 : index + 1]
            highest = max(item.high for item in window)
            lowest = min(item.low for item in window)
            true_range_sum = 0.0
            for offset in range(index - 13, index + 1):
                item = source[offset]
                if offset == 0:
                    true_range_sum += item.high - item.low
                else:
                    previous_close = source[offset - 1].close
                    true_range_sum += max(
                        item.high - item.low,
                        abs(item.high - previous_close),
                        abs(item.low - previous_close),
                    )
            price_range = highest - lowest
            if price_range > 0 and true_range_sum > 0:
                choppiness = 100.0 * math.log10(true_range_sum / price_range) / math.log10(14.0)

        vol_of_vol = None
        if index >= 38:
            volatility_window = realized[index - 19 : index + 1]
            if all(value is not None for value in volatility_window):
                vol_of_vol = _population_stddev(
                    [float(value) for value in volatility_window if value is not None]
                )

        volatility_adjusted_momentum = None
        if index >= 20 and realized[index] not in (None, 0.0):
            volatility_adjusted_momentum = (
                math.log(candle.close / source[index - 20].close) / float(realized[index])
            )

        output.append(
            AdvancedTechnicalSnapshot(
                bar_time_ms=candle.time_ms,
                available_at_ms=candle.time_ms + interval_ms,
                adx14=adx14[index],
                plus_di14=plus_di14[index],
                minus_di14=minus_di14[index],
                rolling_vwap20=rolling_vwap,
                vwap_distance_fraction=vwap_distance,
                volume_zscore20=volume_zscore,
                donchian_position20=donchian_position,
                atr_percentile100=_percentile_rank(atr_fractions, index, 100),
                bollinger_bandwidth_percentile100=_percentile_rank(bandwidths, index, 100),
                realized_volatility20=realized[index],
                parkinson_volatility20=parkinson[index],
                volatility_of_volatility20=vol_of_vol,
                kaufman_efficiency_ratio10=efficiency,
                choppiness_index14=choppiness,
                volatility_adjusted_momentum20=volatility_adjusted_momentum,
                stoch_rsi14=stoch_rsi14[index],
                williams_r14=williams_r14[index],
                cci20=cci20[index],
                awesome_oscillator=awesome_oscillator[index],
                ultimate_oscillator=ultimate_oscillator[index],
                hull_ma9_distance_fraction=hull_ma9_distance[index],
                ichimoku_base26_distance_fraction=ichimoku_base26_distance[index],
            )
        )
    return tuple(output)
