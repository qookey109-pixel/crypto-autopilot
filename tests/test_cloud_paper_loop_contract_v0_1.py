"""Offline contract checks; no provider or R2 access."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CloudPaperLoopContractTests(unittest.TestCase):
    def test_bounded_inactive_contract(self):
        policy = json.loads((ROOT / "config/cloud_paper_loop_v0_1.json").read_text())
        self.assertFalse(policy["activation"]["enabled"])
        self.assertEqual(policy["schedule"]["cron_utc"], "7,22,37,52 * * * *")
        self.assertEqual(policy["schedule"]["maximum_slots_per_utc_day"], 96)
        self.assertEqual(policy["account"]["initial_equity_usd"], 10000)
        self.assertEqual(policy["budget"]["monthly_budget_usd"], 0)
        self.assertEqual(policy["budget"]["provider_requests_per_run"], 3 + 5 + 2 * 5)
        for key in ("provider_requests", "r2_class_a", "r2_class_b", "r2_new_bytes"):
            self.assertEqual(policy["budget"][key + "_per_utc_day"],
                             96 * policy["budget"][key + "_per_run"])
        for key in ("private_exchange_api", "real_money_order", "live_trading",
                    "holdout_access", "source_switch", "model_promotion",
                    "training", "strategy_parameter_changes"):
            self.assertIs(policy["authority"][key], False)

    def test_production_registry_has_no_fixture_or_rejected_strategy(self):
        registry = json.loads(
            (ROOT / "config/cloud_paper_strategy_registry_v0_1.json").read_text()
        )
        self.assertEqual(registry["strategies"], [])
        self.assertEqual(registry["model_quality"], "REJECT")
        self.assertFalse(registry["production_fixture_admission"])
        self.assertFalse(registry["automatic_promotion"])
