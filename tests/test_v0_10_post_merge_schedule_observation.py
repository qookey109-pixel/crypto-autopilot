from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = (
    ROOT
    / "research/receipts/2026-08-28-v0-10-post-merge-schedule-observation.json"
)


def _load() -> dict[str, object]:
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_post_merge_observation_is_new_main_fail_closed_run() -> None:
    receipt = _load()
    source = receipt["source_run"]
    steps = receipt["step_observations"]
    coverage = receipt["coverage_observation"]
    boundary = receipt["observer_boundary"]
    interpretation = receipt["interpretation"]
    assert receipt["status"] == "OBSERVED_FAIL_CLOSED"
    assert source["run_id"] == 33124856368
    assert source["head_sha"] == "a325728cf92c2885ef0611fc1a57f45389de6b77"
    assert source["event"] == "schedule"
    assert source["conclusion"] == "failure"
    assert steps["window_gate"] == "PASS"
    assert steps["atomic_cutover_validation"] == "PASS"
    assert steps["capture_step"] == "FAIL"
    assert coverage["schedule_runs_observed_total"] == 2
    assert coverage["post_merge_schedule_instantiated"] is True
    assert coverage["post_merge_capture_succeeded"] is False
    assert coverage["delivery_recovery_status"] == "NOT_CONFIRMED"
    assert boundary["workflow_logs_read"] is False
    assert boundary["provider_payload_read"] is False
    assert boundary["capture_artifact_read"] is False
    assert boundary["manual_dispatch_used"] is False
    assert interpretation["capture_failure_root_cause"] == "UNCONFIRMED"
    assert interpretation["post_merge_run_proves_metadata_stability"] is False
