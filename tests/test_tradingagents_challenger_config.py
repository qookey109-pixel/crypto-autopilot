from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "tradingagents_research_challenger_v0_1.json"
RECEIPT = (
    ROOT
    / "research"
    / "receipts"
    / "2026-09-15-tradingagents-research-challenger-v0-1-prepared.json"
)


class TradingAgentsChallengerConfigTests(unittest.TestCase):
    def test_config_and_receipt_are_bound_and_fail_closed(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        digest = hashlib.sha256(CONFIG.read_bytes()).hexdigest()

        self.assertEqual(receipt["config"]["sha256"], digest)
        self.assertEqual(config["status"], "PREPARED_RESEARCH_ONLY")
        self.assertFalse(config["upstream"]["vendored"])
        self.assertFalse(config["upstream"]["runtime_dependency_added"])
        self.assertFalse(config["execution"]["upstream_installation_authorized"])
        self.assertFalse(config["execution"]["llm_api_calls_authorized"])
        self.assertFalse(config["execution"]["github_schedule_authorized"])
        self.assertFalse(config["authority"]["holdout_access_authorized"])
        self.assertFalse(config["authority"]["trade_plan_authorized"])
        self.assertFalse(config["authority"]["live_trading_authorized"])


if __name__ == "__main__":
    unittest.main()
