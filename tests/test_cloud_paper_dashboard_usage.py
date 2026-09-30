"""Cloud-only CI checks for partial usage evidence and immutable receipt lineage."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.validate_dashboard_static import validate_cloud_paper_usage_evidence

LEGACY_BUDGET = {
    "monthly_budget_usd": 0,
    "account_wide_usage_evidence": "REVIEW_REQUIRED_V0_2_DATASET_COVERAGE_INCOMPLETE",
    "reservation_guard": "PROVIDER_R2_GUARD_IMPLEMENTED_RUNTIME_NOT_ACTIVATED",
    "state": "BLOCKED_BUDGET",
    "d1_reservation_ledger": "SHARED_LEDGER_CODE_PREPARED_MIGRATIONS_NOT_APPLIED_D1_NOT_PROVISIONED",
    "d1_free_tier_usage_evidence": "UNKNOWN_EMPTY_UNVERIFIED",
    "d1_storage_growth_bytes_per_statement": 16384,
    "d1_storage_growth_policy_bytes_per_utc_day": 12582912,
    "storage_capacity": {
        "state": "USAGE_PARTIAL_BLOCKED",
        "measured_storage_bytes": None,
        "usage_evidence": "PARTIAL_R2_EVIDENCE_NOT_ZERO_OR_COMPLETE",
        "report_object_max_bytes": 262144,
        "per_run_growth_max_bytes": 2097152,
        "per_utc_day_growth_max_bytes": 201326592,
        "max_31_day_growth_bytes": 6241124352,
        "warning_threshold_bytes": 6400000000,
        "hard_stop_bytes": 8000000000,
        "all_writer_coverage_proven": False
    },
    "usage_audit_evidence": {
        "authority": "cloud_paper_usage_audit_v0_2",
        "status": "REVIEW_REQUIRED",
        "reason_code": "DATASET_COVERAGE_INCOMPLETE",
        "run_id": 36584465739,
        "attempt": 1,
        "run_head_sha": "21d37a44c6f3c5bba340908705488a05e7a5f7c7",
        "artifact_id": 11041290995,
        "artifact_name": "cloud-paper-usage-audit-v0-2-36584465739-1",
        "artifact_sha256": "9ece6ff0a937f930d1137b2539052833bb5d94960dff8c1e50cce4cdbdadc258",
        "cloudflare_requests": 1,
        "d1_rows_state": "EMPTY_UNVERIFIED",
        "d1_storage_state": "EMPTY_UNVERIFIED",
        "r2_operations_state": "LIMIT_REACHED",
        "r2_operations_group_count": 10000,
        "r2_storage_state": "PRESENT",
        "r2_storage_group_count": 1297,
        "account_wide_cost": "UNKNOWN",
        "complete_storage_byte_aggregate": "UNKNOWN",
        "shared_writer_coverage": "UNKNOWN",
        "storage_headroom": "UNKNOWN"
    },
    "zero_cost_conclusion": "UNKNOWN",
    "account_wide_writer_coverage": "UNKNOWN"
}


class CloudPaperDashboardUsageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.current = json.loads(Path("web/data/cloud-paper-loop.json").read_text(encoding="utf-8"))
        self.budget = self.current["budget"]

    def test_reviewed_v2_remains_readable(self) -> None:
        self.assertEqual(validate_cloud_paper_usage_evidence(copy.deepcopy(LEGACY_BUDGET)), "V0.2")
        receipt = json.loads(Path("research/receipts/2026-09-29-cloud-paper-usage-audit-v0-2-result.json").read_text())
        e = LEGACY_BUDGET["usage_audit_evidence"]
        for key, source_key in (
            ("run_id", "run_id"), ("attempt", "run_attempt"), ("run_head_sha", "head_sha"),
            ("artifact_id", "artifact_id"), ("artifact_name", "artifact_name"),
        ):
            self.assertEqual(e[key], receipt["source"][source_key])
        self.assertEqual(e["artifact_sha256"], receipt["source"]["artifact_digest"].removeprefix("sha256:"))

    def test_v3_projection_matches_immutable_receipt(self) -> None:
        self.assertEqual(validate_cloud_paper_usage_evidence(self.budget), "V0.3")
        receipt = json.loads(Path("research/receipts/2026-09-29-cloud-paper-r2-usage-audit-v0-3-result.json").read_text())
        e = self.budget["usage_audit_evidence"]
        self.assertEqual((e["run_id"], e["attempt"], e["run_head_sha"]),
                         (receipt["workflow_run"]["id"], receipt["workflow_run"]["attempt"], receipt["workflow_run"]["head_sha"]))
        for key in ("id", "name", "sha256"):
            self.assertEqual(e["artifact_" + key], receipt["artifact"][key])
        self.assertEqual(e["status"], receipt["report"]["status"])
        self.assertEqual(e["reason_code"], receipt["report"]["reason_code"])
        self.assertEqual(e["cloudflare_requests"], receipt["report"]["cloudflare_http_requests_performed"])
        for key in ("returned_bucket_group_count", "object_count", "payload_bytes", "metadata_bytes",
                    "total_bytes", "upload_count", "latest_snapshot_utc"):
            self.assertEqual(e[key], receipt["coverage"]["r2_storage"][key])
        self.assertEqual(e["total_bytes"], e["payload_bytes"] + e["metadata_bytes"])
        self.assertEqual(e["r2_operations_total_requests"], receipt["coverage"]["r2_operations"]["total_requests"])
        self.assertEqual(e["r2_operations_freshness"], receipt["coverage"]["r2_operations"]["freshness"])

    def test_every_known_evidence_field_rejects_change_or_omission(self) -> None:
        for source in (self.budget, LEGACY_BUDGET):
            for key, value in source["usage_audit_evidence"].items():
                if key == "conclusion":
                    continue
                for replacement in (None, True, 0, "PASS"):
                    if type(replacement) is type(value) and replacement == value:
                        continue
                    with self.subTest(authority=source["usage_audit_evidence"]["authority"], key=key, value=replacement):
                        changed = copy.deepcopy(source)
                        changed["usage_audit_evidence"][key] = replacement
                        with self.assertRaises(RuntimeError):
                            validate_cloud_paper_usage_evidence(changed)
                with self.subTest(key=key, omitted=True):
                    changed = copy.deepcopy(source)
                    del changed["usage_audit_evidence"][key]
                    with self.assertRaises(RuntimeError):
                        validate_cloud_paper_usage_evidence(changed)

    def test_unknown_budget_and_partial_capacity_cannot_be_promoted(self) -> None:
        for key in ("account_wide_usage_evidence", "d1_free_tier_usage_evidence",
                    "zero_cost_conclusion", "account_wide_writer_coverage", "state", "monthly_budget_usd"):
            for replacement in ("PASS", 0, False, None):
                if type(replacement) is type(self.budget[key]) and replacement == self.budget[key]:
                    continue
                changed = copy.deepcopy(self.budget)
                changed[key] = replacement
                with self.subTest(key=key, value=replacement), self.assertRaises(RuntimeError):
                    validate_cloud_paper_usage_evidence(changed)
        for key, replacement in (("measured_storage_bytes", 0), ("measured_storage_bytes", 616541780),
                                 ("all_writer_coverage_proven", True)):
            changed = copy.deepcopy(self.budget)
            changed["storage_capacity"][key] = replacement
            with self.subTest(key=key, value=replacement), self.assertRaises(RuntimeError):
                validate_cloud_paper_usage_evidence(changed)

    def test_missing_and_wrong_shape_evidence_fails_closed(self) -> None:
        for key in ("usage_audit_evidence", "storage_capacity"):
            for value in (None, [], "UNKNOWN", 0):
                changed = copy.deepcopy(self.budget)
                changed[key] = value
                with self.subTest(key=key, value=value), self.assertRaises(RuntimeError):
                    validate_cloud_paper_usage_evidence(changed)
        changed = copy.deepcopy(self.budget)
        del changed["storage_capacity"]["measured_storage_bytes"]
        with self.assertRaises(RuntimeError):
            validate_cloud_paper_usage_evidence(changed)


if __name__ == "__main__":
    unittest.main()
