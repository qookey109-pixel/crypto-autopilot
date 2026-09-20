from __future__ import annotations

import json
import unittest
from unittest import mock
from datetime import datetime, timezone

from crypto_autopilot.research.automation_health import (
    WorkflowExpectation,
    evaluate_automation_health,
    evaluate_workflow,
    fetch_workflow_runs,
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

    def test_conditional_workflow_waits_for_dependency_during_grace(self) -> None:
        expectation = WorkflowExpectation(
            workflow="conditional.yml",
            label="Conditional",
            mode="conditional",
            max_age_seconds=7200,
            active_from_utc="2026-08-24T05:00:00Z",
        )
        row = evaluate_workflow(expectation, (), now=NOW)
        self.assertEqual(row["status"], "WAITING_DEPENDENCY")
        self.assertFalse(row["alert"])

    def test_conditional_workflow_without_run_becomes_stale(self) -> None:
        expectation = WorkflowExpectation(
            workflow="conditional.yml",
            label="Conditional",
            mode="conditional",
            max_age_seconds=7200,
            active_from_utc="2026-08-24T00:00:00Z",
        )
        row = evaluate_workflow(expectation, (), now=NOW)
        self.assertEqual(row["status"], "STALE_NO_RUN")
        self.assertTrue(row["alert"])

    def test_conditional_old_success_cannot_hide_staleness(self) -> None:
        expectation = WorkflowExpectation(
            workflow="conditional.yml",
            label="Conditional",
            mode="conditional",
            max_age_seconds=7200,
            active_from_utc="2026-08-24T00:00:00Z",
        )
        row = evaluate_workflow(
            expectation,
            [_run(started="2026-08-24T01:00:00Z")],
            now=NOW,
        )
        self.assertEqual(row["status"], "STALE")
        self.assertTrue(row["alert"])

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

    def test_aggregate_report_separates_execution_dependency_and_business_result(self) -> None:
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
            schema="research-automation-health-v0.2",
        )
        row = report["workflows"][0]
        self.assertEqual(row["execution"]["status"], "HEALTHY")
        self.assertEqual(
            row["dependency"]["status"],
            "UNKNOWN_FROM_GITHUB_RUN_METADATA",
        )
        self.assertEqual(
            row["business_result"]["status"],
            "UNKNOWN_FROM_GITHUB_RUN_METADATA",
        )
        self.assertEqual(row["business_result"]["workflow_conclusion"], "success")

    def test_fetch_workflow_runs_filters_main_schedule_and_pages(self) -> None:
        calls: list[str] = []

        class _Response:
            def __init__(self, payload: dict[str, object]) -> None:
                self.payload = payload

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps(self.payload).encode("utf-8")

        payloads = [
            {"workflow_runs": [_run(started="2026-08-24T05:30:00Z")]},
            {"workflow_runs": []},
        ]

        def fake_urlopen(request, timeout):
            self.assertEqual(timeout, 20)
            calls.append(request.full_url)
            return _Response(payloads.pop(0))

        with mock.patch(
            "crypto_autopilot.research.automation_health.urlopen",
            side_effect=fake_urlopen,
        ):
            rows = fetch_workflow_runs(
                repository="example/repo",
                workflow="daily.yml",
                token="token",
                branch="main",
                allowed_events=("schedule",),
                per_page=1,
                max_pages=3,
            )

        self.assertEqual(len(rows), 1)
        self.assertEqual(len(calls), 2)
        self.assertTrue(all("branch=main" in url for url in calls))
        self.assertTrue(all("event=schedule" in url for url in calls))
        self.assertTrue(all("per_page=1" in url for url in calls))
        self.assertIn("page=1", calls[0])
        self.assertIn("page=2", calls[1])

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
            self.assertEqual(coverage["unmonitored_scheduled_workflows"], [])
            self.assertEqual(coverage["duplicate_monitored_workflows"], [])


if __name__ == "__main__":
    unittest.main()
