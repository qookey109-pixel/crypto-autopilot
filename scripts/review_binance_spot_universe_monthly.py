from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from crypto_autopilot.storage.ephemeral import require_ephemeral_output
from crypto_autopilot.training.monthly_universe_review import (
    build_monthly_universe_objects,
    build_monthly_universe_review,
)
from crypto_autopilot.training.online_r2 import publish_online_objects
from crypto_autopilot.storage.r2 import R2Store
from crypto_autopilot.training.quality import (
    TrainingQualityError,
    V0_3_BASELINE_EVIDENCE_SHA256,
    load_v0_3_bootstrap_baseline,
    load_v0_5_authority_pair,
    validate_catalog_quality,
    validate_monthly_review_contract,
)


_PROVIDER = "binance_spot"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,96}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_EXECUTION_MODES = {
    "local": "LOCAL_DRY_RUN",
    "schedule": "SCHEDULED_REVIEW",
    "workflow_dispatch": "ONE_TIME_MANUAL_WORKFLOW_DISPATCH",
}
_MONTHLY_INTERPRETATION = (
    "Monthly active-catalog and heuristic-classification review only. "
    "A missing symbol is not labeled as delisted without separate provider evidence."
)
_MONTHLY_REVIEW_AUTHORITY_FIELDS = (
    "formal_delisting_determination_authorized",
    "historical_universe_membership_authorized",
    "formal_backtest_admission_authorized",
    "automatic_model_promotion_authorized",
    "automatic_trade_plan_authorized",
    "real_money_order_authorized",
    "live_trading_authorized",
)


def required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required GitHub Actions R2 secret is missing: {name}")
    return value


def utc_now() -> datetime:
    return datetime.now(UTC)


def _require_online_write_window(config: dict[str, object]) -> None:
    schedule = config.get("schedule")
    if not isinstance(schedule, dict):
        raise TrainingQualityError("V0.5 online write schedule is missing")
    stop = datetime.fromisoformat(
        str(schedule["provider_read_stop_utc"]).replace("Z", "+00:00")
    )
    if utc_now() >= stop:
        raise TrainingQualityError("V0.5 online write window is closed")


def _validate_execution_route(
    *, event_name: str, activation_mode: str, dry_run: bool
) -> dict[str, object]:
    expected_mode = _EXECUTION_MODES.get(event_name)
    if expected_mode is None:
        raise TrainingQualityError("unsupported V0.5 monthly workflow event")
    if activation_mode != expected_mode:
        raise TrainingQualityError("V0.5 monthly event and activation mode mismatch")
    if event_name == "local" and not dry_run:
        raise TrainingQualityError("local V0.5 monthly execution must be a dry run")
    return {
        "event_name": event_name,
        "activation_mode": activation_mode,
        "manual_activation": event_name == "workflow_dispatch",
    }


def _require_utc_timestamp(value: object, label: str) -> datetime:
    try:
        if not isinstance(value, str) or not value.endswith("Z"):
            raise ValueError("timestamp must use the Z suffix")
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
            raise ValueError("timestamp must be UTC")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a valid UTC timestamp") from exc
    return parsed


def _catalog_snapshot(catalog: dict[str, object]) -> dict[str, dict[str, str]]:
    markets = catalog.get("markets")
    if not isinstance(markets, list):
        raise ValueError("monthly previous catalog markets must be a list")
    try:
        return {
            str(item["symbol"]): {
                "base_asset": str(item["base_asset"]),
                "quote_asset": str(item["quote_asset"]),
                "asset_class": str(item["asset_class"]),
                "classification_method": str(item["classification_method"]),
                "classification_confidence": str(
                    item["classification_confidence"]
                ),
            }
            for item in markets
            if isinstance(item, dict)
        }
    except KeyError as exc:
        raise ValueError("monthly previous catalog snapshot contract mismatch") from exc


