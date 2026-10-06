from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "prospective_shadow_collection_execution_v0_1.json"
RECEIPT = (
    ROOT
    / "research"
    / "receipts"
    / "2026-10-06-prospective-shadow-collection-execution-v0-1-authority.json"
)


class ProspectiveShadowCollectionExecutionAuthorityV01Tests(unittest.TestCase):
    def test_authority_is_research_only_and_bounded(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            payload["status"],
            "AUTHORIZED_NOT_ACTIVE_UNTIL_IMPLEMENTATION_MERGED",
        )
        self.assertEqual(payload["execution"]["cron_utc"], "17 */4 * * *")
        self.assertEqual(payload["providers"]["pionex"]["maximum_requests_per_run"], 8)
        self.assertEqual(
            payload["providers"]["coinpaprika"]["maximum_requests_per_run"],
            2,
        )
        self.assertEqual(payload["artifact_backend"]["retention_days"], 90)
        self.assertEqual(payload["zero_cost_policy"]["monthly_budget_usd"], 0)

    def test_high_risk_authorities_remain_closed(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        authority = payload["authority"]
        for key in (
            "r2_read_authorized",
            "r2_write_authorized",
            "d1_read_authorized",
            "d1_write_authorized",
            "holdout_access_authorized",
            "training_authorized",
            "model_promotion_authorized",
            "source_switch_authorized",
            "candidate_reranking_change_authorized",
            "strategy_router_threshold_change_authorized",
            "risk_change_authorized",
            "portfolio_admission_change_authorized",
            "paper_submission_authorized",
            "real_money_order_authorized",
            "live_trading_authorized",
            "local_runtime_authorized",
        ):
            self.assertFalse(authority[key], key)

    def test_public_research_and_artifact_scope_is_explicitly_authorized(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        authority = payload["authority"]
        self.assertTrue(authority["research_only"])
        self.assertTrue(authority["provider_public_fetch_authorized"])
        self.assertTrue(authority["github_actions_artifact_read_authorized"])
        self.assertTrue(authority["github_actions_artifact_write_authorized"])
        self.assertTrue(authority["workflow_dispatch_authorized"])
        self.assertTrue(authority["workflow_schedule_authorized"])

    def test_receipt_records_user_authorization_without_scope_expansion(self) -> None:
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(receipt["user_authorization"]["decision"], "AUTHORIZED")
        self.assertEqual(receipt["user_authorization"]["verbatim_reply"], "繼續吧")
        self.assertEqual(
            receipt["evidence_basis_main_sha"],
            "547dbd37cd6137e5ee46b862b82a3bbf395b6808",
        )
        self.assertFalse(
            receipt["safety_boundaries"]["live_trading_authorized"]
        )


if __name__ == "__main__":
    unittest.main()
