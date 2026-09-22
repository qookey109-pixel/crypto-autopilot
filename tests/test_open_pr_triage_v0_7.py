from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRIAGE = ROOT / "research" / "status" / "open-pr-triage-v0-7.json"


class OpenPrTriageV07Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(TRIAGE.read_text(encoding="utf-8"))

    def test_snapshot_is_navigation_only_and_empty(self) -> None:
        payload = self.payload
        self.assertEqual(payload["schema"], "qookey-open-pr-triage-v0.7")
        self.assertEqual(payload["snapshot_date"], "2026-09-22")
        self.assertEqual(payload["repository_authority"], "RESOLVE_MAIN_LIVE_AT_READ_TIME")
        self.assertFalse(payload["merge_authority_granted"])
        self.assertFalse(payload["execution_authority_granted"])
        self.assertFalse(payload["close_authority_granted"])
        self.assertFalse(payload["evidence_basis"]["is_latest_main_claim"])
        self.assertEqual(payload["evidence_basis"]["source_merged_pr"], 448)
        self.assertEqual(
            payload["evidence_basis"]["parent_main_sha"],
            "28099bafdc3addee363933dab4a99a32ea76fc2c",
        )
        self.assertEqual(payload["active_open_pr_count"], 0)
        self.assertEqual(payload["active_open_pr_numbers"], [])

    def test_dependency_review_outcomes_are_explicit(self) -> None:
        reviewed = self.payload["reviewed_pull_requests"]
        self.assertEqual(reviewed["327"]["replacement_pr"], 447)
        self.assertEqual(reviewed["328"]["replacement_pr"], 448)
        self.assertEqual(reviewed["329"]["freeze_guard_run"], 35747058798)
        self.assertEqual(reviewed["330"]["changed_workflow_count"], 77)
        self.assertEqual(reviewed["331"]["outcome"], "CLOSED_NOT_MERGED")

    def test_type_visibility_points_to_current_non_execution_lane(self) -> None:
        current = self.payload["current_type_visibility"]
        self.assertEqual(current["error_count"], 216)
        self.assertFalse(current["blocking_gate"])
        self.assertEqual(current["next_candidate_error_count"], 17)
        self.assertEqual(
            current["next_candidate"],
            "src/crypto_autopilot/binance_expansion_plan.py",
        )
        self.assertIn(
            "src/crypto_autopilot/toolkit/descriptive_context_v0_1.py",
            current["zero_error_candidates"],
        )

    def test_human_navigation_matches_v07(self) -> None:
        human = (ROOT / "docs" / "OPEN_PR_TRIAGE_2026_09_22.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("open pull-request backlog is **zero**", human)
        self.assertIn("open-pr-triage-v0-7.json", human)
        self.assertIn("#447", human)
        self.assertIn("#448", human)
        self.assertIn("35747058798", human)
        self.assertIn("216 errors", human)
        self.assertIn("UNVERIFIED_FROM_GITHUB", human)


if __name__ == "__main__":
    unittest.main()
