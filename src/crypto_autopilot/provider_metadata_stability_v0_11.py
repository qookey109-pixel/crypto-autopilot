from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from . import provider_metadata_capture_v0_2 as v02
from .storage.r2 import R2Store


CONFIG = Path("config/provider_equivalence_v0_11_metadata_stability_evaluation_v0_1.json")
V10_CONFIG = Path("config/provider_equivalence_v0_10_final_atomic_cutover_v0_1.json")
V10_AUTHORITY = Path(
    "research/receipts/2026-08-20-provider-equivalence-v0-10-final-atomic-cutover-authority.json"
)

V0_11_R2_EVALUATION_EXECUTION_AUTHORIZED = False
V0_10_RECEIPT_SCHEMA = "provider-equivalence-v0-10-render-metadata-capture-receipt-v0.1"
V0_10_CAPTURE_PASS_STAGE = "PROVIDER_EQUIVALENCE_V0_10_RENDER_METADATA_CAPTURE_PASS"
V0_11_PASS_STAGE = "PROVIDER_EQUIVALENCE_V0_11_METADATA_STABILITY_PASS"
V0_11_FAIL_STAGE = "PROVIDER_EQUIVALENCE_V0_11_METADATA_STABILITY_FAIL"
V0_11_DISABLED_STAGE = "V0_11_METADATA_STABILITY_R2_EVALUATION_NOT_AUTHORIZED"


@dataclass(frozen=True)
class ValidatedReceipt:
    key: str
    slot_utc: str
    run_id: int
    vectors: dict[str, bytes]
    vector_sha256: dict[str, str]


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def _as_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError(f"expected object: {label}")
    return value


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise RuntimeError(f"timestamp is not timezone-aware: {value}")
    return parsed.astimezone(timezone.utc)


