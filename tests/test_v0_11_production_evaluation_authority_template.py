from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "config/provider_equivalence_v0_11_production_evaluation_authority_template_v0_1.json"
PROTOCOL = ROOT / "config/provider_equivalence_v0_11_metadata_stability_evaluation_v0_1.json"
RUNTIME = ROOT / "src/crypto_autopilot/provider_metadata_stability_v0_11.py"
POST_WINDOW = ROOT / "config/provider_equivalence_v0_11_post_window_execution_package_v0_1.json"
DOC = ROOT / "docs/V0_11_PRODUCTION_EVALUATION_AUTHORITY_TEMPLATE.md"
OPERATIONAL_STATUS = ROOT / "web/data/operational-status.json"


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode()
    return hashlib.sha1(header + payload).hexdigest()


def test_template_is_prepared_but_does_not_authorize_execution() -> None:
    cfg = _load(TEMPLATE)
    assert cfg["status"] == "TEMPLATE_PREPARED_EXECUTION_NOT_AUTHORIZED"
    current = cfg["current_boundary"]
    assert isinstance(current, dict)
    assert all(value is False for value in current.values())


def test_template_binds_exact_frozen_protocol_runtime_and_post_window_package() -> None:
    cfg = _load(TEMPLATE)
    lineage = cfg["frozen_lineage"]
    assert isinstance(lineage, dict)
    assert lineage["v0_11_protocol_blob_sha"] == _git_blob_sha(PROTOCOL)
    assert lineage["v0_11_runtime_blob_sha"] == _git_blob_sha(RUNTIME)
    assert lineage["post_window_package_blob_sha"] == _git_blob_sha(POST_WINDOW)
    assert lineage["v0_11_protocol_blob_sha"] == "58bf122d27804a8c61149743ae8c9afca42aca87"
    assert lineage["v0_11_runtime_blob_sha"] == "9ea9cdbf626fa9ecde2f17f748e1807cd6cd09d5"
    assert lineage["post_window_package_blob_sha"] == "be34e426f8305b2dc940a3354506802008302900"


def test_future_actual_authority_cannot_exist_or_read_r2_before_window_end() -> None:
    cfg = _load(TEMPLATE)
    gate = cfg["creation_gate"]
    assert isinstance(gate, dict)
    assert gate["metadata_capture_window_end_utc"] == "2026-09-04T01:59:59.999Z"
    assert gate["actual_authority_may_be_created_before_window_end"] is False
    assert gate["actual_authority_may_be_merged_before_window_end"] is False
    assert gate["r2_client_may_be_constructed_before_actual_authority_merge"] is False
    assert gate["production_r2_receipts_may_be_listed_before_actual_authority_merge"] is False
    assert gate["production_r2_receipts_may_be_read_before_actual_authority_merge"] is False
    assert gate["critical_path_integrity_must_be_reviewed_before_authority_creation"] is True
    assert gate["unreviewed_mid_window_runtime_drift_must_fail_gate"] is True


def test_future_authority_requires_exact_scope_and_protected_main_lineage() -> None:
    cfg = _load(TEMPLATE)
    fields = cfg["required_actual_authority_fields"]
    assert isinstance(fields, dict)
    assert fields["exact_v0_11_protocol_blob_sha"] == "58bf122d27804a8c61149743ae8c9afca42aca87"
    assert fields["exact_v0_11_runtime_blob_sha_before_execution_enablement"] == "9ea9cdbf626fa9ecde2f17f748e1807cd6cd09d5"
    assert fields["expected_hourly_slot_count"] == 194
    assert fields["candidate_symbol_count"] == 15
    assert fields["mapped_pair_count"] == 45
    assert fields["providers"] == ["pionex", "binance_usdm"]
    assert fields["protected_main_pr_number"] == "REQUIRED_INTEGER"
    assert fields["post_merge_main_sha"] == "REQUIRED_AFTER_MERGE_40_HEX"
    required_ci = fields["required_ci_results"]
    assert "test (3.12)=PASS" in required_ci
    assert "test (3.13)=PASS" in required_ci
    assert "V0.11 evaluator validation=PASS" in required_ci


def test_future_atomic_execution_delta_is_receipt_only_and_one_shot() -> None:
    cfg = _load(TEMPLATE)
    atomic = cfg["atomic_future_execution_change"]
    assert isinstance(atomic, dict)
    assert atomic["must_be_same_reviewed_pr_as_actual_execution_authority"] is True
    assert atomic["may_enable_v0_11_r2_evaluation_only_after_window_end"] is True
    assert atomic["must_not_enable_scheduled_or_automatic_evaluation"] is True
    assert atomic["one_shot_reviewed_execution_path_required"] is True
    assert atomic["future_execution_workflow_may_bind_only_r2_read_credentials"] is True
    assert atomic["metadata_relay_token_must_not_be_bound"] is True
    assert atomic["provider_or_render_network_access_must_not_be_added"] is True
    assert atomic["r2_write_or_delete_permission_must_not_be_added"] is True
    assert atomic["holdout_access_must_not_be_added"] is True

    delta = cfg["only_future_authorized_delta_after_separate_authority_merge"]
    assert isinstance(delta, dict)
    assert set(delta) == {
        "r2_client_construction",
        "r2_receipt_listing",
        "r2_receipt_reads",
        "v0_11_evaluator_execution",
    }


def test_future_authority_must_keep_all_downstream_and_write_boundaries_false() -> None:
    cfg = _load(TEMPLATE)
    forbidden = cfg["must_remain_false_in_future_execution_authority"]
    assert isinstance(forbidden, dict)
    assert all(value is False for value in forbidden.values())

    result = cfg["future_result_boundary"]
    assert isinstance(result, dict)
    assert result["sanitized_result_only"] is True
    assert result["increment_values_may_be_emitted"] is False
    assert result["raw_provider_payloads_may_be_emitted"] is False
    assert result["holdout_values_may_be_emitted"] is False
    assert result["pass_automatically_authorizes_holdout_access"] is False
    assert result["fail_authorizes_holdout_access"] is False
    assert result["exact_result_must_be_frozen_as_repository_receipt"] is True


def test_dashboard_projection_shows_template_without_granting_authority() -> None:
    data = _load(OPERATIONAL_STATUS)
    assert data["authority"] is False
    project = data["project"]
    assert isinstance(project, dict)
    assert project["v0_11ProductionEvaluationAuthorityTemplateState"] == "PREPARED_NOT_AUTHORITY"
    assert project["v0_11ProductionR2EvaluationState"] == "NOT_AUTHORIZED"
    assert project["replacementHoldoutState"] == "FROZEN_UNOPENED"
    source_authorities = data["sourceAuthorities"]
    assert isinstance(source_authorities, list)
    assert "config/provider_equivalence_v0_11_production_evaluation_authority_template_v0_1.json" in source_authorities
    security = data["securityBoundary"]
    assert isinstance(security, dict)
    assert all(value is False for value in security.values())


def test_current_runtime_stays_hard_disabled_and_doc_says_not_authorized() -> None:
    runtime = RUNTIME.read_text(encoding="utf-8")
    assert "V0_11_R2_EVALUATION_EXECUTION_AUTHORIZED = False" in runtime
    text = DOC.read_text(encoding="utf-8")
    assert "TEMPLATE PREPARED / EXECUTION NOT AUTHORIZED" in text
    assert "may not be created or merged before `2026-09-04T01:59:59.999Z`" in text
    assert "A future stability PASS still does **not** authorize holdout access" in text
