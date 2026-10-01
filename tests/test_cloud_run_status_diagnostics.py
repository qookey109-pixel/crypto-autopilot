"""Tests for metadata-only Cloud Paper billing workflow projection."""
from __future__ import annotations

import unittest

from scripts.build_cloud_run_status import project_diagnostic_run


WORKFLOW = "cloud-paper-billing-history-v0-1.yml"


def run(*, run_id: int = 10, branch: str = "main", event: str = "workflow_dispatch",
        path: str = WORKFLOW, repository: str = "qookey109-pixel/crypto-autopilot",
        sha: str = "a" * 40, attempt: int = 1, status: str = "completed",
        conclusion: str | None = "failure") -> dict:
    return {
        "id": run_id,
        "head_branch": branch,
        "event": event,
        "path": f".github/workflows/{path}",
        "head_repository": {"full_name": repository},
        "head_sha": sha,
        "run_attempt": attempt,
        "status": status,
        "conclusion": conclusion,
        "created_at": "2026-10-01T21:54:29Z",
    }


class DiagnosticRunProjectionTests(unittest.TestCase):
    def test_projects_latest_valid_main_dispatch_without_business_claim(self) -> None:
        projected = project_diagnostic_run([
            run(run_id=12, status="in_progress", conclusion=None),
            run(run_id=11, branch="feature"),
            run(run_id=14, attempt=2, conclusion="failure"),
        ], WORKFLOW)
        self.assertEqual(projected["state"], "WORKFLOW_FAILED")
        self.assertEqual(projected["runId"], 14)
        self.assertEqual(projected["runAttempt"], 2)
        self.assertEqual(projected["event"], "workflow_dispatch")
        self.assertEqual(projected["headSha"], "a" * 40)
        self.assertEqual(projected["sourceUrl"],
                         "https://github.com/qookey109-pixel/crypto-autopilot/actions/runs/14")
        self.assertNotIn("report", projected)
        self.assertNotIn("artifact", projected)

    def test_rejects_non_main_foreign_wrong_workflow_and_invalid_sha_runs(self) -> None:
        projected = project_diagnostic_run([
            run(run_id=40, branch="feature"),
            run(run_id=41, repository="someone/else"),
            run(run_id=42, path="other.yml"),
            run(run_id=43, event="schedule"),
            run(run_id=44, sha="invalid"),
        ], WORKFLOW)
        self.assertEqual(projected["state"], "NO_RUN")
        self.assertIsNone(projected["runId"])
        self.assertIsNone(projected["sourceUrl"])

    def test_query_errors_are_not_misreported_as_no_run(self) -> None:
        projected = project_diagnostic_run([], WORKFLOW)
        self.assertEqual(projected["state"], "NO_RUN")


if __name__ == "__main__":
    unittest.main()
