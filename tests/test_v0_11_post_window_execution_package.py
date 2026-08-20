from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "config/provider_equivalence_v0_11_post_window_execution_package_v0_1.json"
REHEARSAL = ROOT / "research/receipts/2026-08-21-provider-equivalence-v0-11-synthetic-failure-rehearsal-pass.json"
RUNTIME = ROOT / "src/crypto_autopilot/provider_metadata_stability_v0_11.py"
WORKFLOW = ROOT / ".github/workflows/validate-v0-11-metadata-stability-evaluator.yml"


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_synthetic_rehearsal_pass_is_exact_and_non_production() -> None:
    receipt = _load(REHEARSAL)
    assert receipt["status"] == "PASS"
    assert receipt["stage"] == "PROVIDER_EQUIVALENCE_V0_11_SYNTHETIC_FAILURE_REHEARSAL_PASS"
    assert receipt["implementation"]["pull_request"] == 153
    assert receipt["implementation"]["pr_head_sha"] == "461d4236f1db90bdc51e9b64a7dc6dbd431cf891"
    assert receipt["implementation"]["merge_commit"] == "3050e8d4cd91895c4e0a29cb2be67443c98d612f"
    evidence = receipt["github_actions_evidence"]
    assert evidence["workflow_run_id"] == 32406756458
    assert evidence["job_id"] == 96547529797
    assert evidence["job_conclusion"] == "success"
    assert evidence["artifact_id"] == 9420558148
    assert evidence["artifact_digest"] == "sha256:0accb74e825444aa286dee35469bd39799d1270bd209589fa9aa404270df99ce"
    assert receipt["required_ci"] == {
        "full_ci_run_id": 32406756474,
        "test_3_12": "PASS",
        "test_3_13": "PASS",
    }
    result = receipt["result"]
    assert result["scenario_count"] == 12
    assert result["synthetic_fixtures_only"] is True
    assert result["production_metadata_evidence_consumed"] is False
    assert result["r2_client_constructed"] is False
    assert result["r2_reads_performed"] is False
    assert result["r2_writes_performed"] is False
    assert result["provider_requests_performed"] == 0
    assert result["render_requests_performed"] == 0
    assert result["capture_artifacts_read"] is False
    assert result["holdout_candles_accessed"] is False
    assert result["holdout_evaluated"] is False
    assert all(value is False for value in receipt["interpretation"].values())


def test_post_window_package_is_prepared_but_not_execution_authority() -> None:
    package = _load(PACKAGE)
    assert package["status"] == "POST_WINDOW_EXECUTION_PACKAGE_PREPARED_EXECUTION_NOT_AUTHORIZED"
    gate = package["frozen_window_completion_gate"]
    assert gate["metadata_capture_window_end_utc"] == "2026-09-04T01:59:59.999Z"
    assert gate["future_execution_authority_may_be_created_before_window_end"] is False
    assert gate["future_production_r2_receipt_read_may_begin_before_window_end"] is False
    assert gate["future_evaluation_must_not_retroactively_backfill_missing_slots"] is True

    boundary = package["current_execution_boundary"]
    assert boundary["package_is_execution_authority"] is False
    for key, value in boundary.items():
        if key != "package_is_execution_authority":
            assert value is False, key


def test_future_sequence_requires_separate_authority_before_any_r2_read() -> None:
    package = _load(PACKAGE)
    sequence = package["future_evaluation_sequence"]
    authority_index = sequence.index("CREATE_SEPARATE_VERSIONED_V0_11_PRODUCTION_EVALUATION_EXECUTION_AUTHORITY")
    merge_index = sequence.index("MERGE_AUTHORITY_THROUGH_PROTECTED_MAIN_AFTER_REQUIRED_CI")
    r2_index = sequence.index("ONLY_THEN_CONSTRUCT_R2_CLIENT_AND_LIST_ALLOWLISTED_V0_10_RECEIPTS")
    evaluate_index = sequence.index("EVALUATE_EXACT_FROZEN_194_SLOT_SEMANTICS")
    assert authority_index < merge_index < r2_index < evaluate_index

    scope = package["future_allowed_input_scope_only_after_separate_authority"]
    assert scope["allowed_object_kind"] == "V0_10_CAPTURE_RECEIPT_JSON_ONLY"
    assert scope["raw_provider_objects_allowed"] is False
    assert scope["holdout_objects_may_be_listed"] is False
    assert scope["holdout_objects_may_be_read"] is False
    assert scope["provider_requests_allowed"] is False
    assert scope["render_requests_allowed"] is False
    assert scope["r2_writes_allowed"] is False
    assert scope["r2_deletes_allowed"] is False


def test_future_result_is_sanitized_and_never_self_authorizes_holdout() -> None:
    package = _load(PACKAGE)
    contract = package["future_sanitized_result_contract"]
    assert contract["expected_slot_count"] == 194
    assert contract["increment_values_may_be_emitted"] is False
    assert contract["raw_provider_responses_may_be_emitted"] is False
    assert contract["holdout_values_may_be_emitted"] is False
    assert contract["result_may_authorize_holdout_access"] is False

    post = package["post_future_stability_result_boundary"]
    assert post["pass_automatically_authorizes_holdout_access"] is False
    assert post["fail_authorizes_holdout_access"] is False
    assert post["separate_versioned_holdout_access_authority_required_after_pass"] is True


def test_current_runtime_and_validation_workflow_remain_hard_disabled_for_production_r2() -> None:
    runtime = RUNTIME.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "V0_11_R2_EVALUATION_EXECUTION_AUTHORIZED = False" in runtime
    assert not any(line == "  schedule:" for line in workflow.splitlines())
    expression_prefix = "$" + "{{ secrets."
    for secret in (
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "CLOUDFLARE_ACCOUNT_ID",
        "R2_BUCKET_NAME",
        "METADATA_RELAY_TOKEN",
    ):
        assert expression_prefix + secret not in workflow
