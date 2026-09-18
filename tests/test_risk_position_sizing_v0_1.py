from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

from crypto_autopilot.risk import (
    PositionSizingPolicy,
    plan_position_size,
    position_sizing_policy_from_config,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "risk_position_sizing_v0_1.json"


class RiskPositionSizingV01Tests(unittest.TestCase):
    def test_long_target_risk_is_derived_from_supplied_stop(self) -> None:
        plan = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
        )

        self.assertEqual(plan.status, "SIZING_READY")
        self.assertEqual(plan.reason, "target_risk_fully_deployed")
        self.assertAlmostEqual(plan.stop_distance_fraction, 0.01)
        self.assertAlmostEqual(plan.target_risk_usd, 1.0)
        self.assertAlmostEqual(plan.realized_risk_usd, 1.0)
        self.assertAlmostEqual(plan.target_notional_usd, 100.0)
        self.assertAlmostEqual(plan.approved_notional_usd, 100.0)
        self.assertAlmostEqual(plan.required_leverage, 1.0)
        self.assertAlmostEqual(plan.realized_leverage, 1.0)
        self.assertAlmostEqual(plan.risk_utilization_fraction, 1.0)
        self.assertEqual(plan.stop_price, 99.0)
        self.assertTrue(plan.stop_preserved)

    def test_short_research_sizing_is_symmetric_without_execution_authority(self) -> None:
        plan = plan_position_size(
            direction="SHORT",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=101.0,
        )

        self.assertEqual(plan.status, "SIZING_READY")
        self.assertEqual(plan.direction, "SHORT")
        self.assertAlmostEqual(plan.target_risk_usd, 1.0)
        self.assertAlmostEqual(plan.realized_risk_usd, 1.0)
        self.assertEqual(plan.stop_price, 101.0)

    def test_leverage_cap_reduces_position_instead_of_tightening_stop(self) -> None:
        plan = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.8,
        )

        self.assertEqual(plan.status, "SIZING_READY")
        self.assertEqual(plan.reason, "size_clipped_to_constraints")
        self.assertAlmostEqual(plan.target_risk_usd, 1.0)
        self.assertAlmostEqual(plan.target_notional_usd, 500.0)
        self.assertAlmostEqual(plan.required_leverage, 5.0)
        self.assertAlmostEqual(plan.approved_notional_usd, 300.0)
        self.assertAlmostEqual(plan.realized_leverage, 3.0)
        self.assertAlmostEqual(plan.realized_risk_usd, 0.6)
        self.assertAlmostEqual(plan.risk_utilization_fraction, 0.6)
        self.assertEqual(plan.clipped_by, ("max_leverage",))
        self.assertEqual(plan.stop_price, 99.8)
        self.assertTrue(plan.stop_preserved)

    def test_maximum_notional_cap_reduces_realized_risk(self) -> None:
        plan = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
            policy=PositionSizingPolicy(maximum_notional_usd=50.0),
        )

        self.assertEqual(plan.status, "SIZING_READY")
        self.assertEqual(plan.clipped_by, ("maximum_notional_usd",))
        self.assertAlmostEqual(plan.target_notional_usd, 100.0)
        self.assertAlmostEqual(plan.approved_notional_usd, 50.0)
        self.assertAlmostEqual(plan.target_risk_usd, 1.0)
        self.assertAlmostEqual(plan.realized_risk_usd, 0.5)
        self.assertAlmostEqual(plan.risk_utilization_fraction, 0.5)
        self.assertEqual(plan.stop_price, 99.0)

    def test_minimum_notional_never_forces_risk_budget_breach(self) -> None:
        plan = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=98.0,
            policy=PositionSizingPolicy(minimum_notional_usd=60.0),
        )

        self.assertEqual(plan.status, "NO_TRADE")
        self.assertEqual(plan.reason, "minimum_notional_exceeds_safe_size")
        self.assertAlmostEqual(plan.target_notional_usd, 50.0)
        self.assertEqual(plan.approved_notional_usd, 0.0)
        self.assertEqual(plan.realized_risk_usd, 0.0)
        self.assertEqual(plan.stop_price, 98.0)

    def test_directional_stop_validation_fails_closed(self) -> None:
        long_plan = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=101.0,
        )
        short_plan = plan_position_size(
            direction="SHORT",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
        )

        self.assertEqual(long_plan.status, "NO_TRADE")
        self.assertEqual(long_plan.reason, "invalid_long_stop")
        self.assertEqual(short_plan.status, "NO_TRADE")
        self.assertEqual(short_plan.reason, "invalid_short_stop")

    def test_daily_loss_and_position_count_gates_are_preserved(self) -> None:
        loss_plan = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
            realized_daily_r=-3.0,
        )
        count_plan = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
            new_positions_today=3,
        )

        self.assertEqual(loss_plan.reason, "daily_loss_gate")
        self.assertEqual(count_plan.reason, "daily_position_count_gate")

    def test_non_finite_runtime_values_fail_closed(self) -> None:
        for value in (math.nan, math.inf, -math.inf):
            plan = plan_position_size(
                direction="LONG",
                equity_usd=value,
                entry_price=100.0,
                stop_price=99.0,
            )
            self.assertEqual(plan.status, "NO_TRADE")
            self.assertEqual(plan.reason, "non_finite_risk_input")

    def test_versioned_config_matches_policy_defaults(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        policy = position_sizing_policy_from_config(payload)

        self.assertEqual(policy, PositionSizingPolicy())
        self.assertFalse(payload["behavior"]["tighten_stop_to_consume_target_risk"])
        self.assertTrue(payload["behavior"]["partial_risk_deployment_allowed"])
        self.assertFalse(payload["authority"]["paper_execution_authorized"])
        self.assertFalse(payload["authority"]["live_trading_authorized"])

    def test_config_parser_rejects_boolean_numeric_fields(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        payload["constraints"]["max_leverage"] = True

        with self.assertRaises(ValueError):
            position_sizing_policy_from_config(payload)


if __name__ == "__main__":
    unittest.main()
