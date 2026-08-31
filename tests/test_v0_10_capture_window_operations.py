from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPERATIONS = ROOT / "config/v0_10_capture_window_operations_v0_1.json"
RUNBOOK = ROOT / "docs/V0_10_CAPTURE_WINDOW_OPERATIONS_RUNBOOK.md"
CAPTURE_WORKFLOW = ROOT / ".github/workflows/provider-equivalence-v0-10-render-metadata-capture.yml"
SUCCESSOR_WORKFLOW = (
    ROOT / ".github/workflows/provider-equivalence-v0-12-successor-metadata-capture.yml"
)
OBSERVER_WORKFLOW = ROOT / ".github/workflows/observe-v0-10-scheduled-capture.yml"
POST_WINDOW = ROOT / "config/provider_equivalence_v0_11_post_window_execution_package_v0_1.json"
OPERATIONAL_STATUS = ROOT / "web/data/operational-status.json"


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_capture_window_operations_preserve_frozen_v0_10_history_after_retirement() -> None:
    cfg = _load(OPERATIONS)
    window = cfg["frozen_window"]
    assert isinstance(window, dict)
    assert cfg["status"] == "CAPTURE_WINDOW_OPERATIONS_PREPARED_NO_NEW_EXECUTION_AUTHORITY"
    assert window["start_utc"] == "2026-08-27T00:00:00Z"
    assert window["end_utc"] == "2026-09-04T01:59:59.999Z"
    assert window["hourly_slot_count"] == 194
    assert window["scheduled_minutes_utc"] == [17, 47]
    assert window["scheduled_attempt_count"] == 388
    assert window["first_scheduled_attempt_utc"] == "2026-08-27T00:17:00Z"
    assert window["last_scheduled_attempt_utc"] == "2026-09-04T01:47:00Z"

    workflow = CAPTURE_WORKFLOW.read_text(encoding="utf-8")
    assert not any(line == "  schedule:" for line in workflow.splitlines())
    successor = SUCCESSOR_WORKFLOW.read_text(encoding="utf-8")
    assert any(line == "  schedule:" for line in successor.splitlines())
    for cron in (
        'cron: "17,47 * 27,28,29,30,31 8 *"',
        'cron: "17,47 * 1,2,3 9 *"',
        'cron: "17,47 0,1 4 9 *"',
    ):
        assert cron not in workflow


def test_operations_policy_forbids_manual_and_retroactive_backfill() -> None:
    cfg = _load(OPERATIONS)
    principles = cfg["operational_principles"]
    assert isinstance(principles, dict)
    assert principles["scheduled_runs_are_primary_execution_path"] is True
    assert principles["manual_capture_backfill_authorized"] is False
    assert principles["retroactive_slot_backfill_authorized"] is False
    assert principles["missed_slots_must_remain_observed_failures"] is True
    assert principles["automatic_repair_authorized"] is False
    assert principles["automatic_redeploy_authorized"] is False
    assert principles["automatic_secret_rotation_authorized"] is False
    assert principles["automatic_budget_override_authorized"] is False


def test_incident_matrix_preserves_fail_closed_semantics() -> None:
    cfg = _load(OPERATIONS)
    rows = cfg["incident_matrix"]
    assert isinstance(rows, list)
    by_incident = {row["incident"]: row for row in rows}
    assert len(by_incident) == 6

    first_failure = by_incident["FIRST_ATTEMPT_17_FAILS_SECOND_47_NOT_YET_RUN"]
    assert "ALLOW_FROZEN_47_MINUTE_SCHEDULED_ATTEMPT_TO_RUN_NORMALLY" in first_failure[
        "allowed_response"
    ]
    assert "MANUAL_CAPTURE_BACKFILL" in first_failure["forbidden_response"]

    missing = by_incident["BOTH_SCHEDULED_ATTEMPTS_FAIL_WITHIN_ONE_UTC_HOUR"]
    assert "RETROACTIVE_BACKFILL" in missing["forbidden_response"]
    assert "DROP_FAILED_RUNS_FROM_LINEAGE" in missing["forbidden_response"]

    r2 = by_incident["R2_FREE_ONLY_HEADROOM_GATE_BLOCKED"]
    assert "STOP_BEFORE_WRITE" in r2["allowed_response"]
    assert "BYPASS_HEADROOM_GATE" in r2["forbidden_response"]

    stale = by_incident["STALE_SCHEDULED_RUN_OVER_30_MINUTES"]
    assert "STOP_BEFORE_PROVIDER_OR_R2_ACCESS" in stale["allowed_response"]
    assert "OVERRIDE_FRESHNESS_GUARD" in stale["forbidden_response"]