def _validate_comparison_baseline(
    baseline: object,
    *,
    config: dict[str, object],
    namespace: str,
    current_review_key: str,
) -> None:
    expected_fields = {
        "source",
        "reference",
        "sha256",
        "market_count",
        "bootstrap_used",
    }
    if not isinstance(baseline, dict) or set(baseline) != expected_fields:
        raise ValueError("monthly previous comparison baseline structure mismatch")
    market_count = baseline.get("market_count")
    policy = config.get("data_quality")
    minimum_market_count = (
        policy.get("minimum_catalog_market_count") if isinstance(policy, dict) else None
    )
    if (
        isinstance(market_count, bool)
        or not isinstance(market_count, int)
        or isinstance(minimum_market_count, bool)
        or not isinstance(minimum_market_count, int)
        or market_count < minimum_market_count
    ):
        raise ValueError("monthly previous comparison baseline market count is unsafe")
    sha256 = baseline.get("sha256")
    if not isinstance(sha256, str) or not _SHA256_RE.fullmatch(sha256):
        raise ValueError("monthly previous comparison baseline SHA-256 is invalid")

    source = baseline.get("source")
    reference = baseline.get("reference")
    bootstrap_used = baseline.get("bootstrap_used")
    if source == "FROZEN_V0_3_PASS_RECEIPT":
        data_quality = config.get("data_quality")
        if (
            not isinstance(data_quality, dict)
            or reference != data_quality.get("baseline_evidence")
            or sha256 != V0_3_BASELINE_EVIDENCE_SHA256
            or market_count != 748
            or bootstrap_used is not True
        ):
            raise ValueError("monthly previous frozen comparison baseline mismatch")
        return
    if source == "PREVIOUS_V0_5_MONTHLY_REVIEW":
        if not isinstance(reference, str):
            raise ValueError("monthly previous comparison reference is invalid")
        prefix = f"{namespace}/runs/run="
        suffix = "/universe-review.json"
        if not reference.startswith(prefix) or not reference.endswith(suffix):
            raise ValueError("monthly previous comparison reference is outside namespace")
        run_id = reference[len(prefix) : -len(suffix)]
        if (
            not _RUN_ID_RE.fullmatch(run_id)
            or reference != f"{prefix}{run_id}{suffix}"
            or reference == current_review_key
            or bootstrap_used is not False
        ):
            raise ValueError("monthly previous comparison reference is unsafe")
        return
    raise ValueError("monthly previous comparison baseline source is invalid")


