from __future__ import annotations

import json
import unittest
from pathlib import Path


class BinanceSpotR2AutomatedTrainingV03Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(
            Path("config/binance_spot_r2_automated_training_v0_3.json").read_text()
        )
        self.authority = json.loads(
            Path(
                "research/receipts/2026-08-22-binance-spot-r2-automated-training-v0-3-authority.json"
            ).read_text()
        )
        self.workflow = Path(
            ".github/workflows/binance-spot-r2-automated-training-v0-3.yml"
        ).read_text()

    def test_exact_online_authority_and_no_trade_boundary(self) -> None:
        self.assertEqual(
            self.config["status"], "R2_FIRST_AUTOMATED_TRAINING_AUTHORIZED_ON_MAIN_MERGE"
        )
        self.assertEqual(self.authority["status"], "AUTHORIZED_ON_MAIN_MERGE")
        boundary = self.config["authority"]
        self.assertTrue(boundary["production_r2_writes_authorized_for_exact_namespaces"])
        self.assertTrue(boundary["automated_research_model_training_authorized"])
        for key in (
            "source_switch_authorized",
            "holdout_access_authorized",
            "automatic_trade_plan_authorized",
            "real_money_order_authorized",
            "live_trading_authorized",
        ):
            self.assertFalse(boundary[key])

    def test_workflow_is_scheduled_and_guards_before_secrets(self) -> None:
        self.assertIn("branches: [main]", self.workflow)
        self.assertIn('cron: "37 2 * * *"', self.workflow)
        guard = self.workflow.index("Check frozen holdout boundary")
        secret = self.workflow.index("CLOUDFLARE_ACCOUNT_ID")
        self.assertLess(guard, secret)
        self.assertIn("secrets.R2_SECRET_ACCESS_KEY", self.workflow)
        self.assertNotIn("web/data/binance-spot", self.workflow)


if __name__ == "__main__":
    unittest.main()
