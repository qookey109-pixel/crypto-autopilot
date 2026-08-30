#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from crypto_autopilot.exchanges.pionex_public import PionexPublicClient
from crypto_autopilot.providers.pionex_alternative_assets import (
    PionexAlternativeAssetError,
    build_catalog,
    canonical_json_bytes,
    sha256_bytes,
)
from crypto_autopilot.providers.pionex_alternative_assets_observability import (
    build_analysis,
    build_objects,
    build_safe_projection,
    load_previous_catalog,
    publish_objects,
    require_execution_window,
    validate_observability_config,
)
from crypto_autopilot.storage.ephemeral import require_ephemeral_output
from crypto_autopilot.storage.r2 import R2Store
from crypto_autopilot.training.online_r2 import current_bucket_bytes


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG_CONFIG = ROOT / "config/pionex_alternative_assets_v0_1.json"
DEFAULT_CONFIG = ROOT / "config/pionex_alternative_assets_observability_v0_2.json"
DEFAULT_AUTHORITY = (
    ROOT
    / "research/receipts/2026-08-30-pionex-alternative-assets-observability-v0-2-authority.json"
)


def required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"required GitHub Actions R2 secret is missing: {name}")
    return value


def create_store() -> R2Store:
    return R2Store(
        account_id=required("CLOUDFLARE_ACCOUNT_ID"),
        bucket=required("R2_BUCKET_NAME"),
        access_key_id=required("R2_ACCESS_KEY_ID"),
        secret_access_key=required("R2_SECRET_ACCESS_KEY"),
    )


