from __future__ import annotations

import math
import unittest

from crypto_autopilot.training.online import DAILY_DIRECTION_FEATURE_NAMES, DAY_MS
from crypto_autopilot.training.weekly_review import build_weekly_model_review


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
            "feature_names": list(DAILY_DIRECTION_FEATURE_NAMES),
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
                "quality_gate": {
                    "required_baseline_improvements": ["log_loss", "brier_score"],
                    "cost_scenario_name": "base",
                    "minimum_net_growth_pct": 0.0,
                    "maximum_diagnostic_drawdown_pct": 50.0,
                    "maximum_symbol_signal_share": 0.75,
                },
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
        self.assertTrue(
            all(item["partition_integrity"]["strictly_chronological"] for item in folds)
        )
        self.assertTrue(all(not item["partition_integrity"]["holdout_accessed"] for item in folds))
        self.assertTrue(all("baseline_comparison" in item for item in folds))
        self.assertIn("diagnostic_max_drawdown_pct", review["cost_and_drawdown_sensitivity"][0])
        self.assertIn("diagnostic_net_growth_pct", review["cost_and_drawdown_sensitivity"][0])
        self.assertIn("maximum_symbol_signal_share", review["asset_exposure"])
        self.assertIn(review["model_quality_gate"]["status"], {"PASS", "REJECT"})
        self.assertFalse(review["model_quality_gate"]["promotion_eligible"])
        self.assertEqual(review["lineage"]["dataset_sha256"], "a" * 64)
        self.assertFalse(review["lineage"]["holdout_accessed"])
        self.assertFalse(review["authority"]["formal_backtest_admission_authorized"])
        self.assertFalse(review["authority"]["automatic_model_promotion_authorized"])
        self.assertFalse(review["authority"]["live_trading_authorized"])

    def test_bad_cost_and_drawdown_evidence_is_rejected_without_failing_pipeline(self) -> None:
        rows = []
        for symbol, asset_class in (
            ("AAAUSDT", "crypto"),
            ("BBBUSDT", "crypto"),
            ("TSLABUSDT", "tokenized_stock_candidate"),
        ):
            close = 100.0
            for day in range(500):
                close *= 0.99
                rows.append(
                    {
                        "asset_class": asset_class,
                        "symbol": symbol,
                        "audit_ok": True,
                        "open_time_ms": day * DAY_MS,
                        "close": close,
                        "quote_volume": 1000.0,
                    }
                )
        review = build_weekly_model_review(
            rows,
            training_config={
                "feature_names": list(DAILY_DIRECTION_FEATURE_NAMES),
                "asset_classes": ["crypto", "tokenized_stock_candidate"],
                "max_train_samples_per_class": 5000,
                "max_test_samples_per_class": 5000,
                "epochs": 2,
                "learning_rate": 0.08,
                "l2": 0.0001,
            },
            review_config={
                "walk_forward_train_fractions": [0.6, 0.8],
                "minimum_fold_train_samples": 100,
                "minimum_fold_validation_samples": 40,
                "long_probability_threshold": 0.0,
                "diagnostic_initial_equity_usd": 10000.0,
                "quality_gate": {
                    "required_baseline_improvements": ["log_loss", "brier_score"],
                    "cost_scenario_name": "base",
                    "minimum_net_growth_pct": 0.0,
                    "maximum_diagnostic_drawdown_pct": 50.0,
                    "maximum_symbol_signal_share": 0.75,
                },
                "cost_scenarios": [
                    {
                        "name": "base",
                        "taker_fee_bps_each_side": 5.0,
                        "slippage_bps_each_fill": 2.0,
                    }
                ],
            },
            data_sha256="b" * 64,
            end_exclusive_ms=600 * DAY_MS,
            generated_at_utc="2026-08-22T00:00:00Z",
        )
        self.assertEqual(review["status"], "PASS")
        self.assertEqual(review["model_quality_gate"]["status"], "REJECT")
        self.assertIn("NET_GROWTH_BELOW_POLICY", review["model_quality_gate"]["failures"])
        self.assertIn("DRAWDOWN_ABOVE_POLICY", review["model_quality_gate"]["failures"])
        self.assertIn(
            "tokenized_stock_candidate",
            review["model_quality_gate"]["baseline_rejected_asset_classes"],
        )
        self.assertFalse(review["authority"]["automatic_model_promotion_authorized"])


if __name__ == "__main__":
    unittest.main()
