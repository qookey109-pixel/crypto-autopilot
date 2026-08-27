from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import scripts.apply_dashboard_latest_authority as dashboard_authority


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "config/v0_10_mid_window_emergency_schedule_reactivation_v0_1.json"
RECEIPT = (
    ROOT
    / "research/receipts/2026-08-27-v0-10-mid-window-emergency-schedule-reactivation-authority.json"
)
FROZEN_CUTOVER = ROOT / "config/provider_equivalence_v0_10_final_atomic_cutover_v0_1.json"
WORKFLOW = ROOT / ".github/workflows/provider-equivalence-v0-10-render-metadata-capture.yml"
RETIRED_WORKFLOW = ROOT / ".github/workflows/provider-equivalence-v0-2-metadata-capture.yml"


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _field_values(field: str, *, lower: int, upper: int) -> set[int]:
    if field == "*":
        return set(range(lower, upper + 1))
    values: set[int] = set()
    for item in field.split(","):
        if "-" in item:
            start_text, end_text = item.split("-", 1)
            values.update(range(int(start_text), int(end_text) + 1))
        else:
            values.add(int(item))
    assert values
    assert min(values) >= lower
    assert max(values) <= upper
    return values


def _matches(cron: str, instant: datetime) -> bool:
    minute, hour, day, month, weekday = cron.split()
    assert weekday == "*"
    return (
        instant.minute in _field_values(minute, lower=0, upper=59)
        and instant.hour in _field_values(hour, lower=0, upper=23)
        and instant.day in _field_values(day, lower=1, upper=31)
        and instant.month in _field_values(month, lower=1, upper=12)
    )


def _expand(crons: list[str]) -> tuple[datetime, ...]:
    cursor = datetime(2026, 8, 27, 0, 0, tzinfo=timezone.utc)
    final_attempt = datetime(2026, 9, 4, 1, 47, tzinfo=timezone.utc)
    attempts: list[datetime] = []
    while cursor <= final_attempt:
        if any(_matches(cron, cursor) for cron in crons):
            attempts.append(cursor)
        cursor += timedelta(minutes=1)
    return tuple(attempts)


def test_emergency_authority_is_bound_to_observed_incident_and_protected_pr() -> None:
    authority = _load(AUTHORITY)
    lineage = authority["lineage"]
    observed = authority["observed_incident"]
    effectivity = authority["effectivity"]
    assert isinstance(lineage, dict)
    assert isinstance(observed, dict)
    assert isinstance(effectivity, dict)

    assert authority["status"] == "AUTHORIZED_FOR_PROTECTED_MAIN_REVIEW_NOT_EFFECTIVE_BEFORE_MERGE"
    assert lineage["pre_change_main_sha"] == "49c6bedb1e79e20963519b7f344762129669feb9"
    assert lineage["minimum_operational_change_commit_sha"] == (
        "10952aedc987c3685149e5817699301b2404e444"
    )
    assert lineage["protected_main_pr_number"] == 201
    assert lineage["post_merge_main_sha"] is None
    assert observed["incident_detected_at_utc"] == "2026-08-27T03:40:07Z"
    assert observed["last_confirmed_at_utc"] == "2026-08-27T07:38:17Z"
    assert observed["schedule_runs_observed"] == 0
    assert observed["direct_root_cause"] == "UNCONFIRMED"
    assert observed["github_documented_schedule_delivery_risk_is_causal_proof"] is False
    assert effectivity["effective_before_merge"] is False
    assert effectivity["effective_on_draft_pr"] is False
    assert effectivity["observed_ci_state"] == "PENDING"
    assert effectivity["requires_human_review_before_merge"] is True
    assert effectivity["automatic_merge_authorized"] is False


def test_original_and_replacement_crons_expand_to_identical_frozen_attempts() -> None:
    authority = _load(AUTHORITY)
    frozen = _load(FROZEN_CUTOVER)
    schedule = authority["schedule_equivalence"]
    assert isinstance(schedule, dict)
    original = schedule["original_authorized_crons"]
    replacement = schedule["replacement_registration_crons"]
    assert isinstance(original, list)
    assert isinstance(replacement, list)
    assert original == frozen["atomic_repository_cutover"]["successor_cron_utc"]

    original_attempts = _expand(original)
    replacement_attempts = _expand(replacement)
    assert replacement_attempts == original_attempts
    assert len(replacement_attempts) == 388
    assert replacement_attempts[0].isoformat() == "2026-08-27T00:17:00+00:00"
    assert replacement_attempts[-1].isoformat() == "2026-09-04T01:47:00+00:00"
    assert {instant.minute for instant in replacement_attempts} == {17, 47}
    hourly_slots = {instant.replace(minute=0) for instant in replacement_attempts}
    assert len(hourly_slots) == 194

    reconfirmed = datetime(2026, 8, 27, 7, 38, 17, tzinfo=timezone.utc)
    assert sum(instant <= reconfirmed for instant in original_attempts) == 15


