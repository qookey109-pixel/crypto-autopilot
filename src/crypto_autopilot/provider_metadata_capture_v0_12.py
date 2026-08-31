from __future__ import annotations

import gzip
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable

from . import provider_metadata_capture_v0_2 as v02
from . import provider_metadata_capture_v0_8_successor as successor
from . import provider_metadata_capture_v0_10 as v10
from .storage.r2 import R2Store

CONFIG = Path("config/provider_equivalence_v0_12_successor_metadata_window_v0_1.json")
AUTHORITY = Path(
    "research/receipts/"
    "2026-08-31-provider-equivalence-v0-12-successor-metadata-window-authority.json"
)
V0_10_OBSERVATION = Path(
    "research/receipts/2026-08-31-v0-10-post-perp-query-schema-mismatch-observation.json"
)

V0_12_EXECUTION_AUTHORIZED_ON_MAIN_MERGE = True
V0_12_RECEIPT_SCHEMA = (
    "provider-equivalence-v0-12-successor-metadata-capture-receipt-v0.1"
)
V0_12_CAPTURE_PASS_STAGE = (
    "PROVIDER_EQUIVALENCE_V0_12_SUCCESSOR_METADATA_CAPTURE_PASS"
)
V0_12_ACTIVATION_AUTHORITY = (
    "provider_equivalence_v0_12_successor_metadata_window_v0_1"
)


