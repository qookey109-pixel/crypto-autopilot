from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from crypto_autopilot.binance_funding import (
    BinanceFundingObservation,
    BinanceVisionFundingArchive,
    combine_funding_archives,
    funding_to_parquet,
    parquet_to_funding,
)
from crypto_autopilot.binance_funding_materialization_plan_v0_2 import build_v0_2_scope
from crypto_autopilot.binance.funding_materializer_v0_2 import (
    AUTHORITY_PATH,
    CADENCE_TOLERANCE_MS,
    CONFIG_PATH,
    EXECUTION_MARKER_PATH,
    EXPECTED_CHECKSUM_SET_SHA256,
    EXPECTED_SCOPE_SHA256,
    PREFLIGHT_AUTHORITY_PATH,
    BinanceFundingMaterializerV02Error,
    FundingChecksumRecord,
    canonical_json_bytes,
    checksum_set_sha256,
    run_metadata_keys,
    sha256_bytes,
    source_keys_from_scope,
    validate_execution_marker,
    validate_preflight_authority,
    validate_runtime_authority,
)
from crypto_autopilot.storage.r2 import R2Store
from preflight_binance_funding_r2_v0_2 import fetch_and_audit


COVERAGE_PATH = "research/receipts/2026-08-18-binance-funding-coverage.json"


@dataclass(frozen=True, slots=True)
class AnnualWrite:
    symbol: str
    year: int
    months: tuple[int, ...]
    canonical_key: str
    receipt_key: str
    observations: tuple[BinanceFundingObservation, ...]
    parquet_payload: bytes
    parquet_sha256: str
    receipt_payload: bytes
    source_rows: tuple[dict[str, object], ...]


