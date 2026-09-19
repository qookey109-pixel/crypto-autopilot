from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = (
    ROOT
    / "research"
    / "receipts"
    / "2026-09-19-crypto-market-data-mcp-evaluation-v0-1.json"
)


class CryptoMarketDataMcpEvaluationV01Tests(unittest.TestCase):
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
            self.payload["crypto_autopilot_base_main_sha"],
            "b1aaddcfe61d1e90c805a0826d3c62351a8d874a",
        )
        self.assertEqual(
            self.payload["candidate_provenance"]["capability_id"],
            "crypto_market_data_mcp",
        )
        self.assertEqual(
            self.payload["upstream"]["repository"],
            "eliasfire617/crypto-market-data-mcp",
        )
        self.assertEqual(
            self.payload["upstream"]["commit"],
            "7720d7116e26e578037c519d6fdae0d9ba0e8a75",
        )
        self.assertEqual(self.payload["upstream"]["license"], "MIT")

    def test_observed_tools_are_read_or_discovery_surfaces(self) -> None:
        tools = set(self.payload["observed_public_tools"])
        self.assertEqual(len(tools), 13)
        forbidden_tools = {
            "create_order",
            "cancel_order",
            "cancel_all_orders",
            "fetch_balance",
            "withdraw",
            "deposit",
            "transfer",
            "set_leverage",
        }
        for tool in tools:
            with self.subTest(tool=tool):
                self.assertNotIn(tool, forbidden_tools)

    def test_recommended_scope_is_derivatives_context_only(self) -> None:
        decision = self.payload["overall_decision"]
        self.assertEqual(
            decision["recommended_scope"],
            "PREFETCHED_DERIVATIVES_CONTEXT_CONTRACT_REFERENCE",
        )
        self.assertTrue(decision["do_not_import_as_runtime_dependency"])
        self.assertTrue(
            decision["do_not_use_upstream_arb_spread_as_trade_instruction"]
        )
        self.assertTrue(
            decision["do_not_replace_binance_or_pionex_canonical_market_authority"]
        )
        self.assertEqual(
            set(decision["priority_fields"]),
            {
                "funding_rate",
                "funding_interval_hours",
                "open_interest_amount",
                "open_interest_value",
                "long_short_ratio",
                "long_pct",
                "short_pct",
            },
        )

    def test_evaluation_grants_zero_operational_authority(self) -> None:
        authority = self.payload["authority"]
        self.assertTrue(authority)
        self.assertTrue(all(value is False for value in authority.values()))

    def test_hosted_auth_does_not_become_project_secret_authority(self) -> None:
        self.assertTrue(self.payload["upstream"]["hosted_http_api_key_required"])
        authority = self.payload["authority"]
        self.assertFalse(authority["upstream_http_api_key_authorized"])
        self.assertFalse(authority["gateway_auth_bypass_authorized"])
        self.assertFalse(authority["external_network_authorized"])


if __name__ == "__main__":
    unittest.main()
