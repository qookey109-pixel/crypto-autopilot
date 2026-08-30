from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any, Mapping

from .pionex_alternative_assets import (
    CatalogObject,
    PionexAlternativeAssetError,
    base_asset_from_pionex_symbol,
    canonical_json_bytes,
    sha256_bytes,
    validate_config as validate_catalog_config,
)


_ASSET_CLASSES = ("us_equity_token", "etf_or_fund_token", "metal_or_other_asset")


def _parse_utc(value: str, *, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PionexAlternativeAssetError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise PionexAlternativeAssetError(f"{field} must be explicit UTC")
    return parsed


def validate_observability_config(
    config: Mapping[str, Any], *, catalog_config_bytes: bytes
) -> None:
    if config.get("version") != "0.2.0":
        raise PionexAlternativeAssetError("unexpected observability config version")
    if config.get("provider") != "pionex_public_futures":
        raise PionexAlternativeAssetError("observability provider changed")
    supersession = config.get("supersession") or {}
    if supersession.get("supersedes_config") != "config/pionex_alternative_assets_v0_1.json":
        raise PionexAlternativeAssetError("V0.2 must supersede the frozen V0.1 catalog config")
    if supersession.get("supersedes_config_sha256") != sha256_bytes(catalog_config_bytes):
        raise PionexAlternativeAssetError("V0.2 catalog-source SHA-256 mismatch")
    for key in (
        "superseded_before_first_provider_request",
        "superseded_before_first_r2_access",
    ):
        if supersession.get(key) is not True:
            raise PionexAlternativeAssetError(f"supersession.{key} must be true")
    if supersession.get("concurrent_v0_1_schedule_authorized") is not False:
        raise PionexAlternativeAssetError("concurrent V0.1 schedule must remain false")

    execution = config.get("execution") or {}
    not_before = _parse_utc(str(execution.get("not_before_utc")), field="not_before_utc")
    stop = _parse_utc(
        str(execution.get("catalog_stop_exclusive_utc")),
        field="catalog_stop_exclusive_utc",
    )
    if not_before >= stop:
        raise PionexAlternativeAssetError("observability execution window is empty")
    if execution.get("first_catalog_cron_utc") != "53 2 4 9 *":
        raise PionexAlternativeAssetError("first catalog schedule changed")
    if execution.get("weekly_catalog_cron_utc") != "53 3 6,13,20,27 9 *":
        raise PionexAlternativeAssetError("weekly catalog schedule changed")
    first_run = _parse_utc(
        str(execution.get("first_scheduled_run_utc")),
        field="first_scheduled_run_utc",
    )
    if first_run != datetime(2026, 9, 4, 2, 53, tzinfo=UTC):
        raise PionexAlternativeAssetError("first scheduled run changed")
    if not not_before <= first_run < stop:
        raise PionexAlternativeAssetError("first scheduled run is outside authority")

    validation = config.get("validation") or {}
    if validation.get("allowed_catalog_schema") != "pionex-alternative-assets-catalog-v0.1":
        raise PionexAlternativeAssetError("catalog schema allowlist changed")
    if int(validation.get("matched_market_minimum_for_pass") or 0) != 1:
        raise PionexAlternativeAssetError("matched-market minimum must remain one")
    ratio = float(validation.get("previous_count_ratio_review_threshold") or 0.0)
    if not 0.0 < ratio <= 1.0:
        raise PionexAlternativeAssetError("previous-count review ratio is invalid")
    for key in (
        "exact_registry_partition_required",
        "exact_asset_class_counts_required",
    ):
        if validation.get(key) is not True:
            raise PionexAlternativeAssetError(f"validation.{key} must be true")
    for key in (
        "unknown_x_suffix_selection_authorized",
        "catalog_absence_is_delisting_proof",
        "automatic_registry_mutation_authorized",
    ):
        if validation.get(key) is not False:
            raise PionexAlternativeAssetError(f"validation.{key} must remain false")

    projection = config.get("capacity_projection") or {}
    if int(projection.get("history_days") or 0) != 1461:
        raise PionexAlternativeAssetError("capacity projection must remain four complete years")
    if projection.get("interval_rows_per_day") != {"15M": 96, "60M": 24, "4H": 6}:
        raise PionexAlternativeAssetError("capacity interval assumptions changed")
    if projection.get("compressed_bytes_per_row_scenarios") != {
        "low": 32,
        "reference": 64,
        "stress": 128,
    }:
        raise PionexAlternativeAssetError("capacity byte scenarios changed")
    if projection.get("projection_is_not_materialization_authority") is not True:
        raise PionexAlternativeAssetError("capacity projection cannot authorize history")

    storage = config.get("storage") or {}
    if storage.get("raw_market_list_projected_to_pages") is not False:
        raise PionexAlternativeAssetError("raw market list cannot be projected to Pages")
    if storage.get("scheduled_pages_deployment_authorized") is not False:
        raise PionexAlternativeAssetError("catalog schedule cannot mutate Pages")
    if storage.get("checked_in_safe_summary_projection_authorized") is not True:
        raise PionexAlternativeAssetError("safe summary projection must be explicit")

    authority = config.get("authority") or {}
    required_true = (
        "public_pionex_symbol_metadata_reads_authorized_after_not_before",
        "production_r2_catalog_lineage_reads_authorized_after_not_before",
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
        raise PionexAlternativeAssetError("observability cannot run before the V0.10 window ends")
    if observed_at >= stop:
        raise PionexAlternativeAssetError("observability authority expired before provider or R2 access")


def _registry_map(catalog_config: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(base): asset_class
        for asset_class, values in catalog_config["registry"].items()
        for base in values
    }


def validate_catalog(
    catalog: Mapping[str, Any], *, catalog_config: Mapping[str, Any]
) -> dict[str, Any]:
    validate_catalog_config(catalog_config)
    if catalog.get("schema") != "pionex-alternative-assets-catalog-v0.1":
        raise PionexAlternativeAssetError("catalog schema rejected")
    if catalog.get("provider") != "pionex_public_futures":
        raise PionexAlternativeAssetError("catalog provider rejected")
    _parse_utc(str(catalog.get("retrieved_at_utc")), field="catalog.retrieved_at_utc")
    authority = catalog.get("authority") or {}
    if authority.get("metadata_only") is not True:
        raise PionexAlternativeAssetError("catalog must remain metadata-only")
    if any(value is not False for key, value in authority.items() if key != "metadata_only"):
        raise PionexAlternativeAssetError("catalog claims downstream authority")

    registry = _registry_map(catalog_config)
    markets = list(catalog.get("markets") or [])
    absent = list(catalog.get("registry_candidates_absent_from_live_catalog") or [])
    unresolved = list(catalog.get("unresolved_x_suffix_symbols") or [])
    market_symbols: set[str] = set()
    matched_bases: set[str] = set()
    class_counts = {asset_class: 0 for asset_class in _ASSET_CLASSES}
    for item in markets:
        symbol = str(item.get("symbol") or "")
        base = str(item.get("base_asset") or "")
        asset_class = str(item.get("asset_class") or "")
        if symbol in market_symbols:
            raise PionexAlternativeAssetError(f"duplicate selected market: {symbol}")
        if base in matched_bases:
            raise PionexAlternativeAssetError(f"duplicate selected base asset: {base}")
        if base_asset_from_pionex_symbol(symbol) != base:
            raise PionexAlternativeAssetError(f"selected symbol/base mismatch: {symbol}")
        if registry.get(base) != asset_class or asset_class not in class_counts:
            raise PionexAlternativeAssetError(f"selected market is outside registry: {symbol}")
        if item.get("status") != "PIONEX_TRADING_AT_RETRIEVAL":
            raise PionexAlternativeAssetError(f"selected market status rejected: {symbol}")
        market_symbols.add(symbol)
        matched_bases.add(base)
        class_counts[asset_class] += 1

    absent_bases: set[str] = set()
    for item in absent:
        base = str(item.get("base_asset") or "")
        asset_class = str(item.get("asset_class") or "")
        if base in absent_bases or base in matched_bases:
            raise PionexAlternativeAssetError(f"invalid absent registry partition: {base}")
        if registry.get(base) != asset_class:
            raise PionexAlternativeAssetError(f"absent market is outside registry: {base}")
        if item.get("status") != "NOT_IN_LIVE_PIONEX_PERP_CATALOG":
            raise PionexAlternativeAssetError(f"absent status rejected: {base}")
        absent_bases.add(base)
    if matched_bases | absent_bases != set(registry):
        raise PionexAlternativeAssetError("matched/absent records do not partition the registry")

    unresolved_symbols: set[str] = set()
    for item in unresolved:
        symbol = str(item.get("symbol") or "")
        base = str(item.get("base_asset") or "")
        if symbol in unresolved_symbols or symbol in market_symbols:
            raise PionexAlternativeAssetError(f"invalid unresolved symbol: {symbol}")
        if not base.endswith("X") or base in registry:
            raise PionexAlternativeAssetError(f"unresolved classifier boundary rejected: {symbol}")
        if item.get("status") != "REVIEW_REQUIRED_NOT_SELECTED":
            raise PionexAlternativeAssetError(f"unresolved status rejected: {symbol}")
        unresolved_symbols.add(symbol)

    matched_count = len(markets)
    if int(catalog.get("registry_candidate_count") or -1) != len(registry):
        raise PionexAlternativeAssetError("catalog registry count mismatch")
    if int(catalog.get("matched_market_count") or -1) != matched_count:
        raise PionexAlternativeAssetError("catalog matched count mismatch")
    if catalog.get("matched_counts_by_class") != class_counts:
        raise PionexAlternativeAssetError("catalog class counts mismatch")
    expected_status = "PASS" if matched_count else "REVIEW_REQUIRED_NO_MATCHES"
    if catalog.get("status") != expected_status:
        raise PionexAlternativeAssetError("catalog status does not match observed evidence")
    review_reasons = []
    if matched_count == 0:
        review_reasons.append("NO_REGISTRY_CANDIDATE_MATCHED_THE_LIVE_CATALOG")
    if unresolved_symbols:
        review_reasons.append("UNKNOWN_X_SUFFIX_SYMBOLS_REQUIRE_REVIEW")
    return {
        "schema": "pionex-alternative-assets-catalog-validation-v0.2",
        "status": "PASS" if not review_reasons else "REVIEW_REQUIRED",
        "matched_market_count": matched_count,
        "matched_counts_by_class": class_counts,
        "registry_candidate_count": len(registry),
        "registry_partition_complete": True,
        "unique_selected_symbols": True,
        "unresolved_x_suffix_count": len(unresolved_symbols),
        "review_reasons": review_reasons,
        "catalog_absence_is_delisting_proof": False,
    }


def compare_catalogs(
    current: Mapping[str, Any],
    previous: Mapping[str, Any] | None,
    *,
    ratio_review_threshold: float,
) -> dict[str, Any]:
    current_by_symbol = {str(item["symbol"]): item for item in current.get("markets") or []}
    if previous is None:
        return {
            "schema": "pionex-alternative-assets-catalog-diff-v0.2",
            "status": "BASELINE_CREATED",
            "previous_catalog_available": False,
            "added_symbols": sorted(current_by_symbol),
            "removed_symbols": [],
            "asset_class_changes": [],
            "matched_count_previous": None,
            "matched_count_current": len(current_by_symbol),
            "matched_count_ratio": None,
            "review_reasons": [],
            "removal_interpretation": "NO_PRIOR_CATALOG; NO_DELISTING_CONCLUSION",
        }
    previous_by_symbol = {
        str(item["symbol"]): item for item in previous.get("markets") or []
    }
    added = sorted(set(current_by_symbol) - set(previous_by_symbol))
    removed = sorted(set(previous_by_symbol) - set(current_by_symbol))
    class_changes = [
        {
            "symbol": symbol,
            "previous_asset_class": previous_by_symbol[symbol]["asset_class"],
            "current_asset_class": current_by_symbol[symbol]["asset_class"],
        }
        for symbol in sorted(set(current_by_symbol) & set(previous_by_symbol))
        if previous_by_symbol[symbol]["asset_class"] != current_by_symbol[symbol]["asset_class"]
    ]
    previous_count = len(previous_by_symbol)
    current_count = len(current_by_symbol)
    ratio = current_count / previous_count if previous_count else None
    reasons = []
    if ratio is not None and ratio < ratio_review_threshold:
        reasons.append("MATCHED_MARKET_COUNT_COLLAPSED_BELOW_FROZEN_RATIO")
    if class_changes:
        reasons.append("ASSET_CLASS_CHANGE_REQUIRES_REVIEW")
    return {
        "schema": "pionex-alternative-assets-catalog-diff-v0.2",
        "status": "REVIEW_REQUIRED" if reasons else "PASS",
        "previous_catalog_available": True,
        "added_symbols": added,
        "removed_symbols": removed,
        "asset_class_changes": class_changes,
        "matched_count_previous": previous_count,
        "matched_count_current": current_count,
        "matched_count_ratio": ratio,
        "review_reasons": reasons,
        "removal_interpretation": (
            "ABSENT_FROM_CURRENT_PIONEX_PERP_CATALOG; NOT_PROOF_OF_DELISTING"
        ),
    }


def project_capacity(market_count: int, *, config: Mapping[str, Any]) -> dict[str, Any]:
    if market_count < 0:
        raise ValueError("market_count cannot be negative")
    projection = config["capacity_projection"]
    days = int(projection["history_days"])
    rows_by_interval = {
        interval: market_count * days * int(rows_per_day)
        for interval, rows_per_day in projection["interval_rows_per_day"].items()
    }
    total_rows = sum(rows_by_interval.values())
    decimal_gb = int(projection["decimal_gb_bytes"])
    overhead = float(projection["operational_overhead_multiplier"])
    scenarios = {}
    for name, bytes_per_row in projection["compressed_bytes_per_row_scenarios"].items():
        canonical_bytes = total_rows * int(bytes_per_row)
        scenarios[name] = {
            "compressed_bytes_per_row_assumption": int(bytes_per_row),
            "canonical_bytes": canonical_bytes,
            "canonical_gb": canonical_bytes / decimal_gb,
            "operational_stress_bytes": int(canonical_bytes * overhead),
            "operational_stress_gb": (canonical_bytes * overhead) / decimal_gb,
        }
    return {
        "schema": "pionex-alternative-assets-history-capacity-projection-v0.2",
        "market_count": market_count,
        "history_days": days,
        "rows_by_interval": rows_by_interval,
        "total_rows": total_rows,
        "scenarios": scenarios,
        "r2_hard_stop_bytes": int(config["storage"]["free_only_hard_stop_bytes"]),
        "historical_materialization_authorized": False,
        "interpretation": "Planning estimate only; actual Parquet compression must be measured before any history authority.",
    }


def build_safe_projection(
    *,
    catalog_config: Mapping[str, Any],
    observability_config: Mapping[str, Any],
    catalog: Mapping[str, Any] | None = None,
    analysis: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidate_counts = {
        asset_class: len(catalog_config["registry"][asset_class])
        for asset_class in _ASSET_CLASSES
    }
    max_capacity = project_capacity(sum(candidate_counts.values()), config=observability_config)
    actual = None
    if catalog is not None and analysis is not None:
        diff = analysis["catalog_diff"]
        actual = {
            "state": analysis["status"],
            "observed_at_utc": catalog["retrieved_at_utc"],
            "matched_market_count": catalog["matched_market_count"],
            "matched_counts_by_class": catalog["matched_counts_by_class"],
            "unresolved_x_suffix_count": analysis["catalog_validation"][
                "unresolved_x_suffix_count"
            ],
            "added_count": len(diff["added_symbols"]),
            "removed_count": len(diff["removed_symbols"]),
            "capacity_reference_gb": analysis["capacity_actual"]["scenarios"][
                "reference"
            ]["canonical_gb"],
        }
    return {
        "schema": "qookey-pionex-alternative-assets-projection-v0.2",
        "authority": False,
        "mode": "METADATA_ONLY_READ_ONLY",
        "status": "WAITING_FIRST_RUN" if actual is None else actual["state"],
        "projection_generated_at_utc": (
            None if actual is None else str(catalog["retrieved_at_utc"])
        ),
        "candidate_registry": {
            "total": sum(candidate_counts.values()),
            "counts_by_class": candidate_counts,
            "is_current_listing_proof": False,
        },
        "actual_catalog": actual,
        "next_scheduled_run_utc": observability_config["execution"][
            "first_scheduled_run_utc"
        ],
        "capacity_candidate_max": max_capacity,
        "safety_boundary": {
            "provider_reads_performed": False,
            "r2_reads_performed": False,
            "r2_writes_performed": False,
            "raw_market_list_exposed": False,
            "holdout_accessed": False,
            "historical_materialization_authorized": False,
            "training_authorized": False,
            "automatic_model_promotion_authorized": False,
            "trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }


def build_analysis(
    *,
    catalog: Mapping[str, Any],
    previous_catalog: Mapping[str, Any] | None,
    catalog_config: Mapping[str, Any],
    observability_config: Mapping[str, Any],
) -> dict[str, Any]:
    validation = validate_catalog(catalog, catalog_config=catalog_config)
    if previous_catalog is not None:
        validate_catalog(previous_catalog, catalog_config=catalog_config)
    diff = compare_catalogs(
        catalog,
        previous_catalog,
        ratio_review_threshold=float(
            observability_config["validation"]["previous_count_ratio_review_threshold"]
        ),
    )
    actual_capacity = project_capacity(
        int(catalog["matched_market_count"]), config=observability_config
    )
    candidate_capacity = project_capacity(
        int(catalog["registry_candidate_count"]), config=observability_config
    )
    review_reasons = [*validation["review_reasons"], *diff["review_reasons"]]
    return {
        "schema": "pionex-alternative-assets-observability-report-v0.2",
        "status": "PASS" if not review_reasons else "REVIEW_REQUIRED",
        "provider": "pionex_public_futures",
        "observed_at_utc": catalog["retrieved_at_utc"],
        "catalog_validation": validation,
        "catalog_diff": diff,
        "capacity_actual": actual_capacity,
        "capacity_candidate_max": candidate_capacity,
        "review_reasons": review_reasons,
        "authority": {
            "metadata_only": True,
            "historical_materialization_authorized": False,
            "training_authorized": False,
            "automatic_model_promotion_authorized": False,
            "trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }


def build_objects(
    *,
    catalog: Mapping[str, Any],
    analysis: Mapping[str, Any],
    safe_projection: Mapping[str, Any],
    config: Mapping[str, Any],
    run_id: str,
) -> tuple[CatalogObject, ...]:
    if not run_id or len(run_id) > 96 or any(
        character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-"
        for character in run_id
    ):
        raise ValueError("run_id must be a safe 1-96 character object-key component")
    prefix = str(config["storage"]["catalog_runs_namespace"]).rstrip("/")
    run_prefix = f"{prefix}/run={run_id}"
    payloads = {
        "catalog": canonical_json_bytes(catalog),
        "analysis": canonical_json_bytes(analysis),
        "safe_projection": canonical_json_bytes(safe_projection),
    }
    keys = {role: f"{run_prefix}/{role}.json" for role in payloads}
    manifest = {
        "schema": "pionex-alternative-assets-observability-manifest-v0.2",
        "status": analysis["status"],
        "provider": "pionex_public_futures",
        "run_id": run_id,
        "generated_at_utc": catalog["retrieved_at_utc"],
        "objects": {
            role: {
                "key": keys[role],
                "sha256": sha256_bytes(payload),
                "bytes": len(payload),
            }
            for role, payload in payloads.items()
        },
        "metadata_only": True,
        "holdout_accessed": False,
    }
    manifest_payload = canonical_json_bytes(manifest)
    manifest_key = f"{run_prefix}/manifest.json"
    latest = {
        "schema": "pionex-alternative-assets-observability-latest-v0.2",
        "provider": "pionex_public_futures",
        "run_id": run_id,
        "generated_at_utc": catalog["retrieved_at_utc"],
        "manifest_key": manifest_key,
        "manifest_sha256": sha256_bytes(manifest_payload),
        "catalog_key": keys["catalog"],
        "catalog_sha256": sha256_bytes(payloads["catalog"]),
        "analysis_key": keys["analysis"],
        "analysis_sha256": sha256_bytes(payloads["analysis"]),
        "matched_market_count": catalog["matched_market_count"],
        "status": analysis["status"],
    }
    return (
        CatalogObject(keys["catalog"], payloads["catalog"], "application/json", True, "catalog"),
        CatalogObject(keys["analysis"], payloads["analysis"], "application/json", True, "analysis"),
        CatalogObject(
            keys["safe_projection"],
            payloads["safe_projection"],
            "application/json",
            True,
            "safe_projection",
        ),
        CatalogObject(manifest_key, manifest_payload, "application/json", True, "manifest"),
        CatalogObject(
            str(config["storage"]["catalog_latest_pointer_key"]),
            canonical_json_bytes(latest),
            "application/json",
            False,
            "latest_pointer",
        ),
    )


def publish_objects(
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
            raise PionexAlternativeAssetError(f"immutable observability conflict: {item.key}")
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
                        "version": "v0.2",
                    },
                )
            )
        restored = store.get_bytes_verified(item.key, expected_sha256=str(receipt["sha256"]))
        if restored != item.payload:
            raise PionexAlternativeAssetError(f"R2 exact-byte mismatch: {item.key}")
        receipts.append({"role": item.role, "action": action, **receipt})
    return {
        "status": "PASS",
        "stage": "PIONEX_ALTERNATIVE_ASSETS_OBSERVABILITY_PUBLISHED_V0_2",
        "current_bucket_bytes_before_write": current_bytes,
        "planned_write_bytes": planned,
        "hard_stop_bytes": hard_stop_bytes,
        "objects": receipts,
        "latest_pointer_written_last": objects[-1].role == "latest_pointer",
        "r2_writes_performed": any(item["action"] == "UPLOAD" for item in receipts),
        "replacement_holdout_accessed": False,
        "live_trading_authorized": False,
    }


def _decode_json(payload: bytes, *, role: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PionexAlternativeAssetError(f"invalid prior {role} JSON") from exc
    if not isinstance(value, dict):
        raise PionexAlternativeAssetError(f"prior {role} must be an object")
    return value


def load_previous_catalog(store: Any, *, config: Mapping[str, Any]) -> dict[str, Any] | None:
    pointer_key = str(config["storage"]["catalog_latest_pointer_key"])
    pointer_payload = store.get_bytes_if_exists(pointer_key)
    if pointer_payload is None:
        return None
    pointer = _decode_json(pointer_payload, role="latest pointer")
    if pointer.get("schema") != "pionex-alternative-assets-observability-latest-v0.2":
        raise PionexAlternativeAssetError("prior latest-pointer schema rejected")
    if pointer.get("provider") != "pionex_public_futures":
        raise PionexAlternativeAssetError("prior latest-pointer provider rejected")
    prefix = str(config["storage"]["catalog_runs_namespace"]).rstrip("/") + "/run="
    manifest_key = str(pointer.get("manifest_key") or "")
    catalog_key = str(pointer.get("catalog_key") or "")
    if not manifest_key.startswith(prefix) or not manifest_key.endswith("/manifest.json"):
        raise PionexAlternativeAssetError("prior manifest key is outside the V0.2 namespace")
    if not catalog_key.startswith(prefix) or not catalog_key.endswith("/catalog.json"):
        raise PionexAlternativeAssetError("prior catalog key is outside the V0.2 namespace")
    manifest_payload = store.get_bytes_verified(
        manifest_key, expected_sha256=str(pointer.get("manifest_sha256") or "")
    )
    manifest = _decode_json(manifest_payload, role="manifest")
    if manifest.get("schema") != "pionex-alternative-assets-observability-manifest-v0.2":
        raise PionexAlternativeAssetError("prior manifest schema rejected")
    catalog_record = (manifest.get("objects") or {}).get("catalog") or {}
    if catalog_record.get("key") != catalog_key:
        raise PionexAlternativeAssetError("prior manifest/catalog key mismatch")
    if catalog_record.get("sha256") != pointer.get("catalog_sha256"):
        raise PionexAlternativeAssetError("prior manifest/catalog SHA mismatch")
    catalog_payload = store.get_bytes_verified(
        catalog_key, expected_sha256=str(pointer.get("catalog_sha256") or "")
    )
    if len(catalog_payload) != int(catalog_record.get("bytes") or -1):
        raise PionexAlternativeAssetError("prior catalog byte count mismatch")
    return _decode_json(catalog_payload, role="catalog")
