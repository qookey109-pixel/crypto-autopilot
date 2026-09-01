from __future__ import annotations

import unittest
from datetime import datetime, timezone

from crypto_autopilot.research.automation_health import (
    WorkflowExpectation,
    evaluate_automation_health,
    evaluate_workflow,
    scheduled_workflow_crons,
    validate_schedule_coverage,
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

    def test_v0_2_report_schema_is_explicit(self) -> None:
        expectation = WorkflowExpectation(
            workflow="daily.yml",
            label="Daily",
            mode="continuous",
            max_age_seconds=7200,
        )
        report = evaluate_automation_health(
            [expectation],
            {"daily.yml": [_run()]},
            now=NOW,
            schema="research-automation-health-v0.2",
        )
        self.assertEqual(report["schema"], "research-automation-health-v0.2")

    def test_schedule_coverage_rejects_manual_event_as_health(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            workflow_dir = Path(directory)
            (workflow_dir / "daily.yml").write_text(
                'name: Daily\non:\n  schedule:\n    - cron: "17 2 * * *"\n',
                encoding="utf-8",
            )
            expectation = WorkflowExpectation(
                workflow="daily.yml",
                label="Daily",
                mode="continuous",
                max_age_seconds=7200,
                allowed_events=("schedule", "workflow_dispatch"),
            )
            with self.assertRaisesRegex(ValueError, "manual events"):
                validate_schedule_coverage([expectation], workflow_dir)

    def test_schedule_coverage_matches_exact_cron_inventory(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as directory:
            workflow_dir = Path(directory)
            (workflow_dir / "daily.yml").write_text(
                'name: Daily\non:\n  schedule:\n    - cron: "17 2 * * *"\n',
                encoding="utf-8",
            )
            expectation = WorkflowExpectation(
                workflow="daily.yml",
                label="Daily",
                mode="continuous",
                max_age_seconds=7200,
                allowed_events=("schedule",),
            )
            self.assertEqual(
                scheduled_workflow_crons(workflow_dir),
                {"daily.yml": ["17 2 * * *"]},
            )
            coverage = validate_schedule_coverage([expectation], workflow_dir)
            self.assertTrue(coverage["complete"])
            self.assertFalse(coverage["manual_events_count_as_health"])


if __name__ == "__main__":
    unittest.main()
