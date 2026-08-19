from __future__ import annotations

import gzip
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import provider_metadata_capture_v0_2 as v02
from . import provider_metadata_capture_v0_8_successor as successor
from .storage.r2 import R2Store

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
V0_10_RECEIPT_SCHEMA = "provider-equivalence-v0-10-render-metadata-capture-receipt-v0.1"
V0_10_CAPTURE_PASS_STAGE = "PROVIDER_EQUIVALENCE_V0_10_RENDER_METADATA_CAPTURE_PASS"


@dataclass(frozen=True)
class V010CaptureArtifacts:
    slot_id: str
    prefix: str
    pionex_key: str
    binance_key: str
    receipt_key: str
    pionex_gzip: bytes
    binance_gzip: bytes
    receipt_bytes: bytes

    @property
    def planned_write_bytes(self) -> int:
        return len(self.pionex_gzip) + len(self.binance_gzip) + len(self.receipt_bytes)


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


def _gzip(raw: bytes) -> bytes:
    return gzip.compress(raw, compresslevel=9, mtime=0)


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )


def build_v0_10_capture_artifacts(
    *,
    pionex: v02.ProviderPayload,
    binance: v02.ProviderPayload,
    protocol: dict[str, Any],
    observed: datetime,
    run_id: str,
) -> V010CaptureArtifacts:
    if not run_id.isdigit():
        raise RuntimeError("GITHUB_RUN_ID must be numeric")
    slot = v02.capture_slot(observed, protocol)
    if slot is None:
        raise RuntimeError("cannot build V0.10 artifacts outside frozen metadata window")

    cfg, _, _ = validate_final_atomic_cutover_authority()
    namespace = str(cfg["storage"]["namespace"]).rstrip("/")
    slot_id = slot.strftime("%Y%m%dT%H0000Z")
    prefix = f"{namespace}/capture/slot={slot_id}/run={run_id}"
    pionex_key = f"{prefix}/pionex-symbols.json.gz"
    binance_key = f"{prefix}/binance-usdm-exchange-info.json.gz"
    receipt_key = f"{prefix}/receipt.json"

    pionex_gzip = _gzip(pionex.raw)
    binance_gzip = _gzip(binance.raw)
    receipt = {
        "schema": V0_10_RECEIPT_SCHEMA,
        "status": "PASS",
        "stage": V0_10_CAPTURE_PASS_STAGE,
        "activation_authority": "provider_equivalence_v0_10_final_atomic_cutover_v0_1",
        "capture_execution_version": "v0_10",
        "slot_utc": slot.isoformat().replace("+00:00", "Z"),
        "observed_at_utc": observed.astimezone(timezone.utc).isoformat(),
        "github_run_id": int(run_id),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "transport": {
            "pionex": "github_hosted_direct_public_https",
            "binance_usdm": "render_free_web_service_v0_10_raw_relay",
            "render_region": "frankfurt",
            "render_plan": "free",
            "render_relay_path": "/metadata/v0-10/binance-exchange-info",
        },
        "providers": {
            "pionex": {
                "raw_key": pionex_key,
                "raw_uncompressed_bytes": len(pionex.raw),
                "raw_sha256": pionex.raw_sha256,
                "gzip_bytes": len(pionex_gzip),
                "gzip_sha256": hashlib.sha256(pionex_gzip).hexdigest(),
                "content_type": pionex.content_type,
                "normalized_vector_sha256": pionex.vector_sha256,
                "normalized_vector": list(pionex.vector),
            },
            "binance_usdm": {
                "raw_key": binance_key,
                "raw_uncompressed_bytes": len(binance.raw),
                "raw_sha256": binance.raw_sha256,
                "gzip_bytes": len(binance_gzip),
                "gzip_sha256": hashlib.sha256(binance_gzip).hexdigest(),
                "content_type": binance.content_type,
                "normalized_vector_sha256": binance.vector_sha256,
                "normalized_vector": list(binance.vector),
            },
        },
        "authorization_boundary": {
            "metadata_only": True,
            "holdout_candle_access_authorized": False,
            "holdout_evaluation_authorized": False,
            "source_switch_authorized": False,
            "provider_splicing_authorized": False,
            "pionex_native_relabel_authorized": False,
            "w1_materialization_authorized": False,
            "automatic_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }
    return V010CaptureArtifacts(
        slot_id=slot_id,
        prefix=prefix,
        pionex_key=pionex_key,
        binance_key=binance_key,
        receipt_key=receipt_key,
        pionex_gzip=pionex_gzip,
        binance_gzip=binance_gzip,
        receipt_bytes=_json_bytes(receipt),
    )


def _r2_store_from_env() -> R2Store:
    return R2Store(
        account_id=os.environ["CLOUDFLARE_ACCOUNT_ID"],
        bucket=os.environ["R2_BUCKET_NAME"],
        access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    )


def capture_v0_10(
    *,
    now: datetime | None = None,
    provider_fetcher: Callable[
        [], tuple[v02.ProviderPayload, v02.ProviderPayload, dict[str, Any]]
    ] = fetch_v0_10_provider_payloads,
    store_factory: Callable[[], Any] = _r2_store_from_env,
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

    cfg, _, _ = validate_final_atomic_cutover_authority()
    protocol, _, _ = v02.load_and_validate_authority()
    observed = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    slot = v02.capture_slot(observed, protocol)
    if slot is None:
        return {
            "status": "SKIP",
            "stage": "OUTSIDE_FROZEN_METADATA_CAPTURE_WINDOW",
            "observed_at_utc": observed.isoformat(),
            "provider_requests_performed": 0,
            "render_relay_requests_performed": 0,
            "r2_client_constructed": False,
            "r2_writes_performed": False,
            "holdout_candles_accessed": False,
            "source_switch_authorized": False,
            "live_trading_authorized": False,
            "activation_authority": "provider_equivalence_v0_10_final_atomic_cutover_v0_1",
            "capture_execution_version": "v0_10",
        }

    pionex, binance, fetched_protocol = provider_fetcher()
    if fetched_protocol["metadata_capture_window"] != protocol["metadata_capture_window"]:
        raise RuntimeError("provider fetcher returned protocol with metadata-window drift")

    run_id = os.environ.get("GITHUB_RUN_ID")
    if not run_id or not run_id.isdigit():
        raise RuntimeError("GITHUB_RUN_ID is required for immutable V0.10 capture keys")
    artifacts = build_v0_10_capture_artifacts(
        pionex=pionex,
        binance=binance,
        protocol=protocol,
        observed=observed,
        run_id=run_id,
    )

    store = store_factory()
    current_bytes = successor.current_bucket_bytes(store)
    hard_stop = int(cfg["storage"]["free_only_operational_hard_stop_bytes"])
    projected_after_write = current_bytes + artifacts.planned_write_bytes
    if projected_after_write > hard_stop:
        return {
            "status": "BLOCKED",
            "stage": "R2_FREE_ONLY_HEADROOM_GATE_BLOCKED_BEFORE_WRITE",
            "current_bucket_bytes": current_bytes,
            "planned_write_bytes": artifacts.planned_write_bytes,
            "projected_after_write_bytes": projected_after_write,
            "hard_stop_bytes": hard_stop,
            "provider_requests_performed": 2,
            "render_relay_requests_performed": 1,
            "r2_client_constructed": True,
            "r2_writes_performed": False,
            "holdout_candles_accessed": False,
            "source_switch_authorized": False,
            "live_trading_authorized": False,
            "activation_authority": "provider_equivalence_v0_10_final_atomic_cutover_v0_1",
            "capture_execution_version": "v0_10",
        }

    for key in (artifacts.pionex_key, artifacts.binance_key, artifacts.receipt_key):
        if store.exists(key):
            raise RuntimeError(f"immutable V0.10 capture key already exists: {key}")

    p_receipt = store.put_bytes(
        artifacts.pionex_key,
        artifacts.pionex_gzip,
        content_type="application/gzip",
        metadata={"provider": "pionex", "slot": artifacts.slot_id, "run": run_id},
    )
    b_receipt = store.put_bytes(
        artifacts.binance_key,
        artifacts.binance_gzip,
        content_type="application/gzip",
        metadata={"provider": "binance_usdm", "slot": artifacts.slot_id, "run": run_id},
    )
    r_receipt = store.put_bytes(
        artifacts.receipt_key,
        artifacts.receipt_bytes,
        content_type="application/json",
        metadata={"dataset": "provider_equivalence_v0_10_metadata", "slot": artifacts.slot_id, "run": run_id},
    )

    store.get_bytes_verified(artifacts.pionex_key, expected_sha256=p_receipt.sha256)
    store.get_bytes_verified(artifacts.binance_key, expected_sha256=b_receipt.sha256)
    store.get_bytes_verified(artifacts.receipt_key, expected_sha256=r_receipt.sha256)

    return {
        "status": "PASS",
        "stage": V0_10_CAPTURE_PASS_STAGE,
        "slot_utc": slot.isoformat().replace("+00:00", "Z"),
        "observed_at_utc": observed.isoformat(),
        "github_run_id": int(run_id),
        "object_count": 3,
        "receipt_key": artifacts.receipt_key,
        "receipt_schema": V0_10_RECEIPT_SCHEMA,
        "pionex_vector_sha256": pionex.vector_sha256,
        "binance_vector_sha256": binance.vector_sha256,
        "prewrite_r2_bucket_bytes": current_bytes,
        "planned_write_bytes": artifacts.planned_write_bytes,
        "r2_hard_stop_bytes": hard_stop,
        "postwrite_sha256_verification": True,
        "provider_requests_performed": 2,
        "render_relay_requests_performed": 1,
        "r2_client_constructed": True,
        "r2_writes_performed": True,
        "r2_deletes_performed": False,
        "holdout_candles_accessed": False,
        "source_switch_authorized": False,
        "live_trading_authorized": False,
        "activation_authority": "provider_equivalence_v0_10_final_atomic_cutover_v0_1",
        "capture_execution_version": "v0_10",
    }
