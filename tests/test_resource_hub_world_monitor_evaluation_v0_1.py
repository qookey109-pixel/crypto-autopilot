from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


RECEIPT = Path(
    "research/receipts/2026-09-15-resource-hub-world-monitor-evaluation-v0-1.json"
)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class ResourceHubWorldMonitorEvaluationV01Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

    def test_receipt_is_exactly_bound_and_not_integration_approval(self) -> None:
        receipt = self.receipt
        self.assertEqual(receipt["schema"], "resource-hub-integration-evaluation-v0.1")
        self.assertEqual(
            receipt["status"],
            "EVALUATED_RESEARCH_ONLY_NOT_APPROVED_FOR_INTEGRATION",
        )
        self.assertTrue(SHA_RE.fullmatch(receipt["crypto_autopilot_base_main_sha"]))
        self.assertTrue(SHA_RE.fullmatch(receipt["candidate_provenance"]["resource_hub_commit"]))
        self.assertTrue(SHA_RE.fullmatch(receipt["upstream"]["commit"]))
        self.assertEqual(receipt["candidate_provenance"]["resource_id"], "world-monitor")
        self.assertEqual(receipt["candidate_provenance"]["candidate_decision"], "REVIEW_REQUIRED")
        self.assertEqual(
            receipt["overall_decision"]["state"],
            "EVALUATED_NOT_APPROVED_FOR_INTEGRATION",
        )

    def test_every_authority_flag_remains_false(self) -> None:
        authority = self.receipt["authority"]
        self.assertTrue(authority)
        self.assertTrue(all(value is False for value in authority.values()))

    def test_market_data_and_generated_context_cannot_become_trading_authority(self) -> None:
        components = self.receipt["component_evaluation"]
        self.assertEqual(
            components["market_and_crypto_data"]["decision"],
            "REJECT_AS_CANONICAL_CRYPTO_MARKET_DATA_AUTHORITY",
        )
        self.assertEqual(
            components["country_instability_index"]["decision"],
            "REFERENCE_ONLY_REQUIRES_INDEPENDENT_CALIBRATION",
        )
        self.assertEqual(
            components["ai_synthesized_briefs"]["decision"],
            "REFERENCE_ONLY_WITH_GROUNDING_REQUIRED",
        )
        overall = self.receipt["overall_decision"]
        self.assertTrue(overall["do_not_use_market_data_as_native_crypto_authority"])
        self.assertTrue(overall["do_not_use_cii_or_ai_briefs_as_directional_signal"])

    def test_only_descriptive_context_and_freshness_contract_are_research_candidates(self) -> None:
        components = self.receipt["component_evaluation"]
        self.assertEqual(
            components["geopolitical_and_supply_chain_context"]["decision"],
            "RESEARCH_CANDIDATE_DESCRIPTIVE_CONTEXT_ONLY",
        )
        self.assertEqual(
            components["freshness_and_provenance_contract"]["decision"],
            "RESEARCH_CANDIDATE",
        )
        self.assertEqual(
            components["mcp_rest_and_sdk_runtime"]["decision"],
            "DEFER_REMOTE_INTEGRATION_V0_1",
        )

    def test_license_and_redistribution_stay_separately_reviewed(self) -> None:
        self.assertEqual(self.receipt["upstream"]["license"], "AGPL-3.0-only")
        self.assertEqual(
            self.receipt["component_evaluation"]["license_and_data_redistribution"]["decision"],
            "REQUIRES_SEPARATE_LICENSE_AND_PROVIDER_REVIEW",
        )
        self.assertTrue(self.receipt["overall_decision"]["do_not_import_as_runtime_dependency"])

    def test_next_step_is_synthetic_and_network_free(self) -> None:
        step = self.receipt["overall_decision"]["recommended_next_step"].lower()
        self.assertIn("synthetic fixtures only", step)
        self.assertIn("do not call world monitor", step)
        self.assertIn("r2", step)
        self.assertIn("frozen holdout", step)

    def test_evaluation_does_not_claim_upstream_tests_were_executed(self) -> None:
        self.assertFalse(
            self.receipt["upstream"]["upstream_test_execution_performed_by_this_evaluation"]
        )


if __name__ == "__main__":
    unittest.main()
