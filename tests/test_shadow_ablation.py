from __future__ import annotations

import math
import unittest

from crypto_autopilot.experiment_registry import (
    build_experiment_registry_entry,
    validate_experiment_registry_entry,
)
from crypto_autopilot.shadow_ablation import FEATURE_GROUPS, run_shadow_ablation


def _rows(days: int = 260) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for symbol_index, symbol in enumerate(("AAAUSDT", "BBBUSDT")):
        close = 100.0 + symbol_index
        for day in range(days):
            previous = close
            close *= 1.0 + (0.002 if day % 4 else -0.001)
            rows.append(
                {
                    "asset_class": "crypto",
                    "symbol": symbol,
                    "audit_ok": True,
                    "open_time_ms": day * 86_400_000,
                    "open": previous,
                    "high": max(previous, close) * 1.002,
                    "low": min(previous, close) * 0.998,
                    "close": close,
                    "base_volume": 100.0 + day,
                    "quote_volume": 1000.0 + 10.0 * math.sin(day / 10),
                }
            )
    return rows


class ShadowAblationTests(unittest.TestCase):
    def _config(self) -> dict[str, object]:
        return {
            "status": "PREPARED_NOT_ACTIVE",
            "authority": {
                "provider_reads_authorized": False,
                "r2_writes_authorized": False,
                "automatic_model_promotion_authorized": False,
                "live_trading_authorized": False,
            },
            "training": {
                "warmup_bars": 100,
                "train_fraction": 0.7,
                "minimum_samples_per_split": 20,
                "regime_minimum_samples": 5,
                "calibration_bins": 10,
                "epochs": 2,
                "learning_rate": 0.08,
                "l2": 0.0001,
                "groups": {name: list(values) for name, values in FEATURE_GROUPS.items()},
            },
        }

    def test_shadow_is_deterministic_and_reports_all_groups(self) -> None:
        config = self._config()
        first = run_shadow_ablation(
            _rows(),
            config=config,
            data_sha256="a" * 64,
            config_sha256="b" * 64,
            end_exclusive_ms=300 * 86_400_000,
        )
        second = run_shadow_ablation(
            _rows(),
            config=config,
            data_sha256="a" * 64,
            config_sha256="b" * 64,
            end_exclusive_ms=300 * 86_400_000,
        )
        self.assertEqual(first, second)
        self.assertEqual(set(first["groups"]), set(FEATURE_GROUPS))
        self.assertFalse(first["authority"]["r2_writes_authorized"])
        self.assertFalse(first["bounded_search"]["automatic_promotion"])
        crypto = first["groups"]["trend"]["classes"]["crypto"]
        self.assertEqual(crypto["status"], "PASS")
        self.assertIn("ece", crypto["test"])
        self.assertIn("regimes", crypto)
        validate_experiment_registry_entry(first["experiment_registry"])

    def test_shadow_rejects_execution_authority(self) -> None:
        config = self._config()
        config["authority"]["r2_writes_authorized"] = True
        with self.assertRaisesRegex(ValueError, "authority boundary"):
            run_shadow_ablation(
                _rows(),
                config=config,
                data_sha256="a" * 64,
                config_sha256="b" * 64,
                end_exclusive_ms=300 * 86_400_000,
            )

    def test_registry_rejects_tampered_lineage_or_promotion(self) -> None:
        entry = build_experiment_registry_entry(
            comparison_key="spot/1d",
            dataset_sha256="a" * 64,
            config_sha256="b" * 64,
            trainer={"name": "trainer", "version": "0.1"},
            environment={"python": "3.13"},
            evaluation={"groups": ["baseline"]},
        )
        validate_experiment_registry_entry(entry)
        entry["promotion_eligible"] = True
        with self.assertRaisesRegex(ValueError, "promotion_eligible"):
            validate_experiment_registry_entry(entry)


if __name__ == "__main__":
    unittest.main()
