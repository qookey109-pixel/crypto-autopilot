from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


RECEIPT = Path(
    "research/receipts/2026-09-15-resource-hub-anti-gambling-trader-evaluation-v0-1.json"
)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class ResourceHubIntegrationEvaluationV01Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

    def test_receipt_is_exactly_bound_and_not_an_integration_approval(self) -> None:
        receipt = self.receipt
        self.assertEqual(receipt["schema"], "resource-hub-integration-evaluation-v0.1")
        self.assertEqual(
            receipt["status"],
            "EVALUATED_RESEARCH_ONLY_NOT_APPROVED_FOR_INTEGRATION",
        )
        self.assertTrue(SHA_RE.fullmatch(receipt["crypto_autopilot_base_main_sha"]))
        self.assertTrue(SHA_RE.fullmatch(receipt["candidate_provenance"]["resource_hub_commit"]))
        self.assertTrue(SHA_RE.fullmatch(receipt["upstream"]["commit"]))
        self.assertEqual(receipt["candidate_provenance"]["resource_id"], "anti-gambling-trader-tw")
        self.assertEqual(receipt["candidate_provenance"]["candidate_decision"], "REVIEW_REQUIRED")
        self.assertEqual(
            receipt["overall_decision"]["state"],
            "EVALUATED_NOT_APPROVED_FOR_INTEGRATION",
        )
        self.assertTrue(receipt["overall_decision"]["do_not_import_as_runtime_dependency"])
        self.assertTrue(receipt["overall_decision"]["do_not_use_as_execution_or_broker_authority"])

    def test_every_authority_flag_remains_false(self) -> None:
        authority = self.receipt["authority"]
        self.assertTrue(authority)
        self.assertTrue(all(value is False for value in authority.values()))

    def test_broker_and_live_surfaces_are_not_promoted(self) -> None:
        components = self.receipt["component_evaluation"]
        self.assertEqual(
            components["paper_broker"]["decision"],
            "REJECT_FOR_CRYPTO_PERP_MODEL",
        )
        self.assertEqual(
            components["broker_adapter_and_live_scaffold"]["decision"],
            "REJECT_FOR_INTEGRATION_V0_1",
        )
        self.assertIn(
            components["statistical_metrics"]["decision"],
            {"RESEARCH_CANDIDATE", "RESEARCH_CANDIDATE_WITH_LIMITATIONS"},
        )
        self.assertEqual(
            components["temporal_holdout"]["decision"],
            "REFERENCE_ONLY",
        )

    def test_evaluation_does_not_claim_upstream_tests_were_executed(self) -> None:
        self.assertFalse(
            self.receipt["upstream"]["upstream_test_execution_performed_by_this_evaluation"]
        )


if __name__ == "__main__":
    unittest.main()
