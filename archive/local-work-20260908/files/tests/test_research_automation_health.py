from __future__ import annotations

import unittest
from datetime import datetime, timezone

from crypto_autopilot.research_automation_health import (
    WorkflowExpectation,
    evaluate_automation_health,
    evaluate_workflow,
)


NOW = datetime(2026, 8, 24, 6, 0, tzinfo=timezone.utc)


def _run(
    *,
    event: str = "schedule",
    status: str = "completed",
    conclusion: str | None = "success",
    started: str = "2026-08-24T05:30:00Z",
) -> dict[str, object]:
    return {
        "id": 42,
        "event": event,
        "status": status,
        "conclusion": conclusion,
        "run_started_at": started,
        "html_url": "https://github.com/example/repo/actions/runs/42",
    }


class ResearchAutomationHealthTests(unittest.TestCase):
    def test_future_bounded_workflow_waits_without_alert(self) -> None:
        expectation = WorkflowExpectation(
            workflow="future.yml",
            label="Future",
            mode="bounded",
            max_age_seconds=3600,
            active_from_utc="2026-08-27T00:00:00Z",
            active_until_utc="2026-09-04T02:00:00Z",
        )
        row = evaluate_workflow(expectation, (), now=NOW)
        self.assertEqual(row["status"], "WAITING_WINDOW")
        self.assertFalse(row["alert"])

    def test_pr_run_cannot_mask_missing_scheduled_run(self) -> None:
        expectation = WorkflowExpectation(
            workflow="capture.yml",
            label="Capture",
            mode="bounded",
            max_age_seconds=3600,
            active_from_utc="2026-08-24T00:00:00Z",
            active_until_utc="2026-08-25T00:00:00Z",
            allowed_events=("schedule",),
        )
        row = evaluate_workflow(expectation, [_run(event="pull_request")], now=NOW)
        self.assertEqual(row["status"], "STALE_NO_RUN")
        self.assertTrue(row["alert"])

    def test_recent_scheduled_success_is_healthy(self) -> None:
        expectation = WorkflowExpectation(
            workflow="daily.yml",
            label="Daily",
            mode="continuous",
            max_age_seconds=7200,
            active_from_utc="2026-08-24T00:00:00Z",
        )
        row = evaluate_workflow(expectation, [_run()], now=NOW)
        self.assertEqual(row["status"], "HEALTHY")
        self.assertFalse(row["alert"])

    def test_latest_failed_run_is_an_alert(self) -> None:
        expectation = WorkflowExpectation(
            workflow="daily.yml",
            label="Daily",
            mode="continuous",
            max_age_seconds=7200,
            active_from_utc="2026-08-24T00:00:00Z",
        )
        row = evaluate_workflow(expectation, [_run(conclusion="failure")], now=NOW)
        self.assertEqual(row["status"], "FAILED")
        self.assertTrue(row["alert"])

    def test_conditional_workflow_waits_for_dependency(self) -> None:
        expectation = WorkflowExpectation(
            workflow="conditional.yml",
            label="Conditional",
            mode="conditional",
            max_age_seconds=7200,
            active_from_utc="2026-08-24T00:00:00Z",
        )
        row = evaluate_workflow(expectation, (), now=NOW)
        self.assertEqual(row["status"], "WAITING_DEPENDENCY")
        self.assertFalse(row["alert"])

    def test_aggregate_report_preserves_zero_runtime_authority(self) -> None:
        expectation = WorkflowExpectation(
            workflow="daily.yml",
            label="Daily",
            mode="continuous",
            max_age_seconds=7200,
            active_from_utc="2026-08-24T00:00:00Z",
        )
        report = evaluate_automation_health(
            [expectation],
            {"daily.yml": [_run()]},
            now=NOW,
        )
        self.assertEqual(report["status"], "PASS")
        self.assertFalse(report["authority"]["provider_access"])
        self.assertFalse(report["authority"]["r2_access"])
        self.assertFalse(report["authority"]["live_trading"])


if __name__ == "__main__":
    unittest.main()
