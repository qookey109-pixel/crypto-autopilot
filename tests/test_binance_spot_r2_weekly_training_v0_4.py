from __future__ import annotations

import json
import unittest
from pathlib import Path


class BinanceSpotR2WeeklyTrainingV04Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(
            Path("config/binance_spot_r2_weekly_training_v0_4.json").read_text()
        )
        self.weekly = Path(
            ".github/workflows/binance-spot-r2-weekly-training-v0-4.yml"
        ).read_text()
        self.monthly = Path(
            ".github/workflows/binance-spot-r2-monthly-universe-review-v0-4.yml"
        ).read_text()

    def test_weekly_and_monthly_schedules_are_exact(self) -> None:
        self.assertEqual(self.config["schedule"]["cron_utc"], "37 2 * * 0")
        self.assertIn('cron: "37 2 * * 0"', self.weekly)
        self.assertNotIn('cron: "37 2 * * *"', self.weekly)
        self.assertEqual(
            self.config["monthly_universe_review"]["cron_utc"],
            "37 3 1 * *",
        )
        self.assertIn('cron: "37 3 1 * *"', self.monthly)

    def test_both_workflows_guard_before_provider_and_r2(self) -> None:
        for workflow in (self.weekly, self.monthly):
            guard = workflow.index("Check frozen holdout boundary")
            provider = workflow.index(
                "Discover public Binance Spot training catalog"
                if "Weekly Training" in workflow
                else "Discover current public Binance Spot catalog"
            )
            secret = workflow.index("CLOUDFLARE_ACCOUNT_ID")
            self.assertLess(guard, provider)
            self.assertLess(guard, secret)
            self.assertIn("Remove ephemeral workspace outputs", workflow)

    def test_research_reviews_do_not_expand_authority(self) -> None:
        authority = self.config["authority"]
        self.assertTrue(authority["walk_forward_research_diagnostics_authorized"])
        self.assertTrue(authority["monthly_classification_review_authorized"])
        for key in (
            "formal_backtest_admission_authorized",
            "automatic_model_promotion_authorized",
            "historical_universe_membership_authorized",
            "holdout_access_authorized",
            "source_switch_authorized",
            "automatic_trade_plan_authorized",
            "real_money_order_authorized",
            "live_trading_authorized",
        ):
            self.assertFalse(authority[key], key)


if __name__ == "__main__":
    unittest.main()
