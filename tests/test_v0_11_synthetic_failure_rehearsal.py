from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "config/provider_equivalence_v0_11_synthetic_failure_rehearsal_v0_1.json"
V0_10_WORKFLOW = ROOT / ".github/workflows/provider-equivalence-v0-10-render-metadata-capture.yml"


def _matrix() -> dict[str, object]:
    payload = json.loads(MATRIX.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_synthetic_rehearsal_matrix_is_exact_and_production_free() -> None:
    payload = _matrix()
    assert payload["status"] == "SYNTHETIC_REHEARSAL_PROTOCOL_FROZEN_NO_PRODUCTION_EVIDENCE"
    scenarios = payload["rehearsal_matrix"]
    assert isinstance(scenarios, list)
    assert len(scenarios) == payload["required_synthetic_scenario_count"] == 12
    ids = [scenario["id"] for scenario in scenarios]
    assert len(ids) == len(set(ids))
    assert ids == [
        "stable_194_slot_control",
        "same_slot_identical_duplicate",
        "missing_hour",
        "same_slot_vector_disagreement",
        "cross_window_vector_drift",
        "normalized_vector_sha_mismatch",
        "receipt_claims_holdout_access",
        "receipt_key_outside_allowlist",
        "prepared_production_entrypoint",
        "v0_10_r2_headroom_block",
        "v0_10_outside_window",
        "v0_10_stale_schedule_guard_contract",
    ]

    boundary = payload["execution_boundary"]
    assert boundary["synthetic_fixtures_only"] is True
    for key in (
        "production_metadata_evidence_consumed",
        "r2_client_construction_authorized",
        "r2_reads_authorized",
        "r2_writes_authorized",
        "provider_requests_authorized",
        "render_requests_authorized",
        "capture_artifact_reads_authorized",
        "holdout_candle_access_authorized",
        "holdout_evaluation_authorized",
        "source_switch_authorized",
        "staged_trade_kline_w1_materialization_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        assert boundary[key] is False

    interpretation = payload["interpretation_boundary"]
    assert all(value is False for value in interpretation.values())


def test_every_rehearsal_selector_exists_in_repository() -> None:
    payload = _matrix()
    for scenario in payload["rehearsal_matrix"]:
        selector = scenario["pytest_selector"]
        path_text, function_name = selector.split("::", 1)
        path = ROOT / path_text
        assert path.is_file(), selector
        source = path.read_text(encoding="utf-8")
        assert f"def {function_name}(" in source, selector


def test_stale_freshness_guard_contract_is_fail_closed_before_provider_or_r2() -> None:
    workflow = V0_10_WORKFLOW.read_text(encoding="utf-8")
    assert "Reject stale scheduled runs before provider or R2 access" in workflow
    assert "age > timedelta(minutes=30)" in workflow
    assert "STALE_QUEUED_RUN_OVER_30_MINUTES" in workflow
    assert "SCHEDULE_FRESHNESS_GUARD_SKIP" in workflow
    assert "'provider_requests_performed': 0" in workflow
    assert "'render_relay_requests_performed': 0" in workflow
    assert "'r2_client_constructed': False" in workflow
    assert "'r2_writes_performed': False" in workflow
    assert "'holdout_candles_accessed': False" in workflow
    capture_step = workflow.index("Capture frozen provider metadata through V0.10 successor path")
    freshness_step = workflow.index("Reject stale scheduled runs before provider or R2 access")
    assert freshness_step < capture_step
