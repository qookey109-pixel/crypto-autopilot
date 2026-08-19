from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from . import provider_metadata_capture_v0_2 as v02
from . import provider_metadata_capture_v0_8_successor as successor

CONFIG = Path("config/provider_equivalence_v0_10_final_atomic_cutover_v0_1.json")
AUTHORITY = Path(
    "research/receipts/2026-08-20-provider-equivalence-v0-10-final-atomic-cutover-authority.json"
)
SMOKE_PASS = Path(
    "research/receipts/2026-08-20-provider-equivalence-v0-9-render-relay-smoke-pass.json"
)

V0_10_FINAL_ATOMIC_CUTOVER_EXECUTION_AUTHORIZED = True
V0_10_RENDER_RELAY_URL = (
    "https://qookey-binance-transport-v0-5.onrender.com"
    "/metadata/v0-10/binance-exchange-info"
)


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def validate_final_atomic_cutover_authority() -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any]
]:
    cfg = _load(CONFIG)
    authority = _load(AUTHORITY)
    smoke = _load(SMOKE_PASS)

    if cfg.get("status") != "FINAL_ATOMIC_CUTOVER_AUTHORIZED_ON_MAIN_MERGE":
        raise RuntimeError("V0.10 final cutover config is not authorized-on-merge")
    if authority.get("status") != "PASS":
        raise RuntimeError("V0.10 final cutover authority is not PASS")
    if authority.get("stage") != (
        "PROVIDER_EQUIVALENCE_V0_10_FINAL_ATOMIC_CUTOVER_AUTHORIZED_ON_MAIN_MERGE"
    ):
        raise RuntimeError("V0.10 final cutover authority stage changed")
    if smoke.get("status") != "PASS" or smoke.get("stage") != (
        "PROVIDER_EQUIVALENCE_V0_9_RENDER_RELAY_LIVE_SMOKE_PASS"
    ):
        raise RuntimeError("V0.9 relay smoke PASS is required")

    result = smoke.get("result") or {}
    if not isinstance(result, dict):
        raise RuntimeError("V0.9 smoke result shape changed")
    if result.get("upstream_status") != 200:
        raise RuntimeError("V0.9 relay smoke upstream status changed")
    if result.get("json_ok") is not True or result.get("symbols_array") is not True:
        raise RuntimeError("V0.9 relay smoke JSON contract changed")
    if not isinstance(result.get("symbol_count"), int) or int(result["symbol_count"]) <= 0:
        raise RuntimeError("V0.9 relay smoke symbol count invalid")
    if result.get("r2_writes_performed") is not False:
        raise RuntimeError("V0.9 smoke unexpectedly wrote R2")
    if result.get("holdout_candles_accessed") is not False:
        raise RuntimeError("V0.9 smoke unexpectedly touched holdout")

    scientific = cfg.get("scientific_scope") or {}
    cutover = cfg.get("atomic_repository_cutover") or {}
    render = cfg.get("render_transport") or {}
    storage = cfg.get("storage") or {}
    boundary = cfg.get("authorization_boundary") or {}
    if not all(
        isinstance(value, dict)
        for value in (scientific, cutover, render, storage, boundary)
    ):
        raise RuntimeError("V0.10 authority shape changed")

    if scientific.get("replacement_holdout_state") != "FROZEN_UNOPENED":
        raise RuntimeError("replacement holdout is not frozen unopened")
    if scientific.get("holdout_candles_access_authorized") is not False:
        raise RuntimeError("V0.10 must not authorize holdout access")
    if cutover.get("old_schedule_removed_in_same_change") is not True:
        raise RuntimeError("old schedule atomic disable requirement changed")
    if cutover.get("successor_schedule_enabled_in_same_change") is not True:
        raise RuntimeError("successor schedule atomic enable requirement changed")
    if cutover.get("concurrent_old_and_new_capture_paths_authorized") is not False:
        raise RuntimeError("concurrent old/new capture cannot be authorized")
    if render.get("plan") != "free" or render.get("monthly_budget_usd") != 0:
        raise RuntimeError("Render FREE-ONLY boundary changed")
    if render.get("v0_7_raw_relay_remains_disabled") is not True:
        raise RuntimeError("historical V0.7 raw relay must remain disabled")
    if render.get("render_receives_r2_credentials") is not False:
        raise RuntimeError("Render must never receive R2 credentials")
    if storage.get("free_only_operational_hard_stop_bytes") != 8_000_000_000:
        raise RuntimeError("V0.10 R2 hard stop changed")
    if storage.get("fresh_bucket_inventory_before_each_write") is not True:
        raise RuntimeError("fresh R2 inventory requirement changed")

    for key in (
        "holdout_candle_access_authorized",
        "holdout_evaluation_authorized",
        "source_switch_authorized",
        "provider_splicing_authorized",
        "pionex_native_relabel_authorized",
        "staged_trade_kline_w1_materialization_authorized",
        "historical_universe_membership_authorized",
        "backtest_admission_authorized",
        "strategy_parameter_change_authorized",
        "automatic_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if boundary.get(key) is not False:
            raise RuntimeError(f"V0.10 forbidden boundary changed: {key}")

    return cfg, authority, smoke


def fetch_v0_10_provider_payloads() -> tuple[
    v02.ProviderPayload, v02.ProviderPayload, dict[str, Any]
]:
    validate_final_atomic_cutover_authority()
    protocol, v07, pionex_symbols, binance_symbols = successor.validate_prepared_runtime_authorities()
    providers = v07["provider_semantics"]
    pionex_cfg = providers["pionex"]
    binance_cfg = providers["binance_usdm"]

    pionex_raw, pionex_content_type = v02._fetch_json_bytes(  # noqa: SLF001
        str(pionex_cfg["public_endpoint"]),
        max_bytes=int(pionex_cfg["raw_uncompressed_response_max_bytes"]),
    )
    binance_raw, binance_content_type = successor._fetch_render_relay_raw(  # noqa: SLF001
        url=V0_10_RENDER_RELAY_URL,
        max_bytes=int(binance_cfg["raw_uncompressed_response_max_bytes"]),
    )

    pionex = v02.ProviderPayload(
        provider="pionex",
        raw=pionex_raw,
        content_type=pionex_content_type,
        vector=v02.parse_pionex_symbols(pionex_raw, pionex_symbols),
    )
    binance = v02.ProviderPayload(
        provider="binance_usdm",
        raw=binance_raw,
        content_type=binance_content_type,
        vector=v02.parse_binance_exchange_info(binance_raw, binance_symbols),
    )
    return pionex, binance, protocol


def capture_v0_10(
    *,
    now: datetime | None = None,
    provider_fetcher: Callable[
        [], tuple[v02.ProviderPayload, v02.ProviderPayload, dict[str, Any]]
    ] = fetch_v0_10_provider_payloads,
    store_factory: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    if not V0_10_FINAL_ATOMIC_CUTOVER_EXECUTION_AUTHORIZED:
        return {
            "status": "SKIP",
            "stage": "V0_10_FINAL_ATOMIC_CUTOVER_EXECUTION_NOT_AUTHORIZED",
            "provider_requests_performed": 0,
            "render_relay_requests_performed": 0,
            "r2_client_constructed": False,
            "r2_writes_performed": False,
            "holdout_candles_accessed": False,
            "source_switch_authorized": False,
            "live_trading_authorized": False,
        }

    validate_final_atomic_cutover_authority()
    kwargs: dict[str, Any] = {
        "now": now,
        "provider_fetcher": provider_fetcher,
    }
    if store_factory is not None:
        kwargs["store_factory"] = store_factory
    result = successor._execute_successor_capture_authorized(**kwargs)  # noqa: SLF001
    result = dict(result)
    result["activation_authority"] = "provider_equivalence_v0_10_final_atomic_cutover_v0_1"
    result["capture_execution_version"] = "v0_10"
    return result
