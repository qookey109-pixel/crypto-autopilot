from __future__ import annotations

import copy
import unittest
from datetime import UTC, datetime, timedelta

from crypto_autopilot.training.detailed import FEATURE_NAMES, IntradayExample
from crypto_autopilot.training.effective_signal_audit_v0_1 import (
    EffectiveSignalAuditError,
    dependence_diagnostics,
    run_effective_signal_audit,
)


def _ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def _examples() -> list[IntradayExample]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    output: list[IntradayExample] = []
    trend_index = FEATURE_NAMES.index("ema20_vs_ema50_1h")
    volatility_index = FEATURE_NAMES.index("atr_percentile_1h")
    for step in range(30):
        time_ms = _ms(start + timedelta(hours=2 * step))
        for symbol_index, symbol in enumerate(("AAAUSDT", "BBBUSDT")):
            label = int((step + symbol_index) % 3 == 0)
            features = [
                (index + 1) * 0.01 + step * 0.001 + symbol_index * 0.0005 + label * 0.002
                for index in range(len(FEATURE_NAMES))
            ]
            features[trend_index] = 0.01 if step % 2 == 0 else -0.01
            features[volatility_index] = (0.2, 0.5, 0.8)[step % 3]
            output.append(
                IntradayExample(
                    symbol=symbol,
                    asset_class="crypto",
                    time_ms=time_ms,
                    features=tuple(features),
                    label=label,
                    forward_return=0.003 if label else -0.001,
                )
            )
    return output


def _training_config() -> dict:
    return {
        "forward_horizon_15m_bars": 16,
        "walk_forward_folds": [
            {
                "name": "fold-1",
                "train_end_exclusive": "2024-01-02T00:00:00Z",
                "test_end_exclusive": "2024-01-03T00:00:00Z",
            },
            {
                "name": "fold-2",
                "train_end_exclusive": "2024-01-03T00:00:00Z",
                "test_end_exclusive": "2024-01-04T00:00:00Z",
            },
        ],
    }


def _policy() -> dict:
    return {
        "lineage": {
            "expected_example_count": 60,
            "expected_symbol_count": 2,
            "source_end_exclusive_utc": "2024-02-01T00:00:00Z",
            "replacement_holdout_start_utc": "2024-03-01T00:00:00Z",
        },
        "diagnostics": {
            "top_n": 5,
            "minimum_symbol_count_per_fold_side": 1,
            "feature_correlation_sample_limit": 20,
            "feature_correlation_threshold": 0.95,
        },
        "authority": {
            "production_r2_training_reads_authorized": True,
            "provider_requests_authorized": False,
            "r2_writes_authorized": False,
            "holdout_access_authorized": False,
            "training_authorized": False,
            "training_publication_authorized": False,
            "strategy_parameter_change_authorized": False,
            "source_switch_authorized": False,
            "automatic_model_promotion_authorized": False,
            "formal_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }


class EffectiveSignalAuditTests(unittest.TestCase):
    def test_report_is_aggregate_only_and_measures_actual_overlap(self) -> None:
        report = run_effective_signal_audit(
            _examples(),
            training_config=_training_config(),
            dataset_fingerprint="fixture-fingerprint",
            expected_dataset_fingerprint="fixture-fingerprint",
            generated_at_utc="2026-09-15T00:00:00Z",
            policy=_policy(),
        )

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["example_count"], 60)
        self.assertEqual(report["symbol_count"], 2)
        self.assertAlmostEqual(
            report["dependence_diagnostics"]["same_symbol_overlap_fraction"], 1.0
        )
        clusters = report["dependence_diagnostics"]["timestamp_clusters"]
        self.assertEqual(clusters["unique_timestamp_count"], 30)
        self.assertEqual(clusters["maximum_examples_at_one_timestamp"], 2)
        self.assertEqual(len(report["walk_forward_folds"]), 2)
        self.assertTrue(report["feature_redundancy"]["top_high_correlation_pairs"])
        self.assertFalse(report["authority"]["holdout_accessed"])
        self.assertFalse(report["authority"]["r2_writes_performed"])
        self.assertFalse(report["authority"]["training_performed"])
        self.assertIn("KEEP_HOLDOUT_CLOSED", report["recommendations"])

    def test_exact_four_hour_spacing_is_not_counted_as_label_overlap(self) -> None:
        examples = _examples()[:2]
        first = examples[0]
        second = IntradayExample(
            symbol=first.symbol,
            asset_class=first.asset_class,
            time_ms=first.time_ms + 4 * 60 * 60 * 1000,
            features=first.features,
            label=first.label,
            forward_return=first.forward_return,
        )
        diagnostics = dependence_diagnostics(
            [first, second], label_horizon_ms=4 * 60 * 60 * 1000
        )
        self.assertEqual(diagnostics["same_symbol_adjacent_pairs"], 1)
        self.assertEqual(diagnostics["same_symbol_overlap_pairs"], 0)

    def test_fingerprint_mismatch_fails_closed(self) -> None:
        with self.assertRaisesRegex(EffectiveSignalAuditError, "fingerprint"):
            run_effective_signal_audit(
                _examples(),
                training_config=_training_config(),
                dataset_fingerprint="wrong",
                expected_dataset_fingerprint="expected",
                generated_at_utc="2026-09-15T00:00:00Z",
                policy=_policy(),
            )

    def test_trading_or_write_authority_cannot_be_enabled(self) -> None:
        policy = copy.deepcopy(_policy())
        policy["authority"]["live_trading_authorized"] = True
        with self.assertRaisesRegex(EffectiveSignalAuditError, "unsafe"):
            run_effective_signal_audit(
                _examples(),
                training_config=_training_config(),
                dataset_fingerprint="fixture-fingerprint",
                expected_dataset_fingerprint="fixture-fingerprint",
                generated_at_utc="2026-09-15T00:00:00Z",
                policy=policy,
            )


if __name__ == "__main__":
    unittest.main()
