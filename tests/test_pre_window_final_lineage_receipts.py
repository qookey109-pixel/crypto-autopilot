from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V11_RECEIPT = ROOT / "research/receipts/2026-08-21-provider-equivalence-v0-11-production-evaluation-authority-template-prepared.json"
RENDER_RECEIPT = ROOT / "research/receipts/2026-08-21-v0-10-render-final-pre-window-readonly-recheck.json"
V11_TEMPLATE = ROOT / "config/provider_equivalence_v0_11_production_evaluation_authority_template_v0_1.json"
V11_RUNTIME = ROOT / "src/crypto_autopilot/provider_metadata_stability_v0_11.py"


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_v0_11_future_authority_template_receipt_binds_exact_pr_and_ci() -> None:
    receipt = _load(V11_RECEIPT)
    assert receipt["status"] == "PASS"
    assert receipt["stage"] == "V0_11_PRODUCTION_EVALUATION_AUTHORITY_TEMPLATE_PREPARED_PASS"
    assert receipt["source_pr"] == 161
    assert receipt["source_pr_head_sha"] == "e2c1ceada6194989a2962bfa3568a3302c3cd49d"
    assert receipt["source_pr_merge_sha"] == "5cd1d7a129f5d4a57bf2a3d368f781077650784b"

    validation = receipt["validation"]
    assert isinstance(validation, dict)
    assert validation["v0_11_validation_run_id"] == 32410536223
    assert validation["v0_11_validation_job_id"] == 96559656357
    assert validation["v0_11_validation_conclusion"] == "success"
    assert validation["full_ci_run_id"] == 32410536345
    assert validation["python_3_12_job_id"] == 96559656547
    assert validation["python_3_12_conclusion"] == "success"
    assert validation["python_3_13_job_id"] == 96559656248
    assert validation["python_3_13_conclusion"] == "success"
    assert validation["v0_10_operations_regression_run_id"] == 32410536373
    assert validation["v0_10_operations_regression_conclusion"] == "success"
    assert validation["dashboard_zh_hant_conclusion"] == "success"
    assert validation["dashboard_static_smoke_conclusion"] == "success"
    assert validation["dashboard_pages_pr_build_conclusion"] == "success"
    assert validation["historical_v0_8_scaffold_conclusion"] == "success"
    assert validation["historical_v0_8_production_execution_reactivated"] is False


def test_v0_11_template_receipt_keeps_current_execution_hard_disabled() -> None:
    receipt = _load(V11_RECEIPT)
    template = _load(V11_TEMPLATE)
    assert template["status"] == "TEMPLATE_PREPARED_EXECUTION_NOT_AUTHORIZED"
    assert template["creation_gate"]["actual_authority_may_be_created_before_window_end"] is False
    assert template["creation_gate"]["actual_authority_may_be_merged_before_window_end"] is False

    boundary = receipt["current_authorization_boundary"]
    assert isinstance(boundary, dict)
    assert all(value is False for value in boundary.values())

    execution = receipt["execution_evidence"]
    assert isinstance(execution, dict)
    assert execution["production_metadata_evidence_consumed"] is False
    assert execution["provider_requests_performed"] == 0
    assert execution["render_requests_performed"] == 0
    assert execution["r2_client_constructed"] is False
    assert execution["r2_receipts_listed"] is False
    assert execution["r2_receipts_read"] is False
    assert execution["r2_writes_performed"] is False
    assert execution["holdout_candles_accessed"] is False
    assert execution["v0_11_production_r2_evaluation_performed"] is False

    runtime = V11_RUNTIME.read_text(encoding="utf-8")
    assert "V0_11_R2_EVALUATION_EXECUTION_AUTHORIZED = False" in runtime


def test_render_final_pre_window_recheck_preserves_v0_10_runtime_freeze() -> None:
    receipt = _load(RENDER_RECEIPT)
    assert receipt["status"] == "PASS"
    assert receipt["stage"] == "V0_10_RENDER_FINAL_PRE_WINDOW_READONLY_RECHECK_PASS"

    service = receipt["service"]
    assert isinstance(service, dict)
    assert service["service_id"] == "srv-da2qlb67bikc73bibobg"
    assert service["slug"] == "qookey-binance-transport-v0-5"
    assert service["branch"] == "main"
    assert service["root_dir"] == "infra/render/binance-transport-free"
    assert service["plan"] == "free"
    assert service["region"] == "frankfurt"
    assert service["health_check_path"] == "/health"
    assert service["maintenance_mode_enabled"] is False
    assert service["suspended"] is False
    assert service["auto_deploy"] is False
    assert service["auto_deploy_trigger"] == "off"

    deploy = receipt["live_deploy"]
    assert isinstance(deploy, dict)
    assert deploy["deploy_id"] == "dep-da35gfoae00c73fpff8g"
    assert deploy["commit_sha"] == "8fce944da479dbda0e2899f9b30b9de62351fa27"
    assert deploy["status"] == "live"
    assert deploy["is_v0_10_activation_commit"] is True
    assert deploy["unexpected_redeploy_after_v0_10_activation"] is False
    assert deploy["latest_deploy_still_v0_10_activation"] is True


def test_render_recheck_is_observation_only_and_grants_no_authority() -> None:
    receipt = _load(RENDER_RECEIPT)
    observed = receipt["read_only_observation_boundary"]
    assert isinstance(observed, dict)
    assert observed["render_deploy_triggered"] is False
    assert observed["render_environment_values_read"] is False
    assert observed["render_environment_values_changed"] is False
    assert observed["provider_requests_performed"] == 0
    assert observed["production_r2_client_constructed"] is False
    assert observed["production_r2_reads_performed"] is False
    assert observed["production_r2_writes_performed"] is False
    assert observed["capture_artifacts_read"] is False
    assert observed["replacement_holdout_accessed"] is False
    assert observed["v0_11_production_evaluation_performed"] is False

    boundary = receipt["authorization_boundary"]
    assert isinstance(boundary, dict)
    assert all(value is False for value in boundary.values())