def _previous_review(
    store: R2Store,
    config: dict[str, object],
    *,
    governance_contract: dict[str, object] | None = None,
    before_access: Callable[[], None] | None = None,
) -> dict | None:
    if config.get("provider") != _PROVIDER:
        raise ValueError("monthly review config provider must be binance_spot")
    monthly = config.get("monthly_universe_review")
    if not isinstance(monthly, dict):
        raise ValueError("monthly_universe_review config must be an object")
    namespace = str(monthly.get("namespace") or "").rstrip("/")
    schema_version = str(monthly.get("schema_version", "v0.4"))
    if schema_version not in {"v0.4", "v0.5"}:
        raise ValueError("unsupported monthly review schema version")
    latest_schema = f"binance-spot-monthly-universe-review-latest-{schema_version}"
    review_schema = f"binance-spot-monthly-universe-review-{schema_version}"
    if not namespace:
        raise ValueError("monthly universe review namespace is required")
    latest_key = str(monthly.get("latest_pointer_key") or "")
    if latest_key != f"{namespace}/latest.json":
        raise ValueError("monthly latest pointer must be inside the configured namespace")

    if before_access is not None:
        before_access()
    latest_payload = store.get_bytes_if_exists(latest_key)
    if latest_payload is None:
        return None
    latest = json.loads(latest_payload)
    if not isinstance(latest, dict):
        raise ValueError("monthly latest pointer must be a JSON object")
    if latest.get("schema") != latest_schema:
        raise ValueError("monthly latest pointer schema mismatch")
    if latest.get("provider") != _PROVIDER:
        raise ValueError("monthly latest pointer provider mismatch")

    run_id = latest.get("run_id")
    if not isinstance(run_id, str) or not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("monthly latest pointer run_id is invalid")
    review_key = latest.get("review_key")
    expected_review_key = f"{namespace}/runs/run={run_id}/universe-review.json"
    if review_key != expected_review_key:
        raise ValueError("monthly previous review key is outside the authorized run namespace")
    review_sha256 = latest.get("review_sha256")
    if not isinstance(review_sha256, str) or not _SHA256_RE.fullmatch(review_sha256):
        raise ValueError("monthly previous review SHA-256 is invalid")

    catalog: dict[str, object] | None = None
    catalog_key: str | None = None
    catalog_sha256: str | None = None
    if schema_version == "v0.5":
        if not isinstance(governance_contract, dict):
            raise ValueError("V0.5 previous review requires current governance contract")
        catalog_key = latest.get("catalog_key")
        expected_catalog_key = f"{namespace}/runs/run={run_id}/market-catalog.json"
        if catalog_key != expected_catalog_key:
            raise ValueError(
                "monthly previous catalog key is outside the authorized run namespace"
            )
        catalog_sha256 = latest.get("catalog_sha256")
        if not isinstance(catalog_sha256, str) or not _SHA256_RE.fullmatch(
            catalog_sha256
        ):
            raise ValueError("monthly previous catalog SHA-256 is invalid")
        if before_access is not None:
            before_access()
        catalog_payload = store.get_bytes_verified(
            catalog_key,
            expected_sha256=catalog_sha256,
        )
        if hashlib.sha256(catalog_payload).hexdigest() != catalog_sha256:
            raise ValueError("monthly previous catalog SHA-256 mismatch")
        catalog = json.loads(catalog_payload)
        if not isinstance(catalog, dict):
            raise ValueError("monthly previous catalog must be a JSON object")
        policy = config.get("data_quality")
        if not isinstance(policy, dict):
            raise ValueError("monthly previous catalog policy is missing")
        validate_catalog_quality(catalog, policy=policy)

    if before_access is not None:
        before_access()
    review_payload = store.get_bytes_verified(
        review_key,
        expected_sha256=review_sha256,
    )
    if hashlib.sha256(review_payload).hexdigest() != review_sha256:
        raise ValueError("monthly previous review SHA-256 mismatch")
    review = json.loads(review_payload)
    if not isinstance(review, dict):
        raise ValueError("monthly previous review must be a JSON object")
    if review.get("schema") != review_schema:
        raise ValueError("monthly previous review schema mismatch")
    if review.get("provider") != _PROVIDER:
        raise ValueError("monthly previous review provider mismatch")
    snapshot = review.get("market_snapshot")
    market_count = review.get("market_count")
    if (
        review.get("status") != "PASS"
        or review.get("mode") != "RESEARCH_CATALOG_REVIEW_ONLY"
        or not isinstance(snapshot, dict)
        or isinstance(market_count, bool)
        or not isinstance(market_count, int)
        or market_count < 0
        or market_count != len(snapshot)
    ):
        raise ValueError("monthly previous review evidence contract mismatch")
    review_authority = review.get("authority")
    if not isinstance(review_authority, dict):
        raise ValueError("monthly previous review authority is missing")
    for key in _MONTHLY_REVIEW_AUTHORITY_FIELDS:
        if review_authority.get(key) is not False:
            raise ValueError(f"unsafe monthly previous review authority: {key}")
    if schema_version == "v0.5":
        assert catalog is not None
        assert catalog_key is not None
        assert catalog_sha256 is not None
        latest_generated = latest.get("generated_at_utc")
        review_generated = review.get("generated_at_utc")
        generated_at = _require_utc_timestamp(
            latest_generated, "monthly latest generated_at_utc"
        )
        if review_generated != latest_generated:
            raise ValueError("monthly latest and review timestamps do not match")
        _require_utc_timestamp(
            review_generated, "monthly previous review generated_at_utc"
        )
        catalog_retrieved = catalog.get("retrieved_at_utc")
        retrieved_at = _require_utc_timestamp(
            catalog_retrieved, "monthly previous catalog retrieved_at_utc"
        )
        if retrieved_at > generated_at:
            raise ValueError("monthly previous catalog timestamp is after review")

        expected_snapshot = _catalog_snapshot(catalog)
        expected_asset_counts = dict(
            sorted(
                Counter(
                    item["asset_class"] for item in expected_snapshot.values()
                ).items()
            )
        )
        expected_quote_counts = dict(
            sorted(
                Counter(
                    item["quote_asset"] for item in expected_snapshot.values()
                ).items()
            )
        )
        if (
            review.get("current_catalog_retrieved_at_utc") != catalog_retrieved
            or review.get("market_snapshot") != expected_snapshot
            or review.get("market_count") != len(expected_snapshot)
            or review.get("asset_class_counts") != expected_asset_counts
            or review.get("quote_asset_counts") != expected_quote_counts
            or review.get("interpretation") != _MONTHLY_INTERPRETATION
            or not isinstance(review.get("baseline_created"), bool)
        ):
            raise ValueError("monthly previous review does not match its catalog")
        if review.get("survivorship_bias_review") != {
            "status": "REVIEW_REQUIRED",
            "current_active_catalog_can_reconstruct_historical_membership": False,
            "absence_from_current_catalog_is_delisting_proof": False,
            "listing_or_delisting_claims_made": False,
            "historical_universe_membership_authorized": False,
        }:
            raise ValueError("monthly previous review survivorship boundary mismatch")
        governance = review.get("governance")
        if (
            not isinstance(governance, dict)
            or set(governance) != {"config", "comparison_baseline"}
            or governance.get("config") != governance_contract
        ):
            raise ValueError("monthly previous review governance config mismatch")
        _validate_comparison_baseline(
            governance.get("comparison_baseline"),
            config=config,
            namespace=namespace,
            current_review_key=review_key,
        )
        review["_verified_catalog_key"] = catalog_key
        review["_verified_catalog_sha256"] = catalog_sha256
    review["_verified_review_key"] = review_key
    review["_verified_review_sha256"] = review_sha256
    return review


