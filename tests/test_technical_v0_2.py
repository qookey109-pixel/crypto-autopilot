from __future__ import annotations

import unittest

from crypto_autopilot.historical import INTERVAL_MS
from crypto_autopilot.market_structure import build_market_structure_series
from crypto_autopilot.models import Candle
from crypto_autopilot.multi_timeframe_technical import build_multi_timeframe_snapshot
from crypto_autopilot.technical import TechnicalDataError, build_technical_series


INTERVAL = "15M"
STEP = INTERVAL_MS[INTERVAL]


def candles_from_closes(
    closes: list[float],
    *,
    interval: str = INTERVAL,
    volumes: list[float] | None = None,
) -> list[Candle]:
    step = INTERVAL_MS[interval]
    volume_values = volumes or [10.0] * len(closes)
    return [
        Candle(
            time_ms=index * step,
            open=close,
            high=close + 1.0,
            low=max(0.1, close - 1.0),
            close=close,
            volume=volume_values[index],
        )
        for index, close in enumerate(closes)
    ]


def flat_candles(count: int, *, interval: str = INTERVAL) -> list[Candle]:
    return candles_from_closes([100.0] * count, interval=interval)


class TechnicalV02IndicatorTests(unittest.TestCase):
    def test_ema200_and_normalized_trend_warmup_are_explicit(self) -> None:
        closes = [100.0 + index * 0.25 for index in range(200)]
        series = build_technical_series(candles_from_closes(closes), INTERVAL)

        self.assertIsNone(series[198].ema200)
        self.assertIsNotNone(series[199].ema200)
        self.assertIsNotNone(series[199].ema20_ema50_distance_fraction)
        self.assertIsNotNone(series[199].ema50_ema200_distance_fraction)
        self.assertIsNotNone(series[199].ema20_slope_atr)
        self.assertTrue(series[199].ready_v0_2)

    def test_rsi14_wilder_boundaries_and_flat_definition(self) -> None:
        rising = build_technical_series(candles_from_closes([float(i) for i in range(1, 16)]), INTERVAL)
        self.assertIsNone(rising[13].rsi14)
        self.assertEqual(rising[14].rsi14, 100.0)

        flat = build_technical_series(flat_candles(15), INTERVAL)
        self.assertEqual(flat[14].rsi14, 50.0)

    def test_macd_warmup_chain_is_explicit(self) -> None:
        series = build_technical_series(
            candles_from_closes([100.0 + index for index in range(34)]), INTERVAL
        )
        self.assertIsNone(series[24].macd)
        self.assertIsNotNone(series[25].macd)
        self.assertIsNone(series[32].macd_signal)
        self.assertIsNotNone(series[33].macd_signal)
        self.assertIsNotNone(series[33].macd_histogram)

    def test_bollinger_constant_and_nonzero_variance(self) -> None:
        flat = build_technical_series(flat_candles(30), INTERVAL)[-1]
        self.assertEqual(flat.bollinger_mid, 100.0)
        self.assertEqual(flat.bollinger_bandwidth, 0.0)
        self.assertIsNone(flat.bollinger_position)

        varying = build_technical_series(
            candles_from_closes([100.0 + (index % 5) for index in range(30)]), INTERVAL
        )[-1]
        self.assertIsNotNone(varying.bollinger_upper)
        self.assertGreater(varying.bollinger_bandwidth or 0.0, 0.0)
        self.assertIsNotNone(varying.bollinger_position)

    def test_atr_fraction_and_volume_ratio_are_normalized_features(self) -> None:
        volumes = [10.0] * 19 + [20.0]
        snapshot = build_technical_series(
            candles_from_closes([100.0] * 20, volumes=volumes), INTERVAL
        )[-1]
        self.assertAlmostEqual(snapshot.atr14_fraction or 0.0, 0.02)
        self.assertAlmostEqual(snapshot.volume_ratio or 0.0, 20.0 / 10.5)
        self.assertIn("rsi14", snapshot.normalized_features)
        self.assertNotIn("BUY", snapshot.normalized_features)


class TechnicalV02DataQualityTests(unittest.TestCase):
    def test_invalid_ohlc_fails_closed(self) -> None:
        candles = flat_candles(20)
        candles[5] = Candle(candles[5].time_ms, 100.0, 99.0, 98.0, 100.0, 10.0)
        with self.assertRaises(TechnicalDataError):
            build_technical_series(candles, INTERVAL)

    def test_gap_and_duplicate_fail_closed(self) -> None:
        candles = flat_candles(25)
        with_gap = candles[:10] + candles[11:]
        with self.assertRaises(TechnicalDataError):
            build_technical_series(with_gap, INTERVAL)

        with_duplicate = candles[:10] + [candles[9]] + candles[10:]
        with self.assertRaises(TechnicalDataError):
            build_market_structure_series(with_duplicate, INTERVAL)

    def test_empty_input_is_deterministically_empty(self) -> None:
        self.assertEqual(build_technical_series([], INTERVAL), ())
        self.assertEqual(build_market_structure_series([], INTERVAL), ())


