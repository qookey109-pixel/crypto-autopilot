from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "config/v0_10_mid_window_emergency_pionex_perp_query_v0_1.json"
RECEIPT = (
    ROOT
    / "research/receipts/2026-08-30-v0-10-mid-window-emergency-pionex-perp-query-authority.json"
)


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_authority_is_bound_to_incident_commit_and_protected_pr() -> None:
    authority = _load(AUTHORITY)
    lineage = authority["lineage"]
    incident = authority["observed_incident"]
    assert isinstance(lineage, dict)
    assert isinstance(incident, dict)

    assert authority["status"] == (
        "AUTHORIZED_FOR_PROTECTED_MAIN_REVIEW_NOT_EFFECTIVE_BEFORE_MERGE"
    )
    assert lineage["pre_change_main_sha"] == (
        "62c3fee76016f8f42d3e444df79f87e2d55a5fc8"
    )
    assert lineage["minimum_operational_change_commit_sha"] == (
        "a56fcff85e65a051b3848a0362edfa7a6e9019f6"
    )
    assert lineage["protected_main_pr_number"] == 210
    assert lineage["post_merge_main_sha"] is None
    assert incident["latest_failed_run"]["run_id"] == 33286173327
    assert incident["documented_default_when_type_omitted"] == "SPOT"
    assert incident["provider_payload_or_capture_artifact_read_for_this_repair"] is False
    assert incident["prior_failed_or_missing_slots_remain_failures"] is True


def test_authority_changes_only_explicit_pionex_perp_request() -> None:
    authority = _load(AUTHORITY)
    request = authority["request_contract"]
    assert isinstance(request, dict)

    assert request == {
        "provider": "pionex",
        "method": "GET",
        "endpoint": "https://api.pionex.com/api/v1/common/symbols",
        "query_parameter": "type",
        "query_value": "PERP",
        "additional_query_parameters_added": [],
        "public_endpoint_no_api_key_required": True,
        "conflicting_existing_type_must_fail_closed": True,
        "binance_request_changed": False,
        "render_relay_changed": False,
    }
    assert authority["exact_critical_paths_changed_from_frozen_baseline"] == [
        ".github/workflows/provider-equivalence-v0-10-render-metadata-capture.yml",
        "src/crypto_autopilot/provider_metadata_capture_v0_10.py",
    ]


def test_emergency_preserves_frozen_scope_and_all_downstream_boundaries() -> None:
    authority = _load(AUTHORITY)
    scope = authority["preserved_frozen_scope"]
    boundary = authority["authorization_boundary"]
    render = authority["render_boundary"]
    effectivity = authority["effectivity"]
    assert isinstance(scope, dict)
    assert isinstance(boundary, dict)
    assert isinstance(render, dict)
    assert isinstance(effectivity, dict)

    assert all(value is True for key, value in scope.items() if key != "replacement_holdout_state")
    assert scope["replacement_holdout_state"] == "FROZEN_UNOPENED"
    assert all(value is False for value in boundary.values())
    assert all(value is False for value in render.values())
    assert effectivity["effective_before_merge"] is False
    assert effectivity["effective_on_draft_pr"] is False
    assert effectivity["requires_human_review_before_merge"] is True
    assert effectivity["automatic_merge_authorized"] is False


def test_receipt_is_pending_and_records_zero_external_execution() -> None:
    receipt = _load(RECEIPT)
    required = receipt["required_validation"]
    execution = receipt["execution_evidence"]
    assert isinstance(required, dict)
    assert isinstance(execution, dict)

    assert receipt["status"] == "PENDING_REQUIRED_CI_AND_PROTECTED_MAIN_MERGE"
    assert receipt["source_pr"] == 210
    assert receipt["minimum_operational_change_commit_sha"] == (
        "a56fcff85e65a051b3848a0362edfa7a6e9019f6"
    )
    assert required["local_targeted_tests"] == "PASS_9_TESTS"
    assert required["full_local_pytest"] == "PASS_648_TESTS_221_SUBTESTS"
    assert required["post_merge_main_sha"] is None
    assert all(value is False or value == 0 for value in execution.values())
