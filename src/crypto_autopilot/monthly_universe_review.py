from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .online_r2_training import OnlineObject, json_bytes, sha256_bytes


_RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,96}$")


def _market_snapshot(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item["symbol"]): {
            "base_asset": str(item["base_asset"]),
            "quote_asset": str(item["quote_asset"]),
            "asset_class": str(item["asset_class"]),
            "classification_method": str(item["classification_method"]),
            "classification_confidence": str(item["classification_confidence"]),
        }
        for item in catalog.get("markets", [])
    }


def build_monthly_universe_review(
    current_catalog: dict[str, Any],
    *,
    previous_review: dict[str, Any] | None,
    generated_at_utc: str,
    schema_version: str = "v0.4",
) -> dict[str, Any]:
    if schema_version not in {"v0.4", "v0.5"}:
        raise ValueError("unsupported monthly universe review schema version")
    current = _market_snapshot(current_catalog)
    baseline_created = previous_review is None
    previous = (previous_review or {}).get("market_snapshot") or {}
    current_symbols = set(current)
    previous_symbols = set(previous)
    added = [] if baseline_created else sorted(current_symbols - previous_symbols)
    absent = [] if baseline_created else sorted(previous_symbols - current_symbols)
    classification_changes = []
    for symbol in sorted(current_symbols & previous_symbols):
        before = previous[symbol]
        after = current[symbol]
        if (
            before.get("asset_class") != after["asset_class"]
            or before.get("classification_method") != after["classification_method"]
        ):
            classification_changes.append(
                {
                    "symbol": symbol,
                    "previous_asset_class": before.get("asset_class"),
                    "current_asset_class": after["asset_class"],
                    "previous_method": before.get("classification_method"),
                    "current_method": after["classification_method"],
                }
            )
    tokenized = sorted(
        symbol
        for symbol, item in current.items()
        if item["asset_class"] == "tokenized_stock_candidate"
    )
    previous_tokenized = (
        set(tokenized)
        if baseline_created
        else {
            symbol
            for symbol, item in previous.items()
            if item.get("asset_class") == "tokenized_stock_candidate"
        }
    )
    return {
        "schema": f"binance-spot-monthly-universe-review-{schema_version}",
        "status": "PASS",
        "mode": "RESEARCH_CATALOG_REVIEW_ONLY",
        "provider": "binance_spot",
        "generated_at_utc": generated_at_utc,
        "current_catalog_retrieved_at_utc": current_catalog.get("retrieved_at_utc"),
        "baseline_created": baseline_created,
        "market_count": len(current),
        "asset_class_counts": dict(
            sorted(Counter(item["asset_class"] for item in current.values()).items())
        ),
        "quote_asset_counts": dict(
            sorted(Counter(item["quote_asset"] for item in current.values()).items())
        ),
        "added_since_previous_monthly_review": added,
        "absent_from_current_active_catalog": absent,
        "classification_changes": classification_changes,
        "tokenized_stock_candidates": {
            "count": len(tokenized),
            "symbols": tokenized,
            "added": sorted(set(tokenized) - previous_tokenized),
            "removed": sorted(previous_tokenized - set(tokenized)),
            "classification_is_heuristic": True,
        },
        "survivorship_bias_review": {
            "status": "REVIEW_REQUIRED",
            "current_active_catalog_can_reconstruct_historical_membership": False,
            "absence_from_current_catalog_is_delisting_proof": False,
            "listing_or_delisting_claims_made": False,
            "historical_universe_membership_authorized": False,
        },
        "market_snapshot": current,
        "authority": {
            "formal_delisting_determination_authorized": False,
            "historical_universe_membership_authorized": False,
            "formal_backtest_admission_authorized": False,
            "automatic_model_promotion_authorized": False,
            "automatic_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
        "interpretation": (
            "Monthly active-catalog and heuristic-classification review only. "
            "A missing symbol is not labeled as delisted without separate provider evidence."
        ),
    }


def build_monthly_universe_objects(
    *,
    config: dict[str, Any],
    run_id: str,
    catalog: bytes,
    review: bytes,
    generated_at_utc: str,
) -> tuple[OnlineObject, ...]:
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("run_id must be a safe 1-96 character object-key component")
    monthly = config["monthly_universe_review"]
    schema_version = str(monthly.get("schema_version", "v0.4"))
    if schema_version not in {"v0.4", "v0.5"}:
        raise ValueError("unsupported monthly universe object schema version")
    prefix = str(monthly["namespace"]).rstrip("/")
    run_prefix = f"{prefix}/runs/run={run_id}"
    catalog_object = OnlineObject(
        f"{run_prefix}/market-catalog.json",
        catalog,
        "application/json",
        True,
        "monthly_catalog",
    )
    review_object = OnlineObject(
        f"{run_prefix}/universe-review.json",
        review,
        "application/json",
        True,
        "monthly_universe_review",
    )
    latest = {
        "schema": f"binance-spot-monthly-universe-review-latest-{schema_version}",
        "provider": "binance_spot",
        "run_id": run_id,
        "generated_at_utc": generated_at_utc,
        "catalog_key": catalog_object.key,
        "catalog_sha256": sha256_bytes(catalog),
        "review_key": review_object.key,
        "review_sha256": sha256_bytes(review),
    }
    latest_object = OnlineObject(
        str(monthly["latest_pointer_key"]),
        json_bytes(latest),
        "application/json",
        False,
        "latest_pointer",
    )
    return catalog_object, review_object, latest_object
