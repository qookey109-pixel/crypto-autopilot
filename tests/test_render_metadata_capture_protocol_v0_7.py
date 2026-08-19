from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V02 = ROOT / "config/provider_equivalence_v0_2_metadata_capture_v0_2.json"
V07 = ROOT / "config/provider_equivalence_v0_7_render_metadata_capture_protocol_v0_1.json"
RECEIPT = ROOT / "research/receipts/2026-08-19-provider-equivalence-v0-7-render-metadata-capture-protocol-prepared.json"
SERVER = ROOT / "infra/render/binance-transport-free/server.py"


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text())
    assert isinstance(payload, dict)
    return payload


def _server_module():
    spec = importlib.util.spec_from_file_location("render_transport_v07", SERVER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v07_preserves_exact_v02_holdout_and_metadata_window() -> None:
    v02 = _load(V02)
    v07 = _load(V07)
    assert v07["status"] == "PROTOCOL_AND_RUNTIME_BOUNDARY_FROZEN_EXECUTION_NOT_AUTHORIZED"

    for key in ("start_utc", "end_utc", "duration_hours", "intervals", "candidate_symbol_count", "mapped_pair_count"):
        assert v07["holdout"][key] == v02["candidate_holdout"][key]
    for key in ("start_utc", "end_utc", "hourly_slot_count", "scheduled_minutes_utc", "nominal_capture_attempts"):
        assert v07["metadata_capture_window"][key] == v02["metadata_capture_window"][key]

    assert v07["lineage"]["v0_2_protocol_mutated"] is False
    assert v07["lineage"]["v0_2_authority_mutated"] is False
    assert v07["holdout"]["candles_accessed"] is False
    assert v07["holdout"]["candles_evaluated"] is False


def test_v07_render_relay_is_hard_disabled_even_if_environment_requests_enablement() -> None:
    module = _server_module()
    prior = os.environ.get("METADATA_RELAY_ENABLED")
    try:
        os.environ["METADATA_RELAY_ENABLED"] = "true"
        assert module.METADATA_RELAY_EXECUTION_AUTHORIZED is False
        assert module.metadata_relay_enabled() is False
    finally:
        if prior is None:
            os.environ.pop("METADATA_RELAY_ENABLED", None)
        else:
            os.environ["METADATA_RELAY_ENABLED"] = prior

    cfg = _load(V07)
    runtime = cfg["render_runtime_boundary"]
    assert runtime["relay_scaffold_implemented"] is True
    assert runtime["code_execution_gate_frozen_false"] is True
    assert runtime["environment_flags_cannot_override_frozen_false_code_gate"] is True
    assert runtime["relay_activation_requires_separate_code_change_and_versioned_authority"] is True


def test_v07_uses_render_only_for_binance_transport_and_keeps_r2_credentials_on_github() -> None:
    cfg = _load(V07)
    providers = cfg["provider_semantics"]
    orchestration = cfg["github_orchestration_boundary"]

    assert providers["binance_usdm"]["official_endpoint"] == "https://fapi.binance.com/fapi/v1/exchangeInfo"
    assert providers["binance_usdm"]["transport_authority"] == "render_free_web_service"
    assert providers["binance_usdm"]["raw_bytes_must_be_forwarded_without_reserialization"] is True
    assert providers["binance_usdm"]["render_raw_persistence_authorized"] is False
    assert providers["binance_usdm"]["render_r2_credentials_authorized"] is False
    assert orchestration["runner"] == "github_hosted_ubuntu"
    assert orchestration["binance_fetch_direct_from_github_runner"] is False
    assert orchestration["binance_fetch_via_render_relay"] is True
    assert orchestration["r2_credentials_location"] == "github_actions_secrets_only"
    assert orchestration["render_must_not_receive_r2_credentials"] is True


def test_v07_is_free_only_and_execution_remains_closed() -> None:
    cfg = _load(V07)
    receipt = _load(RECEIPT)
    storage = cfg["storage"]
    boundary = cfg["execution_boundary"]

    assert cfg["render_runtime_boundary"]["plan"] == "free"
    assert cfg["render_runtime_boundary"]["monthly_runtime_budget_usd"] == 0
    assert storage["projected_metadata_storage_cap_bytes"] + storage["current_bucket_usage_reference_bytes"] < storage["free_policy_operational_hard_stop_bytes"]
    assert storage["prewrite_free_tier_headroom_check_required"] is True

    assert boundary["render_metadata_relay_implementation_authorized"] is True
    for key in (
        "render_metadata_relay_enablement_authorized",
        "render_metadata_capture_execution_authorized",
        "scheduled_capture_activation_authorized",
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

    assert receipt["prepared_architecture"]["provider_metadata_capture_performed"] is False
    assert receipt["prepared_architecture"]["r2_writes_performed"] is False


def test_binance_api_key_scope_is_not_project_wide_banned() -> None:
    cfg = _load(V07)
    boundary = cfg["binance_api_key_boundary"]
    assert boundary["public_exchange_info_requires_api_key"] is False
    assert boundary["project_wide_binance_api_key_prohibition_declared"] is False
    assert boundary["binance_api_key_authorized_for_this_public_metadata_relay"] is False
    assert boundary["api_key_bypass_for_transport_failure_authorized"] is False
    assert boundary["future_authenticated_binance_api_may_be_versioned_separately"] is True


def test_old_self_hosted_schedule_requires_explicit_cutover_before_v07_execution() -> None:
    cfg = _load(V07)
    orchestration = cfg["github_orchestration_boundary"]
    receipt = _load(RECEIPT)
    assert orchestration["schedule_trigger_enabled_by_this_protocol"] is False
    assert orchestration["old_v0_2_self_hosted_schedule_path_may_run_concurrently"] is False
    assert orchestration["old_v0_2_schedule_cutover_required_before_v0_7_execution"] is True
    assert receipt["cutover_requirement"]["separate_versioned_execution_cutover_authority_required"] is True
