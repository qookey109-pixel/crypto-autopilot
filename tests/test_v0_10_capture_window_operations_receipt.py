from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "research/receipts/2026-08-21-v0-10-capture-window-operations-prepared.json"
OPERATIONS = ROOT / "config/v0_10_capture_window_operations_v0_1.json"


def _load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_operations_receipt_freezes_exact_pass_evidence_without_new_authority() -> None:
    receipt = _load(RECEIPT)
    operations = _load(OPERATIONS)

    assert receipt["status"] == "PASS"
    assert receipt["stage"] == "V0_10_CAPTURE_WINDOW_OPERATIONS_PREPARED_PASS"
    assert receipt["source_pr"] == 156
    assert receipt["source_pr_head_sha"] == "9c2109e8273e0c8248d7030a2e200f5b4b1f284e"
    assert receipt["source_pr_merge_sha"] == "21ea11e01b08929da925cfa9d965f8ebebd8d078"
    assert operations["status"] == "CAPTURE_WINDOW_OPERATIONS_PREPARED_NO_NEW_EXECUTION_AUTHORITY"

    window = receipt["frozen_window"]
    assert isinstance(window, dict)
    assert window["hourly_slot_count"] == 194
    assert window["scheduled_minutes_utc"] == [17, 47]
    assert window["scheduled_attempt_count"] == 388

    dedicated = receipt["ci_evidence"]["dedicated_validation"]
    assert dedicated["workflow_run_id"] == 32408849173
    assert dedicated["job_id"] == 96554283712
    assert dedicated["conclusion"] == "success"
    assert dedicated["regression_test_count"] == 7
    assert dedicated["regression_test_result"] == "PASS"
    assert dedicated["production_execution_surface_assertion"] == "PASS"

    full_ci = receipt["ci_evidence"]["full_ci"]
    assert full_ci["workflow_run_id"] == 32408849225
    assert full_ci["python_3_12_conclusion"] == "success"
    assert full_ci["python_3_13_conclusion"] == "success"

    evidence = receipt["execution_evidence"]
    assert isinstance(evidence, dict)
    assert evidence["production_metadata_evidence_consumed"] is False
    assert evidence["provider_requests_performed"] == 0
    assert evidence["render_requests_performed"] == 0
    assert evidence["r2_client_constructed"] is False
    assert evidence["r2_reads_performed"] is False
    assert evidence["r2_writes_performed"] is False
    assert evidence["capture_artifacts_read"] is False
    assert evidence["holdout_candles_accessed"] is False
    assert evidence["v0_11_production_r2_evaluation_performed"] is False

    boundary = receipt["authorization_boundary"]
    assert isinstance(boundary, dict)
    assert all(value is False for key, value in boundary.items() if key != "receipt_is_new_v0_10_capture_authority")
    assert boundary["receipt_is_new_v0_10_capture_authority"] is False