def _canonical_vector_bytes(vector: list[dict[str, str]]) -> bytes:
    return json.dumps(vector, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def validate_v0_11_protocol() -> tuple[
    dict[str, Any], dict[str, Any], tuple[str, ...], tuple[str, ...]
]:
    config = _load(CONFIG)
    v10 = _load(V10_CONFIG)
    authority = _load(V10_AUTHORITY)
    v02_protocol, pionex_symbols, binance_symbols = v02.load_and_validate_authority()

    if config.get("status") != "EVALUATOR_PROTOCOL_FROZEN_EXECUTION_NOT_AUTHORIZED":
        raise RuntimeError("V0.11 evaluator protocol is not frozen")
    if v10.get("status") != "FINAL_ATOMIC_CUTOVER_AUTHORIZED_ON_MAIN_MERGE":
        raise RuntimeError("V0.10 cutover config is not effective-on-merge authority")
    if authority.get("status") != "PASS" or authority.get("stage") != (
        "PROVIDER_EQUIVALENCE_V0_10_FINAL_ATOMIC_CUTOVER_AUTHORIZED_ON_MAIN_MERGE"
    ):
        raise RuntimeError("V0.10 final cutover authority is not PASS")

    scope = _as_dict(config.get("frozen_scope"), "V0.11 frozen_scope")
    input_contract = _as_dict(config.get("input_contract"), "V0.11 input_contract")
    rules = _as_dict(config.get("evaluation_rules"), "V0.11 evaluation_rules")
    execution = _as_dict(config.get("execution_boundary"), "V0.11 execution_boundary")
    workflow = _as_dict(config.get("workflow_boundary"), "V0.11 workflow_boundary")
    v10_scope = _as_dict(v10.get("scientific_scope"), "V0.10 scientific_scope")
    v10_storage = _as_dict(v10.get("storage"), "V0.10 storage")

    if scope.get("metadata_capture_start_utc") != v10_scope.get("metadata_capture_start_utc"):
        raise RuntimeError("V0.11 metadata start drifted from V0.10")
    if scope.get("metadata_capture_end_utc") != v10_scope.get("metadata_capture_end_utc"):
        raise RuntimeError("V0.11 metadata end drifted from V0.10")
    if scope.get("expected_hourly_slot_count") != 194:
        raise RuntimeError("V0.11 expected slot count changed")
    if scope.get("scheduled_minutes_utc") != [17, 47]:
        raise RuntimeError("V0.11 scheduled minutes changed")
    if scope.get("candidate_symbol_count") != 15 or scope.get("mapped_pair_count") != 45:
        raise RuntimeError("V0.11 frozen symbol/pair scope changed")
    if scope.get("replacement_holdout_state") != "FROZEN_UNOPENED":
        raise RuntimeError("V0.11 replacement holdout must remain unopened")
    if input_contract.get("metadata_namespace") != v10_storage.get("namespace"):
        raise RuntimeError("V0.11 metadata namespace drifted from V0.10")
    if input_contract.get("allowed_object_kind") != "V0_10_CAPTURE_RECEIPT_JSON_ONLY":
        raise RuntimeError("V0.11 input kind changed")
    if input_contract.get("raw_provider_objects_may_be_read_by_evaluator") is not False:
        raise RuntimeError("V0.11 evaluator cannot read raw provider objects")
    if input_contract.get("holdout_objects_may_be_listed_or_read_by_evaluator") is not False:
        raise RuntimeError("V0.11 evaluator cannot list/read holdout objects")
    if input_contract.get("normalized_vector_length_per_provider") != 15:
        raise RuntimeError("V0.11 normalized vector length changed")

    if rules.get("partial_window_may_produce_pass") is not False:
        raise RuntimeError("partial V0.11 evaluation cannot PASS")
    if rules.get("post_hoc_deadband_authorized") is not False:
        raise RuntimeError("post-hoc deadband cannot be authorized")
    if rules.get("post_hoc_symbol_scope_change_authorized") is not False:
        raise RuntimeError("post-hoc symbol scope change cannot be authorized")
    if rules.get("post_hoc_provider_splicing_authorized") is not False:
        raise RuntimeError("post-hoc provider splicing cannot be authorized")

    for key in (
        "production_r2_evaluation_execution_authorized_by_this_protocol",
        "r2_client_construction_authorized_by_this_protocol",
        "r2_receipt_reads_authorized_by_this_protocol",
        "r2_writes_authorized",
        "r2_deletes_authorized",
        "provider_requests_authorized",
        "render_requests_authorized",
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
        if execution.get(key) is not False:
            raise RuntimeError(f"V0.11 execution boundary changed: {key}")

    for key in (
        "scheduled_evaluation_enabled",
        "automatic_post_window_evaluation_enabled",
        "workflow_dispatch_production_evaluation_enabled",
    ):
        if workflow.get(key) is not False:
            raise RuntimeError(f"V0.11 workflow unexpectedly enables execution: {key}")

    v02_window = _as_dict(v02_protocol.get("metadata_capture_window"), "V0.2 metadata window")
    if v02_window.get("hourly_slot_count") != 194:
        raise RuntimeError("V0.2 frozen slot count changed")
    if v02_window.get("scheduled_minutes_utc") != [17, 47]:
        raise RuntimeError("V0.2 frozen scheduled minutes changed")
    if v02_window.get("stability_policy") != (
        "ALL_COMPLETE_CAPTURE_VECTORS_ACROSS_THE_FULL_CAPTURE_WINDOW_MUST_MATCH_EXACTLY_PER_PROVIDER"
    ):
        raise RuntimeError("V0.2 frozen stability policy changed")
    if v02_window.get("missing_hour_policy") != "METADATA_APPLICABILITY_INVALID_NO_HOLDOUT_EVALUATION":
        raise RuntimeError("V0.2 missing-hour policy changed")
    if v02_window.get("changed_vector_policy") != "METADATA_APPLICABILITY_INVALID_NO_HOLDOUT_EVALUATION":
        raise RuntimeError("V0.2 changed-vector policy changed")

    return config, v10, pionex_symbols, binance_symbols


def expected_slot_strings(config: dict[str, Any] | None = None) -> tuple[str, ...]:
    cfg = config or validate_v0_11_protocol()[0]
    scope = _as_dict(cfg.get("frozen_scope"), "V0.11 frozen_scope")
    start = _parse_utc(str(scope["metadata_capture_start_utc"]))
    end = _parse_utc(str(scope["metadata_capture_end_utc"]))
    slot = start.replace(minute=0, second=0, microsecond=0)
    last = end.replace(minute=0, second=0, microsecond=0)
    slots: list[str] = []
    while slot <= last:
        slots.append(slot.isoformat().replace("+00:00", "Z"))
        slot += timedelta(hours=1)
    if len(slots) != int(scope["expected_hourly_slot_count"]):
        raise RuntimeError(f"computed V0.11 slot count mismatch: {len(slots)}")
    return tuple(slots)


def _receipt_key_regex(namespace: str) -> re.Pattern[str]:
    prefix = re.escape(namespace.rstrip("/"))
    return re.compile(
        rf"^{prefix}/capture/slot=(?P<slot>\d{{8}}T\d{{6}}Z)/run=(?P<run>\d+)/receipt\.json$"
    )


def _validate_vector(
    *,
    provider: str,
    value: Any,
    expected_symbols: tuple[str, ...],
    expected_sha256: Any,
) -> tuple[bytes, str]:
    if not isinstance(value, list) or len(value) != 15:
        raise RuntimeError(f"{provider}: normalized vector must contain exactly 15 rows")
    rows: list[dict[str, str]] = []
    required_keys = {"symbol", "price_increment", "status", "contract_type", "source_field"}
    for row in value:
        if not isinstance(row, dict) or set(row) != required_keys:
            raise RuntimeError(f"{provider}: normalized vector row shape changed")
        normalized: dict[str, str] = {}
        for key in sorted(required_keys):
            field = row.get(key)
            if not isinstance(field, str) or not field:
                raise RuntimeError(f"{provider}: normalized vector field invalid: {key}")
            normalized[key] = field
        rows.append(normalized)

    symbols = [row["symbol"] for row in rows]
    if len(set(symbols)) != 15:
        raise RuntimeError(f"{provider}: duplicate normalized symbols")
    if set(symbols) != set(expected_symbols):
        raise RuntimeError(f"{provider}: normalized symbol set drifted")
    if symbols != sorted(symbols):
        raise RuntimeError(f"{provider}: normalized vector ordering drifted")

    canonical = _canonical_vector_bytes(rows)
    actual_sha256 = _sha256(canonical)
    if not isinstance(expected_sha256, str) or expected_sha256 != actual_sha256:
        raise RuntimeError(f"{provider}: normalized vector SHA-256 mismatch")
    return canonical, actual_sha256


def validate_capture_receipt(
    *, key: str, receipt: Mapping[str, Any]
) -> ValidatedReceipt:
    config, _, pionex_symbols, binance_symbols = validate_v0_11_protocol()
    input_contract = _as_dict(config.get("input_contract"), "V0.11 input_contract")
    namespace = str(input_contract["metadata_namespace"])
    match = _receipt_key_regex(namespace).fullmatch(key)
    if match is None:
        raise RuntimeError("receipt key is outside exact V0.10 metadata receipt allowlist")

    if not isinstance(receipt, Mapping):
        raise RuntimeError("capture receipt must be an object")
    if receipt.get("schema") != V0_10_RECEIPT_SCHEMA:
        raise RuntimeError("capture receipt schema changed")
    if receipt.get("status") != "PASS" or receipt.get("stage") != V0_10_CAPTURE_PASS_STAGE:
        raise RuntimeError("capture receipt is not a V0.10 PASS receipt")
    if receipt.get("capture_execution_version") != "v0_10":
        raise RuntimeError("capture execution version changed")
    if receipt.get("activation_authority") != "provider_equivalence_v0_10_final_atomic_cutover_v0_1":
        raise RuntimeError("capture activation authority changed")

    slot_text = str(receipt.get("slot_utc") or "")
    if slot_text not in set(expected_slot_strings(config)):
        raise RuntimeError("capture receipt slot is outside frozen 194-slot window")
    slot_dt = _parse_utc(slot_text)
    if slot_dt.minute or slot_dt.second or slot_dt.microsecond:
        raise RuntimeError("capture receipt slot is not an exact UTC hour")
    expected_key_slot = slot_dt.strftime("%Y%m%dT%H0000Z")
    if match.group("slot") != expected_key_slot:
        raise RuntimeError("capture receipt key slot does not match receipt slot")

    run_id = receipt.get("github_run_id")
    if not isinstance(run_id, int) or run_id <= 0:
        raise RuntimeError("capture receipt github_run_id invalid")
    if match.group("run") != str(run_id):
        raise RuntimeError("capture receipt key run does not match github_run_id")

    prefix = f"{namespace.rstrip('/')}/capture/slot={expected_key_slot}/run={run_id}"
    providers = _as_dict(receipt.get("providers"), "capture providers")
    if set(providers) != {"pionex", "binance_usdm"}:
        raise RuntimeError("capture receipt provider set changed")

    expected_by_provider = {
        "pionex": pionex_symbols,
        "binance_usdm": binance_symbols,
    }
    expected_raw_key = {
        "pionex": f"{prefix}/pionex-symbols.json.gz",
        "binance_usdm": f"{prefix}/binance-usdm-exchange-info.json.gz",
    }
    vectors: dict[str, bytes] = {}
    hashes: dict[str, str] = {}
    for provider in ("pionex", "binance_usdm"):
        row = _as_dict(providers.get(provider), f"capture provider {provider}")
        if row.get("raw_key") != expected_raw_key[provider]:
            raise RuntimeError(f"{provider}: raw key does not match receipt prefix")
        canonical, digest = _validate_vector(
            provider=provider,
            value=row.get("normalized_vector"),
            expected_symbols=expected_by_provider[provider],
            expected_sha256=row.get("normalized_vector_sha256"),
        )
        vectors[provider] = canonical
        hashes[provider] = digest

    transport = _as_dict(receipt.get("transport"), "capture transport")
    if transport.get("pionex") != "github_hosted_direct_public_https":
        raise RuntimeError("Pionex V0.10 transport changed")
    if transport.get("binance_usdm") != "render_free_web_service_v0_10_raw_relay":
        raise RuntimeError("Binance V0.10 transport changed")
    if transport.get("render_region") != "frankfurt" or transport.get("render_plan") != "free":
        raise RuntimeError("Render V0.10 free/region boundary changed")
    if transport.get("render_relay_path") != "/metadata/v0-10/binance-exchange-info":
        raise RuntimeError("V0.10 Render relay path changed")

    boundary = _as_dict(receipt.get("authorization_boundary"), "capture authorization boundary")
    if boundary.get("metadata_only") is not True:
        raise RuntimeError("capture receipt is not metadata-only")
    for field in (
        "holdout_candle_access_authorized",
        "holdout_evaluation_authorized",
        "source_switch_authorized",
        "provider_splicing_authorized",
        "pionex_native_relabel_authorized",
        "w1_materialization_authorized",
        "automatic_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if boundary.get(field) is not False:
            raise RuntimeError(f"capture receipt forbidden boundary changed: {field}")

    return ValidatedReceipt(
        key=key,
        slot_utc=slot_text,
        run_id=run_id,
        vectors=vectors,
        vector_sha256=hashes,
    )


def evaluate_receipt_set(receipts: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    config, _, _, _ = validate_v0_11_protocol()
    expected_slots = expected_slot_strings(config)
    expected_set = set(expected_slots)
    valid: list[ValidatedReceipt] = []
    invalid_keys: list[str] = []

    for key in sorted(receipts):
        try:
            valid.append(validate_capture_receipt(key=key, receipt=receipts[key]))
        except (KeyError, TypeError, ValueError, RuntimeError):
            invalid_keys.append(key)

    by_slot: dict[str, list[ValidatedReceipt]] = {slot: [] for slot in expected_slots}
    for receipt in valid:
        if receipt.slot_utc not in expected_set:
            invalid_keys.append(receipt.key)
            continue
        by_slot[receipt.slot_utc].append(receipt)

    covered_slots = tuple(slot for slot in expected_slots if by_slot[slot])
    missing_slots = tuple(slot for slot in expected_slots if not by_slot[slot])
    intra_slot_disagreements: list[str] = []
    global_vectors: dict[str, set[bytes]] = {"pionex": set(), "binance_usdm": set()}
    global_hashes: dict[str, set[str]] = {"pionex": set(), "binance_usdm": set()}

    for slot in expected_slots:
        slot_receipts = by_slot[slot]
        if not slot_receipts:
            continue
        for provider in ("pionex", "binance_usdm"):
            slot_vectors = {receipt.vectors[provider] for receipt in slot_receipts}
            if len(slot_vectors) != 1:
                intra_slot_disagreements.append(f"{slot}:{provider}")
            for receipt in slot_receipts:
                global_vectors[provider].add(receipt.vectors[provider])
                global_hashes[provider].add(receipt.vector_sha256[provider])

    cross_window_drift = [
        provider
        for provider in ("pionex", "binance_usdm")
        if len(global_vectors[provider]) > 1
    ]
    stable_hashes: dict[str, str | None] = {}
    for provider in ("pionex", "binance_usdm"):
        hashes = global_hashes[provider]
        stable_hashes[provider] = next(iter(hashes)) if len(hashes) == 1 else None

    passed = (
        len(invalid_keys) == 0
        and len(missing_slots) == 0
        and len(covered_slots) == 194
        and len(intra_slot_disagreements) == 0
        and len(cross_window_drift) == 0
        and all(stable_hashes[provider] is not None for provider in stable_hashes)
    )

    return {
        "status": "PASS" if passed else "FAIL",
        "stage": V0_11_PASS_STAGE if passed else V0_11_FAIL_STAGE,
        "evaluation_protocol": "provider_equivalence_v0_11_metadata_stability_evaluation_v0_1",
        "expected_slot_count": 194,
        "covered_slot_count": len(covered_slots),
        "complete_valid_receipt_count": len(valid),
        "invalid_receipt_count": len(set(invalid_keys)),
        "invalid_receipt_keys": sorted(set(invalid_keys)),
        "missing_slot_count": len(missing_slots),
        "missing_slot_ids": list(missing_slots),
        "intra_slot_disagreement_count": len(intra_slot_disagreements),
        "intra_slot_disagreements": sorted(intra_slot_disagreements),
        "cross_window_vector_drift_providers": sorted(cross_window_drift),
        "stable_provider_vector_sha256": stable_hashes,
        "increment_values_emitted": False,
        "raw_provider_responses_emitted": False,
        "r2_client_constructed": False,
        "r2_receipt_reads_performed": 0,
        "r2_writes_performed": False,
        "r2_deletes_performed": False,
        "provider_requests_performed": 0,
        "render_requests_performed": 0,
        "holdout_candles_accessed": False,
        "holdout_evaluated": False,
        "holdout_access_authorized": False,
        "source_switch_authorized": False,
        "live_trading_authorized": False,
    }


def _r2_store_from_env() -> R2Store:
    return R2Store(
        account_id=os.environ["CLOUDFLARE_ACCOUNT_ID"],
        bucket=os.environ["R2_BUCKET_NAME"],
        access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    )


def _load_receipts_from_store(store: Any) -> tuple[dict[str, dict[str, Any]], int]:
    config, _, _, _ = validate_v0_11_protocol()
    input_contract = _as_dict(config.get("input_contract"), "V0.11 input_contract")
    namespace = str(input_contract["metadata_namespace"])
    prefix = f"{namespace.rstrip('/')}/capture/"
    pattern = _receipt_key_regex(namespace)
    paginator = store.client.get_paginator("list_objects_v2")
    keys: list[str] = []
    for page in paginator.paginate(Bucket=store.bucket, Prefix=prefix):
        for item in page.get("Contents", []) or []:
            key = str(item.get("Key") or "")
            if not key.endswith("/receipt.json"):
                continue
            if pattern.fullmatch(key) is None:
                raise RuntimeError("unexpected receipt-like key outside V0.11 allowlist")
            keys.append(key)

    receipts: dict[str, dict[str, Any]] = {}
    reads = 0
    for key in sorted(set(keys)):
        payload = store.get_bytes_if_exists(key)
        if payload is None:
            raise RuntimeError(f"listed V0.10 receipt disappeared before read: {key}")
        reads += 1
        parsed = json.loads(payload.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise RuntimeError(f"V0.10 receipt is not JSON object: {key}")
        receipts[key] = parsed
    return receipts, reads


def run_v0_11_r2_evaluation(
    *, store_factory: Callable[[], Any] = _r2_store_from_env
) -> dict[str, Any]:
    validate_v0_11_protocol()
    if not V0_11_R2_EVALUATION_EXECUTION_AUTHORIZED:
        return {
            "status": "SKIP",
            "stage": V0_11_DISABLED_STAGE,
            "evaluation_protocol": "provider_equivalence_v0_11_metadata_stability_evaluation_v0_1",
            "r2_client_constructed": False,
            "r2_receipt_reads_performed": 0,
            "r2_writes_performed": False,
            "provider_requests_performed": 0,
            "render_requests_performed": 0,
            "increment_values_emitted": False,
            "raw_provider_responses_emitted": False,
            "holdout_candles_accessed": False,
            "holdout_evaluated": False,
            "holdout_access_authorized": False,
            "source_switch_authorized": False,
            "live_trading_authorized": False,
        }

    store = store_factory()
    receipts, reads = _load_receipts_from_store(store)
    result = evaluate_receipt_set(receipts)
    result["r2_client_constructed"] = True
    result["r2_receipt_reads_performed"] = reads
    return result
