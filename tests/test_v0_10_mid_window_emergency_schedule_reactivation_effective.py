from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import scripts.apply_dashboard_latest_authority as dashboard_authority


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "config/v0_10_mid_window_emergency_schedule_reactivation_v0_1.json"
PRE_MERGE_RECEIPT = (
    ROOT
    / "research/receipts/2026-08-27-v0-10-mid-window-emergency-schedule-reactivation-authority.json"
)
EFFECTIVE_RECEIPT = (
    ROOT
    / "research/receipts/2026-08-27-v0-10-mid-window-emergency-schedule-reactivation-effective.json"
)
WORKFLOW = ROOT / ".github/workflows/provider-equivalence-v0-10-render-metadata-capture.yml"
SUCCESSOR_WORKFLOW = (
    ROOT / ".github/workflows/provider-equivalence-v0-12-successor-metadata-capture.yml"
)
STATUS = ROOT / "PROJECT_STATUS.md"


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_effective_receipt_binds_exact_protected_main_merge() -> None:
    receipt = _load(EFFECTIVE_RECEIPT)
    assert receipt["status"] == "PASS"
    assert receipt["stage"] == (
        "V0_10_MID_WINDOW_EMERGENCY_SCHEDULE_REACTIVATION_EFFECTIVE_ON_PROTECTED_MAIN"
    )
    assert receipt["source_pr"] == 201
    assert receipt["source_pr_head_sha"] == (
        "5148161fecd3a0939e51a6ad94db3ec475ae95a2"
    )
    assert receipt["post_merge_main_sha"] == (
        "cf83b6320bc0f0817d8e6ae15d88fe304b933330"
    )
    assert receipt["merged_at_utc"] == "2026-08-27T13:26:40Z"
    assert receipt["effectivity"]["schedule_registration_text_effective"] is True
    assert receipt["effectivity"]["semantic_schedule_authority_changed"] is False
    observation = receipt["preserved_incident_evidence"]
    assert observation["first_post_merge_scheduled_instant_utc"] == (
        "2026-08-27T13:47:00Z"
    )
    assert observation["post_merge_observed_at_utc"] == "2026-08-27T13:51:28Z"
    assert observation["first_post_merge_run_instantiated_at_observation"] is False
    assert observation["schedule_runs_observed_at_post_merge_observation"] == 1
    assert observation["elapsed_trigger_instants_at_post_merge_observation"] == 28


def test_pre_merge_evidence_remains_immutable_and_non_effective_at_creation() -> None:
    authority = _load(AUTHORITY)
    receipt = _load(PRE_MERGE_RECEIPT)
    assert authority["lineage"]["post_merge_main_sha"] is None
    assert authority["status"] == (
        "AUTHORIZED_FOR_PROTECTED_MAIN_REVIEW_NOT_EFFECTIVE_BEFORE_MERGE"
    )
    assert receipt["required_validation"]["post_merge_main_sha"] is None
    assert receipt["effectivity"]["authority_effective_at_receipt_creation"] is False


def test_effective_registration_receipt_remains_historical_after_v012_retirement() -> None:
    receipt = _load(EFFECTIVE_RECEIPT)
    active_crons = re.findall(
        r'^\s+- cron: "([^"]+)"$',
        WORKFLOW.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    assert active_crons == []
    assert receipt["validated_change"]["effective_registration_crons"] == [
        "17,47 * 27,28,29,30,31 8 *",
        "17,47 * 1,2,3 9 *",
        "17,47 0,1 4 9 *",
    ]
    successor_crons = re.findall(
        r'^\s+- cron: "([^"]+)"$',
        SUCCESSOR_WORKFLOW.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    assert successor_crons == [
        "17,47 2-23 4 9 *",
        "17,47 * 5,6,7,8,9,10,11 9 *",
        "17,47 0-3 12 9 *",
    ]
    assert receipt["validated_change"]["semantic_attempt_set_equal"] is True
    assert receipt["validated_change"]["frozen_attempt_count"] == 388
    assert receipt["validated_change"]["frozen_hourly_slot_count"] == 194
    assert receipt["validated_change"]["scheduled_minutes_utc"] == [17, 47]
    assert all(value is False for value in receipt["authorization_boundary"].values())
    assert all(
        value is False or value == 0
        for value in receipt["post_merge_receipt_execution_evidence"].values()
    )


def test_status_and_dashboard_project_effective_post_merge_lineage() -> None:
    status = STATUS.read_text(encoding="utf-8")
    assert "V0.10 MID-WINDOW SCHEDULE RE-REGISTRATION HISTORICAL EFFECTIVE" in status
    assert "PR #201 DRAFT / NOT EFFECTIVE" not in status
    assert "V0.10 PIONEX PERP QUERY EFFECTIVE" in status
    assert "PROPOSED IN PR #210 / NOT EFFECTIVE" not in status

    lineage = dashboard_authority.validate_render_lineage()
    receipt = lineage["v10_emergency_schedule_effective"]
    assert receipt["status"] == "PASS"
    interpretation = receipt["interpretation"]
    assert interpretation["receipt_means_github_will_deliver_future_schedule_events"] is False
    assert interpretation["receipt_means_pionex_provider_failure_is_resolved"] is False

    observation = dashboard_authority.validate_v10_post_perp_schema_observation()
    assert observation["status"] == "FAIL_CLOSED"
    assert observation["lineage"]["source_pr"] == 210
    assert observation["operational_interpretation"]["r2_client_constructed"] is False
    assert observation["scientific_impact"][
        "current_frozen_window_eligible_for_complete_194_slot_pass"
    ] is False


def test_dashboard_overlay_emits_effective_registration_state(
    tmp_path: Path, monkeypatch
) -> None:
    source = ROOT / "web/data/dashboard.json"
    output = tmp_path / "dashboard.json"
    output.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "apply_dashboard_latest_authority.py",
            "--input",
            str(output),
            "--output",
            str(output),
        ],
    )
    assert dashboard_authority.main() == 0
    dashboard = _load(output)
    project = dashboard["project"]
    assert project["v0_10EmergencyScheduleRegistrationState"] == "HISTORICAL_EFFECTIVE"
    assert project["v0_10EmergencyScheduleRegistrationMergeSha"] == (
        "cf83b6320bc0f0817d8e6ae15d88fe304b933330"
    )
    assert project["v0_10PerpQueryMergeSha"] == (
        "a34cf471876971a97200de4974906743642ed61f"
    )
    assert project["v0_10CaptureOperationalState"] == (
        "RETIRED_AFTER_FAIL_CLOSED_PIONEX_SCHEMA_MISMATCH"
    )
    assert project["v0_10CaptureObservedFailedRunCount"] == 6
    assert project["v0_10CaptureLatestObservedRunId"] == 33366572161
    assert project["metadataStabilityState"] == "NOT_YET_RUN"
    assert project["metadataStabilityEligibilityState"] == (
        "V0_10_BLOCKED_V0_12_NOT_YET_RUN"
    )
    assert any(
        item["name"] == "V0.10 Schedule Re-registration"
        and item["status"] == "HISTORICAL"
        for item in dashboard["pipeline"]
    )
    assert any(
        item["name"] == "V0.10 Scheduled Capture"
        and item["status"] == "RETIRED"
        for item in dashboard["pipeline"]
    )
    assert any(
        item["name"] == "V0.12 Successor Metadata Window"
        and item["status"] == "AUTHORIZED"
        for item in dashboard["pipeline"]
    )
    assert any(
        item["name"] == "V0.12 Metadata Capture"
        and item["status"] == "AUTHORIZED"
        and item["critical"] is False
        for item in dashboard["gates"]
    )
