from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRIAGE = ROOT / "research" / "status" / "open-pr-triage-v0-5.json"


class OpenPrTriageV05Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(TRIAGE.read_text(encoding="utf-8"))

    def test_snapshot_is_navigation_only_and_current(self) -> None:
        payload = self.payload
        self.assertEqual(payload["schema"], "qookey-open-pr-triage-v0.5")
        self.assertEqual(payload["snapshot_date"], "2026-09-22")
        self.assertEqual(
            payload["repository_authority"],
            "RESOLVE_MAIN_LIVE_AT_READ_TIME",
        )
        self.assertFalse(payload["merge_authority_granted"])
        self.assertFalse(payload["execution_authority_granted"])
        self.assertFalse(payload["close_authority_granted"])
        self.assertFalse(payload["evidence_basis"]["is_latest_main_claim"])
        self.assertEqual(payload["evidence_basis"]["source_merged_pr"], 426)
        self.assertEqual(
            payload["evidence_basis"]["parent_main_sha"],
            "09dfb0d79b88dc56f3cb582c91d8091617437ce2",
        )

    def test_active_open_backlog_is_dependabot_only(self) -> None:
        payload = self.payload
        expected = [326, 327, 328, 329, 330, 331]
        self.assertEqual(payload["active_open_pr_count"], 6)
        self.assertEqual(payload["active_open_pr_numbers"], expected)
        self.assertEqual(set(payload["pull_requests"]), {str(n) for n in expected})
        self.assertEqual(
            payload["recommended_review_order"],
            [329, 326, 327, 328, 330, 331],
        )

    def test_major_dependency_risks_remain_explicit(self) -> None:
        prs = self.payload["pull_requests"]
        self.assertEqual(
            prs["330"]["classification"],
            "DEPENDENCY_REVIEW_MAJOR_CRITICAL_ACTION",
        )
        self.assertIn("FREEZE", prs["330"]["risk"])
        self.assertEqual(
            prs["331"]["classification"],
            "DEPENDENCY_REVIEW_MAJOR_RUNTIME",
        )
        self.assertEqual(
            prs["331"]["current_main_review"],
            "BLOCKED_PENDING_PUBLIC_COMPATIBILITY_AND_FROZEN_CONSTRAINT_REVIEW",
        )
        self.assertIn(
            "pyproject.toml currently declares pyarrow>=18,<22",
            prs["331"]["conflicts_with_current_main"],
        )

    def test_old_architecture_prs_are_closed_historical_references(self) -> None:
        closed = self.payload["closed_historical_references"]
        for number in ("336", "315", "307", "306", "302", "249", "199", "168", "167", "166"):
            with self.subTest(pr=number):
                self.assertIn(number, closed)
                self.assertTrue(closed[number].startswith("CLOSED_NOT_MERGED"))

    def test_v05_remains_historical_snapshot(self) -> None:
        payload = self.payload
        self.assertEqual(payload["active_open_pr_count"], 6)
        self.assertEqual(payload["active_open_pr_numbers"], [326, 327, 328, 329, 330, 331])
        self.assertEqual(payload["evidence_basis"]["source_merged_pr"], 426)
        self.assertFalse(payload["evidence_basis"]["is_latest_main_claim"])


if __name__ == "__main__":
    unittest.main()
