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
    build_catalog_objects,
    canonical_json_bytes,
    load_authority_pair,
    publish_catalog_objects,
    require_execution_window,
)
from crypto_autopilot.storage.ephemeral import require_ephemeral_output
from crypto_autopilot.storage.r2 import R2Store
from crypto_autopilot.training.online_r2 import current_bucket_bytes


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config/pionex_alternative_assets_v0_1.json"
DEFAULT_AUTHORITY = (
    ROOT
    / "research/receipts/2026-08-30-pionex-alternative-assets-v0-1-authority.json"
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish the bounded Pionex alternative-assets metadata catalog"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--observed-at-utc")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    output = require_ephemeral_output(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    observed_at = parse_utc(args.observed_at_utc)
    config, authority, _config_bytes = load_authority_pair(args.config, args.authority)
    try:
        require_execution_window(config, observed_at=observed_at)
    except PionexAlternativeAssetError as exc:
        reason = str(exc)
        if not any(marker in reason for marker in ("V0.10 window", "authority expired")):
            raise
        report = {
            "schema": "pionex-alternative-assets-catalog-run-report-v0.1",
            "status": "SKIPPED",
            "stage": (
                "PIONEX_ALTERNATIVE_ASSETS_CATALOG_AUTHORITY_EXPIRED"
                if "expired" in reason
                else "PIONEX_ALTERNATIVE_ASSETS_CATALOG_NOT_BEFORE_GUARD"
            ),
            "observed_at_utc": utc_text(observed_at),
            "reason": reason,
            "provider_requests_performed": 0,
            "r2_access_performed": False,
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
                "private_api_authorized": False,
                "real_money_order_authorized": False,
                "live_trading_authorized": False,
            },
        }
        output.write_bytes(canonical_json_bytes(report))
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0

    store = create_store()
    hard_stop = int(config["storage"]["free_only_hard_stop_bytes"])
    reservation = int(config["storage"]["maximum_planned_run_bytes"])
    before_provider_bytes = current_bucket_bytes(store)
    if before_provider_bytes + reservation > hard_stop:
        raise PionexAlternativeAssetError(
            "R2 FREE-ONLY headroom gate blocked before Pionex metadata access"
        )

    symbols = PionexPublicClient().list_perpetual_symbols()
    catalog = build_catalog(symbols, config=config, retrieved_at_utc=utc_text(observed_at))
    objects = build_catalog_objects(config=config, catalog=catalog, run_id=args.run_id)
    before_write_bytes = current_bucket_bytes(store)
    publication = publish_catalog_objects(
        store=store,
        objects=objects,
        hard_stop_bytes=hard_stop,
        current_bytes=before_write_bytes,
    )
    if publication["status"] != "PASS":
        raise PionexAlternativeAssetError(str(publication["stage"]))

    report: dict[str, Any] = {
        "schema": "pionex-alternative-assets-catalog-run-report-v0.1",
        "status": catalog["status"],
        "stage": publication["stage"],
        "provider": "pionex_public_futures",
        "run_id": args.run_id,
        "observed_at_utc": utc_text(observed_at),
        "candidate_registry_count": catalog["registry_candidate_count"],
        "observed_pionex_perp_count": catalog["observed_pionex_perp_count"],
        "matched_market_count": catalog["matched_market_count"],
        "matched_counts_by_class": catalog["matched_counts_by_class"],
        "r2": publication,
        "authority_receipt_status": authority["status"],
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
            "private_api_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }
    output.write_bytes(canonical_json_bytes(report))
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
