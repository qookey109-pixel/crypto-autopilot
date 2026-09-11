from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "config/pionex_funding_history_v0_1.json"
EXEC_CONFIG = ROOT / "config/pionex_funding_history_execution_v0_1.json"
RECEIPT = ROOT / "research/receipts/2026-09-11-pionex-funding-history-execution-v0-1-authority.json"
RUNNER = ROOT / "scripts/run_pionex_funding_history_v0_1.py"
PROTOCOL_SHA256 = "9117e707203b35ef9d7420b96033cd339b97c549f03e3cdae2ecece4637b6834"
EXEC_CONFIG_SHA256 = "d2cdafc5900573eb7d9971b7e3d7b9e5e34f50d16a510b56dcd7e0512b5e3315"


class PionexFundingHistoryExecutionV01Tests(unittest.TestCase):
    def test_configs_are_exactly_sha_bound(self) -> None:
        self.assertEqual(hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(), PROTOCOL_SHA256)
        self.assertEqual(hashlib.sha256(EXEC_CONFIG.read_bytes()).hexdigest(), EXEC_CONFIG_SHA256)
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(receipt["protocol_config_sha256"], PROTOCOL_SHA256)
        self.assertEqual(receipt["execution_config_sha256"], EXEC_CONFIG_SHA256)

    def test_execution_is_public_bounded_and_not_wired(self) -> None:
        config = json.loads(EXEC_CONFIG.read_text(encoding="utf-8"))
        execution = config["execution"]
        authority = config["authority"]
        self.assertEqual(execution["requests_per_second"], 3)
        self.assertEqual(execution["request_timeout_seconds"], 15)
        self.assertEqual(execution["automatic_retries"], 0)
        self.assertFalse(execution["workflow_wiring_included_by_this_stage"])
        self.assertTrue(authority["public_pionex_funding_reads_after_merge"])
        self.assertFalse(authority["private_api"])
        self.assertFalse(authority["r2_read"])
        self.assertFalse(authority["r2_write"])
        self.assertFalse(authority["holdout_access"])
        self.assertFalse(authority["simulation_data_admission"])
        self.assertFalse(authority["live_trading"])

    def test_protocol_remains_exact_fixed_window(self) -> None:
        protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        source = protocol["source"]
        self.assertEqual(source["symbol"], "BTC_USDT_PERP")
        self.assertEqual(source["start_utc"], "2026-08-01T00:00:00Z")
        self.assertEqual(source["end_exclusive_utc"], "2026-08-28T00:00:00Z")
        self.assertEqual(source["page_limit"], 500)
        self.assertEqual(source["maximum_requests"], 3)
        self.assertEqual(source["retry_count"], 0)
        self.assertFalse(protocol["completeness"]["fixed_cadence_assumption"])
        self.assertFalse(protocol["completeness"]["zero_funding_fill"])

    def test_runner_is_secret_free_and_main_manual_only(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn('"GITHUB_EVENT_NAME": "workflow_dispatch"', text)
        self.assertIn('"GITHUB_REF": "refs/heads/main"', text)
        self.assertIn('"GITHUB_RUN_ATTEMPT": "1"', text)
        self.assertNotIn("secrets.", text)
        self.assertNotIn("PIONEX-KEY", text)
        self.assertNotIn("R2_", text)
        self.assertIn("simulation_data_admission_authorized", text)
        self.assertIn("formal_backtest_admission_authorized", text)


if __name__ == "__main__":
    unittest.main()
