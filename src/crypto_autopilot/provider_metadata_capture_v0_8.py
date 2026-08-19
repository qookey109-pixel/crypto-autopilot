from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CONFIG = Path("config/provider_equivalence_v0_8_render_metadata_execution_cutover_v0_1.json")
V07 = Path("config/provider_equivalence_v0_7_render_metadata_capture_protocol_v0_1.json")
V02 = Path("config/provider_equivalence_v0_2_metadata_capture_v0_2.json")
V08_RECEIPT = Path(
    "research/receipts/2026-08-19-provider-equivalence-v0-8-render-metadata-cutover-prepared.json"
)
V02_WORKFLOW = Path(".github/workflows/provider-equivalence-v0-2-metadata-capture.yml")

# V0.8 is preparation only. A later, separately versioned activation authority
# must change this constant together with the old/new schedule cutover.
V0_8_CAPTURE_EXECUTION_AUTHORIZED = False


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def validate_cutover_contract() -> dict[str, Any]:
    config = _load(CONFIG)
    v07 = _load(V07)
    v02 = _load(V02)
    receipt = _load(V08_RECEIPT)

    if config.get("status") != "CUTOVER_CONTRACT_FROZEN_EXECUTION_NOT_AUTHORIZED":
        raise RuntimeError("V0.8 cutover contract is not frozen")
    if receipt.get("status") != "PASS":
        raise RuntimeError("V0.8 preparation receipt is not PASS")
    if receipt.get("stage") != (
        "PROVIDER_EQUIVALENCE_V0_8_RENDER_METADATA_CUTOVER_PREPARED_EXECUTION_NOT_AUTHORIZED"
    ):
        raise RuntimeError("V0.8 preparation receipt stage changed")
    if v07.get("status") != "PROTOCOL_AND_RUNTIME_BOUNDARY_FROZEN_EXECUTION_NOT_AUTHORIZED":
        raise RuntimeError("V0.7 successor protocol state changed")
    if v02.get("status") != "PROTOCOL_FROZEN_BEFORE_METADATA_EVIDENCE":
        raise RuntimeError("V0.2 metadata protocol state changed")

    scope = config["scientific_scope"]
    holdout = v07["holdout"]
    window = v07["metadata_capture_window"]
    v02_holdout = v02["candidate_holdout"]
    v02_window = v02["metadata_capture_window"]

    for key, config_key in (
        ("start_utc", "holdout_start_utc"),
        ("end_utc", "holdout_end_utc"),
    ):
        expected = str(v02_holdout[key])
        if str(holdout[key]) != expected or str(scope[config_key]) != expected:
            raise RuntimeError(f"holdout scope drift: {key}")

    for key, config_key in (
        ("start_utc", "metadata_capture_start_utc"),
        ("end_utc", "metadata_capture_end_utc"),
        ("hourly_slot_count", "hourly_slot_count"),
        ("scheduled_minutes_utc", "scheduled_minutes_utc"),
    ):
        expected = v02_window[key]
        if window[key] != expected or scope[config_key] != expected:
            raise RuntimeError(f"metadata window drift: {key}")

    if scope["candidate_symbol_count"] != 15 or scope["mapped_pair_count"] != 45:
        raise RuntimeError("frozen symbol/pair scope changed")
    if scope["holdout_candles_accessed"] is not False or scope["holdout_evaluated"] is not False:
        raise RuntimeError("holdout boundary changed")

    successor = config["successor_execution_path"]
    boundary = config["authorization_boundary"]
    cutover = config["atomic_cutover_contract"]
    secret = config["secret_boundary"]

    if successor["render_code_execution_gate_expected_now"] is not False:
        raise RuntimeError("Render relay gate must remain false in V0.8 preparation")
    if successor["successor_capture_execution_gate_expected_now"] is not False:
        raise RuntimeError("successor capture gate must remain false in V0.8 preparation")
    if successor["successor_schedule_enabled_now"] is not False:
        raise RuntimeError("successor schedule must remain disabled")
    if cutover["concurrent_old_and_new_capture_paths_authorized"] is not False:
        raise RuntimeError("concurrent capture paths must remain forbidden")
    if cutover["atomic_activation_required"] is not True:
        raise RuntimeError("atomic activation requirement changed")
    if secret["secret_value_committed_to_repository"] is not False:
        raise RuntimeError("relay secret must never be committed")
    if secret["secret_value_required_in_chat"] is not False:
        raise RuntimeError("relay secret must not be required in chat")
    if secret["render_receives_r2_credentials"] is not False:
        raise RuntimeError("Render must not receive R2 credentials")

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
        if boundary[key] is not False:
            raise RuntimeError(f"forbidden V0.8 authorization changed: {key}")

    old_workflow = V02_WORKFLOW.read_text(encoding="utf-8")
    if "  schedule:" not in old_workflow:
        raise RuntimeError("V0.2 current schedule unexpectedly absent before activation authority")

    return {
        "status": "PASS",
        "stage": "V0_8_CUTOVER_CONTRACT_VALIDATION_PASS",
        "old_capture_path": "github_self_hosted_mac",
        "successor_capture_path": "render_free_web_service",
        "old_schedule_present": True,
        "successor_schedule_enabled": False,
        "render_relay_enabled": False,
        "successor_capture_execution_authorized": False,
        "r2_writes_performed": False,
        "holdout_candles_accessed": False,
        "source_switch_authorized": False,
        "live_trading_authorized": False,
    }


def guarded_capture_entrypoint() -> dict[str, Any]:
    validate_cutover_contract()
    if not V0_8_CAPTURE_EXECUTION_AUTHORIZED:
        return {
            "status": "SKIP",
            "stage": "V0_8_CAPTURE_EXECUTION_NOT_AUTHORIZED",
            "provider_requests_performed": 0,
            "render_relay_requests_performed": 0,
            "r2_client_constructed": False,
            "r2_writes_performed": False,
            "holdout_candles_accessed": False,
            "source_switch_authorized": False,
            "live_trading_authorized": False,
        }
    raise RuntimeError("V0.8 activation implementation requires a later versioned authority")
