from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "research/receipts/2026-08-21-v0-10-mid-window-emergency-template-prepared.json"
TEMPLATE = ROOT / "config/v0_10_mid_window_emergency_change_template_v0_1.json"


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_receipt_freezes_exact_template_validation_without_authorizing_change() -> None:
    receipt = _load(RECEIPT)
    template = _load(TEMPLATE)

    assert receipt["status"] == "PASS"
    assert receipt["stage"] == "V0_10_MID_WINDOW_EMERGENCY_CHANGE_TEMPLATE_PREPARED_PASS"
    assert receipt["source_pr"] == 159
    assert receipt["source_pr_head_sha"] == "f7623ec3b5cb4ecb079506463e9af75a7b0dec5f"
    assert receipt["source_pr_merge_sha"] == "84ae0dedef182673839266428c5077b6d0bc9de1"
    assert template["status"] == "TEMPLATE_PREPARED_NOT_AUTHORITY"

    validation = receipt["validation"]
    assert isinstance(validation, dict)
    assert validation["dedicated_workflow_run_id"] == 32409816752
    assert validation["dedicated_job_id"] == 96557369760
    assert validation["dedicated_conclusion"] == "success"
    assert validation["full_ci_run_id"] == 32409816739
    assert validation["python_3_12_conclusion"] == "success"
    assert validation["python_3_13_conclusion"] == "success"
    assert validation["dashboard_zh_hant_conclusion"] == "success"
    assert validation["dashboard_static_smoke_conclusion"] == "success"
    assert validation["dashboard_pages_pr_build_conclusion"] == "success"
    assert validation["historical_v0_8_production_execution_reactivated"] is False

    evidence = receipt["execution_evidence"]
    assert isinstance(evidence, dict)
    assert evidence["production_metadata_evidence_consumed"] is False
    assert evidence["provider_requests_performed"] == 0
    assert evidence["render_requests_performed"] == 0
    assert evidence["render_deploy_triggered"] is False
    assert evidence["r2_client_constructed"] is False
    assert evidence["r2_reads_performed"] is False
    assert evidence["r2_writes_performed"] is False
    assert evidence["capture_artifacts_read"] is False
    assert evidence["holdout_candles_accessed"] is False
    assert evidence["holdout_evaluated"] is False
    assert evidence["v0_11_production_r2_evaluation_performed"] is False

    forbidden = receipt["forbidden_even_under_future_emergency"]
    assert isinstance(forbidden, dict)
    assert all(value is False for value in forbidden.values())

    interpretation = receipt["interpretation"]
    assert isinstance(interpretation, dict)
    assert interpretation["pass_means_template_is_prepared_and_validated"] is True
    assert interpretation["pass_means_mid_window_production_change_is_authorized"] is False
    assert interpretation["pass_means_prior_missing_slot_can_be_repaired"] is False
    assert interpretation["pass_means_metadata_stability_pass"] is False
    assert interpretation["pass_means_holdout_access_authorized"] is False
