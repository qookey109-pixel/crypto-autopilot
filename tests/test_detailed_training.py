from __future__ import annotations

import math
import unittest

from crypto_autopilot.training.detailed import (
    FEATURE_NAMES,
    IntradayExample,
    build_intraday_examples,
    predict,
    run_intraday_training,
    split_contiguous_candles,
)
from crypto_autopilot.historical import INTERVAL_MS
from crypto_autopilot.models import Candle


def candles(interval: str, count: int) -> tuple[Candle, ...]:
    step = INTERVAL_MS[{"15m": "15M", "1h": "60M", "4h": "4H"}[interval]]
    output = []
    for index in range(count):
        close = 100.0 + index * 0.01 + math.sin(index / 17.0) * 0.3
        output.append(
            Candle(
                time_ms=index * step,
                open=close - 0.05,
                high=close + 0.2,
                low=close - 0.2,
                close=close,
                volume=100.0 + index % 23,
            )
        )
    return tuple(output)


def candles_with_gap(
    interval: str,
    count: int,
    *,
    gap_index: int,
    missing_bars: int,
) -> tuple[Candle, ...]:
    base = candles(interval, count)
    step = INTERVAL_MS[{"15m": "15M", "1h": "60M", "4h": "4H"}[interval]]
    output = []
    for index, candle in enumerate(base):
        shift = missing_bars * step if index >= gap_index else 0
        output.append(
            Candle(
                time_ms=candle.time_ms + shift,
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=candle.volume,
            )
        )
    return tuple(output)


class DetailedTrainingTests(unittest.TestCase):
    def test_split_contiguous_candles_preserves_gap_without_filling(self) -> None:
        source = candles_with_gap("15m", 10, gap_index=4, missing_bars=3)
        segments = split_contiguous_candles(source, INTERVAL_MS["15M"])
        self.assertEqual([len(segment) for segment in segments], [4, 6])
        self.assertEqual(sum(len(segment) for segment in segments), len(source))
        self.assertEqual(segments[0][-1], source[3])
        self.assertEqual(segments[1][0], source[4])

    def test_split_contiguous_candles_rejects_invalid_interval(self) -> None:
        with self.assertRaisesRegex(ValueError, "interval must be positive"):
            split_contiguous_candles(candles("15m", 2), 0)

    def test_multitimeframe_examples_are_causal_and_have_frozen_feature_order(self) -> None:
        result = build_intraday_examples(
            symbol="BTCUSDT",
            asset_class="crypto",
            candles_by_interval={
                "15m": candles("15m", 5000),
                "1h": candles("1h", 1250),
                "4h": candles("4h", 320),
            },
            sample_stride_15m_bars=4,
            forward_horizon_15m_bars=16,
            label_cost_bps_round_trip=14.0,
        )
        self.assertGreater(len(result), 100)
        self.assertTrue(all(len(item.features) == len(FEATURE_NAMES) for item in result))
        self.assertEqual(result, sorted(result, key=lambda item: item.time_ms))
        self.assertGreaterEqual(result[0].time_ms, 200 * INTERVAL_MS["4H"])

    def test_15m_returns_and_labels_do_not_cross_internal_gap(self) -> None:
        gap_index = 3000
        missing_bars = 41
        source = candles_with_gap(
            "15m",
            6000,
            gap_index=gap_index,
            missing_bars=missing_bars,
        )
        result = build_intraday_examples(
            symbol="CTKUSDT",
            asset_class="crypto",
            candles_by_interval={
                "15m": source,
                "1h": candles("1h", 1600),
                "4h": candles("4h", 420),
            },
            sample_stride_15m_bars=1,
            forward_horizon_15m_bars=16,
            label_cost_bps_round_trip=14.0,
        )
        step = INTERVAL_MS["15M"]
        first_post_gap_open = source[gap_index].time_ms
        unsafe_window_end = first_post_gap_open + 16 * step
        self.assertFalse(
            any(first_post_gap_open <= item.time_ms < unsafe_window_end for item in result)
        )
        self.assertTrue(any(item.time_ms > first_post_gap_open + 400 * step for item in result))

    def test_stale_context_is_not_reused_across_1h_or_4h_gap(self) -> None:
        gap_start_ms = 700 * INTERVAL_MS["60M"]
        source = candles("15m", 5000)
        one_hour = candles_with_gap("1h", 1250, gap_index=700, missing_bars=12)
        four_hour_gap_index = gap_start_ms // INTERVAL_MS["4H"]
        four_hour = candles_with_gap(
            "4h",
            340,
            gap_index=four_hour_gap_index,
            missing_bars=3,
        )
        result = build_intraday_examples(
            symbol="CTKUSDT",
            asset_class="crypto",
            candles_by_interval={"15m": source, "1h": one_hour, "4h": four_hour},
            sample_stride_15m_bars=1,
            forward_horizon_15m_bars=16,
            label_cost_bps_round_trip=14.0,
        )
        stale_start = one_hour[699].time_ms + 2 * INTERVAL_MS["60M"]
        stale_end = min(one_hour[700].time_ms, four_hour[four_hour_gap_index].time_ms)
        self.assertLess(stale_start, stale_end)
        self.assertFalse(any(stale_start <= item.time_ms < stale_end for item in result))

    def test_walk_forward_training_preserves_reject_without_promotion(self) -> None:
        examples = []
        day = 86_400_000
        for index in range(1200):
            features = tuple(math.sin(index / (offset + 3)) for offset in range(len(FEATURE_NAMES)))
            label = int(features[0] + features[1] > 0)
            examples.append(
                IntradayExample(
                    symbol=f"S{index % 20:02d}USDT",
                    asset_class="crypto",
                    time_ms=index * day,
                    features=features,
                    label=label,
                    forward_return=0.003 if label else -0.002,
                )
            )
        config = {
            "training": {
                "maximum_total_examples": 1200,
                "minimum_train_examples": 100,
                "minimum_test_examples": 50,
                "epochs": 3,
                "learning_rate": 0.05,
                "l2": 0.0001,
                "probability_threshold": 0.55,
                "walk_forward_folds": [
                    {
                        "name": "one",
                        "train_end_exclusive": "1971-02-05T00:00:00Z",
                        "test_end_exclusive": "1971-05-16T00:00:00Z"
                    },
                    {
                        "name": "two",
                        "train_end_exclusive": "1971-05-16T00:00:00Z",
                        "test_end_exclusive": "1971-08-24T00:00:00Z"
                    }
                ],
                "cost_scenarios": [
                    {"name": "base", "fee_bps_per_side": 5.0, "slippage_bps_per_side": 2.0},
                    {"name": "stress", "fee_bps_per_side": 10.0, "slippage_bps_per_side": 5.0}
                ]
            }
        }
        model, metrics = run_intraday_training(
            examples,
            config=config,
            dataset_fingerprint="a" * 64,
            generated_at_utc="2026-09-06T00:00:00Z",
        )
        self.assertEqual(model["model"]["feature_names"], list(FEATURE_NAMES))
        self.assertIn(metrics["model_quality_gate"]["status"], {"PASS", "REJECT"})
        self.assertFalse(model["authority"]["automatic_model_promotion_authorized"])
        self.assertFalse(model["authority"]["live_trading_authorized"])
        self.assertGreaterEqual(predict(examples[-1], model["model"]), 0.0)


if __name__ == "__main__":
    unittest.main()
