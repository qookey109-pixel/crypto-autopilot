from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "config/v0_10_mid_window_emergency_change_template_v0_1.json"
OPERATIONS = ROOT / "config/v0_10_capture_window_operations_v0_1.json"
RUNBOOK = ROOT / "docs/V0_10_MID_WINDOW_EMERGENCY_CHANGE_TEMPLATE.md"


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_template_is_prepared_but_never_authority() -> None:
    cfg = _load(TEMPLATE)
    assert cfg["status"] == "TEMPLATE_PREPARED_NOT_AUTHORITY"
    use = cfg["use_conditions"]
    assert isinstance(use, dict)
    assert use["template_itself_is_authority"] is False
    assert use["may_be_used_before_frozen_window_start"] is False
    assert use["may_be_used_after_frozen_window_end"] is False
    assert use["may_be_used_only_for_observed_production_critical_incident"] is True
    assert use["waiting_for_next_frozen_scheduled_attempt_must_be_considered_first"] is True


def test_future_emergency_authority_requires_lineage_and_protected_pr() -> None:
    cfg = _load(TEMPLATE)
    fields = cfg["required_at_use_time"]
    shape = cfg["permitted_change_shape"]
    assert isinstance(fields, dict)
    assert isinstance(shape, dict)
    for key in (
        "incident_id",
        "incident_detected_at_utc",
        "affected_critical_paths",
        "observed_failure_evidence_refs",
        "pre_change_main_sha",
        "minimum_change_description",
        "exact_files_allowed_to_change",
        "reviewed_test_plan",
        "rollback_or_stop_condition",
        "post_change_head_sha_before_merge",
        "protected_main_pr_number",
        "post_merge_main_sha",
    ):
        assert key in fields
    assert shape["minimum_necessary_change_only"] is True
    assert shape["must_be_versioned_separate_emergency_authority"] is True
    assert shape["must_use_protected_main_pr"] is True
    assert shape["must_bind_pre_and_post_change_sha"] is True


def test_emergency_cannot_rewrite_frozen_science_or_prior_failures() -> None:
    cfg = _load(TEMPLATE)
    shape = cfg["permitted_change_shape"]
    assert isinstance(shape, dict)
    assert shape["must_preserve_prior_failed_blocked_stale_and_missing_evidence"] is True
    assert shape["must_preserve_provider_provenance"] is True
    assert shape["must_preserve_frozen_window_boundaries"] is True
    assert shape["must_preserve_194_hourly_slots"] is True
    assert shape["must_preserve_scheduled_minutes_utc"] == [17, 47]
    assert shape["must_preserve_15_symbol_scope"] is True
    assert shape["must_preserve_45_pair_scope"] is True
    assert shape["must_preserve_8gb_free_only_hard_stop"] is True
    assert shape["must_preserve_30_minute_freshness_guard"] is True
    assert shape["must_keep_replacement_holdout_frozen_unopened"] is True

    forbidden = cfg["forbidden_even_under_emergency"]
    assert isinstance(forbidden, dict)
    assert all(value is False for value in forbidden.values())


def test_render_boundary_cannot_be_bypassed_by_template() -> None:
    cfg = _load(TEMPLATE)
    render = cfg["render_change_boundary"]
    assert isinstance(render, dict)
    assert render["render_change_allowed_without_separate_emergency_authority"] is False
    assert render["render_auto_deploy_should_remain_off"] is True
    assert render["render_redeploy_may_be_triggered_by_template"] is False
    assert render["render_may_receive_r2_credentials"] is False
    assert render["transport_change_requires_pre_and_post_deploy_ids"] is True


def test_template_matches_capture_window_no_backfill_policy() -> None:
    cfg = _load(TEMPLATE)
    operations = _load(OPERATIONS)
    principles = operations["operational_principles"]
    policy = operations["mid_window_change_policy"]
    forbidden = cfg["forbidden_even_under_emergency"]
    assert isinstance(principles, dict)
    assert isinstance(policy, dict)
    assert isinstance(forbidden, dict)
    assert principles["manual_capture_backfill_authorized"] is False
    assert principles["retroactive_slot_backfill_authorized"] is False
    assert policy["emergency_change_requires_separate_versioned_authority"] is True
    assert policy["emergency_change_requires_protected_main_pr"] is True
    assert forbidden["retroactive_slot_backfill_authorized"] is False
    assert forbidden["manual_capture_as_replacement_for_prior_missing_slot_authorized"] is False


def test_human_template_states_failure_may_need_to_remain_failure() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "TEMPLATE PREPARED / NOT AUTHORITY" in text
    assert "failed `:17` run is not itself a reason to intervene" in text
    assert "cannot turn earlier failed or missing evidence into PASS" in text
    assert "allow the post-window V0.11 result to fail closed" in text
