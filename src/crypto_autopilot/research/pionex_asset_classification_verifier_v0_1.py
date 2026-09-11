"""Pure prepared-only Pionex asset-classification verification.

This module performs no network, R2, holdout, account, training, or trading I/O.
It consumes an already-produced Pionex universe report, the frozen alternative-
asset registry bytes, and caller-supplied CoinPaprika /coins bytes.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Mapping
from typing import Any


class AssetClassificationRejected(ValueError):
    pass


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _load_object(payload: bytes, *, label: str) -> Mapping[str, Any]:
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AssetClassificationRejected(f"{label} must be valid UTF-8 JSON") from exc
    if not isinstance(decoded, Mapping):
        raise AssetClassificationRejected(f"{label} must be a JSON object")
    return decoded


def _load_list(payload: bytes, *, label: str) -> list[Any]:
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AssetClassificationRejected(f"{label} must be valid UTF-8 JSON") from exc
    if not isinstance(decoded, list):
        raise AssetClassificationRejected(f"{label} must be a JSON array")
    return decoded


def _registry_map(config: Mapping[str, Any]) -> dict[str, str]:
    registry = config.get("registry")
    if not isinstance(registry, Mapping):
        raise AssetClassificationRejected("alternative registry is missing")
    output: dict[str, str] = {}
    for asset_class, values in registry.items():
        if not isinstance(values, list):
            raise AssetClassificationRejected("alternative registry class must be a list")
        for value in values:
            base = str(value)
            if base != base.upper() or not base.isascii() or not base.isalnum():
                raise AssetClassificationRejected(f"unsafe alternative base asset: {base!r}")
            previous = output.setdefault(base, str(asset_class))
            if previous != str(asset_class):
                raise AssetClassificationRejected(f"alternative registry overlap: {base}")
    return output


def validate_config(
    config: Mapping[str, Any], *, alternative_registry_bytes: bytes
) -> dict[str, str]:
    if config.get("schema") != "pionex-asset-classification-verifier-v0.1":
        raise AssetClassificationRejected("unexpected verifier schema")
    if config.get("version") != "0.1.0":
        raise AssetClassificationRejected("unexpected verifier version")
    if config.get("status") != "PREPARED_NOT_EXECUTION_AUTHORITY":
        raise AssetClassificationRejected("verifier must remain prepared-only")

    inputs = config.get("inputs")
    if not isinstance(inputs, Mapping):
        raise AssetClassificationRejected("inputs contract missing")
    if inputs.get("universe_report_schema") != "pionex-research-universe-run-report-v0.1":
        raise AssetClassificationRejected("universe report schema changed")
    if inputs.get("universe_provider") != "pionex_public_futures":
        raise AssetClassificationRejected("universe provider changed")
    if inputs.get("alternative_registry") != "config/pionex_alternative_assets_v0_1.json":
        raise AssetClassificationRejected("alternative registry path changed")
    if inputs.get("alternative_registry_sha256") != _sha256(alternative_registry_bytes):
        raise AssetClassificationRejected("alternative registry SHA-256 mismatch")
    if inputs.get("crypto_registry_provider") != "coinpaprika":
        raise AssetClassificationRejected("crypto registry provider changed")
    if inputs.get("crypto_registry_endpoint") != "https://api.coinpaprika.com/v1/coins":
        raise AssetClassificationRejected("CoinPaprika endpoint changed")
    if inputs.get("crypto_registry_authentication_required") is not False:
        raise AssetClassificationRejected("prepared verifier must not require authentication")
    if inputs.get("crypto_registry_expected_types") != ["coin", "token"]:
        raise AssetClassificationRejected("CoinPaprika type contract changed")

    policy = config.get("classification_policy")
    expected_policy = {
        "alternative_registry_match": "VERIFIED_ALTERNATIVE",
        "unique_active_coinpaprika_symbol_match": "VERIFIED_CRYPTO",
        "zero_active_coinpaprika_symbol_matches": "UNRESOLVED",
        "multiple_active_coinpaprika_symbol_matches": "UNRESOLVED",
        "inactive_coinpaprika_entries_are_evidence": False,
        "universe_fallback_crypto_label_is_evidence": False,
        "alternative_registry_precedence_over_crypto_registry": True,
        "symbol_matching_case": "ASCII_UPPERCASE_EXACT",
        "partial_classification_promotes_full_readiness": False,
    }
    if policy != expected_policy:
        raise AssetClassificationRejected("classification policy changed")

    prepared = config.get("prepared_execution_shape")
    if not isinstance(prepared, Mapping):
        raise AssetClassificationRejected("prepared execution shape missing")
    expected_prepared = {
        "provider_request_count": 1,
        "automatic_retries": 0,
        "metadata_only": True,
        "raw_provider_payload_persistence_authorized": False,
        "r2_read_authorized": False,
        "r2_write_authorized": False,
        "github_actions_main_only_if_later_authorized": True,
        "workflow_dispatch_only_if_later_authorized": True,
        "workflow_included_by_this_stage": False,
    }
    if prepared != expected_prepared:
        raise AssetClassificationRejected("prepared execution shape changed")

    output = config.get("output_contract")
    if output != {
        "authority": False,
        "include_per_market_classification": True,
        "include_unresolved_symbols": True,
        "include_coinpaprika_payload_sha256": True,
        "all_selected_markets_verified_required_to_clear_blocker": True,
    }:
        raise AssetClassificationRejected("output contract changed")

    authority = config.get("authority")
    if not isinstance(authority, Mapping):
        raise AssetClassificationRejected("authority contract missing")
    if authority.get("fixture_validation") is not True:
        raise AssetClassificationRejected("fixture validation must remain enabled")
    if any(value is not False for key, value in authority.items() if key != "fixture_validation"):
        raise AssetClassificationRejected("prepared verifier unexpectedly grants execution authority")

    alternative = _load_object(alternative_registry_bytes, label="alternative registry")
    return _registry_map(alternative)


def _coinpaprika_index(payload: bytes) -> dict[str, list[dict[str, str]]]:
    rows = _load_list(payload, label="CoinPaprika /coins payload")
    seen_ids: set[str] = set()
    index: dict[str, list[dict[str, str]]] = defaultdict(list)
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise AssetClassificationRejected("CoinPaprika row must be an object")
        coin_id = raw.get("id")
        symbol = raw.get("symbol")
        active = raw.get("is_active")
        coin_type = raw.get("type")
        if not isinstance(coin_id, str) or not coin_id:
            raise AssetClassificationRejected("CoinPaprika id must be non-empty")
        if coin_id in seen_ids:
            raise AssetClassificationRejected(f"duplicate CoinPaprika id: {coin_id}")
        seen_ids.add(coin_id)
        if not isinstance(symbol, str) or not symbol:
            raise AssetClassificationRejected(f"CoinPaprika symbol missing for {coin_id}")
        normalized = symbol.upper()
        if normalized != symbol or not normalized.isascii() or not normalized.isalnum():
            raise AssetClassificationRejected(f"unsafe CoinPaprika symbol: {symbol!r}")
        if not isinstance(active, bool):
            raise AssetClassificationRejected(f"CoinPaprika is_active invalid for {coin_id}")
        if coin_type not in {"coin", "token"}:
            raise AssetClassificationRejected(f"CoinPaprika type invalid for {coin_id}")
        if active:
            index[normalized].append({"id": coin_id, "type": str(coin_type)})
    return dict(index)


def verify_selected_market_classification(
    config: Mapping[str, Any],
    *,
    alternative_registry_bytes: bytes,
    universe_report: Mapping[str, Any],
    coinpaprika_payload: bytes,
) -> dict[str, object]:
    alternative_map = validate_config(
        config, alternative_registry_bytes=alternative_registry_bytes
    )
    if universe_report.get("schema") != config["inputs"]["universe_report_schema"]:
        raise AssetClassificationRejected("unexpected universe report schema")
    if universe_report.get("status") != "PASS":
        raise AssetClassificationRejected("universe report must be PASS")
    if universe_report.get("provider") != config["inputs"]["universe_provider"]:
        raise AssetClassificationRejected("universe report provider changed")
    markets = universe_report.get("markets")
    if not isinstance(markets, list) or not markets:
        raise AssetClassificationRejected("universe report markets missing")
    declared_count = universe_report.get("selected_market_count")
    if not isinstance(declared_count, int) or declared_count != len(markets):
        raise AssetClassificationRejected("selected market count mismatch")

    crypto_index = _coinpaprika_index(coinpaprika_payload)
    seen_symbols: set[str] = set()
    rows: list[dict[str, object]] = []
    unresolved: list[str] = []

    for market in markets:
        if not isinstance(market, Mapping):
            raise AssetClassificationRejected("universe market must be an object")
        symbol = market.get("symbol")
        base = market.get("base_asset")
        fallback = market.get("asset_class")
        if not isinstance(symbol, str) or symbol != symbol.upper() or not symbol.isascii():
            raise AssetClassificationRejected("universe symbol must be ASCII uppercase")
        if symbol in seen_symbols:
            raise AssetClassificationRejected(f"duplicate universe symbol: {symbol}")
        seen_symbols.add(symbol)
        if not isinstance(base, str) or base != base.upper() or not base.isascii() or not base.isalnum():
            raise AssetClassificationRejected(f"unsafe universe base asset: {base!r}")

        alternative_class = alternative_map.get(base)
        if alternative_class is not None:
            row = {
                "symbol": symbol,
                "base_asset": base,
                "state": "VERIFIED_ALTERNATIVE",
                "asset_class": alternative_class,
                "evidence": "PIONEX_ALTERNATIVE_REGISTRY",
                "universe_fallback_asset_class": fallback,
                "universe_fallback_used_as_evidence": False,
            }
        else:
            candidates = crypto_index.get(base, [])
            if len(candidates) == 1:
                candidate = candidates[0]
                row = {
                    "symbol": symbol,
                    "base_asset": base,
                    "state": "VERIFIED_CRYPTO",
                    "asset_class": "crypto",
                    "evidence": "COINPAPRIKA_UNIQUE_ACTIVE_SYMBOL",
                    "coinpaprika_id": candidate["id"],
                    "coinpaprika_type": candidate["type"],
                    "universe_fallback_asset_class": fallback,
                    "universe_fallback_used_as_evidence": False,
                }
            else:
                reason = (
                    "NO_ACTIVE_COINPAPRIKA_SYMBOL_MATCH"
                    if not candidates
                    else "AMBIGUOUS_ACTIVE_COINPAPRIKA_SYMBOL"
                )
                row = {
                    "symbol": symbol,
                    "base_asset": base,
                    "state": "UNRESOLVED",
                    "asset_class": None,
                    "reason": reason,
                    "candidate_ids": [candidate["id"] for candidate in candidates],
                    "universe_fallback_asset_class": fallback,
                    "universe_fallback_used_as_evidence": False,
                }
                unresolved.append(symbol)
        rows.append(row)

    verified_alternative = sum(row["state"] == "VERIFIED_ALTERNATIVE" for row in rows)
    verified_crypto = sum(row["state"] == "VERIFIED_CRYPTO" for row in rows)
    all_verified = not unresolved and len(rows) == len(markets)
    return {
        "schema": "pionex-asset-classification-verification-result-v0.1",
        "status": "PASS" if all_verified else "REVIEW_REQUIRED",
        "authority": False,
        "selected_market_count": len(rows),
        "verified_crypto_count": verified_crypto,
        "verified_alternative_count": verified_alternative,
        "unresolved_count": len(unresolved),
        "unresolved_symbols": unresolved,
        "all_selected_markets_verified": all_verified,
        "full_simulation_readiness_cleared_by_this_result": False,
        "universe_fallback_crypto_labels_used_as_evidence": False,
        "coinpaprika_payload_sha256": _sha256(coinpaprika_payload),
        "classifications": rows,
        "safety_boundary": {
            "provider_fetch_authorized": False,
            "r2_read_authorized": False,
            "r2_write_authorized": False,
            "universe_membership_change_authorized": False,
            "holdout_access_authorized": False,
            "training_authorized": False,
            "automatic_model_promotion_authorized": False,
            "strategy_change_authorized": False,
            "source_switch_authorized": False,
            "trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }
