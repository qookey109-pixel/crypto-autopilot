from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.inspect_shared_writer_static_readiness_v0_1 import (
    REGISTRY_PATH,
    REVIEWED_PATHS,
    ROOT,
    SharedWiringReviewRequired,
    inspect_current_checkout,
    inspect_unverified_shared_writers,
)


def fixtures():
    registry = json.loads((ROOT / REGISTRY_PATH).read_text(encoding="utf-8"))
    workflows = {path: (ROOT / path).read_text(encoding="utf-8") for path in REVIEWED_PATHS}
    scripts = {
        route[0]: (ROOT / route[0]).read_text(encoding="utf-8")
        for route in REVIEWED_PATHS.values()
    }
    return registry, workflows, scripts


class SharedWriterStaticReadinessV01Tests(unittest.TestCase):
    def test_current_four_are_traceable_but_never_production_admitted(self):
        result = inspect_current_checkout()
        self.assertEqual(result["status"], "REVIEW_REQUIRED_SHARED_ADMISSION_UNVERIFIED")
        self.assertEqual(result["scope"], "REPOSITORY_SOURCE_ONLY")
        self.assertEqual(result["reviewed_writer_count"], 4)
        self.assertEqual(len(result["writer_reviews"]), 4)
        for row in result["writer_reviews"]:
            self.assertTrue(row["static_route_shape_matches_review"])
            self.assertFalse(row["shared_account_admission_verified"])
            self.assertFalse(row["runtime_query_meter_verified"])
            self.assertFalse(row["account_wide_writer_coverage_proven"])
        for field in (
            "account_inventory_complete_proven",
            "external_writer_inventory_verified",
            "production_query_meter_verified",
            "d1_account_usage_headroom_verified",
            "paper_activation_allowed",
            "live_trading_authorized",
            "cloudflare_access_performed",
            "this_result_grants_execution_authority",
        ):
            with self.subTest(field=field):
                self.assertFalse(result[field])

    def test_no_forged_verified_status_or_activation_claim(self):
        for key, value in (
            ("registration_state", "SHARED_ADMISSION_VERIFIED"),
            ("registration_state", "ACTIVE"),
            ("resource", "D1"),
        ):
            registry, workflows, scripts = fixtures()
            registry["repository_writers"][0][key] = value
            with self.subTest(key=key), self.assertRaises(SharedWiringReviewRequired):
                inspect_unverified_shared_writers(registry, workflows, scripts)

        for field in (
            "account_wide_coverage_proven",
            "shared_admission_integrated_for_all_repository_writers",
            "d1_provisioned",
            "activation_enabled",
            "legacy_existing_writes_claimed_globally_admitted",
        ):
            registry, workflows, scripts = fixtures()
            registry["production_gate"][field] = True
            with self.subTest(field=field), self.assertRaisesRegex(
                SharedWiringReviewRequired, "ACCOUNT_COVERAGE_OR_GATE"
            ):
                inspect_unverified_shared_writers(registry, workflows, scripts)

    def test_new_or_deleted_writer_requires_review(self):
        registry, workflows, scripts = fixtures()
        registry["repository_writers"].append({
            "writer_id": "crypto-autopilot:unreviewed",
            "workflow": ".github/workflows/unreviewed.yml",
            "resource": "R2",
            "registration_state": "SHARED_ADMISSION_VERIFIED",
        })
        with self.assertRaisesRegex(SharedWiringReviewRequired, "COUNT_DRIFT"):
            inspect_unverified_shared_writers(registry, workflows, scripts)
        registry, workflows, scripts = fixtures()
        registry["repository_writers"].pop()
        with self.assertRaisesRegex(SharedWiringReviewRequired, "COUNT_DRIFT"):
            inspect_unverified_shared_writers(registry, workflows, scripts)

    def test_changed_entrypoint_route_and_incomplete_workflow_block(self):
        registry, workflows, scripts = fixtures()
        path = ".github/workflows/live-paper-run-coordinator-v0-1.yml"
        workflows[path] = workflows[path].replace(
            "scripts/run_live_paper_coordinator_v0_1.py",
            "scripts/new_unreviewed_coordinator.py",
        )
        with self.assertRaisesRegex(SharedWiringReviewRequired, "ROUTE"):
            inspect_unverified_shared_writers(registry, workflows, scripts)

        registry, workflows, scripts = fixtures()
        script = REVIEWED_PATHS[path][0]
        scripts[script] = scripts[script].replace(
            "R2PaperRunStore(",
            "UnknownR2Writer(",
        )
        with self.assertRaisesRegex(SharedWiringReviewRequired, "ENTRYPOINT_SHAPE"):
            inspect_unverified_shared_writers(registry, workflows, scripts)

        registry, workflows, scripts = fixtures()
        scripts[script] += "\nSharedWriterR2Budget.admit(\n"
        with self.assertRaisesRegex(SharedWiringReviewRequired, "GATE_REFERENCE_CHANGED"):
            inspect_unverified_shared_writers(registry, workflows, scripts)

    def test_external_account_completeness_cannot_be_inferred(self):
        for state, complete in (
            ("ATTESTED", True),
            ("UNCONFIRMED", True),
            ("ATTESTED", False),
        ):
            registry, workflows, scripts = fixtures()
            registry["external_writer_inventory"].update(state=state, complete=complete)
            with self.subTest(state=state, complete=complete), self.assertRaises(
                SharedWiringReviewRequired
            ):
                inspect_unverified_shared_writers(registry, workflows, scripts)

    def test_duplicate_registered_writer_not_mistaken_for_complete(self):
        registry, workflows, scripts = fixtures()
        registry["repository_writers"][1] = copy.deepcopy(registry["repository_writers"][0])
        with self.assertRaisesRegex(SharedWiringReviewRequired, "IDENTITY_OR_WORKFLOW"):
            inspect_unverified_shared_writers(registry, workflows, scripts)


if __name__ == "__main__":
    unittest.main()