def load_json(path: str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise BinanceFundingMaterializerV02Error(f"expected JSON object: {path}")
    return payload


def source_row(archive: BinanceVisionFundingArchive) -> dict[str, object]:
    receipt = archive.receipt
    return {
        "symbol": receipt.symbol,
        "period": receipt.period,
        "source_url": receipt.source_url,
        "checksum_url": receipt.checksum_url,
        "archive_filename": receipt.archive_filename,
        "archive_sha256": receipt.archive_sha256,
        "rows": receipt.row_count,
        "first_time_ms": receipt.first_time_ms,
        "last_time_ms": receipt.last_time_ms,
        "interval_hours": list(receipt.interval_hours),
        "min_rate": receipt.min_rate,
        "max_rate": receipt.max_rate,
        "cadence_anomalies": receipt.cadence_anomalies,
        "audit_ok": receipt.audit_ok,
    }


def build_partition_receipt(
    *,
    symbol: str,
    year: int,
    months: tuple[int, ...],
    canonical_key: str,
    parquet_sha256: str,
    parquet_bytes: int,
    observations: tuple[BinanceFundingObservation, ...],
    source_rows: tuple[dict[str, object], ...],
) -> bytes:
    return canonical_json_bytes(
        {
            "schema": "binance-funding-r2-partition-receipt-v0.2",
            "status": "PASS",
            "provider": "binance_usdm",
            "delivery": "binance_vision",
            "dataset": "fundingRate",
            "symbol": symbol,
            "year": year,
            "source_months": list(months),
            "source_archive_count": len(source_rows),
            "source_archives": [
                {
                    "period": row["period"],
                    "archive_sha256": row["archive_sha256"],
                    "rows": row["rows"],
                    "first_time_ms": row["first_time_ms"],
                    "last_time_ms": row["last_time_ms"],
                    "interval_hours": row["interval_hours"],
                }
                for row in source_rows
            ],
            "canonical_scope_sha256": EXPECTED_SCOPE_SHA256,
            "source_checksum_set_sha256": EXPECTED_CHECKSUM_SET_SHA256,
            "canonical_key": canonical_key,
            "canonical_parquet_sha256": parquet_sha256,
            "canonical_parquet_bytes": parquet_bytes,
            "rows": len(observations),
            "first_time_ms": observations[0].funding_time_ms,
            "last_time_ms": observations[-1].funding_time_ms,
            "funding_interval_hours": sorted(
                {item.funding_interval_hours for item in observations}
            ),
            "cadence_jitter_tolerance_ms": CADENCE_TOLERANCE_MS,
            "raw_source_calc_time_preserved": True,
            "source_declared_funding_interval_hours_preserved": True,
            "native_to_execution_exchange": False,
            "hypeusdt_2026_deferred": symbol == "HYPEUSDT",
            "source_switch_authorized": False,
            "provider_splicing_authorized": False,
            "interpolation_authorized": False,
            "pionex_native_relabel_authorized": False,
            "backtest_admission_authorized": False,
            "trade_plan_authorized": False,
            "live_trading_authorized": False,
        }
    )


def rebuild_full_preflight(*, workers: int):
    config = load_json(CONFIG_PATH)
    authority = load_json(AUTHORITY_PATH)
    frozen_preflight = load_json(PREFLIGHT_AUTHORITY_PATH)
    marker = load_json(EXECUTION_MARKER_PATH)
    coverage = load_json(COVERAGE_PATH)
    scope = build_v0_2_scope(coverage)
    scope_sha, expected_checksum_sha = validate_runtime_authority(
        config=config,
        authority=authority,
        scope=scope,
    )
    validate_preflight_authority(frozen_preflight)
    validate_execution_marker(marker)
    if scope_sha != EXPECTED_SCOPE_SHA256 or expected_checksum_sha != EXPECTED_CHECKSUM_SET_SHA256:
        raise BinanceFundingMaterializerV02Error("Funding V0.2 execution constants changed")

    keys = source_keys_from_scope(scope)
    checksum_records: list[FundingChecksumRecord] = []
    archives: dict[tuple[str, str], BinanceVisionFundingArchive] = {}
    with ThreadPoolExecutor(max_workers=min(workers, len(keys))) as executor:
        futures = {executor.submit(fetch_and_audit, key): key for key in keys}
        for future in as_completed(futures):
            key = futures[future]
            try:
                checksum_record, archive = future.result()
            except Exception as exc:
                raise BinanceFundingMaterializerV02Error(
                    f"Funding V0.2 execution preflight failed for {key.identity}: {exc}"
                ) from exc
            checksum_records.append(checksum_record)
            archives[key.identity] = archive

    checksum_records.sort(key=lambda row: (row.symbol, row.period))
    if len(checksum_records) != 1003 or len(archives) != 1003:
        raise BinanceFundingMaterializerV02Error("Funding V0.2 execution requires 1,003 source archives")
    observed_checksum_sha = checksum_set_sha256(tuple(checksum_records))
    if observed_checksum_sha != EXPECTED_CHECKSUM_SET_SHA256:
        raise BinanceFundingMaterializerV02Error(
            "Funding V0.2 source checksum-set changed after frozen preflight authority"
        )

    annuals: list[AnnualWrite] = []
    for annual in scope.annual_scopes:
        selected = tuple(
            archives[(annual.symbol, f"{annual.year:04d}-{month:02d}")]
            for month in annual.months
        )
        observations = combine_funding_archives(
            selected,
            symbol=annual.symbol,
            year=annual.year,
            cadence_jitter_tolerance_ms=CADENCE_TOLERANCE_MS,
        )
        artifact = funding_to_parquet(observations)
        if parquet_to_funding(artifact.payload) != list(observations):
            raise BinanceFundingMaterializerV02Error(
                f"Funding V0.2 local Parquet round-trip mismatch: {annual.symbol} {annual.year}"
            )
        rows = tuple(source_row(item) for item in selected)
        annuals.append(
            AnnualWrite(
                symbol=annual.symbol,
                year=annual.year,
                months=annual.months,
                canonical_key=annual.canonical_key,
                receipt_key=annual.receipt_key,
                observations=observations,
                parquet_payload=artifact.payload,
                parquet_sha256=artifact.sha256,
                receipt_payload=build_partition_receipt(
                    symbol=annual.symbol,
                    year=annual.year,
                    months=annual.months,
                    canonical_key=annual.canonical_key,
                    parquet_sha256=artifact.sha256,
                    parquet_bytes=len(artifact.payload),
                    observations=observations,
                    source_rows=rows,
                ),
                source_rows=rows,
            )
        )
    annuals.sort(key=lambda item: (item.symbol, item.year))
    if len(annuals) != 94:
        raise BinanceFundingMaterializerV02Error("Funding V0.2 execution requires 94 annual builds")
    if any(item.symbol == "HYPEUSDT" and item.year == 2026 for item in annuals):
        raise BinanceFundingMaterializerV02Error("HYPEUSDT 2026 escaped Funding V0.2 execution scope")
    return scope, tuple(keys), tuple(checksum_records), archives, tuple(annuals)


def exact_action(existing: bytes | None, expected: bytes, key: str) -> str:
    if existing is None:
        return "UPLOAD"
    if existing != expected:
        raise BinanceFundingMaterializerV02Error(
            f"existing R2 object conflicts with Funding V0.2 authorized bytes: {key}"
        )
    return "VERIFY_EXISTING"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID") or "0")
    parser.add_argument("--output", default="artifacts/binance-funding-r2-v0-2-execution/result.json")
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 24:
        raise ValueError("workers must be between 1 and 24")

    scope, keys, checksum_records, archives, annuals = rebuild_full_preflight(workers=args.workers)
    metadata = run_metadata_keys(args.run_id)
    source_manifest = {
        "schema": "binance-funding-r2-source-manifest-v0.2",
        "status": "PASS",
        "provider": "binance_usdm",
        "dataset": "fundingRate",
        "canonical_scope_sha256": EXPECTED_SCOPE_SHA256,
        "source_checksum_set_sha256": EXPECTED_CHECKSUM_SET_SHA256,
        "source_archive_count": 1003,
        "sources": [source_row(archives[key.identity]) for key in keys],
        "hypeusdt_2026_deferred": True,
        "source_switch_authorized": False,
        "live_trading_authorized": False,
    }
    canonical_manifest = {
        "schema": "binance-funding-r2-canonical-manifest-v0.2",
        "status": "PASS",
        "provider": "binance_usdm",
        "dataset": "fundingRate",
        "canonical_scope_sha256": EXPECTED_SCOPE_SHA256,
        "source_checksum_set_sha256": EXPECTED_CHECKSUM_SET_SHA256,
        "canonical_object_count": 94,
        "partition_receipt_count": 94,
        "objects": [
            {
                "symbol": item.symbol,
                "year": item.year,
                "source_months": list(item.months),
                "rows": len(item.observations),
                "first_time_ms": item.observations[0].funding_time_ms,
                "last_time_ms": item.observations[-1].funding_time_ms,
                "canonical_key": item.canonical_key,
                "canonical_parquet_bytes": len(item.parquet_payload),
                "canonical_parquet_sha256": item.parquet_sha256,
                "partition_receipt_key": item.receipt_key,
                "partition_receipt_sha256": sha256_bytes(item.receipt_payload),
            }
            for item in annuals
        ],
        "hypeusdt_2026_deferred": True,
        "source_switch_authorized": False,
        "live_trading_authorized": False,
    }
    runtime_preflight = {
        "schema": "binance-funding-r2-materialization-runtime-preflight-v0.2",
        "status": "PASS",
        "stage": "BINANCE_FUNDING_R2_V0_2_RUNTIME_PREFLIGHT_PASS",
        "run_id": str(args.run_id),
        "canonical_scope_sha256": EXPECTED_SCOPE_SHA256,
        "source_checksum_set_sha256": EXPECTED_CHECKSUM_SET_SHA256,
        "source_archive_count": 1003,
        "annual_canonical_object_count": 94,
        "total_funding_observations": sum(len(item.observations) for item in annuals),
        "total_local_parquet_bytes": sum(len(item.parquet_payload) for item in annuals),
        "all_source_content_audits_pass": True,
        "all_annual_cross_month_audits_pass": True,
        "all_annual_parquet_round_trips_pass": True,
        "hypeusdt_2026_deferred": True,
        "r2_writes_performed_before_this_receipt": False,
        "live_trading_authorized": False,
    }

    expected: dict[str, tuple[bytes, str, dict[str, str] | None]] = {
        metadata.source_manifest: (canonical_json_bytes(source_manifest), "application/json", None),
        metadata.canonical_manifest: (canonical_json_bytes(canonical_manifest), "application/json", None),
        metadata.preflight_receipt: (canonical_json_bytes(runtime_preflight), "application/json", None),
    }
    observations_by_key: dict[str, tuple[BinanceFundingObservation, ...]] = {}
    for item in annuals:
        expected[item.canonical_key] = (
            item.parquet_payload,
            "application/vnd.apache.parquet",
            {
                "provider": "binance_usdm",
                "dataset": "fundingRate",
                "source-scope-sha256": EXPECTED_SCOPE_SHA256,
                "source-checksum-set-sha256": EXPECTED_CHECKSUM_SET_SHA256,
            },
        )
        expected[item.receipt_key] = (item.receipt_payload, "application/json", None)
        observations_by_key[item.canonical_key] = item.observations
    if len(expected) != 191 or len(set(expected)) != 191:
        raise BinanceFundingMaterializerV02Error(
            f"Funding V0.2 pre-result identity count must be 191, got {len(expected)}"
        )
    if any("pionex" in key.lower() for key in expected):
        raise BinanceFundingMaterializerV02Error("Funding V0.2 attempted Pionex namespace")

    store = R2Store(
        account_id=os.environ["CLOUDFLARE_ACCOUNT_ID"],
        bucket=os.environ["R2_BUCKET_NAME"],
        access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    )

    actions: dict[str, str] = {}
    for key, (payload, _, _) in expected.items():
        actions[key] = exact_action(store.get_bytes_if_exists(key), payload, key)

    uploaded_before_result = sum(action == "UPLOAD" for action in actions.values())
    verified_before_result = sum(action == "VERIFY_EXISTING" for action in actions.values())
    result_payload = {
        "schema": "binance-funding-r2-materialization-result-v0.2",
        "status": "PASS",
        "stage": "BINANCE_FUNDING_R2_V0_2_MATERIALIZATION_PASS",
        "provider": "binance_usdm",
        "dataset": "fundingRate",
        "run_id": str(args.run_id),
        "canonical_scope_sha256": EXPECTED_SCOPE_SHA256,
        "source_checksum_set_sha256": EXPECTED_CHECKSUM_SET_SHA256,
        "source_archive_count": 1003,
        "canonical_object_count": 94,
        "partition_receipt_count": 94,
        "run_metadata_object_count": 4,
        "authorized_object_identity_count": 192,
        "uploaded_before_result": uploaded_before_result,
        "verified_existing_before_result": verified_before_result,
        "prewrite_exact_conflict_scan_pass": True,
        "post_write_sha_verification_required": True,
        "post_write_exact_funding_observation_equality_required": True,
        "hypeusdt_2026_deferred": True,
        "source_switch_authorized": False,
        "provider_splicing_authorized": False,
        "interpolation_authorized": False,
        "pionex_native_relabel_authorized": False,
        "backtest_admission_authorized": False,
        "trade_plan_authorized": False,
        "real_money_order_authorized": False,
        "live_trading_authorized": False,
    }
    result_bytes = canonical_json_bytes(result_payload)
    result_action = exact_action(store.get_bytes_if_exists(metadata.result), result_bytes, metadata.result)
    expected[metadata.result] = (result_bytes, "application/json", None)
    actions[metadata.result] = result_action
    if len(expected) != 192 or len(set(expected)) != 192:
        raise BinanceFundingMaterializerV02Error("Funding V0.2 exact identity count must be 192")

    write_order = [metadata.source_manifest, metadata.canonical_manifest, metadata.preflight_receipt]
    for item in annuals:
        write_order.extend((item.canonical_key, item.receipt_key))
    write_order.append(metadata.result)
    if len(write_order) != 192 or len(set(write_order)) != 192:
        raise BinanceFundingMaterializerV02Error("Funding V0.2 write order must contain 192 unique identities")

    for key in write_order:
        payload, content_type, object_metadata = expected[key]
        if actions[key] == "UPLOAD":
            receipt = store.put_bytes(
                key,
                payload,
                content_type=content_type,
                metadata=object_metadata,
            )
            restored = store.get_bytes_verified(key, expected_sha256=receipt.sha256)
        else:
            restored = store.get_bytes_if_exists(key)
            if restored is None:
                raise BinanceFundingMaterializerV02Error(
                    f"Funding V0.2 existing object disappeared after prewrite scan: {key}"
                )
        if restored != payload:
            raise BinanceFundingMaterializerV02Error(f"Funding V0.2 post-write byte mismatch: {key}")
        if key in observations_by_key and parquet_to_funding(restored) != list(observations_by_key[key]):
            raise BinanceFundingMaterializerV02Error(
                f"Funding V0.2 post-write observation mismatch: {key}"
            )

    output_result = {
        **result_payload,
        "result_object_action": result_action,
        "uploaded_object_count": sum(action == "UPLOAD" for action in actions.values()),
        "verified_existing_object_count": sum(
            action == "VERIFY_EXISTING" for action in actions.values()
        ),
        "all_192_authorized_objects_verified_after_write": True,
        "actual_r2_materialization_completed": True,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(output_result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output_result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
