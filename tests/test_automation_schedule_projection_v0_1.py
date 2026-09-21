from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import build_automation_schedule_projection as schedule_builder
from scripts.build_dashboard_content_hash import build_content_hash


ROOT = Path(__file__).resolve().parents[1]


def test_checked_in_automation_projection_matches_versioned_sources() -> None:
    expected = schedule_builder.build_projection(checked_in_fixture=True)
    actual = json.loads(
        (ROOT / "web/data/operations-schedule.json").read_text(encoding="utf-8")
    )
    assert actual == expected
    assert actual["authority"] is False
    assert actual["summary"]["scheduledJobCount"] == 7
    assert actual["summary"]["projectedScheduledJobCount"] == 7
    assert actual["summary"]["repositoryScheduledWorkflowCount"] == 7
    assert actual["summary"]["monitoredScheduledWorkflowCount"] == 7
    assert actual["summary"]["scheduleInventoryConverged"] is True
    assert actual["summary"]["waitingAuthorityCount"] == 3
    assert actual["summary"]["plannedNotScheduledCount"] == 5
    assert actual["summary"]["core100HistoryStatus"] == "COMPLETE"
    assert actual["summary"]["core100HistoryRetirementPending"] is False
    assert actual["summary"]["core100HistoryScheduleRetired"] is True
    assert actual["summary"]["core100TrainingDedupeState"] == "ACTIVE_FINGERPRINT_NO_CHANGE"
    assert actual["sourceStatus"]["scheduleInventory"] == {
        "state": "CONVERGED",
        "repositoryScheduledWorkflowCount": 7,
        "projectedScheduledJobCount": 7,
        "monitoredScheduledWorkflowCount": 7,
        "freshnessAndEffectivePeriodSource": "config/research_automation_health_v0_2.json",
        "automaticOperationsInventory": "config/github_automatic_research_operations_v0_5.json",
    }
    assert actual["sourceStatus"]["resourceHub"]["state"] == (
        "SCHEDULED_READ_ONLY_CHANGE_WATCH"
    )
    assert actual["sourceStatus"]["externalCapabilityRegistry"]["candidateCount"] == 10
    core100 = actual["sourceStatus"]["core100"]
    assert core100["historyState"] == "COMPLETE_SCHEDULE_RETIRED"
    assert core100["historyGenericBackfillRetired"] is True
    assert core100["trainingState"] == "FINGERPRINT_DEDUP_ACTIVE"
    assert core100["trainingBaselineRunId"] == 34918219864
    assert core100["trainingNoChangeWritesR2"] is False
    assert actual["sourceStatus"]["zecV0_3"]["expectedCells"] == 256
    assert actual["sourceStatus"]["zecV0_3"]["completedCells"] == 0
    items = {row["id"]: row for row in actual["items"]}
    assert items["resource-hub-change-watch-v0-2"]["freshness_seconds"] == 108000
    assert items["research-signal-v0-2"]["freshness_seconds"] == 108000
    assert items["research-signal-quality-v0-1"]["freshness_seconds"] == 108000
    assert items["automation-health-v0-2"]["freshness_seconds"] == 14400
    assert items["dashboard-pages-projection"]["freshness_seconds"] == 108000
    assert items["core100-training-v0-1-2"]["freshness_seconds"] == 691200
    assert items["pionex-alternative-observability-v0-2"]["freshness_seconds"] == 691200
    assert all(
        row["freshness_source"] == "config/research_automation_health_v0_2.json"
        for row in items.values()
        if row.get("expected_crons")
    )
    assert all(value is False for value in actual["safetyBoundary"].values())


def test_projection_fails_closed_on_workflow_cron_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = json.loads(schedule_builder.POLICY.read_text(encoding="utf-8"))
    target = next(
        row for row in policy["jobs"] if row["id"] == "resource-hub-change-watch-v0-2"
    )
    target["expected_crons"] = ["14 1 * * *"]
    changed = tmp_path / "schedule-policy.json"
    changed.write_text(json.dumps(policy), encoding="utf-8")
    monkeypatch.setattr(schedule_builder, "POLICY", changed)

    with pytest.raises(RuntimeError, match="workflow cron drift"):
        schedule_builder.build_projection(checked_in_fixture=True)


def test_resource_hub_v0_2_workflow_is_daily_read_only_change_watch() -> None:
    workflow = (
        ROOT / ".github/workflows/resource-hub-supply-chain-v0-2.yml"
    ).read_text(encoding="utf-8")
    assert 'cron: "13 1 * * *"' in workflow
    assert "actions: read" in workflow
    assert "contents: read" in workflow
    assert "resource_hub_change_watch_v0_2.py" in workflow
    assert "automatic_pull_request_authorized" in workflow
    assert "pull-requests: write" not in workflow
    assert "gh pr create" not in workflow


def test_dashboard_pages_has_daily_backstop_and_content_hash_dedup() -> None:
    workflow = (
        ROOT / ".github/workflows/dashboard-github-pages.yml"
    ).read_text(encoding="utf-8")
    assert 'cron: "43 4 * * *"' in workflow
    assert '"Resource Hub Supply Chain V0.2"' in workflow
    assert "build_automation_schedule_projection.py" in workflow
    assert "build_dashboard_content_hash.py" in workflow
    assert "steps.content-hash.outputs.deploy_required == 'true'" in workflow
    assert "needs.build.outputs.deploy_required == 'true'" in workflow


def test_business_content_hash_ignores_build_timestamp_only(tmp_path: Path) -> None:
    site = tmp_path / "site"
    data = site / "data"
    assets = site / "assets"
    data.mkdir(parents=True)
    assets.mkdir(parents=True)
    (site / "index.html").write_text("<main>same</main>", encoding="utf-8")
    (assets / "app.js").write_text("console.log('same')", encoding="utf-8")
    dashboard = {
        "authority": False,
        "generatedAtUtc": "2026-09-20T00:00:00Z",
        "project": {"state": "PASS"},
    }
    (data / "dashboard.json").write_text(json.dumps(dashboard), encoding="utf-8")

    first, _ = build_content_hash(site)
    dashboard["generatedAtUtc"] = "2026-09-21T00:00:00Z"
    (data / "dashboard.json").write_text(json.dumps(dashboard), encoding="utf-8")
    second, _ = build_content_hash(site)
    assert first == second

    dashboard["project"]["state"] = "REVIEW_REQUIRED"
    (data / "dashboard.json").write_text(json.dumps(dashboard), encoding="utf-8")
    third, _ = build_content_hash(site)
    assert third != second


def test_business_content_hash_changes_for_frontend_asset(tmp_path: Path) -> None:
    site = tmp_path / "site"
    (site / "data").mkdir(parents=True)
    (site / "assets").mkdir(parents=True)
    (site / "index.html").write_text("<main>same</main>", encoding="utf-8")
    app = site / "assets/app.js"
    app.write_text("console.log('a')", encoding="utf-8")
    first, _ = build_content_hash(site)
    app.write_text("console.log('b')", encoding="utf-8")
    second, _ = build_content_hash(site)
    assert first != second