def test_observer_remains_metadata_only() -> None:
    text = OBSERVER_WORKFLOW.read_text(encoding="utf-8")
    assert "actions: read" in text
    assert "contents: read" in text
    assert "capture_artifact_read': False" in text
    assert "r2_client_constructed': False" in text
    assert "r2_reads_performed': False" in text
    assert "r2_writes_performed': False" in text
    assert "holdout_accessed': False" in text
    assert "v0_11_evaluation_performed': False" in text
    for secret in (
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "CLOUDFLARE_ACCOUNT_ID",
        "R2_BUCKET_NAME",
        "METADATA_RELAY_TOKEN",
    ):
        assert f"secrets.{secret}" not in text


def test_mid_window_emergency_change_cannot_rewrite_science() -> None:
    cfg = _load(OPERATIONS)
    policy = cfg["mid_window_change_policy"]
    assert isinstance(policy, dict)
    assert policy["default_state"] == "NO_PRODUCTION_CRITICAL_MUTATION"
    assert policy["emergency_change_requires_separate_versioned_authority"] is True
    assert policy["emergency_change_requires_protected_main_pr"] is True
    assert policy["emergency_change_must_not_retroactively_validate_prior_missing_slots"] is True
    assert policy["emergency_change_must_not_change_frozen_thresholds_or_scope"] is True
    assert policy["emergency_change_must_not_open_holdout"] is True


def test_runbook_and_post_window_package_keep_v0_11_unauthorized() -> None:
    cfg = _load(OPERATIONS)
    boundary = cfg["current_authorization_boundary"]
    assert isinstance(boundary, dict)
    for key in (
        "this_document_changes_v0_10_capture_authority",
        "this_document_authorizes_manual_capture",
        "this_document_authorizes_r2_reads",
        "this_document_authorizes_r2_writes",
        "this_document_authorizes_provider_requests",
        "this_document_authorizes_render_requests",
        "this_document_authorizes_v0_11_production_evaluation",
        "holdout_candle_access_authorized",
        "holdout_evaluation_authorized",
        "source_switch_authorized",
        "provider_splicing_authorized",
        "staged_trade_kline_w1_materialization_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        assert boundary[key] is False

    post = _load(POST_WINDOW)
    current = post["current_execution_boundary"]
    assert isinstance(current, dict)
    assert current["v0_11_production_r2_evaluation_authorized"] is False
    assert current["r2_client_construction_authorized"] is False
    assert current["holdout_candle_access_authorized"] is False

    runbook = RUNBOOK.read_text(encoding="utf-8")
    assert "PREPARED / NO NEW EXECUTION AUTHORITY" in runbook
    assert "Do not manually backfill" in runbook
    assert "FROZEN_UNOPENED" in runbook


def test_dashboard_projection_exposes_operations_without_granting_authority() -> None:
    dashboard = _load(OPERATIONAL_STATUS)
    assert dashboard["authority"] is False
    project = dashboard["project"]
    assert isinstance(project, dict)
    assert project["v0_10CaptureWindowOperationsState"] == "PREPARED"
    assert project["v0_10ScheduledAttemptCount"] == 388
    assert project["manualCaptureBackfillAuthorized"] is False
    assert project["retroactiveSlotBackfillAuthorized"] is False
    assert project["midWindowCriticalMutationDefaultAuthorized"] is False
    assert project["emergencyCriticalPathChangeRequiresVersionedAuthority"] is True
    assert project["v0_11ProductionR2EvaluationState"] == "NOT_AUTHORIZED"
    assert project["replacementHoldoutState"] == "FROZEN_UNOPENED"

    security = dashboard["securityBoundary"]
    assert isinstance(security, dict)
    assert all(value is False for value in security.values())

    source_authorities = dashboard["sourceAuthorities"]
    assert isinstance(source_authorities, list)
    assert "config/v0_10_capture_window_operations_v0_1.json" in source_authorities
