from __future__ import annotations

import gzip
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import provider_metadata_capture_v0_2 as v02
from .storage.r2 import R2Store

V07 = Path("config/provider_equivalence_v0_7_render_metadata_capture_protocol_v0_1.json")
V08 = Path("config/provider_equivalence_v0_8_render_metadata_execution_cutover_v0_1.json")
HANDSHAKE = Path(
    "research/receipts/2026-08-19-provider-equivalence-v0-8-shared-relay-secret-handshake-pass.json"
)

EXPECTED_HANDSHAKE_STAGE = "PROVIDER_EQUIVALENCE_V0_8_SHARED_RELAY_SECRET_HANDSHAKE_PASS"
USER_AGENT = "qookey-provider-equivalence-v0-8-successor-capture/0.1"


@dataclass(frozen=True)
class CaptureArtifacts:
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


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def validate_prepared_runtime_authorities() -> tuple[
    dict[str, Any], dict[str, Any], tuple[str, ...], tuple[str, ...]
]:
    protocol, pionex_symbols, binance_symbols = v02.load_and_validate_authority()
    v07 = _load_json(V07)
    v08 = _load_json(V08)
    handshake = _load_json(HANDSHAKE)

    if v07.get("status") != "PROTOCOL_AND_RUNTIME_BOUNDARY_FROZEN_EXECUTION_NOT_AUTHORIZED":
        raise RuntimeError("V0.7 successor metadata protocol is not frozen")
    if v08.get("status") != "CUTOVER_CONTRACT_FROZEN_EXECUTION_NOT_AUTHORIZED":
        raise RuntimeError("V0.8 cutover contract is not frozen")
    if handshake.get("status") != "PASS" or handshake.get("stage") != EXPECTED_HANDSHAKE_STAGE:
        raise RuntimeError("V0.8 shared-secret handshake authority is not PASS")

    result = handshake.get("result") or {}
    interpretation = handshake.get("interpretation") or {}
    if not isinstance(result, dict) or not isinstance(interpretation, dict):
        raise RuntimeError("V0.8 shared-secret handshake receipt shape changed")
    if result.get("shared_secret_match") is not True:
        raise RuntimeError("matching relay secret has not been proven")
    if result.get("secret_value_recorded") is not False:
        raise RuntimeError("relay secret value must never be recorded")
    if result.get("provider_requests_performed") != 0:
        raise RuntimeError("handshake must remain provider-request free")
    if result.get("r2_writes_performed") is not False:
        raise RuntimeError("handshake must remain R2-write free")
    if interpretation.get("authorizes_final_cutover") is not False:
        raise RuntimeError("handshake receipt must not authorize final cutover")

    storage = v07.get("storage") or {}
    runtime = v07.get("render_runtime_boundary") or {}
    github = v07.get("github_orchestration_boundary") or {}
    boundary = v07.get("execution_boundary") or {}
    if not all(isinstance(value, dict) for value in (storage, runtime, github, boundary)):
        raise RuntimeError("V0.7 successor runtime shape changed")

    if runtime.get("plan") != "free" or runtime.get("monthly_runtime_budget_usd") != 0:
        raise RuntimeError("Render successor runtime is no longer FREE-ONLY")
    if runtime.get("code_execution_gate_frozen_false") is not True:
        raise RuntimeError("Render relay code gate is not frozen false")
    if github.get("schedule_trigger_enabled_by_this_protocol") is not False:
        raise RuntimeError("successor schedule unexpectedly enabled")
    if github.get("render_must_not_receive_r2_credentials") is not True:
        raise RuntimeError("Render R2 credential boundary changed")
    if boundary.get("render_metadata_relay_enablement_authorized") is not False:
        raise RuntimeError("relay enablement unexpectedly authorized")
    if boundary.get("render_metadata_capture_execution_authorized") is not False:
        raise RuntimeError("successor capture unexpectedly authorized")
    if boundary.get("metadata_only_r2_writes_authorized_by_this_protocol") is not False:
        raise RuntimeError("successor R2 writes unexpectedly authorized")

    hard_stop = int(storage["free_policy_operational_hard_stop_bytes"])
    if hard_stop != 8_000_000_000:
        raise RuntimeError("FREE-ONLY R2 hard stop changed")
    if storage.get("prewrite_free_tier_headroom_check_required") is not True:
        raise RuntimeError("fresh R2 headroom gate is not required")

    return protocol, v07, pionex_symbols, binance_symbols


