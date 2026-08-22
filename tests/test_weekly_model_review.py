from __future__ import annotations

import math
import unittest

from crypto_autopilot.online_training import DAY_MS
from crypto_autopilot.weekly_model_review import build_weekly_model_review


class WeeklyModelReviewTests(unittest.TestCase):
    def test_walk_forward_cost_drawdown_and_exposure_are_research_only(self) -> None:
        rows = []
        for symbol_index, symbol in enumerate(("AAAUSDT", "BBBUSDT")):
            close = 100.0 + symbol_index
            for day in range(500):
                close *= 1.0 + (0.006 if day % 4 else -0.004)
                rows.append(
                    {
                        "asset_class": "crypto",
                        "symbol": symbol,
                        "audit_ok": True,
                        "open_time_ms": day * DAY_MS,
                        "close": close,
                        "quote_volume": 1000.0 + 20.0 * math.sin(day / 8),
                    }
                )
        training = {
            "feature_names": ["a", "b", "c", "d", "e"],
            "asset_classes": ["crypto"],
            "max_train_samples_per_class": 5000,
            "max_test_samples_per_class": 5000,
            "epochs": 3,
            "learning_rate": 0.08,
            "l2": 0.0001,
        }
        review = build_weekly_model_review(
            rows,
            training_config=training,
            review_config={
                "walk_forward_train_fractions": [0.6, 0.8],
                "minimum_fold_train_samples": 100,
                "minimum_fold_validation_samples": 40,
                "long_probability_threshold": 0.5,
                "diagnostic_initial_equity_usd": 10000.0,
                "cost_scenarios": [
                    {
                        "name": "base",
                        "taker_fee_bps_each_side": 5.0,
                        "slippage_bps_each_fill": 2.0,
                    }
                ],
            },
            data_sha256="a" * 64,
            end_exclusive_ms=600 * DAY_MS,
            generated_at_utc="2026-08-22T00:00:00Z",
        )
        self.assertEqual(review["status"], "PASS")
        folds = review["walk_forward"]["classes"]["crypto"]["folds"]
        self.assertEqual([item["status"] for item in folds], ["PASS", "PASS"])
        self.assertIn("diagnostic_max_drawdown_pct", review["cost_and_drawdown_sensitivity"][0])
        self.assertIn("maximum_symbol_signal_share", review["asset_exposure"])
        self.assertFalse(review["authority"]["formal_backtest_admission_authorized"])
        self.assertFalse(review["authority"]["automatic_model_promotion_authorized"])
        self.assertFalse(review["authority"]["live_trading_authorized"])


if __name__ == "__main__":
    unittest.main()
