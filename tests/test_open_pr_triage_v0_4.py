from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OpenPrTriageV04Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(
            (ROOT / "research/status/open-pr-triage-v0-4.json").read_text(
                encoding="utf-8"
            )
        )

    def test_snapshot_is_navigation_only(self) -> None:
        payload = self.payload
        self.assertEqual(payload["schema"], "qookey-open-pr-triage-v0.4")
        self.assertEqual(payload["snapshot_date"], "2026-09-17")
        self.assertEqual(
            payload["repository_authority"], "RESOLVE_MAIN_LIVE_AT_READ_TIME"
        )
        self.assertFalse(payload["merge_authority_granted"])
        self.assertFalse(payload["execution_authority_granted"])
        self.assertFalse(payload["close_authority_granted"])
        self.assertFalse(payload["evidence_basis"]["is_latest_main_claim"])
        self.assertEqual(payload["evidence_basis"]["source_merged_pr"], 340)

    def test_current_open_pr_lanes_are_explicit(self) -> None:
        prs = self.payload["pull_requests"]
        self.assertEqual(prs["336"]["classification"], "SUPERSEDED_OLD_BASE")
        self.assertEqual(prs["315"]["classification"], "REBUILD_FROM_CURRENT_MAIN")
        self.assertEqual(prs["307"]["classification"], "REBUILD_FROM_CURRENT_MAIN")
        self.assertEqual(prs["306"]["classification"], "REBUILD_FROM_CURRENT_MAIN")
        self.assertEqual(
            prs["302"]["classification"], "EVIDENCE_PRESERVED_CODE_REVIEW_ONLY"
        )
        self.assertEqual(prs["302"]["evidence_preserved_by_pr"], 340)

        dependabot = {"326", "327", "328", "329", "330", "331"}
        for pr_number in dependabot:
            self.assertEqual(prs[pr_number]["classification"], "DEPENDENCY_REVIEW")

        salvage = {"166", "167", "168", "199", "249"}
        for pr_number in salvage:
            self.assertEqual(prs[pr_number]["classification"], "SALVAGE_DRAFT")

    def test_recent_resolution_history_is_not_reopened(self) -> None:
        resolved = self.payload["recently_resolved"]
        self.assertEqual(resolved["305"]["outcome"], "CLOSED_NOT_MERGED")
        self.assertEqual(resolved["323"]["outcome"], "MERGED")
        self.assertEqual(resolved["339"]["outcome"], "MERGED")
        self.assertEqual(
            resolved["340"]["outcome"],
            "MERGED_POST_MERGE_CI_PAGES_FREEZE_GUARD_GREEN",
        )

    def test_human_snapshot_exists(self) -> None:
        human = (ROOT / "docs/OPEN_PR_TRIAGE_2026_09_17.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("#336", human)
        self.assertIn("#302", human)
        self.assertIn("#326", human)
        self.assertIn("#331", human)
        self.assertIn("No item in this triage is self-authorized", human)


if __name__ == "__main__":
    unittest.main()