class MarketStructureV02Tests(unittest.TestCase):
    def test_trailing_range_excludes_current_candle(self) -> None:
        closes = [100.0, 101.0, 102.0, 110.0, 109.0, 108.0]
        series = build_market_structure_series(
            candles_from_closes(closes), INTERVAL, rolling_window=3
        )
        self.assertEqual(series[3].rolling_previous_high, 103.0)
        self.assertTrue(series[3].breakout_above_previous_range)

    def test_swing_is_visible_only_after_right_bar_confirmation(self) -> None:
        closes = [10.0, 9.0, 12.0, 11.0, 15.0, 13.0, 14.0, 12.0]
        series = build_market_structure_series(
            candles_from_closes(closes), INTERVAL, rolling_window=3, swing_left=2, swing_right=2
        )
        self.assertFalse(series[4].confirmed_swing_high)
        self.assertTrue(series[6].confirmed_swing_high)
        self.assertEqual(series[6].most_recent_confirmed_swing_high, 16.0)

    def test_future_mutation_cannot_change_past_structure(self) -> None:
        closes = [100.0 + ((index % 7) - 3) for index in range(40)]
        original = candles_from_closes(closes)
        mutated = list(original)
        for index in range(25, len(mutated)):
            candle = mutated[index]
            mutated[index] = Candle(
                candle.time_ms,
                candle.open * 3.0,
                candle.high * 3.0,
                candle.low * 3.0,
                candle.close * 3.0,
                candle.volume * 3.0,
            )
        baseline = build_market_structure_series(original, INTERVAL)
        changed = build_market_structure_series(mutated, INTERVAL)
        self.assertEqual(baseline[:25], changed[:25])


class MultiTimeframeV02Tests(unittest.TestCase):
    def test_missing_timeframe_is_not_ready(self) -> None:
        candles_15m = flat_candles(220, interval="15M")
        candles_60m = flat_candles(220, interval="60M")
        snapshot = build_multi_timeframe_snapshot(
            symbol="BTC_USDT_PERP",
            as_of_ms=10_000_000_000,
            candles_by_interval={"15M": candles_15m, "60M": candles_60m},
        )
        self.assertFalse(snapshot.ready)
        self.assertIsNone(snapshot.four_hour)

    def test_alignment_uses_only_available_closed_bars(self) -> None:
        candles_by_interval = {
            interval: flat_candles(220, interval=interval) for interval in ("4H", "60M", "15M")
        }
        as_of_ms = 100 * INTERVAL_MS["15M"] + INTERVAL_MS["15M"] - 1
        snapshot = build_multi_timeframe_snapshot(
            symbol="BTC_USDT_PERP",
            as_of_ms=as_of_ms,
            candles_by_interval=candles_by_interval,
        )
        self.assertIsNotNone(snapshot.fifteen_minute)
        self.assertLessEqual(snapshot.fifteen_minute.available_at_ms, as_of_ms)  # type: ignore[union-attr]
        self.assertIsNotNone(snapshot.one_hour)
        self.assertLessEqual(snapshot.one_hour.available_at_ms, as_of_ms)  # type: ignore[union-attr]
        self.assertIsNotNone(snapshot.four_hour)
        self.assertLessEqual(snapshot.four_hour.available_at_ms, as_of_ms)  # type: ignore[union-attr]
        self.assertFalse(snapshot.ready)

    def test_future_four_hour_candle_cannot_leak_into_earlier_snapshot(self) -> None:
        candles_by_interval = {
            interval: flat_candles(220, interval=interval) for interval in ("4H", "60M", "15M")
        }
        as_of_ms = 2 * INTERVAL_MS["4H"]
        baseline = build_multi_timeframe_snapshot(
            symbol="BTC_USDT_PERP",
            as_of_ms=as_of_ms,
            candles_by_interval=candles_by_interval,
        )
        mutated = {interval: list(candles) for interval, candles in candles_by_interval.items()}
        future = mutated["4H"][2]
        mutated["4H"][2] = Candle(
            future.time_ms,
            1_000.0,
            1_001.0,
            999.0,
            1_000.0,
            999.0,
        )
        changed = build_multi_timeframe_snapshot(
            symbol="BTC_USDT_PERP", as_of_ms=as_of_ms, candles_by_interval=mutated
        )
        self.assertEqual(baseline.four_hour, changed.four_hour)


if __name__ == "__main__":
    unittest.main()
