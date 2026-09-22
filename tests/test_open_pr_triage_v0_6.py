from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRIAGE = ROOT / "research" / "status" / "open-pr-triage-v0-6.json"


class OpenPrTriageV06Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(TRIAGE.read_text(encoding="utf-8"))

    def test_snapshot_is_navigation_only(self) -> None:
        payload = self.payload
        self.assertEqual(payload["schema"], "qookey-open-pr-triage-v0.6")
        self.assertEqual(payload["snapshot_date"], "2026-09-22")
        self.assertEqual(payload["repository_authority"], "RESOLVE_MAIN_LIVE_AT_READ_TIME")
        self.assertFalse(payload["merge_authority_granted"])
        self.assertFalse(payload["execution_authority_granted"])
        self.assertFalse(payload["close_authority_granted"])
        self.assertFalse(payload["evidence_basis"]["is_latest_main_claim"])
        self.assertEqual(payload["evidence_basis"]["source_merged_pr"], 442)
        self.assertEqual(
            payload["evidence_basis"]["parent_main_sha"],
            "89b7335204d09232b25b407e593294fbdb5913f2",
        )

    def test_current_open_backlog_includes_441_and_dependabot(self) -> None:
        payload = self.payload
        self.assertEqual(payload["active_open_pr_count"], 7)
        self.assertEqual(
            payload["active_open_pr_numbers"],
            [441, 326, 327, 328, 329, 330, 331],
        )
        self.assertEqual(
            payload["dependency_review_order"],
            [329, 326, 327, 328, 330, 331],
        )
        self.assertIn("441", payload["non_dependabot_open_prs"])
        self.assertEqual(
            set(payload["dependency_pull_requests"]),
            {"326", "327", "328", "329", "330", "331"},
        )

    def test_remote_inventory_does_not_authorize_local_cleanup(self) -> None:
        payload = self.payload
        research_context = payload["remote_branch_inventory"]["codex/research-context-v0-1"]
        dashboard = payload["remote_branch_inventory"]["codex/dashboard-schedule-audit-20260922"]
        self.assertEqual(research_context["ahead_by"], 0)
        self.assertEqual(research_context["unique_remote_commits"], 0)
        self.assertEqual(dashboard["ahead_by"], 0)
        self.assertEqual(dashboard["classification"], "MERGED_VIA_PR_442")
        self.assertEqual(payload["local_checkout_visibility"], "UNVERIFIED_FROM_GITHUB")
        self.assertFalse(payload["local_cleanup_authorized"])

    def test_v06_remains_historical_snapshot(self) -> None:
        payload = self.payload
        self.assertEqual(payload["active_open_pr_count"], 7)
        self.assertEqual(
            payload["active_open_pr_numbers"],
            [441, 326, 327, 328, 329, 330, 331],
        )
        self.assertEqual(payload["evidence_basis"]["source_merged_pr"], 442)
        self.assertFalse(payload["evidence_basis"]["is_latest_main_claim"])


if __name__ == "__main__":
    unittest.main()
