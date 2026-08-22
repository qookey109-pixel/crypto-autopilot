from __future__ import annotations

import json
import unittest
from pathlib import Path


RECEIPT = Path(
    "research/receipts/2026-08-22-v0-10-observer-rehearsal-window-pre-review-prepared.json"
)


class ObserverRehearsalWindowPreReviewReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

    def test_exact_pr_and_final_ci_lineage_is_frozen(self) -> None:
        receipt = self.receipt
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["source_pr"], 164)
        self.assertEqual(
            receipt["source_pr_merge_sha"],
            "2b55bc7d6d853b45cfa0efa5375dfe0b14f7f3cb",
        )
        validation = receipt["validation"]
        self.assertEqual(validation["initial_ci_run_id"], 32543756325)
        self.assertEqual(validation["initial_conclusion"], "failure")
        self.assertEqual(validation["initial_failure_scope"], "SYNTHETIC_TEST_HARNESS_ONLY")
        self.assertIs(validation["production_code_failure_observed"], False)
        self.assertIs(validation["production_workflow_failure_observed"], False)
        self.assertEqual(validation["final_ci_run_id"], 32543805574)
        self.assertEqual(validation["final_python_3_12_conclusion"], "success")
        self.assertEqual(validation["final_python_3_13_conclusion"], "success")
        self.assertEqual(validation["ruff_conclusion"], "success")
        self.assertEqual(validation["full_unit_tests_conclusion"], "success")

    def test_observer_rehearsal_scope_is_exact_and_read_only(self) -> None:
        rehearsal = self.receipt["observer_rehearsal"]
        self.assertEqual(rehearsal["scenario_count"], 8)
        self.assertEqual(rehearsal["source_workflow_failure"], "FAIL_CLOSED")
        self.assertEqual(rehearsal["missing_capture_job"], "FAIL_CLOSED")
        self.assertEqual(rehearsal["both_attempts_fail"], "BOTH_FAIL_CLOSED")
        self.assertEqual(
            rehearsal["r2_blocked_visibility_boundary"],
            "NOT_CLASSIFIABLE_FROM_GITHUB_EXECUTION_METADATA_ONLY",
        )
        for key in (
            "observer_capture_artifact_read",
            "observer_r2_read",
            "observer_provider_data_read",
            "observer_holdout_read",
            "observer_v0_11_execution",
        ):
            self.assertIs(rehearsal[key], False)

    def test_window_pre_review_does_not_grant_production_access(self) -> None:
        review = self.receipt["window_pre_review"]
        self.assertEqual(review["status"], "PREPARED_NOT_EXECUTION_AUTHORITY")
        self.assertEqual(review["earliest_review_after_utc"], "2026-09-04T01:59:59.999Z")
        self.assertIs(
            review["repository_github_actions_critical_path_and_render_metadata_read_only"],
            True,
        )
        for key in (
            "production_r2_object_listing_allowed",
            "production_r2_receipt_read_allowed",
            "capture_artifact_read_allowed",
            "provider_payload_read_allowed",
            "replacement_holdout_read_allowed",
            "manual_or_retroactive_backfill_allowed",
            "ready_state_authorizes_v0_11",
            "ready_state_guarantees_194_valid_receipts",
        ):
            self.assertIs(review[key], False)

    def test_no_execution_evidence_or_downstream_authority_was_consumed(self) -> None:
        execution = self.receipt["execution_evidence"]
        self.assertIs(execution["production_metadata_evidence_consumed"], False)
        self.assertEqual(execution["provider_requests_performed"], 0)
        self.assertEqual(execution["render_provider_requests_performed"], 0)
        self.assertIs(execution["render_deploy_triggered"], False)
        self.assertIs(execution["r2_client_constructed"], False)
        self.assertIs(execution["r2_reads_performed"], False)
        self.assertIs(execution["r2_writes_performed"], False)
        self.assertIs(execution["capture_artifacts_read"], False)
        self.assertIs(execution["holdout_candles_accessed"], False)
        self.assertIs(execution["v0_11_production_r2_evaluation_performed"], False)

        boundary = self.receipt["authorization_boundary"]
        self.assertTrue(all(value is False for value in boundary.values()))


if __name__ == "__main__":
    unittest.main()
