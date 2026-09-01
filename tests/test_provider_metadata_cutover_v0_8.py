from __future__ import annotations

import json
import os
from pathlib import Path

from crypto_autopilot import provider_metadata_capture_v0_8 as v08


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/provider_equivalence_v0_8_render_metadata_execution_cutover_v0_1.json"
V07 = ROOT / "config/provider_equivalence_v0_7_render_metadata_capture_protocol_v0_1.json"
V02 = ROOT / "config/provider_equivalence_v0_2_metadata_capture_v0_2.json"
V010 = ROOT / "config/provider_equivalence_v0_10_final_atomic_cutover_v0_1.json"
SUCCESSOR_WORKFLOW = ROOT / ".github/workflows/provider-equivalence-v0-8-render-metadata-capture.yml"
OLD_WORKFLOW = ROOT / ".github/workflows/provider-equivalence-v0-2-metadata-capture.yml"
V010_WORKFLOW = ROOT / ".github/workflows/provider-equivalence-v0-10-render-metadata-capture.yml"
V012_WORKFLOW = ROOT / ".github/workflows/provider-equivalence-v0-12-successor-metadata-capture.yml"


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_v08_contract_validates_and_preserves_v02_v07_scope() -> None:
    result = v08.validate_cutover_contract()
    assert result["status"] == "PASS"
    assert result["stage"] == "V0_8_CUTOVER_CONTRACT_VALIDATION_PASS"
    assert result["old_schedule_present"] is True
    assert result["successor_schedule_enabled"] is False
    assert result["render_relay_enabled"] is False
    assert result["successor_capture_execution_authorized"] is False

    v02 = _load(V02)
    v07 = _load(V07)
    config = _load(CONFIG)
    assert config["scientific_scope"]["holdout_start_utc"] == v02["candidate_holdout"]["start_utc"]
    assert config["scientific_scope"]["holdout_end_utc"] == v02["candidate_holdout"]["end_utc"]
    assert config["scientific_scope"]["metadata_capture_start_utc"] == v02["metadata_capture_window"]["start_utc"]
    assert config["scientific_scope"]["metadata_capture_end_utc"] == v02["metadata_capture_window"]["end_utc"]
    assert config["scientific_scope"]["scheduled_minutes_utc"] == v07["metadata_capture_window"]["scheduled_minutes_utc"]
    assert config["scientific_scope"]["hourly_slot_count"] == 194
    assert config["scientific_scope"]["candidate_symbol_count"] == 15
    assert config["scientific_scope"]["mapped_pair_count"] == 45


def test_v08_guard_cannot_be_enabled_by_environment_secrets() -> None:
    prior = {key: os.environ.get(key) for key in ("METADATA_RELAY_TOKEN", "METADATA_RELAY_ENABLED", "R2_SECRET_ACCESS_KEY")}
    try:
        os.environ["METADATA_RELAY_TOKEN"] = "sentinel-not-a-real-secret"
        os.environ["METADATA_RELAY_ENABLED"] = "true"
        os.environ["R2_SECRET_ACCESS_KEY"] = "sentinel-not-a-real-secret"
        assert v08.V0_8_CAPTURE_EXECUTION_AUTHORIZED is False
        result = v08.guarded_capture_entrypoint()
        assert result["status"] == "SKIP"
        assert result["provider_requests_performed"] == 0
        assert result["render_relay_requests_performed"] == 0
        assert result["r2_client_constructed"] is False
        assert result["r2_writes_performed"] is False
        assert result["holdout_candles_accessed"] is False
    finally:
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def test_v08_requires_atomic_exclusive_cutover_and_out_of_band_secret() -> None:
    config = _load(CONFIG)
    cutover = config["atomic_cutover_contract"]
    secret = config["secret_boundary"]
    boundary = config["authorization_boundary"]

    assert cutover["atomic_activation_required"] is True
    assert cutover["concurrent_old_and_new_capture_paths_authorized"] is False
    assert cutover["old_v0_2_schedule_must_be_disabled_in_same_activation_change"] is True
    assert cutover["successor_schedule_may_be_enabled_before_old_schedule_disabled"] is False
    assert secret["shared_relay_secret_required_before_activation"] is True
    assert secret["secret_value_committed_to_repository"] is False
    assert secret["secret_value_required_in_chat"] is False
    assert secret["out_of_band_secret_provisioning_required"] is True
    assert secret["render_receives_r2_credentials"] is False

    for key in (
        "old_v0_2_schedule_disable_authorized_by_this_protocol",
        "render_metadata_relay_enablement_authorized",
        "successor_scheduled_capture_activation_authorized",
        "metadata_only_r2_writes_authorized_by_this_protocol",
        "holdout_candle_access_authorized",
        "holdout_evaluation_authorized",
        "source_switch_authorized",
        "provider_splicing_authorized",
        "pionex_native_relabel_authorized",
        "staged_trade_kline_w1_materialization_authorized",
        "historical_universe_membership_authorized",
        "backtest_admission_authorized",
        "automatic_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        assert boundary[key] is False, key


def test_v08_prepared_topology_history_is_preserved_after_v012_successor_transition() -> None:
    old_lines = OLD_WORKFLOW.read_text(encoding="utf-8").splitlines()
    v08_lines = SUCCESSOR_WORKFLOW.read_text(encoding="utf-8").splitlines()
    v010_lines = V010_WORKFLOW.read_text(encoding="utf-8").splitlines()
    v012_lines = V012_WORKFLOW.read_text(encoding="utf-8").splitlines()
    v010 = _load(V010)

    # V0.8 remains a frozen prepared/no-schedule historical stage.
    assert not any(line == "  schedule:" for line in v08_lines)
    assert v08.V0_8_CAPTURE_EXECUTION_AUTHORIZED is False

    # V0.10 remains frozen historical authority; V0.12 owns the current schedule.
    assert not any(line == "  schedule:" for line in old_lines)
    assert not any(line == "  schedule:" for line in v010_lines)
    assert any(line == "  schedule:" for line in v012_lines)
    cutover = v010["atomic_repository_cutover"]
    assert cutover["old_schedule_removed_in_same_change"] is True
    assert cutover["successor_schedule_enabled_in_same_change"] is True
    assert cutover["concurrent_old_and_new_capture_paths_authorized"] is False
