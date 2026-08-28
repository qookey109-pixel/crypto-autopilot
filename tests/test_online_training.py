from __future__ import annotations

import math
import unittest

from crypto_autopilot.training.online import (
    DAILY_DIRECTION_FEATURE_NAMES,
    DAY_MS,
    train_daily_direction_models,
)


class OnlineTrainingTests(unittest.TestCase):
    def test_deterministic_daily_model_trains_without_trade_authority(self) -> None:
        rows = []
        for symbol_index, symbol in enumerate(("AAAUSDT", "BBBUSDT")):
            close = 100.0 + symbol_index
            for day in range(420):
                close *= 1.0 + (0.003 if day % 3 else -0.002)
                rows.append(
                    {
                        "asset_class": "crypto",
                        "symbol": symbol,
                        "audit_ok": True,
                        "open_time_ms": day * DAY_MS,
                        "close": close,
                        "quote_volume": 1000.0 + 10.0 * math.sin(day / 10),
                    }
                )
        config = {
            "feature_names": [
                "return_1d",
                "return_3d",
                "return_7d",
                "close_vs_ma7",
                "quote_volume_vs_ma7",
            ],
            "asset_classes": ["crypto", "tokenized_stock_candidate"],
            "minimum_train_samples": 100,
            "minimum_test_samples": 40,
            "max_train_samples_per_class": 1000,
            "max_test_samples_per_class": 1000,
            "epochs": 3,
            "learning_rate": 0.08,
            "l2": 0.0001,
            "target": "next_complete_daily_close_up",
        }
        first = train_daily_direction_models(
            rows,
            training_config=config,
            data_sha256="a" * 64,
            end_exclusive_ms=500 * DAY_MS,
            generated_at_utc="2026-08-22T00:00:00Z",
        )
        second = train_daily_direction_models(
            rows,
            training_config=config,
            data_sha256="a" * 64,
            end_exclusive_ms=500 * DAY_MS,
            generated_at_utc="2026-08-22T00:00:00Z",
        )
        self.assertEqual(first, second)
        model, metrics = first
        self.assertEqual(model["status"], "PASS")
        self.assertEqual(model["models"]["crypto"]["status"], "PASS")
        self.assertEqual(model["models"]["tokenized_stock_candidate"]["status"], "NOT_READY")
        self.assertEqual(
            model["feature_contract"]["ordered_names"],
            list(DAILY_DIRECTION_FEATURE_NAMES),
        )
        self.assertGreater(metrics["classes"]["crypto"]["test"]["samples"], 40)
        self.assertFalse(model["authority"]["live_trading_authorized"])
        self.assertEqual(metrics["mode"], "RESEARCH_DIAGNOSTICS_ONLY")
        self.assertFalse(metrics["authority"]["automatic_model_promotion_authorized"])
        self.assertFalse(metrics["authority"]["live_trading_authorized"])

    def test_rejects_rows_marked_audit_false(self) -> None:
        rows = [
            {
                "asset_class": "crypto",
                "symbol": "BADUSDT",
                "audit_ok": False,
                "open_time_ms": day * DAY_MS,
                "close": 100 + day,
                "quote_volume": 1000,
            }
            for day in range(500)
        ]
        config = {
            "feature_names": list(DAILY_DIRECTION_FEATURE_NAMES),
            "asset_classes": ["crypto"],
            "minimum_train_samples": 10,
            "minimum_test_samples": 5,
            "max_train_samples_per_class": 100,
            "max_test_samples_per_class": 100,
            "epochs": 1,
            "learning_rate": 0.1,
            "l2": 0.0,
            "target": "next_complete_daily_close_up",
        }
        model, _ = train_daily_direction_models(
            rows,
            training_config=config,
            data_sha256="b" * 64,
            end_exclusive_ms=600 * DAY_MS,
            generated_at_utc="2026-08-22T00:00:00Z",
        )
        self.assertEqual(model["status"], "NOT_READY")

    def test_feature_contract_rejects_reordered_or_renamed_labels(self) -> None:
        config = {
            "feature_names": list(reversed(DAILY_DIRECTION_FEATURE_NAMES)),
            "asset_classes": ["crypto"],
            "minimum_train_samples": 10,
            "minimum_test_samples": 5,
            "max_train_samples_per_class": 100,
            "max_test_samples_per_class": 100,
            "epochs": 1,
            "learning_rate": 0.1,
            "l2": 0.0,
            "target": "next_complete_daily_close_up",
        }
        with self.assertRaisesRegex(ValueError, "feature contract mismatch"):
            train_daily_direction_models(
                [],
                training_config=config,
                data_sha256="c" * 64,
                end_exclusive_ms=600 * DAY_MS,
                generated_at_utc="2026-08-22T00:00:00Z",
            )


if __name__ == "__main__":
    unittest.main()
