from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CONFIG = Path("config/v0_10_window_completion_pre_review_checklist_v0_1.json")
DOC = Path("docs/V0_10_WINDOW_COMPLETION_PRE_REVIEW_CHECKLIST.md")


def _load() -> dict[str, Any]:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_checklist_is_prepared_but_not_execution_authority() -> None:
    cfg = _load()
    assert cfg["status"] == "PREPARED_NOT_EXECUTION_AUTHORITY"
    boundary = cfg["authorization_boundary"]
    assert isinstance(boundary, dict)
    assert all(value is False for value in boundary.values())


def test_checklist_preserves_exact_window_and_attempt_scope() -> None:
    gate = _load()["window_gate"]
    assert gate["metadata_capture_start_utc"] == "2026-08-27T00:00:00Z"
    assert gate["metadata_capture_end_utc"] == "2026-09-04T01:59:59.999Z"
    assert gate["review_may_begin_before_window_end"] is False
    assert gate["expected_hourly_slot_count"] == 194
    assert gate["scheduled_attempt_count"] == 388
    assert gate["scheduled_minutes_utc"] == [17, 47]


def test_pre_review_input_scope_is_read_only_and_excludes_production_evidence() -> None:
    allowed = _load()["allowed_read_only_inputs"]
    assert allowed["repository_main_history_and_diffs"] is True
    assert allowed["critical_path_freeze_manifest_and_guard_results"] is True
    assert allowed["github_actions_v0_10_run_job_step_metadata"] is True
    assert allowed["github_actions_observer_run_job_step_metadata"] is True
    assert allowed["versioned_emergency_authority_repository_lineage_if_any"] is True
    assert allowed["render_service_metadata"] is True
    assert allowed["render_deploy_metadata"] is True
    for forbidden in (
        "production_r2_object_listing",
        "production_r2_receipt_read",
        "capture_artifact_read",
        "provider_payload_read",
        "render_provider_payload_read",
        "replacement_holdout_read",
    ):
        assert allowed[forbidden] is False


def test_ready_state_does_not_imply_stability_or_receipt_coverage() -> None:
    semantics = _load()["decision_semantics"]
    assert semantics["pre_review_can_declare_metadata_stability_pass"] is False
    assert semantics["pre_review_can_declare_metadata_stability_fail_from_r2_receipts"] is False
    assert semantics["pre_review_can_authorize_v0_11_production_r2_evaluation"] is False
    assert semantics["pre_review_can_authorize_r2_client_construction"] is False
    assert semantics["pre_review_can_authorize_r2_receipt_listing_or_reads"] is False
    assert semantics["pre_review_can_authorize_holdout_access"] is False
    assert semantics["pre_review_can_authorize_manual_or_retroactive_backfill"] is False
    assert semantics["missing_or_failed_github_attempts_must_be_preserved"] is True
    assert semantics["missing_or_failed_github_attempts_may_be_repaired"] is False
    assert semantics["ready_state_means_only_separate_authority_may_be_considered"] is True
    assert semantics["ready_state_does_not_guarantee_194_valid_r2_receipts"] is True


def test_critical_path_review_fails_closed_on_unreviewed_drift() -> None:
    review = _load()["critical_path_review"]
    assert review["baseline_commit"] == "4a805b30183b23e29ea36689dfaa2ba0a4e4533f"
    assert review["unreviewed_critical_path_drift_allowed"] is False
    assert review["reviewed_mid_window_change_requires_versioned_emergency_authority"] is True
    assert review["retroactive_reclassification_of_prior_failures_allowed"] is False


def test_human_runbook_repeats_non_execution_boundary() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "PREPARED / NOT EXECUTION AUTHORITY" in text
    assert "Do **not** list/read production R2" in text
    assert "do not backfill them" in text
    assert "does not authorize that evaluation" in text
    assert "does not imply that 194 valid R2 receipts exist" in text