@dataclass(frozen=True)
class V012CaptureArtifacts:
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


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise RuntimeError("successor window timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _positive_decimal_source_string(value: object, *, field: str) -> str:
    if not isinstance(value, (str, int, float)):
        raise RuntimeError(f"{field} is not scalar")
    text = str(value)
    try:
        parsed = Decimal(text)
    except InvalidOperation as exc:
        raise RuntimeError(f"{field} is not decimal: {text}") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise RuntimeError(f"{field} must be finite and positive: {text}")
    return text


def validate_successor_authority() -> tuple[dict[str, Any], dict[str, Any]]:
    cfg = _load(CONFIG)
    authority = _load(AUTHORITY)
    observation = _load(V0_10_OBSERVATION)

    if cfg.get("status") != (
        "AUTHORIZED_FOR_PROTECTED_MAIN_REVIEW_NOT_EFFECTIVE_BEFORE_MERGE"
    ):
        raise RuntimeError("V0.12 successor config is not authorized-on-merge")
    if authority.get("status") != "PASS" or authority.get("stage") != (
        "PROVIDER_EQUIVALENCE_V0_12_SUCCESSOR_METADATA_WINDOW_AUTHORIZED_ON_MAIN_MERGE"
    ):
        raise RuntimeError("V0.12 successor authority receipt is not PASS")
    if authority.get("protocol") != str(CONFIG):
        raise RuntimeError("V0.12 authority protocol binding changed")
    if observation.get("status") != "FAIL_CLOSED":
        raise RuntimeError("V0.10 fail-closed observation is required")
    impact = observation.get("scientific_impact") or {}
    if impact.get("current_frozen_window_eligible_for_complete_194_slot_pass") is not False:
        raise RuntimeError("V0.10 incomplete-window evidence changed")

    transition = cfg.get("atomic_schedule_transition") or {}
    window = cfg.get("successor_window") or {}
    normalization = cfg.get("pionex_normalization_contract") or {}
    render = cfg.get("render_transport") or {}
    storage = cfg.get("storage") or {}
    stability = cfg.get("frozen_future_stability_contract") or {}
    boundary = cfg.get("authorization_boundary") or {}
    if not all(
        isinstance(item, dict)
        for item in (
            transition,
            window,
            normalization,
            render,
            storage,
            stability,
            boundary,
        )
    ):
        raise RuntimeError("V0.12 successor authority shape changed")

    if transition.get("retired_workflow_schedule_removed_in_same_change") is not True:
        raise RuntimeError("V0.10 schedule retirement must be atomic")
    if transition.get("successor_schedule_enabled_in_same_change") is not True:
        raise RuntimeError("V0.12 schedule activation must be atomic")
    if transition.get("concurrent_v0_10_and_v0_12_capture_paths_authorized") is not False:
        raise RuntimeError("concurrent V0.10 and V0.12 capture paths are forbidden")
    if transition.get("hourly_slot_count") != 194:
        raise RuntimeError("V0.12 hourly slot count changed")
    if transition.get("scheduled_attempt_count") != 388:
        raise RuntimeError("V0.12 scheduled attempt count changed")

    start = _utc(str(window.get("start_utc")))
    end = _utc(str(window.get("end_utc")))
    if start != datetime(2026, 9, 4, 2, tzinfo=timezone.utc):
        raise RuntimeError("V0.12 successor start changed")
    if end != datetime(2026, 9, 12, 3, 59, 59, 999000, tzinfo=timezone.utc):
        raise RuntimeError("V0.12 successor end changed")
    if window.get("expected_hourly_slot_count") != 194:
        raise RuntimeError("V0.12 successor window slot count changed")
    if window.get("candidate_symbol_count") != 15 or window.get("mapped_pair_count") != 45:
        raise RuntimeError("V0.12 frozen symbol scope changed")
    if window.get("replacement_holdout_state") != "FROZEN_UNOPENED":
        raise RuntimeError("replacement holdout state changed")

    if normalization.get("query") != {"type": "PERP"}:
        raise RuntimeError("V0.12 Pionex PERP query changed")
    if normalization.get("both_representations_present_must_agree") is not True:
        raise RuntimeError("V0.12 Pionex agreement guard changed")
    if normalization.get("missing_or_unknown_representation_policy") != (
        "FAIL_CLOSED_BEFORE_R2_CLIENT"
    ):
        raise RuntimeError("V0.12 Pionex missing-field policy changed")

    if render.get("plan") != "free" or render.get("monthly_budget_usd") != 0:
        raise RuntimeError("V0.12 Render FREE-ONLY boundary changed")
    if render.get("render_code_or_deploy_changed") is not False:
        raise RuntimeError("V0.12 must reuse the existing Render relay")
    if render.get("render_receives_r2_credentials") is not False:
        raise RuntimeError("Render must never receive R2 credentials")
    if storage.get("free_only_operational_hard_stop_bytes") != 8_000_000_000:
        raise RuntimeError("V0.12 R2 hard stop changed")
    if storage.get("fresh_bucket_inventory_before_each_write") is not True:
        raise RuntimeError("V0.12 fresh R2 inventory requirement changed")
    if stability.get("partial_window_may_produce_pass") is not False:
        raise RuntimeError("partial V0.12 window cannot pass")
    if stability.get("production_r2_evaluation_authorized_now") is not False:
        raise RuntimeError("V0.12 must not authorize production stability evaluation")

    for key in (
        "v0_10_scheduled_execution_authorized_after_main_merge",
        "v0_10_manual_capture_authorized",
        "v0_10_or_v0_12_retroactive_backfill_authorized",
        "production_stability_evaluation_authorized",
        "holdout_candle_access_authorized",
        "holdout_evaluation_authorized",
        "source_switch_authorized",
        "provider_splicing_authorized",
        "pionex_native_relabel_authorized",
        "staged_trade_kline_w1_materialization_authorized",
        "historical_universe_membership_authorized",
        "backtest_admission_authorized",
        "strategy_parameter_change_authorized",
        "automatic_model_promotion_authorized",
        "automatic_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if boundary.get(key) is not False:
            raise RuntimeError(f"V0.12 forbidden boundary changed: {key}")
    if boundary.get("v0_12_metadata_capture_execution_authorized_on_main_merge") is not True:
        raise RuntimeError("V0.12 capture authority missing")
    if boundary.get("v0_12_metadata_only_r2_writes_authorized_on_main_merge") is not True:
        raise RuntimeError("V0.12 metadata-only R2 authority missing")

    return cfg, authority


def capture_slot(observed: datetime, cfg: dict[str, Any]) -> datetime | None:
    normalized = observed.astimezone(timezone.utc)
    window = cfg["successor_window"]
    if not _utc(str(window["start_utc"])) <= normalized <= _utc(str(window["end_utc"])):
        return None
    return normalized.replace(minute=0, second=0, microsecond=0)


def _contract_type(row: dict[str, Any], *, symbol: str) -> tuple[str, str]:
    contract_type = row.get("contractType")
    market_type = row.get("type")
    normalized_contract: str | None = None
    source_fields: list[str] = []

    if contract_type is not None:
        if contract_type != "PERPETUAL":
            raise RuntimeError(f"Pionex contractType invalid: {symbol}")
        normalized_contract = "PERPETUAL"
        source_fields.append("contractType")
    if market_type is not None:
        if market_type != "PERP":
            raise RuntimeError(f"Pionex type invalid: {symbol}")
        if normalized_contract not in (None, "PERPETUAL"):
            raise RuntimeError(f"Pionex contract fields disagree: {symbol}")
        normalized_contract = "PERPETUAL"
        source_fields.append("type")
    if normalized_contract is None:
        raise RuntimeError(f"Pionex contractType/type missing: {symbol}")
    return normalized_contract, "+".join(source_fields)


def _status(row: dict[str, Any], *, symbol: str) -> tuple[str, str]:
    explicit = row.get("status")
    enabled = row.get("enable")
    normalized_status: str | None = None
    source_fields: list[str] = []

    if explicit is not None:
        if explicit not in {"TRADING", "OFFLINE"}:
            raise RuntimeError(f"Pionex status invalid: {symbol}")
        normalized_status = str(explicit)
        source_fields.append("status")
    if enabled is not None:
        if not isinstance(enabled, bool):
            raise RuntimeError(f"Pionex enable is not boolean: {symbol}")
        enabled_status = "TRADING" if enabled else "OFFLINE"
        if normalized_status not in (None, enabled_status):
            raise RuntimeError(f"Pionex status/enable disagree: {symbol}")
        normalized_status = enabled_status
        source_fields.append("enable")
    if normalized_status is None:
        raise RuntimeError(f"Pionex status/enable missing: {symbol}")
    return normalized_status, "+".join(source_fields)


def parse_pionex_perp_symbols(
    raw: bytes, expected_symbols: tuple[str, ...]
) -> tuple[dict[str, str], ...]:
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict) or payload.get("result") is not True:
        raise RuntimeError("Pionex successor payload result is not true")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("Pionex successor payload missing data object")
    rows = data.get("symbols")
    if not isinstance(rows, list):
        raise RuntimeError("Pionex successor payload missing data.symbols list")

    expected = set(expected_symbols)
    found: dict[str, dict[str, str]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError("Pionex successor symbol row is not object")
        symbol = str(row.get("symbol", ""))
        if symbol not in expected:
            continue
        if symbol in found:
            raise RuntimeError(f"duplicate Pionex successor symbol: {symbol}")
        quote_step = _positive_decimal_source_string(
            row.get("quoteStep"), field=f"{symbol}.quoteStep"
        )
        contract_type, contract_source = _contract_type(row, symbol=symbol)
        status, status_source = _status(row, symbol=symbol)
        found[symbol] = {
            "symbol": symbol,
            "price_increment": quote_step,
            "status": status,
            "contract_type": contract_type,
            "source_field": (
                "data.symbols[].quoteStep;"
                f"contract={contract_source};status={status_source}"
            ),
        }

    missing = expected - set(found)
    if missing:
        raise RuntimeError(f"Pionex successor metadata missing frozen symbols: {sorted(missing)}")
    return tuple(found[symbol] for symbol in sorted(found))


def fetch_v0_12_provider_payloads() -> tuple[
    v02.ProviderPayload, v02.ProviderPayload, dict[str, Any]
]:
    cfg, _ = validate_successor_authority()
    _, v07, pionex_symbols, binance_symbols = successor.validate_prepared_runtime_authorities()
    providers = v07["provider_semantics"]
    pionex_cfg = providers["pionex"]
    binance_cfg = providers["binance_usdm"]

    pionex_raw, pionex_content_type = v02._fetch_json_bytes(  # noqa: SLF001
        v10._pionex_perp_endpoint(str(pionex_cfg["public_endpoint"])),  # noqa: SLF001
        max_bytes=int(pionex_cfg["raw_uncompressed_response_max_bytes"]),
    )
    binance_raw, binance_content_type = successor._fetch_render_relay_raw(  # noqa: SLF001
        url=str(cfg["render_transport"]["service_url"])
        + str(cfg["render_transport"]["reused_authenticated_raw_relay_path"]),
        max_bytes=int(binance_cfg["raw_uncompressed_response_max_bytes"]),
    )

    pionex = v02.ProviderPayload(
        provider="pionex",
        raw=pionex_raw,
        content_type=pionex_content_type,
        vector=parse_pionex_perp_symbols(pionex_raw, pionex_symbols),
    )
    binance = v02.ProviderPayload(
        provider="binance_usdm",
        raw=binance_raw,
        content_type=binance_content_type,
        vector=v02.parse_binance_exchange_info(binance_raw, binance_symbols),
    )
    return pionex, binance, cfg


def _gzip(raw: bytes) -> bytes:
    return gzip.compress(raw, compresslevel=9, mtime=0)


def _json_bytes(payload: dict[str, Any]) -> bytes:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    return text.encode("utf-8")


def build_v0_12_capture_artifacts(
    *,
    pionex: v02.ProviderPayload,
    binance: v02.ProviderPayload,
    cfg: dict[str, Any],
    observed: datetime,
    run_id: str,
) -> V012CaptureArtifacts:
    if not run_id.isdigit():
        raise RuntimeError("GITHUB_RUN_ID must be numeric")
    slot = capture_slot(observed, cfg)
    if slot is None:
        raise RuntimeError("cannot build V0.12 artifacts outside successor window")

    namespace = str(cfg["storage"]["namespace"]).rstrip("/")
    slot_id = slot.strftime("%Y%m%dT%H0000Z")
    prefix = f"{namespace}/capture/slot={slot_id}/run={run_id}"
    pionex_key = f"{prefix}/pionex-symbols.json.gz"
    binance_key = f"{prefix}/binance-usdm-exchange-info.json.gz"
    receipt_key = f"{prefix}/receipt.json"

    pionex_gzip = _gzip(pionex.raw)
    binance_gzip = _gzip(binance.raw)
    receipt = {
        "schema": V0_12_RECEIPT_SCHEMA,
        "status": "PASS",
        "stage": V0_12_CAPTURE_PASS_STAGE,
        "activation_authority": V0_12_ACTIVATION_AUTHORITY,
        "capture_execution_version": "v0_12",
        "slot_utc": slot.isoformat().replace("+00:00", "Z"),
        "observed_at_utc": observed.astimezone(timezone.utc).isoformat(),
        "github_run_id": int(run_id),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "transport": {
            "pionex": "github_hosted_direct_public_https",
            "binance_usdm": "render_free_web_service_v0_10_raw_relay_reused_by_v0_12",
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
                "normalization_contract": "v0_12_contractType_or_type_status_or_enable",
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
            "v0_10_replay_or_backfill_authorized": False,
            "production_stability_evaluation_authorized": False,
            "holdout_candle_access_authorized": False,
            "holdout_evaluation_authorized": False,
            "source_switch_authorized": False,
            "provider_splicing_authorized": False,
            "pionex_native_relabel_authorized": False,
            "w1_materialization_authorized": False,
            "automatic_model_promotion_authorized": False,
            "automatic_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }
    return V012CaptureArtifacts(
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


def _skip_payload(*, observed: datetime, stage: str) -> dict[str, Any]:
    return {
        "status": "SKIP",
        "stage": stage,
        "observed_at_utc": observed.isoformat(),
        "provider_requests_performed": 0,
        "render_relay_requests_performed": 0,
        "r2_client_constructed": False,
        "r2_writes_performed": False,
        "r2_deletes_performed": False,
        "holdout_candles_accessed": False,
        "source_switch_authorized": False,
        "live_trading_authorized": False,
        "activation_authority": V0_12_ACTIVATION_AUTHORITY,
        "capture_execution_version": "v0_12",
    }


def capture_v0_12(
    *,
    now: datetime | None = None,
    provider_fetcher: Callable[
        [], tuple[v02.ProviderPayload, v02.ProviderPayload, dict[str, Any]]
    ] = fetch_v0_12_provider_payloads,
    store_factory: Callable[[], Any] = _r2_store_from_env,
) -> dict[str, Any]:
    observed = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not V0_12_EXECUTION_AUTHORIZED_ON_MAIN_MERGE:
        return _skip_payload(
            observed=observed,
            stage="V0_12_SUCCESSOR_METADATA_CAPTURE_EXECUTION_NOT_AUTHORIZED",
        )
    if os.environ.get("GITHUB_EVENT_NAME") != "schedule":
        return _skip_payload(
            observed=observed,
            stage="V0_12_SUCCESSOR_METADATA_CAPTURE_SCHEDULE_EVENT_REQUIRED",
        )

    cfg, _ = validate_successor_authority()
    slot = capture_slot(observed, cfg)
    if slot is None:
        return _skip_payload(
            observed=observed,
            stage="OUTSIDE_V0_12_SUCCESSOR_METADATA_CAPTURE_WINDOW",
        )

    pionex, binance, fetched_cfg = provider_fetcher()
    if fetched_cfg["successor_window"] != cfg["successor_window"]:
        raise RuntimeError("provider fetcher returned V0.12 window drift")

    run_id = os.environ.get("GITHUB_RUN_ID")
    if not run_id or not run_id.isdigit():
        raise RuntimeError("GITHUB_RUN_ID is required for immutable V0.12 capture keys")
    artifacts = build_v0_12_capture_artifacts(
        pionex=pionex,
        binance=binance,
        cfg=cfg,
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
            "r2_deletes_performed": False,
            "holdout_candles_accessed": False,
            "source_switch_authorized": False,
            "live_trading_authorized": False,
            "activation_authority": V0_12_ACTIVATION_AUTHORITY,
            "capture_execution_version": "v0_12",
        }

    for key in (artifacts.pionex_key, artifacts.binance_key, artifacts.receipt_key):
        if store.exists(key):
            raise RuntimeError(f"immutable V0.12 capture key already exists: {key}")

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
        metadata={
            "dataset": "provider_equivalence_v0_12_metadata",
            "slot": artifacts.slot_id,
            "run": run_id,
        },
    )

    store.get_bytes_verified(artifacts.pionex_key, expected_sha256=p_receipt.sha256)
    store.get_bytes_verified(artifacts.binance_key, expected_sha256=b_receipt.sha256)
    store.get_bytes_verified(artifacts.receipt_key, expected_sha256=r_receipt.sha256)

    return {
        "status": "PASS",
        "stage": V0_12_CAPTURE_PASS_STAGE,
        "slot_utc": slot.isoformat().replace("+00:00", "Z"),
        "observed_at_utc": observed.isoformat(),
        "github_run_id": int(run_id),
        "object_count": 3,
        "receipt_key": artifacts.receipt_key,
        "receipt_schema": V0_12_RECEIPT_SCHEMA,
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
        "activation_authority": V0_12_ACTIVATION_AUTHORITY,
        "capture_execution_version": "v0_12",
    }
