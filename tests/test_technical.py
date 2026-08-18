from __future__ import annotations

import unittest

from crypto_autopilot.historical import INTERVAL_MS
from crypto_autopilot.models import Candle
from crypto_autopilot.technical import (
    TechnicalDataError,
    build_technical_series,
    closed_snapshots_as_of,
    latest_closed_snapshot,
)


INTERVAL = "15M"
STEP = INTERVAL_MS[INTERVAL]


def flat_candles(count: int, *, start_ms: int = 0) -> list[Candle]:
    return [
        Candle(
            time_ms=start_ms + index * STEP,
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            volume=10.0,
        )
        for index in range(count)
    ]


def trend_candles(count: int) -> list[Candle]:
    candles: list[Candle] = []
    for index in range(count):
        close = 100.0 + index * 0.5
        candles.append(
            Candle(
                time_ms=index * STEP,
                open=close - 0.2,
                high=close + 1.0,
                low=close - 1.0,
                close=close,
                volume=100.0 + index,
            )
        )
    return candles


class TechnicalFeaturesTest(unittest.TestCase):
    def test_constant_series_has_expected_raw_indicators(self) -> None:
        series = build_technical_series(flat_candles(60), INTERVAL)
        snapshot = series[-1]

        self.assertTrue(snapshot.ready)
        self.assertAlmostEqual(snapshot.ema20 or 0.0, 100.0)
        self.assertAlmostEqual(snapshot.ema50 or 0.0, 100.0)
        self.assertAlmostEqual(snapshot.ema20_slope or 0.0, 0.0)
        self.assertAlmostEqual(snapshot.atr14 or 0.0, 2.0)
        self.assertAlmostEqual(snapshot.volume_sma20 or 0.0, 10.0)
        self.assertAlmostEqual(snapshot.volume_ratio or 0.0, 1.0)
        self.assertEqual(snapshot.previous_high, 101.0)
        self.assertAlmostEqual(snapshot.extension_from_ema20_atr or 0.0, 0.0)

    def test_bar_is_unavailable_until_exact_close_time(self) -> None:
        series = build_technical_series(flat_candles(2), INTERVAL)
        first = series[0]

        self.assertEqual(first.bar_time_ms, 0)
        self.assertEqual(first.available_at_ms, STEP)
        self.assertEqual(closed_snapshots_as_of(series, STEP - 1), ())
        self.assertEqual(closed_snapshots_as_of(series, STEP), (first,))
        self.assertIsNone(latest_closed_snapshot(series, STEP - 1))
        self.assertEqual(latest_closed_snapshot(series, STEP), first)

    def test_future_candle_mutation_cannot_change_past_snapshots(self) -> None:
        original = trend_candles(80)
        mutated = list(original)
        for index in range(60, 80):
            candle = mutated[index]
            mutated[index] = Candle(
                time_ms=candle.time_ms,
                open=candle.open * 10.0,
                high=candle.high * 10.0,
                low=candle.low * 10.0,
                close=candle.close * 10.0,
                volume=candle.volume * 100.0,
            )

        baseline = build_technical_series(original, INTERVAL)
        changed = build_technical_series(mutated, INTERVAL)
        self.assertEqual(baseline[:60], changed[:60])
        self.assertNotEqual(baseline[60:], changed[60:])

    def test_gap_and_duplicate_are_rejected_without_repair(self) -> None:
        candles = flat_candles(60)
        with_gap = candles[:10] + candles[11:]
        with self.assertRaises(TechnicalDataError):
            build_technical_series(with_gap, INTERVAL)

        with_duplicate = candles[:10] + [candles[9]] + candles[10:]
        with self.assertRaises(TechnicalDataError):
            build_technical_series(with_duplicate, INTERVAL)

    def test_warmup_requires_ema50_history(self) -> None:
        series = build_technical_series(trend_candles(55), INTERVAL)
        self.assertFalse(series[48].ready)
        self.assertTrue(series[49].ready)

        as_of_49_close = series[49].available_at_ms
        self.assertEqual(
            latest_closed_snapshot(series, as_of_49_close, require_ready=True),
            series[49],
        )

    def test_normalized_extension_is_raw_value_not_strategy_gate(self) -> None:
        series = build_technical_series(trend_candles(60), INTERVAL)
        snapshot = series[-1]
        self.assertIsNotNone(snapshot.extension_from_ema20_atr)
        self.assertGreater(snapshot.extension_from_ema20_atr or 0.0, 0.0)
        self.assertFalse(hasattr(snapshot, "not_overextended"))
        self.assertFalse(hasattr(snapshot, "volume_confirmed"))

    def test_repeated_build_is_exactly_deterministic(self) -> None:
        candles = trend_candles(80)
        self.assertEqual(
            build_technical_series(candles, INTERVAL),
            build_technical_series(candles, INTERVAL),
        )


if __name__ == "__main__":
    unittest.main()
