from __future__ import annotations

import json
import unittest
from pathlib import Path

from crypto_autopilot.research.liquidation_coverage_sensitivity_v0_1 import (
    DECISION,
    LiquidationCoverageSensitivityPolicy,
    assess_liquidation_coverage_sensitivity,
    liquidation_coverage_sensitivity_policy_from_config,
)
from crypto_autopilot.research.liquidation_quality_context_v0_1 import (
    build_liquidation_quality_context,
)
from crypto_autopilot.research.venue_local_liquidation_summary_v0_1 import (
    build_venue_local_liquidation_summary,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "liquidation_coverage_sensitivity_v0_1.json"


def summary(events):
    context = build_liquidation_quality_context(
        symbol="BTCUSDT",
        as_of_ms=10_000,
        input_class="synthetic_fixture",
        evidence=events,
    )
    return build_venue_local_liquidation_summary(
        snapshot=context,
        venue="binance",
    )


class LiquidationCoverageSensitivityV01Tests(unittest.TestCase):
    def test_reports_retention_without_creating_weight(self) -> None:
        reference = summary(
            [
                {
                    "exchange": "binance",
                    "symbol": "BTCUSDT",
                    "coverage_quality": "UPSTREAM_DECLARED_THROTTLED_SNAPSHOT",
                    "side_semantics": "LONG_LIQUIDATED",
                    "event_timestamp_ms": 9000,
                    "observed_at_ms": 9001,
                    "available_at_ms": 9002,
                    "price": 100,
                    "quantity": 4,
                },
                {
                    "exchange": "binance",
                    "symbol": "BTCUSDT",
                    "coverage_quality": "UPSTREAM_DECLARED_THROTTLED_SNAPSHOT",
                    "side_semantics": "SHORT_LIQUIDATED",
                    "event_timestamp_ms": 9100,
                    "observed_at_ms": 9101,
                    "available_at_ms": 9102,
                    "price": 100,
                    "quantity": 2,
                },
            ]
        )
        degraded = summary(
            [
                {
                    "exchange": "binance",
                    "symbol": "BTCUSDT",
                    "coverage_quality": "DEGRADED_OR_UNKNOWN",
                    "side_semantics": "SHORT_LIQUIDATED",
                    "event_timestamp_ms": 9100,
                    "observed_at_ms": 9101,
                    "available_at_ms": 9102,
                    "price": 100,
                    "quantity": 2,
                }
            ]
        )

        result = assess_liquidation_coverage_sensitivity(
            reference_summary=reference,
            degraded_summary=degraded,
        )

        self.assertEqual(result["decision"], DECISION)
        self.assertEqual(result["event_count"]["retention_ratio"], 0.5)
        self.assertAlmostEqual(
            result["notional_metrics"]["gross_liquidated_notional_usd"][
                "retention_ratio"
            ],
            1 / 3,
        )
        self.assertTrue(result["side_imbalance"]["sign_changed"])
        self.assertIsNone(result["correction_weight"])
        self.assertIsNone(result["estimated_real_missingness_rate"])
        self.assertFalse(
            result["authority"]["coverage_weighting_authorized"]
        )

    def test_real_or_non_synthetic_input_fails_closed(self) -> None:
        synthetic = summary([])
        for input_class in (
            "existing_non_holdout_fixture",
            "provider_live",
            "replacement_holdout",
        ):
            with self.subTest(input_class=input_class):
                bad = {**synthetic, "input_class": input_class}
                with self.assertRaises(ValueError):
                    assess_liquidation_coverage_sensitivity(
                        reference_summary=bad,
                        degraded_summary=bad,
                    )

    def test_cross_venue_comparison_fails_closed(self) -> None:
        one = summary([])
        other = {**one, "venue": "okx"}
        with self.assertRaises(ValueError):
            assess_liquidation_coverage_sensitivity(
                reference_summary=one,
                degraded_summary=other,
            )

    def test_misaligned_symbol_or_time_fails_closed(self) -> None:
        one = summary([])
        for bad in (
            {**one, "symbol": "ETHUSDT"},
            {**one, "as_of_ms": 10_001},
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    assess_liquidation_coverage_sensitivity(
                        reference_summary=one,
                        degraded_summary=bad,
                    )

    def test_degraded_fixture_cannot_add_events(self) -> None:
        reference = summary([])
        degraded = {**reference, "event_count": 1}
        with self.assertRaises(ValueError):
            assess_liquidation_coverage_sensitivity(
                reference_summary=reference,
                degraded_summary=degraded,
            )

    def test_zero_reference_metric_has_no_retention_ratio(self) -> None:
        zero = summary([])
        result = assess_liquidation_coverage_sensitivity(
            reference_summary=zero,
            degraded_summary=zero,
        )
        self.assertIsNone(result["event_count"]["retention_ratio"])
        self.assertIsNone(
            result["notional_metrics"]["gross_liquidated_notional_usd"][
                "retention_ratio"
            ]
        )

    def test_config_keeps_real_missingness_and_weights_closed(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            liquidation_coverage_sensitivity_policy_from_config(payload),
            LiquidationCoverageSensitivityPolicy(),
        )
        self.assertTrue(payload["policy"]["synthetic_sensitivity_authorized"])
        self.assertTrue(
            all(
                value is False
                for key, value in payload["policy"].items()
                if key != "synthetic_sensitivity_authorized"
            )
        )


if __name__ == "__main__":
    unittest.main()
