from __future__ import annotations

import unittest

from crypto_autopilot.paper_simulation_demo import build_demo_payload


class PaperSimulationDemoTest(unittest.TestCase):
    def test_demo_is_deterministic_and_stays_inside_paper_boundary(self) -> None:
        first = build_demo_payload()
        second = build_demo_payload()

        self.assertEqual(first, second)
        self.assertEqual(first["status"], "PASS")
        self.assertEqual(first["mode"], "PAPER_ONLY")
        self.assertEqual(first["data_class"], "SYNTHETIC_FIXTURE")
        authority = first["authority"]
        self.assertIs(authority["trade_plans_auto_generated"], False)
        self.assertIs(authority["trade_plan_authorized"], False)
        self.assertIs(authority["real_money_order_authorized"], False)
        self.assertIs(authority["live_trading_authorized"], False)
        self.assertEqual(authority["provider_requests_performed"], 0)
        self.assertIs(authority["r2_reads_performed"], False)
        self.assertIs(authority["r2_writes_performed"], False)
        self.assertIs(authority["holdout_candles_accessed"], False)
        self.assertIs(authority["holdout_evaluated"], False)

    def test_demo_exercises_target_stop_costs_and_end_of_data(self) -> None:
        payload = build_demo_payload()
        metrics = payload["metrics"]
        trades = payload["trades"]

        self.assertEqual(metrics["trade_count"], 3)
        self.assertEqual(payload["rejected_plans"], [])
        self.assertEqual(
            [trade["exit_reason"] for trade in trades],
            ["target", "stop", "end_of_data"],
        )
        self.assertGreater(metrics["total_fees_usd"], 0)
        self.assertGreater(metrics["total_slippage_cost_usd"], 0)
        self.assertNotEqual(metrics["total_funding_usd"], 0)
        self.assertEqual(len(payload["equity_curve"]), 4)


if __name__ == "__main__":
    unittest.main()
