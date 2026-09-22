from __future__ import annotations

import unittest
from datetime import UTC, datetime

from crypto_autopilot.features.vwap_research import (
    VwapResearchDataError,
    build_vwap_research_series,
)
from crypto_autopilot.historical import INTERVAL_MS
from crypto_autopilot.models import Candle


STEP = INTERVAL_MS["4H"]


def _ts(year: int, month: int, day: int, hour: int = 0) -> int:
    return int(datetime(year, month, day, hour, tzinfo=UTC).timestamp() * 1000)


def _candles(
    count: int,
    *,
    start_ms: int = _ts(2026, 1, 26),
    volume: float = 100.0,
) -> tuple[Candle, ...]:
    rows: list[Candle] = []
    for index in range(count):
        base = 100.0 + index * 0.2 + (index % 5) * 0.05
        rows.append(
            Candle(
                time_ms=start_ms + index * STEP,
                open=base,
                high=base + 1.0,
                low=base - 1.0,
                close=base + 0.25,
                volume=0.0 if volume == 0 else volume + (index % 7),
            )
        )
    return tuple(rows)


def _build(candles: tuple[Candle, ...]):
    return build_vwap_research_series(
        candles,
        "4H",
        provider="synthetic-provider",
        instrument="TESTUSDT",
        volume_unit="base_asset",
    )


class VwapResearchTests(unittest.TestCase):
    def test_metadata_and_closed_bar_availability_are_explicit(self) -> None:
        series = _build(_candles(3))
        first = series[0]
        self.assertEqual(first.provider, "synthetic-provider")
        self.assertEqual(first.instrument, "TESTUSDT")
        self.assertEqual(first.volume_unit, "base_asset")
        self.assertEqual(first.available_at_ms, first.bar_time_ms + STEP)

    def test_vwap_distance_and_weighted_stddev_match_manual_math(self) -> None:
        start = _ts(2026, 1, 26)
        candles = (
            Candle(start, 99.0, 102.0, 98.0, 100.0, 1.0),
            Candle(start + STEP, 101.0, 104.0, 100.0, 102.0, 3.0),
        )
        value = _build(candles)[-1].day
        # HLC3 values are 100 and 102, so weighted VWAP = 101.5.
        self.assertAlmostEqual(value.vwap or 0.0, 101.5)
        self.assertAlmostEqual(value.distance_fraction or 0.0, 0.5 / 101.5)
        self.assertAlmostEqual(value.weighted_stddev or 0.0, (0.75) ** 0.5)
        self.assertAlmostEqual(value.stddev_position or 0.0, 0.5 / ((0.75) ** 0.5))
        self.assertTrue(value.ready)

    def test_day_week_and_month_anchors_reset_on_utc_boundaries(self) -> None:
        series = _build(_candles(60))
        by_time = {item.bar_time_ms: item for item in series}

        jan_27 = by_time[_ts(2026, 1, 27)]
        self.assertEqual(jan_27.day.bar_count, 1)
        self.assertGreater(jan_27.week.bar_count, 1)
        self.assertGreater(jan_27.month.bar_count, 1)

        feb_1 = by_time[_ts(2026, 2, 1)]
        self.assertEqual(feb_1.day.bar_count, 1)
        self.assertEqual(feb_1.month.bar_count, 1)
        self.assertGreater(feb_1.week.bar_count, 1)

        feb_2 = by_time[_ts(2026, 2, 2)]
        self.assertEqual(feb_2.day.bar_count, 1)
        self.assertEqual(feb_2.week.bar_count, 1)
        self.assertGreater(feb_2.month.bar_count, 1)

    def test_trailing_windows_have_exact_warmup(self) -> None:
        series = _build(_candles(180))
        self.assertEqual(series[40].trailing_7d.reason, "INSUFFICIENT_HISTORY")
        self.assertFalse(series[40].trailing_7d.ready)
        self.assertEqual(series[41].trailing_7d.bar_count, 42)
        self.assertTrue(series[41].trailing_7d.ready)

        self.assertEqual(series[178].trailing_30d.reason, "INSUFFICIENT_HISTORY")
        self.assertFalse(series[178].trailing_30d.ready)
        self.assertEqual(series[179].trailing_30d.bar_count, 180)
        self.assertTrue(series[179].trailing_30d.ready)

    def test_prefix_invariance_blocks_future_leakage(self) -> None:
        candles = _candles(70)
        short = _build(candles[:50])
        long = _build(candles)
        self.assertEqual(short, long[:50])

    def test_trailing_7d_evicts_old_bars(self) -> None:
        original = list(_candles(50))
        changed = list(original)
        first = changed[0]
        changed[0] = Candle(
            time_ms=first.time_ms,
            open=1000.0,
            high=1002.0,
            low=998.0,
            close=1001.0,
            volume=10000.0,
        )
        left = _build(tuple(original))[-1].trailing_7d
        right = _build(tuple(changed))[-1].trailing_7d
        self.assertEqual(left, right)
        self.assertEqual(left.bar_count, 42)

    def test_zero_volume_and_zero_variance_are_explicit(self) -> None:
        zero_volume = _build(_candles(2, volume=0.0))
        self.assertEqual(zero_volume[-1].day.reason, "ZERO_VOLUME")
        self.assertFalse(zero_volume[-1].day.ready)

        start = _ts(2026, 1, 26)
        flat = tuple(
            Candle(
                time_ms=start + index * STEP,
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.0,
                volume=100.0,
            )
            for index in range(2)
        )
        flat_value = _build(flat)[-1].day
        self.assertEqual(flat_value.reason, "ZERO_VARIANCE")
        self.assertFalse(flat_value.ready)
        self.assertEqual(flat_value.weighted_stddev, 0.0)
        self.assertIsNotNone(flat_value.vwap)
        self.assertIsNone(flat_value.stddev_position)

    def test_gap_and_invalid_candle_fail_closed(self) -> None:
        candles = list(_candles(5))
        with self.assertRaises(VwapResearchDataError):
            _build(tuple(candles[:2] + candles[3:]))

        invalid = list(_candles(5))
        item = invalid[2]
        invalid[2] = Candle(
            time_ms=item.time_ms,
            open=item.open,
            high=item.low - 1.0,
            low=item.low,
            close=item.close,
            volume=item.volume,
        )
        with self.assertRaises(VwapResearchDataError):
            _build(tuple(invalid))

    def test_partial_bar_trailing_windows_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not divide trailing_30d exactly"):
            build_vwap_research_series(
                (),
                "1W",
                provider="synthetic-provider",
                instrument="TESTUSDT",
                volume_unit="base_asset",
            )


if __name__ == "__main__":
    unittest.main()
