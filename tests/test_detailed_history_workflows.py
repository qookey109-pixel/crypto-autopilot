from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DetailedHistoryWorkflowTests(unittest.TestCase):
    def test_backfill_workflow_is_serialized_r2_only_and_has_no_trading_secret(self) -> None:
        current = (
            ROOT / ".github/workflows/binance-usdm-detailed-history-v0-1.yml"
        ).read_text()
        frozen = (
            ROOT
            / "research/frozen/workflows/2026-09-12-binance-usdm-detailed-history-v0-1.yml"
        ).read_text()

        self.assertIn('cron: "23 */2 9-30 9 *"', frozen)
        self.assertIn("python scripts/check_history_cadence_authority.py", frozen)
        self.assertIn("--repair-config config/bnx_archive_repair_v0_1.json", frozen)

        self.assertNotIn('cron: "23 */2 9-30 9 *"', current)
        self.assertNotIn("  backfill:", current)
        self.assertIn("RETIRED / REPAIR ONLY", current)
        self.assertIn("python scripts/check_core100_history_retirement_v0_1.py", current)
        self.assertIn("binance_usdm_detailed_history_v0_1_2.json", current)
        self.assertIn("crypto-core-100-v0-1-2-authority.json", current)
        self.assertIn("cancel-in-progress: false", current)
        self.assertIn("persist-credentials: false", current)
        self.assertIn("R2_SECRET_ACCESS_KEY", current)
        self.assertNotIn("PIONEX_API_KEY", current)
        self.assertNotIn("BINANCE_API_KEY", current)
        self.assertNotIn("place_order", current.lower())
        self.assertNotIn("/api/v1/trade", current)

    def test_training_workflow_reads_complete_dataset_and_never_promotes(self) -> None:
        text = (
            ROOT / ".github/workflows/binance-usdm-detailed-training-v0-1.yml"
        ).read_text()
        self.assertIn('cron: "37 4 * * 0"', text)
        self.assertIn("binance_usdm_detailed_history_v0_1_2.json", text)
        self.assertIn("train_binance_detailed_history_models_v0_4.py", text)
        self.assertIn("core100_training_fingerprint_v0_2_successor_v0_1.json", text)
        self.assertIn("bootstrap_v0_2", text)
        self.assertIn("CORE100_V02_BOOTSTRAP", text)
        self.assertIn("actions: read", text)
        self.assertIn("REVIEW_REQUIRED", text)
        self.assertIn("r2_writes_performed", text)
        self.assertNotIn("PIONEX_API_KEY", text)
        self.assertNotIn("place_order", text.lower())

        wrapper = (
            ROOT / "scripts/train_binance_detailed_history_models_v0_3.py"
        ).read_text()
        self.assertIn('V02 = ROOT / "scripts/train_binance_detailed_history_models_v0_2.py"', wrapper)
        self.assertIn("DEFAULT_FINGERPRINT_CONFIG", wrapper)
        self.assertIn("training_performed", wrapper)
        self.assertIn("r2_writes_performed", wrapper)


if __name__ == "__main__":
    unittest.main()
