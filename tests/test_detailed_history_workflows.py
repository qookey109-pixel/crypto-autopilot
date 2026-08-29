from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DetailedHistoryWorkflowTests(unittest.TestCase):
    def test_backfill_workflow_is_serialized_r2_only_and_has_no_trading_secret(self) -> None:
        text = (
            ROOT / ".github/workflows/binance-usdm-detailed-history-v0-1.yml"
        ).read_text()
        self.assertIn('cron: "23 */6 4-30 9 *"', text)
        self.assertIn("binance_usdm_detailed_history_v0_1_2.json", text)
        self.assertIn("crypto-core-100-v0-1-2-authority.json", text)
        self.assertIn("cancel-in-progress: false", text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("R2_SECRET_ACCESS_KEY", text)
        self.assertNotIn("PIONEX_API_KEY", text)
        self.assertNotIn("BINANCE_API_KEY", text)
        self.assertNotIn("place_order", text.lower())
        self.assertNotIn("/api/v1/trade", text)

    def test_training_workflow_reads_complete_dataset_and_never_promotes(self) -> None:
        text = (
            ROOT / ".github/workflows/binance-usdm-detailed-training-v0-1.yml"
        ).read_text()
        self.assertIn('cron: "37 4 * * 0"', text)
        self.assertIn("binance_usdm_detailed_history_v0_1_2.json", text)
        self.assertIn("train_binance_detailed_history_models.py", text)
        self.assertIn("automatic_model_promotion_authorized", text)
        self.assertIn("live_trading_authorized", text)
        self.assertNotIn("PIONEX_API_KEY", text)
        self.assertNotIn("place_order", text.lower())


if __name__ == "__main__":
    unittest.main()
