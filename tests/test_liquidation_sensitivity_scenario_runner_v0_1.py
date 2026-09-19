from __future__ import annotations

import unittest

from crypto_autopilot.research.liquidation_quality_context_v0_1 import (
    build_liquidation_quality_context,
)
from crypto_autopilot.research.liquidation_sensitivity_scenario_runner_v0_1 import (
    SCENARIOS,
    LiquidationSensitivityScenarioRunnerPolicy,
    run_liquidation_sensitivity_scenarios,
)


def sample_snapshot():
    rows = [
        ("LONG_LIQUIDATED", 1, 100),
        ("SHORT_LIQUIDATED", 2, 200),
        ("LONG_LIQUIDATED", 4, 300),
        ("SHORT_LIQUIDATED", 3, 400),
    ]
    evidence = []
    for side, quantity, offset in rows:
        evidence.append({
            "exchange": "binance",
            "symbol": "BTCUSDT",
            "coverage_quality": "UPSTREAM_DECLARED_THROTTLED_SNAPSHOT",
            "side_semantics": side,
            "event_timestamp_ms": 8000 + offset,
            "observed_at_ms": 8001 + offset,
            "available_at_ms": 8002 + offset,
            "price": 100,
            "quantity": quantity,
        })
    return build_liquidation_quality_context(
        symbol="BTCUSDT",
        as_of_ms=10_000,
        input_class="synthetic_fixture",
        evidence=evidence,
    )


class LiquidationSensitivityScenarioRunnerV01Tests(unittest.TestCase):
    def test_runs_fixed_scenarios_deterministically(self):
        one = run_liquidation_sensitivity_scenarios(snapshot=sample_snapshot(), venue="binance")
        two = run_liquidation_sensitivity_scenarios(snapshot=sample_snapshot(), venue="binance")
        self.assertEqual(one, two)
        self.assertEqual(one["scenario_count"], 8)
        self.assertEqual(tuple(row["scenario"] for row in one["scenarios"]), SCENARIOS)
        self.assertFalse(one["random_sampling_used"])
        self.assertIsNone(one["estimated_real_missingness_rate"])
        self.assertIsNone(one["correction_weight"])

    def test_expected_drop_sets(self):
        result = run_liquidation_sensitivity_scenarios(snapshot=sample_snapshot(), venue="binance")
        rows = {row["scenario"]: row["drop_event_indices"] for row in result["scenarios"]}
        self.assertEqual(rows["drop_first"], [0])
        self.assertEqual(rows["drop_last"], [3])
        self.assertEqual(rows["drop_largest_long"], [2])
        self.assertEqual(rows["drop_largest_short"], [3])
        self.assertEqual(rows["drop_every_second"], [1, 3])
        self.assertEqual(rows["drop_all_long"], [0, 2])
        self.assertEqual(rows["drop_all_short"], [1, 3])
        self.assertEqual(rows["drop_all_events"], [0, 1, 2, 3])

    def test_all_events_is_zero_observation_stress(self):
        result = run_liquidation_sensitivity_scenarios(snapshot=sample_snapshot(), venue="binance")
        all_events = next(row for row in result["scenarios"] if row["scenario"] == "drop_all_events")
        self.assertEqual(all_events["sensitivity"]["event_count"]["degraded"], 0)
        self.assertEqual(all_events["sensitivity"]["event_count"]["retention_ratio"], 0.0)

    def test_non_synthetic_fails_closed(self):
        snapshot = sample_snapshot()
        snapshot["input_class"] = "existing_non_holdout_fixture"
        with self.assertRaises(ValueError):
            run_liquidation_sensitivity_scenarios(snapshot=snapshot, venue="binance")

    def test_requires_both_sides_and_multiple_events(self):
        snapshot = sample_snapshot()
        snapshot["events"] = snapshot["events"][:1]
        with self.assertRaises(ValueError):
            run_liquidation_sensitivity_scenarios(snapshot=snapshot, venue="binance")

    def test_policy_cannot_expand_authority(self):
        with self.assertRaises(ValueError):
            LiquidationSensitivityScenarioRunnerPolicy(signal_generation_authorized=True)


if __name__ == "__main__":
    unittest.main()
