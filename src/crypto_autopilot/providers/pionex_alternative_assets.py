from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping


_RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,96}$")
_PIONEX_PERP_SUFFIX = "_USDT_PERP"
_ASSET_CLASSES = ("us_equity_token", "etf_or_fund_token", "metal_or_other_asset")


class PionexAlternativeAssetError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CatalogObject:
    key: str
    payload: bytes
    content_type: str
    immutable: bool
    role: str


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def base_asset_from_pionex_symbol(symbol: str) -> str | None:
    normalized = str(symbol).upper()
    if not normalized.endswith(_PIONEX_PERP_SUFFIX):
        return None
    base = normalized[: -len(_PIONEX_PERP_SUFFIX)]
    if not base or not base.isascii() or not base.isalnum():
        return None
    return base


def _parse_utc(value: str, *, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PionexAlternativeAssetError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise PionexAlternativeAssetError(f"{field} must be explicit UTC")
    return parsed


def validate_config(config: Mapping[str, Any]) -> None:
    if config.get("version") != "0.1.0":
        raise PionexAlternativeAssetError("unexpected alternative-asset config version")
    if config.get("provider") != "pionex_public_futures":
        raise PionexAlternativeAssetError("provider must remain pionex_public_futures")
    registry = config.get("registry")
    if not isinstance(registry, Mapping) or tuple(registry) != _ASSET_CLASSES:
        raise PionexAlternativeAssetError("registry must contain the three frozen asset classes")
    seen: set[str] = set()
    for asset_class in _ASSET_CLASSES:
        values = registry.get(asset_class)
        if not isinstance(values, list) or not values:
            raise PionexAlternativeAssetError(f"registry.{asset_class} must be non-empty")
        for value in values:
            base = str(value).upper()
            if base != value or not base.isascii() or not base.isalnum():
                raise PionexAlternativeAssetError(f"unsafe registry base asset: {value!r}")
            if base in seen:
                raise PionexAlternativeAssetError(f"duplicate registry base asset: {base}")
            seen.add(base)

    execution = config.get("execution")
    if not isinstance(execution, Mapping):
        raise PionexAlternativeAssetError("execution contract is missing")
    not_before = _parse_utc(str(execution.get("not_before_utc")), field="not_before_utc")
    stop = _parse_utc(str(execution.get("catalog_stop_exclusive_utc")), field="catalog_stop_exclusive_utc")
    if not_before >= stop:
        raise PionexAlternativeAssetError("catalog execution window is empty")

    authority = config.get("authority")
    if not isinstance(authority, Mapping):
        raise PionexAlternativeAssetError("authority contract is missing")
    required_true = (
        "public_pionex_symbol_metadata_reads_authorized_after_not_before",
        "production_r2_catalog_writes_authorized_after_not_before",
    )
    required_false = (
        "pionex_kline_reads_authorized",
        "pionex_funding_reads_authorized",
        "pionex_trade_or_orderbook_reads_authorized",
        "replacement_holdout_access_authorized",
        "historical_materialization_authorized",
        "training_authorized",
        "automatic_model_promotion_authorized",
        "formal_trade_plan_authorized",
        "private_api_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
        "v0_10_production_critical_path_change_authorized",
    )
    for key in required_true:
        if authority.get(key) is not True:
            raise PionexAlternativeAssetError(f"authority.{key} must be true")
    for key in required_false:
        if authority.get(key) is not False:
            raise PionexAlternativeAssetError(f"authority.{key} must remain false")


def require_execution_window(config: Mapping[str, Any], *, observed_at: datetime) -> None:
    if observed_at.tzinfo is None or observed_at.utcoffset() != UTC.utcoffset(observed_at):
        raise PionexAlternativeAssetError("observed_at must be explicit UTC")
    execution = config["execution"]
    not_before = _parse_utc(str(execution["not_before_utc"]), field="not_before_utc")
    stop = _parse_utc(
        str(execution["catalog_stop_exclusive_utc"]), field="catalog_stop_exclusive_utc"
    )
    if observed_at < not_before:
        raise PionexAlternativeAssetError("catalog cannot run before the V0.10 window ends")
    if observed_at >= stop:
        raise PionexAlternativeAssetError("catalog authority expired before provider or R2 access")


def load_authority_pair(
    config_path: Path, authority_path: Path
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    config_bytes = config_path.read_bytes()
    config = json.loads(config_bytes)
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    declared_config = str(authority.get("config") or "")
    actual_config = config_path.as_posix()
    if actual_config != declared_config and not actual_config.endswith(f"/{declared_config}"):
        raise PionexAlternativeAssetError("authority points to a different config")
    digest = sha256_bytes(config_bytes)
    if authority.get("config_sha256") != digest:
        raise PionexAlternativeAssetError("authority/config SHA-256 mismatch")
    validate_config(config)
    return config, authority, config_bytes


def _registry_map(config: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(base): asset_class
        for asset_class, values in config["registry"].items()
        for base in values
    }


def build_catalog(
    observed_symbols: Iterable[str],
    *,
    config: Mapping[str, Any],
    retrieved_at_utc: str,
) -> dict[str, Any]:
    validate_config(config)
    _parse_utc(retrieved_at_utc, field="retrieved_at_utc")
    observed = tuple(sorted({str(value).upper() for value in observed_symbols}))
    bases = {
        symbol: base_asset_from_pionex_symbol(symbol)
        for symbol in observed
    }
    eligible = {symbol: base for symbol, base in bases.items() if base is not None}
    registry = _registry_map(config)
    matched = []
    for symbol, base in eligible.items():
        asset_class = registry.get(str(base))
        if asset_class is None:
            continue
        matched.append(
            {
                "symbol": symbol,
                "base_asset": base,
                "quote_asset": "USDT",
                "market_type": "PERP",
                "asset_class": asset_class,
                "classification_method": "explicit_official_listing_registry_plus_live_pionex_intersection",
                "status": "PIONEX_TRADING_AT_RETRIEVAL",
            }
        )
    matched.sort(key=lambda item: (item["asset_class"], item["symbol"]))
    matched_bases = {str(item["base_asset"]) for item in matched}
    absent = [
        {"base_asset": base, "asset_class": asset_class, "status": "NOT_IN_LIVE_PIONEX_PERP_CATALOG"}
        for base, asset_class in sorted(registry.items(), key=lambda item: (item[1], item[0]))
        if base not in matched_bases
    ]
    unresolved = [
        {
            "symbol": symbol,
            "base_asset": base,
            "status": "REVIEW_REQUIRED_NOT_SELECTED",
            "reason": "X_SUFFIX_IS_NOT_SUFFICIENT_TO_PROVE_NON_CRYPTO_ASSET_CLASS",
        }
        for symbol, base in sorted(eligible.items())
        if str(base).endswith("X") and str(base) not in registry
    ]
    counts = {
        asset_class: sum(item["asset_class"] == asset_class for item in matched)
        for asset_class in _ASSET_CLASSES
    }
    return {
        "schema": "pionex-alternative-assets-catalog-v0.1",
        "status": "PASS" if matched else "REVIEW_REQUIRED_NO_MATCHES",
        "provider": "pionex_public_futures",
        "source_endpoint": "https://api.pionex.com/api/v1/common/symbols?type=PERP&status=TRADING",
        "retrieved_at_utc": retrieved_at_utc,
        "registry_candidate_count": len(registry),
        "observed_pionex_perp_count": len(observed),
        "matched_market_count": len(matched),
        "matched_counts_by_class": counts,
        "markets": matched,
        "registry_candidates_absent_from_live_catalog": absent,
        "unresolved_x_suffix_symbols": unresolved,
        "classification_note": (
            "Only an explicit registry entry intersected with the live Pionex PERP catalog is selected. "
            "An X suffix alone never proves that a symbol represents a stock, ETF or real-world asset."
        ),
        "authority": {
            "metadata_only": True,
            "pionex_kline_reads_performed": False,
            "pionex_funding_reads_performed": False,
            "pionex_trade_or_orderbook_reads_performed": False,
            "replacement_holdout_accessed": False,
            "historical_materialization_authorized": False,
            "training_authorized": False,
            "automatic_model_promotion_authorized": False,
            "formal_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }


def build_catalog_objects(
    *, config: Mapping[str, Any], catalog: Mapping[str, Any], run_id: str
) -> tuple[CatalogObject, ...]:
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("run_id must be a safe 1-96 character object-key component")
    storage = config["storage"]
    prefix = str(storage["catalog_runs_namespace"]).rstrip("/")
    catalog_key = f"{prefix}/run={run_id}/catalog.json"
    catalog_payload = canonical_json_bytes(catalog)
    manifest = {
        "schema": "pionex-alternative-assets-catalog-manifest-v0.1",
        "status": catalog["status"],
        "provider": "pionex_public_futures",
        "run_id": run_id,
        "generated_at_utc": catalog["retrieved_at_utc"],
        "catalog_key": catalog_key,
        "catalog_sha256": sha256_bytes(catalog_payload),
        "catalog_bytes": len(catalog_payload),
        "matched_market_count": catalog["matched_market_count"],
        "metadata_only": True,
        "holdout_accessed": False,
    }
    manifest_payload = canonical_json_bytes(manifest)
    manifest_key = f"{prefix}/run={run_id}/manifest.json"
    latest = {
        "schema": "pionex-alternative-assets-catalog-latest-v0.1",
        "provider": "pionex_public_futures",
        "run_id": run_id,
        "generated_at_utc": catalog["retrieved_at_utc"],
        "catalog_key": catalog_key,
        "catalog_sha256": sha256_bytes(catalog_payload),
        "manifest_key": manifest_key,
        "manifest_sha256": sha256_bytes(manifest_payload),
        "matched_market_count": catalog["matched_market_count"],
    }
    return (
        CatalogObject(catalog_key, catalog_payload, "application/json", True, "catalog"),
        CatalogObject(manifest_key, manifest_payload, "application/json", True, "manifest"),
        CatalogObject(
            str(storage["catalog_latest_pointer_key"]),
            canonical_json_bytes(latest),
            "application/json",
            False,
            "latest_pointer",
        ),
    )


def publish_catalog_objects(
    *, store: Any, objects: tuple[CatalogObject, ...], hard_stop_bytes: int, current_bytes: int
) -> dict[str, Any]:
    planned = sum(len(item.payload) for item in objects)
    if current_bytes + planned > hard_stop_bytes:
        return {
            "status": "BLOCKED",
            "stage": "R2_FREE_ONLY_HEADROOM_GATE_BLOCKED_BEFORE_WRITE",
            "current_bucket_bytes": current_bytes,
            "planned_write_bytes": planned,
            "hard_stop_bytes": hard_stop_bytes,
            "r2_writes_performed": False,
        }
    receipts = []
    for item in objects:
        existing = store.get_bytes_if_exists(item.key) if item.immutable else None
        if item.immutable and existing is not None and existing != item.payload:
            raise PionexAlternativeAssetError(f"immutable catalog conflict: {item.key}")
        if existing == item.payload:
            action = "VERIFY_EXISTING"
            receipt = {
                "bucket": store.bucket,
                "key": item.key,
                "bytes": len(existing),
                "sha256": sha256_bytes(existing),
                "etag": None,
            }
        else:
            action = "UPLOAD"
            receipt = asdict(
                store.put_bytes(
                    item.key,
                    item.payload,
                    content_type=item.content_type,
                    metadata={
                        "provider": "pionex_public_futures",
                        "role": item.role,
                        "version": "v0.1",
                    },
                )
            )
        restored = store.get_bytes_verified(item.key, expected_sha256=str(receipt["sha256"]))
        if restored != item.payload:
            raise PionexAlternativeAssetError(f"R2 exact-byte round trip mismatch: {item.key}")
        receipts.append({"role": item.role, "action": action, **receipt})
    return {
        "status": "PASS",
        "stage": "PIONEX_ALTERNATIVE_ASSETS_CATALOG_PUBLISHED_V0_1",
        "current_bucket_bytes_before_write": current_bytes,
        "planned_write_bytes": planned,
        "hard_stop_bytes": hard_stop_bytes,
        "objects": receipts,
        "latest_pointer_written_last": objects[-1].role == "latest_pointer",
        "r2_writes_performed": any(item["action"] == "UPLOAD" for item in receipts),
        "replacement_holdout_accessed": False,
        "live_trading_authorized": False,
    }