def test_workflow_uses_only_replacement_registration_text() -> None:
    authority = _load(AUTHORITY)
    schedule = authority["schedule_equivalence"]
    assert isinstance(schedule, dict)
    workflow_text = WORKFLOW.read_text(encoding="utf-8")
    active_crons = re.findall(r'^\s+- cron: "([^"]+)"$', workflow_text, flags=re.MULTILINE)
    assert active_crons == schedule["replacement_registration_crons"]
    retired_lines = RETIRED_WORKFLOW.read_text(encoding="utf-8").splitlines()
    assert not any(line == "  schedule:" for line in retired_lines)
    assert not any("runs-on: [self-hosted" in line for line in retired_lines)


def test_exact_change_set_is_bounded_and_reviewable() -> None:
    authority = _load(AUTHORITY)
    assert set(authority["exact_files_allowed_to_change"]) == {
        ".github/workflows/provider-equivalence-v0-10-render-metadata-capture.yml",
        ".github/workflows/v0-10-critical-path-freeze-guard.yml",
        "PROJECT_STATUS.md",
        "config/v0_10_mid_window_emergency_schedule_reactivation_v0_1.json",
        "research/receipts/2026-08-27-v0-10-mid-window-emergency-schedule-reactivation-authority.json",
        "scripts/apply_dashboard_latest_authority.py",
        "tests/test_current_workflow_actions_node24.py",
        "tests/test_final_atomic_cutover_v0_10.py",
        "tests/test_retired_execution_workflows_hygiene.py",
        "tests/test_v0_10_critical_path_freeze_guard.py",
        "tests/test_v0_10_capture_window_operations.py",
        "tests/test_v0_10_mid_window_emergency_schedule_reactivation_v0_1.py",
    }
    assert len(authority["reviewed_test_plan"]) == 7


def test_dashboard_projection_accepts_only_the_authorized_schedule_registration() -> None:
    lineage = dashboard_authority.validate_render_lineage()
    emergency = lineage["v10_emergency_schedule_authority"]
    assert isinstance(emergency, dict)
    assert emergency["status"] == (
        "AUTHORIZED_FOR_PROTECTED_MAIN_REVIEW_NOT_EFFECTIVE_BEFORE_MERGE"
    )
    assert emergency["effectivity"]["effective_on_draft_pr"] is False
    assert all(value is False for value in emergency["authorization_boundary"].values())


def test_receipt_is_pending_and_records_zero_external_execution() -> None:
    receipt = _load(RECEIPT)
    required = receipt["required_validation"]
    effectivity = receipt["effectivity"]
    execution = receipt["execution_evidence"]
    assert isinstance(required, dict)
    assert isinstance(effectivity, dict)
    assert isinstance(execution, dict)
    assert receipt["status"] == "PENDING_REQUIRED_CI_AND_PROTECTED_MAIN_MERGE"
    assert receipt["source_pr"] == 201
    assert required["test_3_12"] == "PENDING"
    assert required["test_3_13"] == "PENDING"
    assert required["post_merge_main_sha"] is None
    assert effectivity["authority_effective_at_receipt_creation"] is False
    assert effectivity["draft_pr_authorizes_execution"] is False
    assert effectivity["requires_merge_to_protected_main"] is True
    assert all(value is False or value == 0 for value in execution.values())


def test_emergency_change_does_not_expand_science_or_trading_authority() -> None:
    authority = _load(AUTHORITY)
    scope = authority["preserved_frozen_scope"]
    boundary = authority["authorization_boundary"]
    render = authority["render_boundary"]
    assert isinstance(scope, dict)
    assert isinstance(boundary, dict)
    assert isinstance(render, dict)
    assert scope["hourly_slot_count_preserved"] is True
    assert scope["symbol_scope_15_preserved"] is True
    assert scope["pair_scope_45_preserved"] is True
    assert scope["r2_free_only_hard_stop_8gb_preserved"] is True
    assert scope["freshness_guard_30_minutes_preserved"] is True
    assert scope["replacement_holdout_state"] == "FROZEN_UNOPENED"
    assert all(value is False for value in boundary.values())
    assert render["transport_affected"] is False
    assert render["render_redeploy_authorized"] is False
    assert render["render_secret_change_authorized"] is False
    assert render["render_may_receive_r2_credentials"] is False