def parse_utc(value: str | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError("--observed-at-utc must be explicit UTC")
    return parsed


def utc_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_authority(
    *, config_path: Path, catalog_config_path: Path, authority_path: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    config_bytes = config_path.read_bytes()
    catalog_config_bytes = catalog_config_path.read_bytes()
    config = json.loads(config_bytes)
    catalog_config = json.loads(catalog_config_bytes)
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    declared_config = str(authority.get("config") or "")
    actual_config = config_path.as_posix()
    if actual_config != declared_config and not actual_config.endswith(f"/{declared_config}"):
        raise PionexAlternativeAssetError("authority points to a different V0.2 config")
    if authority.get("config_sha256") != sha256_bytes(config_bytes):
        raise PionexAlternativeAssetError("V0.2 authority/config SHA-256 mismatch")
    if authority.get("catalog_source_sha256") != sha256_bytes(catalog_config_bytes):
        raise PionexAlternativeAssetError("V0.2 authority/catalog-source SHA-256 mismatch")
    validate_observability_config(config, catalog_config_bytes=catalog_config_bytes)
    return config, catalog_config, authority


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish validated Pionex alternative-asset catalog observability evidence"
    )
    parser.add_argument("--catalog-config", type=Path, default=DEFAULT_CATALOG_CONFIG)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--observed-at-utc")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--projection-output", type=Path, required=True)
    args = parser.parse_args()

    output = require_ephemeral_output(args.output)
    projection_output = require_ephemeral_output(args.projection_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    projection_output.parent.mkdir(parents=True, exist_ok=True)
    observed_at = parse_utc(args.observed_at_utc)
    config, catalog_config, authority = load_authority(
        config_path=args.config,
        catalog_config_path=args.catalog_config,
        authority_path=args.authority,
    )
    try:
        require_execution_window(config, observed_at=observed_at)
    except PionexAlternativeAssetError as exc:
        reason = str(exc)
        if not any(marker in reason for marker in ("V0.10 window", "authority expired")):
            raise
        projection = build_safe_projection(
            catalog_config=catalog_config,
            observability_config=config,
        )
        report = {
            "schema": "pionex-alternative-assets-observability-run-report-v0.2",
            "status": "SKIPPED",
            "stage": (
                "PIONEX_ALTERNATIVE_ASSETS_OBSERVABILITY_AUTHORITY_EXPIRED"
                if "expired" in reason
                else "PIONEX_ALTERNATIVE_ASSETS_OBSERVABILITY_NOT_BEFORE_GUARD"
            ),
            "observed_at_utc": utc_text(observed_at),
            "reason": reason,
            "provider_requests_performed": 0,
            "r2_access_performed": False,
            "authority": {
                "metadata_only": True,
                "historical_materialization_authorized": False,
                "training_authorized": False,
                "automatic_model_promotion_authorized": False,
                "formal_trade_plan_authorized": False,
                "private_api_authorized": False,
                "real_money_order_authorized": False,
                "live_trading_authorized": False,
            },
        }
        output.write_bytes(canonical_json_bytes(report))
        projection_output.write_bytes(canonical_json_bytes(projection))
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0

    store = create_store()
    hard_stop = int(config["storage"]["free_only_hard_stop_bytes"])
    reservation = int(config["storage"]["maximum_planned_run_bytes"])
    before_read_bytes = current_bucket_bytes(store)
    if before_read_bytes + reservation > hard_stop:
        raise PionexAlternativeAssetError(
            "R2 FREE-ONLY headroom gate blocked before catalog-lineage/provider access"
        )
    previous_catalog = load_previous_catalog(store, config=config)
    symbols = PionexPublicClient().list_perpetual_symbols()
    catalog = build_catalog(
        symbols,
        config=catalog_config,
        retrieved_at_utc=utc_text(observed_at),
    )
    analysis = build_analysis(
        catalog=catalog,
        previous_catalog=previous_catalog,
        catalog_config=catalog_config,
        observability_config=config,
    )
    projection = build_safe_projection(
        catalog_config=catalog_config,
        observability_config=config,
        catalog=catalog,
        analysis=analysis,
    )
    objects = build_objects(
        catalog=catalog,
        analysis=analysis,
        safe_projection=projection,
        config=config,
        run_id=args.run_id,
    )
    before_write_bytes = current_bucket_bytes(store)
    publication = publish_objects(
        store=store,
        objects=objects,
        hard_stop_bytes=hard_stop,
        current_bytes=before_write_bytes,
    )
    if publication["status"] != "PASS":
        raise PionexAlternativeAssetError(str(publication["stage"]))

    report: dict[str, Any] = {
        "schema": "pionex-alternative-assets-observability-run-report-v0.2",
        "status": analysis["status"],
        "stage": publication["stage"],
        "provider": "pionex_public_futures",
        "run_id": args.run_id,
        "observed_at_utc": utc_text(observed_at),
        "candidate_registry_count": catalog["registry_candidate_count"],
        "observed_pionex_perp_count": catalog["observed_pionex_perp_count"],
        "matched_market_count": catalog["matched_market_count"],
        "matched_counts_by_class": catalog["matched_counts_by_class"],
        "catalog_validation_status": analysis["catalog_validation"]["status"],
        "catalog_diff_status": analysis["catalog_diff"]["status"],
        "added_count": len(analysis["catalog_diff"]["added_symbols"]),
        "removed_count": len(analysis["catalog_diff"]["removed_symbols"]),
        "capacity_reference_gb": analysis["capacity_actual"]["scenarios"]["reference"][
            "canonical_gb"
        ],
        "r2": publication,
        "authority_receipt_status": authority["status"],
        "operations": {
            "provider_symbol_metadata_requests_performed": 1,
            "r2_catalog_lineage_read_performed": previous_catalog is not None,
            "r2_catalog_evidence_written": publication["r2_writes_performed"],
        },
        "authority": {
            "metadata_only": True,
            "historical_materialization_authorized": False,
            "training_authorized": False,
            "automatic_model_promotion_authorized": False,
            "formal_trade_plan_authorized": False,
            "private_api_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }
    output.write_bytes(canonical_json_bytes(report))
    projection_output.write_bytes(canonical_json_bytes(projection))
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
