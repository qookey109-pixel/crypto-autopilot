"""Offline contract checks; no provider or R2 access."""
import json
from pathlib import Path
import unittest

from crypto_autopilot.paper.cloud_budget_v0_1 import CloudBudgetPolicy
from crypto_autopilot.paper.cloud_loop_v0_1 import MAXIMUM_START_DELAY_MS

ROOT = Path(__file__).resolve().parents[1]


class CloudPaperLoopContractTests(unittest.TestCase):
    def test_bounded_inactive_contract(self):
        policy = json.loads((ROOT / "config/cloud_paper_loop_v0_1.json").read_text())
        self.assertFalse(policy["activation"]["enabled"])
        self.assertEqual(policy["schedule"]["cron_utc"], "7,22,37,52 * * * *")
        self.assertEqual(policy["schedule"]["maximum_slots_per_utc_day"], 96)
        self.assertEqual(
            policy["schedule"]["stale_start_max_seconds"] * 1000,
            MAXIMUM_START_DELAY_MS,
        )
        self.assertEqual(policy["account"]["initial_equity_usd"], 10000)
        self.assertEqual(policy["budget"]["monthly_budget_usd"], 0)
        self.assertEqual(policy["budget"]["provider_requests_per_run"], 3 + 5 + 2 * 5)
        for key in ("provider_requests", "r2_class_a", "r2_class_b", "r2_new_bytes"):
            self.assertEqual(policy["budget"][key + "_per_utc_day"],
                             96 * policy["budget"][key + "_per_run"])
        storage = json.loads(
            (ROOT / "config/cloud_paper_storage_policy_v0_1.json").read_text()
        )
        budget = policy["budget"]
        self.assertEqual(storage["status"], "POLICY_ONLY_NOT_ACTIVATION_AUTHORITY")
        self.assertEqual(storage["scope"]["report_object_max_bytes"], budget["r2_object_max_bytes"])
        self.assertEqual(storage["scope"]["per_run_growth_max_bytes"], budget["r2_new_bytes_per_run"])
        self.assertEqual(storage["scope"]["per_utc_day_growth_max_bytes"], budget["r2_new_bytes_per_utc_day"])
        self.assertEqual(storage["scope"]["max_slots_per_utc_day"], policy["schedule"]["maximum_slots_per_utc_day"])
        self.assertEqual(
            storage["scope"]["max_31_day_growth_bytes"],
            storage["scope"]["per_utc_day_growth_max_bytes"] * 31,
        )
        self.assertLess(storage["scope"]["warning_threshold_bytes"], storage["scope"]["hard_stop_bytes"])
        self.assertEqual(
            CloudBudgetPolicy().r2_warning_bytes,
            storage["scope"]["warning_threshold_bytes"],
        )
        self.assertEqual(
            CloudBudgetPolicy().r2_hard_stop_bytes,
            storage["scope"]["hard_stop_bytes"],
        )
        self.assertFalse(storage["retention"]["automatic_delete"])
        self.assertFalse(storage["retention"]["manual_delete_authorized"])
        self.assertEqual(
            storage["retention"]["mode"],
            "INDEFINITE_APPEND_ONLY_UNTIL_SEPARATE_AUTHORITY",
        )
        self.assertFalse(storage["authority"]["activation_authorized"])

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
