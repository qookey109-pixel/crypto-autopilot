from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = (
    ROOT
    / "research"
    / "receipts"
    / "2026-09-19-agentfeed-evaluation-v0-1.json"
)


class AgentFeedEvaluationV01Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(RECEIPT.read_text(encoding="utf-8"))

    def test_exact_candidate_and_upstream_lineage(self) -> None:
        self.assertEqual(
            self.payload["schema"],
            "external-capability-integration-evaluation-v0.1",
        )
        self.assertEqual(
            self.payload["status"],
            "EVALUATED_RESEARCH_ONLY_NOT_APPROVED_FOR_RUNTIME",
        )
        self.assertEqual(
            self.payload["candidate_provenance"]["capability_id"],
            "agentfeed",
        )
        self.assertEqual(
            self.payload["upstream"]["repository"],
            "seekdaseek/agentfeed",
        )
        self.assertEqual(
            self.payload["upstream"]["commit"],
            "0e1db87a65dc0cc0b890c2257e10e12cd3966cf7",
        )
        self.assertEqual(self.payload["upstream"]["license"], "MIT")

    def test_paid_wallet_surface_is_explicitly_rejected(self) -> None:
        upstream = self.payload["upstream"]
        decision = self.payload["overall_decision"]
        authority = self.payload["authority"]

        self.assertEqual(upstream["payment_protocol"], "x402")
        self.assertEqual(upstream["payment_asset"], "USDC")
        self.assertTrue(upstream["paid_runtime"])
        self.assertTrue(upstream["upstream_wallet_payment_supported"])
        self.assertTrue(decision["do_not_use_paid_runtime"])
        self.assertTrue(decision["do_not_create_or_fund_wallet"])
        self.assertTrue(decision["do_not_store_private_key"])
        self.assertFalse(authority["wallet_creation_authorized"])
        self.assertFalse(authority["wallet_funding_authorized"])
        self.assertFalse(authority["private_key_access_authorized"])
        self.assertFalse(authority["x402_payment_authorized"])
        self.assertFalse(authority["paid_call_authorized"])

    def test_liquidation_coverage_is_not_treated_as_uniform(self) -> None:
        decision = self.payload["overall_decision"]
        component = self.payload["component_evaluation"][
            "historical_liquidation_tape"
        ]

        self.assertTrue(
            decision["do_not_treat_cross_venue_liquidation_coverage_as_uniform"]
        )
        self.assertEqual(
            component["decision"],
            "RESEARCH_CANDIDATE_WITH_VENUE_QUALITY_FLAGS_REQUIRED",
        )

    def test_composite_scores_cannot_become_strategy_authority(self) -> None:
        decision = self.payload["overall_decision"]
        authority = self.payload["authority"]

        self.assertTrue(decision["do_not_use_composite_scores_as_strategy_authority"])
        self.assertFalse(authority["strategy_router_integration_authorized"])
        self.assertFalse(authority["daily_opportunity_integration_authorized"])
        self.assertFalse(authority["formal_trade_plan_authorized"])
        self.assertFalse(authority["real_money_order_authorized"])
        self.assertFalse(authority["live_real_trading_authorized"])

    def test_evaluation_grants_zero_operational_authority(self) -> None:
        authority = self.payload["authority"]
        self.assertTrue(authority)
        self.assertTrue(all(value is False for value in authority.values()))


if __name__ == "__main__":
    unittest.main()
