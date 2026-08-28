from __future__ import annotations

import math
import unittest

from crypto_autopilot.training.detailed import (
    FEATURE_NAMES,
    IntradayExample,
    build_intraday_examples,
    predict,
    run_intraday_training,
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


class DetailedTrainingTests(unittest.TestCase):
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

