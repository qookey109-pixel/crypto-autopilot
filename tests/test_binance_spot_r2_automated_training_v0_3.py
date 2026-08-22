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
        self.online_pass = json.loads(
            Path(
                "research/receipts/2026-08-22-binance-spot-r2-automated-training-v0-3-pass.json"
            ).read_text()
        )
        self.workflow = Path(
            ".github/workflows/binance-spot-r2-automated-training-v0-3.yml"
        ).read_text()
        self.retirement = json.loads(
            Path(
                "research/receipts/2026-08-22-r2-only-local-artifact-retirement-v0-3.json"
            ).read_text()
        )

    def test_exact_online_authority_and_no_trade_boundary(self) -> None:
        self.assertEqual(
            self.config["status"], "R2_FIRST_AUTOMATED_TRAINING_AUTHORIZED_ON_MAIN_MERGE"
        )
        self.assertEqual(self.authority["status"], "AUTHORIZED_ON_MAIN_MERGE")
        self.assertEqual(
            self.config["source"]["market_data_base_url"],
            "https://data-api.binance.vision",
        )
        boundary = self.config["authority"]
        storage = self.config["storage"]
        self.assertEqual(storage["persistent_store"], "cloudflare_r2_only")
        self.assertFalse(storage["local_persistent_artifacts_authorized"])
        self.assertTrue(storage["github_actions_ephemeral_workspace_authorized"])
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

    def test_daily_workflow_is_retired_without_provider_or_r2_execution(self) -> None:
        self.assertIn("V0.3 — RETIRED", self.workflow)
        self.assertIn("V0.5 governance", self.workflow)
        self.assertNotIn("schedule:", self.workflow)
        self.assertNotIn("CLOUDFLARE_ACCOUNT_ID", self.workflow)
        self.assertNotIn("discover_binance_training_universe.py", self.workflow)
        self.assertIn("37 2 * * 0", self.workflow)

    def test_online_pass_records_verified_r2_publish_without_trade_authority(self) -> None:
        self.assertEqual(self.online_pass["status"], "PASS")
        self.assertEqual(self.online_pass["workflow_run"]["conclusion"], "success")
        self.assertEqual(self.online_pass["dataset"]["row_count"], 701275)
        self.assertTrue(self.online_pass["r2_publish"]["latest_pointer_written_last"])
        self.assertTrue(
            self.online_pass["r2_publish"]["all_objects_round_trip_sha256_verified"]
        )
        self.assertFalse(self.online_pass["authority"]["live_trading_authorized"])

    def test_local_artifact_retirement_is_bound_to_verified_r2_run(self) -> None:
        self.assertEqual(self.retirement["status"], "PASS")
        self.assertEqual(self.retirement["removed_local_generated_files"], 759)
        self.assertEqual(self.retirement["removed_local_generated_file_bytes"], 207898718)
        self.assertEqual(
            self.retirement["canonical_r2_dataset_sha256"],
            self.online_pass["dataset"]["parquet_sha256"],
        )
        self.assertFalse(self.retirement["authority"]["local_persistent_artifacts_authorized"])


if __name__ == "__main__":
    unittest.main()