def main() -> int:
    parser = argparse.ArgumentParser(description="Review Binance Spot universe monthly and publish to R2")
    parser.add_argument("--config", default="config/binance_spot_r2_training_governance_v0_5.json")
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID") or "local")
    parser.add_argument("--review-output", required=True)
    parser.add_argument("--receipt-output", required=True)
    parser.add_argument(
        "--event-name",
        default=os.getenv("GITHUB_EVENT_NAME") or "local",
    )
    parser.add_argument(
        "--activation-mode",
        default=os.getenv("V0_5_MONTHLY_ACTIVATION_MODE") or "LOCAL_DRY_RUN",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    review_output = require_ephemeral_output(args.review_output)
    receipt_output = require_ephemeral_output(args.receipt_output)

    config_path = Path(args.config)
    config_payload = config_path.read_bytes()
    config = json.loads(config_payload)
    _, governance_contract = load_v0_5_authority_pair(
        config,
        config_path=config_path,
        config_payload=config_payload,
        repository_root=REPOSITORY_ROOT,
    )
    execution_route = _validate_execution_route(
        event_name=args.event_name,
        activation_mode=args.activation_mode,
        dry_run=args.dry_run,
    )
    bootstrap_baseline = load_v0_3_bootstrap_baseline(
        config,
        repository_root=REPOSITORY_ROOT,
    )

    catalog_payload = Path(args.catalog).read_bytes()
    catalog = json.loads(catalog_payload)
    data_quality_policy = config.get("data_quality")
    catalog_quality = None
    if data_quality_policy is not None:
        catalog_quality = validate_catalog_quality(catalog, policy=data_quality_policy)

    store = None
    previous = None
    comparison_baseline: dict[str, object]
    if not args.dry_run:
        _require_online_write_window(config)
        store = R2Store(
            account_id=required("CLOUDFLARE_ACCOUNT_ID"),
            bucket=required("R2_BUCKET_NAME"),
            access_key_id=required("R2_ACCESS_KEY_ID"),
            secret_access_key=required("R2_SECRET_ACCESS_KEY"),
        )
        previous = _previous_review(
            store,
            config,
            governance_contract=governance_contract,
            before_access=lambda: _require_online_write_window(config),
        )
        if previous is None and not execution_route["manual_activation"]:
            raise TrainingQualityError(
                "V0.5 monthly baseline requires the authorized manual activation"
            )
        if execution_route["manual_activation"] and previous is not None:
            raise TrainingQualityError(
                "V0.5 monthly manual activation already completed"
            )
        if data_quality_policy is not None:
            previous_market_count = (
                int(previous["market_count"])
                if previous is not None
                else int(bootstrap_baseline["dataset"]["market_count_requested"])
            )
            catalog_quality = validate_catalog_quality(
                catalog,
                policy=data_quality_policy,
                previous_market_count=previous_market_count,
            )
        comparison_baseline = {
            "source": (
                "PREVIOUS_V0_5_MONTHLY_REVIEW"
                if previous is not None
                else "FROZEN_V0_3_PASS_RECEIPT"
            ),
            "reference": (
                previous["_verified_review_key"]
                if previous is not None
                else config["data_quality"]["baseline_evidence"]
            ),
            "sha256": (
                previous["_verified_review_sha256"]
                if previous is not None
                else V0_3_BASELINE_EVIDENCE_SHA256
            ),
            "market_count": previous_market_count,
            "bootstrap_used": previous is None,
        }
    else:
        previous_market_count = int(
            bootstrap_baseline["dataset"]["market_count_requested"]
        )
        if data_quality_policy is not None:
            catalog_quality = validate_catalog_quality(
                catalog,
                policy=data_quality_policy,
                previous_market_count=previous_market_count,
            )
        comparison_baseline = {
            "source": "FROZEN_V0_3_PASS_RECEIPT",
            "reference": config["data_quality"]["baseline_evidence"],
            "sha256": V0_3_BASELINE_EVIDENCE_SHA256,
            "market_count": previous_market_count,
            "bootstrap_used": True,
        }
    generated = utc_now().isoformat().replace("+00:00", "Z")
    monthly_config = config["monthly_universe_review"]
    schema_version = str(monthly_config.get("schema_version", "v0.4"))
    review = build_monthly_universe_review(
        catalog,
        previous_review=previous,
        generated_at_utc=generated,
        schema_version=schema_version,
    )
    review["governance"] = {
        "config": governance_contract,
        "comparison_baseline": comparison_baseline,
    }
    monthly_review_contract = validate_monthly_review_contract(
        review,
        catalog=catalog,
        previous_review=previous,
        governance_contract=governance_contract,
        comparison_baseline=comparison_baseline,
        expected_generated_at_utc=generated,
    )
    review_payload = (json.dumps(review, ensure_ascii=False, indent=2) + "\n").encode()
    objects = build_monthly_universe_objects(
        config=config,
        run_id=args.run_id,
        catalog=catalog_payload,
        review=review_payload,
        generated_at_utc=generated,
    )
    if args.dry_run:
        result = {
            "status": "PREPARED",
            "stage": f"BINANCE_SPOT_MONTHLY_UNIVERSE_REVIEW_DRY_RUN_{schema_version.upper()}",
            "r2_client_constructed": False,
            "r2_writes_performed": False,
            "objects": [
                {"role": item.role, "key": item.key, "bytes": len(item.payload)}
                for item in objects
            ],
        }
    else:
        assert store is not None
        result = publish_online_objects(
            store=store,
            objects=objects,
            hard_stop_bytes=int(config["storage"]["free_only_hard_stop_bytes"]),
            pass_stage=f"BINANCE_SPOT_MONTHLY_UNIVERSE_REVIEW_PUBLISHED_{schema_version.upper()}",
            metadata_version=schema_version,
            before_access=lambda: _require_online_write_window(config),
            before_write=lambda: _require_online_write_window(config),
        )
    result.update(
        {
            "generated_at_utc": generated,
            "run_id": args.run_id,
            "provider": "binance_spot",
            "execution_route": execution_route,
            "governance_contract": governance_contract,
            "monthly_review_contract": monthly_review_contract,
            "comparison_baseline": comparison_baseline,
            "baseline_created": review["baseline_created"],
            "market_count": review["market_count"],
            "catalog_quality_gate": catalog_quality,
            "historical_universe_membership_authorized": False,
            "formal_backtest_admission_authorized": False,
            "automatic_model_promotion_authorized": False,
            "automatic_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        }
    )
    review_output.parent.mkdir(parents=True, exist_ok=True)
    review_output.write_bytes(review_payload)
    receipt_output.parent.mkdir(parents=True, exist_ok=True)
    receipt_output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": result["status"], "markets": review["market_count"]}))
    return 0 if result["status"] in {"PASS", "PREPARED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
