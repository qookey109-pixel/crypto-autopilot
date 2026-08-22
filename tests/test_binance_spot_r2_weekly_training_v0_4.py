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

    def test_historical_config_remains_v04_without_v05_policy(self) -> None:
        self.assertEqual(self.config["version"], "0.4.0")
        self.assertEqual(
            self.config["status"],
            "R2_ONLY_WEEKLY_MODEL_REVIEW_AUTHORIZED_ON_MAIN_MERGE",
        )
        self.assertNotIn("quality_gate", self.config["weekly_review"])
        self.assertEqual(self.config["storage"]["schema_version"], "v0.4")

    def test_v04_workflows_are_validation_only_retirement_checks(self) -> None:
        for workflow in (self.weekly, self.monthly):
            self.assertIn("V0.4 — RETIRED", workflow)
            self.assertNotIn("schedule:", workflow)
            self.assertNotIn("CLOUDFLARE_ACCOUNT_ID", workflow)
            self.assertNotIn("discover_binance_training_universe.py", workflow)
            self.assertNotIn("publish_binance_spot_training_to_r2.py", workflow)


if __name__ == "__main__":
    unittest.main()