def _fetch_render_relay_raw(*, url: str, max_bytes: int, timeout_seconds: float = 30.0) -> tuple[bytes, str]:
    token = os.environ.get("METADATA_RELAY_TOKEN")
    if not token:
        raise RuntimeError("METADATA_RELAY_TOKEN is required for the successor Binance relay")

    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            status = int(getattr(response, "status", 200))
            if status != 200:
                raise RuntimeError(f"Render relay HTTP {status}")
            raw = response.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise RuntimeError("Render relay payload exceeds frozen max bytes")
            content_type = str(response.headers.get("Content-Type", "application/json"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Render relay request failed: {exc}") from exc

    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("symbols"), list):
        raise RuntimeError("Render relay did not return Binance exchangeInfo shape")
    return raw, content_type


def fetch_successor_provider_payloads() -> tuple[v02.ProviderPayload, v02.ProviderPayload, dict[str, Any]]:
    protocol, v07, pionex_symbols, binance_symbols = validate_prepared_runtime_authorities()
    providers = v07["provider_semantics"]
    pionex_cfg = providers["pionex"]
    binance_cfg = providers["binance_usdm"]

    pionex_raw, pionex_content_type = v02._fetch_json_bytes(  # noqa: SLF001
        str(pionex_cfg["public_endpoint"]),
        max_bytes=int(pionex_cfg["raw_uncompressed_response_max_bytes"]),
    )
    binance_raw, binance_content_type = _fetch_render_relay_raw(
        url=str(binance_cfg["render_relay_url"]),
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
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def build_capture_artifacts(
    *,
    pionex: v02.ProviderPayload,
    binance: v02.ProviderPayload,
    protocol: dict[str, Any],
    observed: datetime,
    run_id: str,
) -> CaptureArtifacts:
    if not run_id.isdigit():
        raise RuntimeError("GITHUB_RUN_ID must be numeric")
    slot = v02.capture_slot(observed, protocol)
    if slot is None:
        raise RuntimeError("cannot build successor artifacts outside frozen metadata window")

    v07 = _load_json(V07)
    namespace = str(v07["storage"]["namespace"]).rstrip("/")
    slot_id = slot.strftime("%Y%m%dT%H0000Z")
    prefix = f"{namespace}/capture/slot={slot_id}/run={run_id}"
    pionex_key = f"{prefix}/pionex-symbols.json.gz"
    binance_key = f"{prefix}/binance-usdm-exchange-info.json.gz"
    receipt_key = f"{prefix}/receipt.json"

    pionex_gzip = _gzip(pionex.raw)
    binance_gzip = _gzip(binance.raw)
    receipt = {
        "schema": "provider-equivalence-v0-8-render-metadata-capture-receipt-v0.1",
        "status": "PASS",
        "slot_utc": slot.isoformat().replace("+00:00", "Z"),
        "observed_at_utc": observed.astimezone(timezone.utc).isoformat(),
        "github_run_id": int(run_id),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "transport": {
            "pionex": "github_hosted_direct_public_https",
            "binance_usdm": "render_free_web_service",
            "render_region": "frankfurt",
            "render_plan": "free",
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
    receipt_bytes = _json_bytes(receipt)
    return CaptureArtifacts(
        slot_id=slot_id,
        prefix=prefix,
        pionex_key=pionex_key,
        binance_key=binance_key,
        receipt_key=receipt_key,
        pionex_gzip=pionex_gzip,
        binance_gzip=binance_gzip,
        receipt_bytes=receipt_bytes,
    )


def _r2_store_from_env() -> R2Store:
    return R2Store(
        account_id=os.environ["CLOUDFLARE_ACCOUNT_ID"],
        bucket=os.environ["R2_BUCKET_NAME"],
        access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    )


def current_bucket_bytes(store: Any) -> int:
    paginator = store.client.get_paginator("list_objects_v2")
    total = 0
    for page in paginator.paginate(Bucket=store.bucket):
        for item in page.get("Contents", []) or []:
            total += int(item.get("Size", 0))
    return total


def execute_successor_capture(
    *,
    now: datetime | None = None,
    provider_fetcher: Callable[[], tuple[v02.ProviderPayload, v02.ProviderPayload, dict[str, Any]]] = fetch_successor_provider_payloads,
    store_factory: Callable[[], Any] = _r2_store_from_env,
) -> dict[str, Any]:
    protocol, v07, _, _ = validate_prepared_runtime_authorities()
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
        }

    pionex, binance, fetched_protocol = provider_fetcher()
    if fetched_protocol["metadata_capture_window"] != protocol["metadata_capture_window"]:
        raise RuntimeError("provider fetcher returned protocol with metadata-window drift")

    run_id = os.environ.get("GITHUB_RUN_ID")
    if not run_id or not run_id.isdigit():
        raise RuntimeError("GITHUB_RUN_ID is required for immutable successor capture keys")
    artifacts = build_capture_artifacts(
        pionex=pionex,
        binance=binance,
        protocol=protocol,
        observed=observed,
        run_id=run_id,
    )

    store = store_factory()
    current_bytes = current_bucket_bytes(store)
    hard_stop = int(v07["storage"]["free_policy_operational_hard_stop_bytes"])
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
        }

    for key in (artifacts.pionex_key, artifacts.binance_key, artifacts.receipt_key):
        if store.exists(key):
            raise RuntimeError(f"immutable successor capture key already exists: {key}")

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
        metadata={"dataset": "provider_equivalence_v0_8_metadata", "slot": artifacts.slot_id, "run": run_id},
    )

    store.get_bytes_verified(artifacts.pionex_key, expected_sha256=p_receipt.sha256)
    store.get_bytes_verified(artifacts.binance_key, expected_sha256=b_receipt.sha256)
    store.get_bytes_verified(artifacts.receipt_key, expected_sha256=r_receipt.sha256)

    return {
        "status": "PASS",
        "stage": "PROVIDER_EQUIVALENCE_V0_8_RENDER_METADATA_CAPTURE_PASS",
        "slot_utc": slot.isoformat().replace("+00:00", "Z"),
        "observed_at_utc": observed.isoformat(),
        "github_run_id": int(run_id),
        "object_count": 3,
        "receipt_key": artifacts.receipt_key,
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
    }
