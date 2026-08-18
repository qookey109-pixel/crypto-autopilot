from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from crypto_autopilot.binance_funding import (
    BinanceFundingObservation,
    BinanceVisionFundingArchive,
    BinanceVisionFundingArchiveKey,
    combine_funding_archives,
    funding_to_parquet,
    ingest_funding_archive,
    parquet_to_funding,
)
from crypto_autopilot.binance_funding_materialization_plan import (
    FundingMaterializationScope,
    build_materialization_scope,
)
from crypto_autopilot.binance_funding_materializer import (
    MATERIALIZATION_AUTHORITY_AMENDMENT_PATH,
    MATERIALIZATION_AUTHORITY_PATH,
    SOURCE_CHECKSUM_SET_AUTHORITY_PATH,
    BinanceFundingMaterializationError,
    FundingChecksumRecord,
    canonical_json_bytes,
    checksum_set_sha256,
    run_metadata_keys,
    sha256_bytes,
    source_keys_from_scope,
    validate_authority_bundle,
    validate_execution_marker,
)
from crypto_autopilot.binance_vision import parse_checksum
from crypto_autopilot.storage.r2 import R2Store


COVERAGE_AUTHORITY_PATH = "research/receipts/2026-08-18-binance-funding-coverage.json"
DEFAULT_EXECUTION_MARKER = "config/binance_funding_r2_materialization_execution_v0_1.json"
CADENCE_TOLERANCE_MS = 50


@dataclass(slots=True)
class AnnualBuild:
    symbol: str
    year: int
    months: tuple[int, ...]
    canonical_key: str
    receipt_key: str
    observations: tuple[BinanceFundingObservation, ...]
    parquet_payload: bytes
    parquet_sha256: str
    source_records: tuple[dict[str, object], ...]
    receipt_payload: bytes


@dataclass(slots=True)
class PreflightBundle:
    scope: FundingMaterializationScope
    scope_sha256: str
    checksum_set_sha256: str
    source_manifest: dict[str, object]
    canonical_manifest: dict[str, object]
    preflight_receipt: dict[str, object]
    annual_builds: tuple[AnnualBuild, ...]


def load_json(path: str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise BinanceFundingMaterializationError(f"expected JSON object: {path}")
    return payload


def fetch_bytes(url: str, *, attempts: int = 3, timeout_seconds: float = 30.0) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = Request(
            url,
            headers={"Accept": "*/*", "User-Agent": "qookey-crypto-autopilot-funding-r2/0.1"},
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - frozen Binance Vision HTTPS host
                return response.read()
        except HTTPError as exc:
            last_error = exc
            if exc.code not in {408, 425, 429, 500, 502, 503, 504}:
                break
        except (URLError, TimeoutError) as exc:
            last_error = exc
        if attempt + 1 < attempts:
            time.sleep(1.0 * (attempt + 1))
    raise BinanceFundingMaterializationError(f"failed to fetch {url}: {last_error}") from last_error


def fetch_checksum_set(
    keys: tuple[BinanceVisionFundingArchiveKey, ...],
    *,
    workers: int,
) -> tuple[tuple[FundingChecksumRecord, ...], dict[tuple[str, str], bytes]]:
    records: list[FundingChecksumRecord] = []
    payloads: dict[tuple[str, str], bytes] = {}

    def one(key: BinanceVisionFundingArchiveKey) -> tuple[FundingChecksumRecord, bytes]:
        payload = fetch_bytes(key.checksum_url)
        digest, filename = parse_checksum(payload)
        if filename != key.filename:
            raise BinanceFundingMaterializationError(
                f"Funding CHECKSUM filename mismatch for {key.identity}: {filename}"
            )
        return FundingChecksumRecord(key.symbol, key.period, digest), payload

    with ThreadPoolExecutor(max_workers=min(workers, len(keys))) as executor:
        futures = {executor.submit(one, key): key for key in keys}
        for future in as_completed(futures):
            record, payload = future.result()
            records.append(record)
            payloads[(record.symbol, record.period)] = payload

    records.sort(key=lambda item: (item.symbol, item.period))
    if len(records) != 1010 or len(payloads) != 1010:
        raise BinanceFundingMaterializationError(
            f"Funding checksum preflight expected 1,010 records, got {len(records)}"
        )
    return tuple(records), payloads


def fetch_archives(
    keys: tuple[BinanceVisionFundingArchiveKey, ...],
    checksum_payloads: dict[tuple[str, str], bytes],
    checksum_records: tuple[FundingChecksumRecord, ...],
    *,
    workers: int,
) -> dict[tuple[str, str], BinanceVisionFundingArchive]:
    expected_sha = {(item.symbol, item.period): item.archive_sha256 for item in checksum_records}
    results: dict[tuple[str, str], BinanceVisionFundingArchive] = {}

    def one(key: BinanceVisionFundingArchiveKey) -> BinanceVisionFundingArchive:
        archive_bytes = fetch_bytes(key.url)
        ingested = ingest_funding_archive(
            key,
            archive_bytes=archive_bytes,
            checksum_payload=checksum_payloads[key.identity],
            cadence_jitter_tolerance_ms=CADENCE_TOLERANCE_MS,
        )
        if ingested.receipt.archive_sha256 != expected_sha[key.identity]:
            raise BinanceFundingMaterializationError(
                f"Funding archive SHA differs from checksum-set preflight: {key.identity}"
            )
        return ingested

    with ThreadPoolExecutor(max_workers=min(workers, len(keys))) as executor:
        futures = {executor.submit(one, key): key for key in keys}
        for future in as_completed(futures):
            archive = future.result()
            results[archive.key.identity] = archive

    if len(results) != 1010:
        raise BinanceFundingMaterializationError(
            f"Funding content preflight expected 1,010 archives, got {len(results)}"
        )
    return results


def source_record(archive: BinanceVisionFundingArchive) -> dict[str, object]:
    receipt = archive.receipt
    return {
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "dataset": "fundingRate",
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
    scope_sha256: str,
    checksum_set_sha256_value: str,
    symbol: str,
    year: int,
    months: tuple[int, ...],
    canonical_key: str,
    parquet_sha256: str,
    parquet_bytes: int,
    observations: tuple[BinanceFundingObservation, ...],
    source_records: tuple[dict[str, object], ...],
) -> bytes:
    payload = {
        "schema": "binance-funding-r2-partition-receipt-v0.1",
        "status": "PASS",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "dataset": "fundingRate",
        "symbol": symbol,
        "year": year,
        "source_months": list(months),
        "source_archive_count": len(source_records),
        "source_archives": [
            {
                "period": row["period"],
                "archive_sha256": row["archive_sha256"],
                "rows": row["rows"],
                "first_time_ms": row["first_time_ms"],
                "last_time_ms": row["last_time_ms"],
                "interval_hours": row["interval_hours"],
            }
            for row in source_records
        ],
        "canonical_scope_sha256": scope_sha256,
        "source_checksum_set_sha256": checksum_set_sha256_value,
        "canonical_key": canonical_key,
        "canonical_parquet_sha256": parquet_sha256,
        "canonical_parquet_bytes": parquet_bytes,
        "rows": len(observations),
        "first_time_ms": observations[0].funding_time_ms,
        "last_time_ms": observations[-1].funding_time_ms,
        "funding_interval_hours": sorted({item.funding_interval_hours for item in observations}),
        "raw_source_calc_time_preserved": True,
        "source_declared_funding_interval_hours_preserved": True,
        "cadence_jitter_tolerance_ms": CADENCE_TOLERANCE_MS,
        "native_to_execution_exchange": False,
        "source_switch_authorized": False,
        "pionex_native_relabel_authorized": False,
        "backtest_admission_authorized": False,
        "trade_plan_authorized": False,
        "live_trading_authorized": False,
    }
    return canonical_json_bytes(payload)


def build_annual_artifacts(
    scope: FundingMaterializationScope,
    archives: dict[tuple[str, str], BinanceVisionFundingArchive],
    *,
    scope_sha256: str,
    checksum_set_sha256_value: str,
) -> tuple[AnnualBuild, ...]:
    builds: list[AnnualBuild] = []
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
        parquet = funding_to_parquet(observations)
        if parquet.rows <= 0 or parquet.first_time_ms is None or parquet.last_time_ms is None:
            raise BinanceFundingMaterializationError(
                f"empty annual Funding Parquet artifact: {annual.symbol} {annual.year}"
            )
        records = tuple(source_record(item) for item in selected)
        receipt_payload = build_partition_receipt(
            scope_sha256=scope_sha256,
            checksum_set_sha256_value=checksum_set_sha256_value,
            symbol=annual.symbol,
            year=annual.year,
            months=annual.months,
            canonical_key=annual.canonical_key,
            parquet_sha256=parquet.sha256,
            parquet_bytes=len(parquet.payload),
            observations=observations,
            source_records=records,
        )
        builds.append(
            AnnualBuild(
                symbol=annual.symbol,
                year=annual.year,
                months=annual.months,
                canonical_key=annual.canonical_key,
                receipt_key=annual.receipt_key,
                observations=observations,
                parquet_payload=parquet.payload,
                parquet_sha256=parquet.sha256,
                source_records=records,
                receipt_payload=receipt_payload,
            )
        )
    builds.sort(key=lambda item: (item.symbol, item.year))
    if len(builds) != 95:
        raise BinanceFundingMaterializationError(
            f"Funding annual build count mismatch: expected 95, got {len(builds)}"
        )
    return tuple(builds)


def run_preflight(*, workers: int) -> PreflightBundle:
    coverage = load_json(COVERAGE_AUTHORITY_PATH)
    materialization_authority = load_json(MATERIALIZATION_AUTHORITY_PATH)
    amendment = load_json(MATERIALIZATION_AUTHORITY_AMENDMENT_PATH)
    checksum_authority = load_json(SOURCE_CHECKSUM_SET_AUTHORITY_PATH)
    scope = build_materialization_scope(coverage)
    scope_sha, expected_checksum_sha = validate_authority_bundle(
        materialization_authority=materialization_authority,
        amendment=amendment,
        checksum_set_authority=checksum_authority,
        scope=scope,
    )
    source_keys = source_keys_from_scope(scope)
    checksum_records, checksum_payloads = fetch_checksum_set(source_keys, workers=workers)
    observed_checksum_sha = checksum_set_sha256(checksum_records)
    if observed_checksum_sha != expected_checksum_sha:
        raise BinanceFundingMaterializationError(
            "Funding source checksum-set changed; explicit source revision review is required"
        )
    archives = fetch_archives(
        source_keys,
        checksum_payloads,
        checksum_records,
        workers=workers,
    )
    annual_builds = build_annual_artifacts(
        scope,
        archives,
        scope_sha256=scope_sha,
        checksum_set_sha256_value=observed_checksum_sha,
    )

    source_rows = [source_record(archives[key.identity]) for key in source_keys]
    canonical_rows = [
        {
            "symbol": item.symbol,
            "year": item.year,
            "source_months": list(item.months),
            "source_archive_count": len(item.source_records),
            "rows": len(item.observations),
            "first_time_ms": item.observations[0].funding_time_ms,
            "last_time_ms": item.observations[-1].funding_time_ms,
            "funding_interval_hours": sorted(
                {point.funding_interval_hours for point in item.observations}
            ),
            "canonical_key": item.canonical_key,
            "canonical_parquet_bytes": len(item.parquet_payload),
            "canonical_parquet_sha256": item.parquet_sha256,
            "partition_receipt_key": item.receipt_key,
            "partition_receipt_sha256": sha256_bytes(item.receipt_payload),
        }
        for item in annual_builds
    ]
    source_manifest = {
        "schema": "binance-funding-r2-source-manifest-v0.1",
        "status": "PASS",
        "provider": "binance_usdm",
        "dataset": "fundingRate",
        "canonical_scope_sha256": scope_sha,
        "source_checksum_set_sha256": observed_checksum_sha,
        "source_archive_count": len(source_rows),
        "sources": source_rows,
        "source_switch_authorized": False,
        "live_trading_authorized": False,
    }
    canonical_manifest = {
        "schema": "binance-funding-r2-canonical-manifest-v0.1",
        "status": "PASS",
        "provider": "binance_usdm",
        "dataset": "fundingRate",
        "canonical_scope_sha256": scope_sha,
        "source_checksum_set_sha256": observed_checksum_sha,
        "canonical_object_count": len(canonical_rows),
        "partition_receipt_count": len(canonical_rows),
        "objects": canonical_rows,
        "source_switch_authorized": False,
        "live_trading_authorized": False,
    }
    preflight_receipt = {
        "schema": "binance-funding-r2-materialization-preflight-v0.1",
        "status": "PASS",
        "stage": "BINANCE_FUNDING_R2_PREFLIGHT_PASS",
        "provider": "binance_usdm",
        "dataset": "fundingRate",
        "canonical_scope_sha256": scope_sha,
        "source_checksum_set_sha256": observed_checksum_sha,
        "source_archive_count": len(source_rows),
        "annual_canonical_object_count": len(canonical_rows),
        "annual_partition_receipt_count": len(canonical_rows),
        "all_source_checksums_match_frozen_set": True,
        "all_source_content_audits_pass": True,
        "all_annual_cross_month_audits_pass": True,
        "all_annual_parquet_objects_built_locally": True,
        "cadence_jitter_tolerance_ms": CADENCE_TOLERANCE_MS,
        "r2_credentials_used": False,
        "r2_writes_performed": False,
        "source_switch_authorized": False,
        "pionex_native_relabel_authorized": False,
        "backtest_admission_authorized": False,
        "trade_plan_authorized": False,
        "live_trading_authorized": False,
    }
    return PreflightBundle(
        scope=scope,
        scope_sha256=scope_sha,
        checksum_set_sha256=observed_checksum_sha,
        source_manifest=source_manifest,
        canonical_manifest=canonical_manifest,
        preflight_receipt=preflight_receipt,
        annual_builds=annual_builds,
    )


def exact_existing_action(existing: bytes | None, expected: bytes, *, key: str) -> str:
    if existing is None:
        return "upload"
    if existing != expected:
        raise BinanceFundingMaterializationError(
            f"existing R2 object conflicts with authorized Funding materialization: {key}"
        )
    return "verified_existing"


def put_or_verify_exact(
    store: R2Store,
    *,
    key: str,
    payload: bytes,
    content_type: str,
    action: str,
    metadata: dict[str, str] | None = None,
) -> bytes:
    if action == "upload":
        receipt = store.put_bytes(
            key,
            payload,
            content_type=content_type,
            metadata=metadata,
        )
        return store.get_bytes_verified(key, expected_sha256=receipt.sha256)
    restored = store.get_bytes_if_exists(key)
    if restored is None or restored != payload:
        raise BinanceFundingMaterializationError(
            f"existing R2 object changed after prewrite verification: {key}"
        )
    return restored


def run_write(
    *,
    preflight: PreflightBundle,
    marker_path: str,
    run_id: str,
) -> dict[str, object]:
    marker = load_json(marker_path)
    validate_execution_marker(
        marker,
        scope_sha256=preflight.scope_sha256,
        checksum_set_sha256_value=preflight.checksum_set_sha256,
    )
    metadata_keys = run_metadata_keys(run_id)
    source_manifest_bytes = canonical_json_bytes(preflight.source_manifest)
    canonical_manifest_bytes = canonical_json_bytes(preflight.canonical_manifest)
    preflight_bytes = canonical_json_bytes(preflight.preflight_receipt)
    result_payload = {
        "schema": "binance-funding-r2-materialization-result-v0.1",
        "status": "PASS",
        "stage": "BINANCE_FUNDING_R2_MATERIALIZATION_PASS",
        "provider": "binance_usdm",
        "dataset": "fundingRate",
        "run_id": str(run_id),
        "canonical_scope_sha256": preflight.scope_sha256,
        "source_checksum_set_sha256": preflight.checksum_set_sha256,
        "source_archive_count": 1010,
        "canonical_object_count": 95,
        "partition_receipt_count": 95,
        "run_metadata_object_count": 4,
        "authorized_object_identity_count": 194,
        "post_write_sha_verification": True,
        "post_write_exact_funding_observation_equality": True,
        "source_switch_authorized": False,
        "pionex_native_relabel_authorized": False,
        "backtest_admission_authorized": False,
        "trade_plan_authorized": False,
        "live_trading_authorized": False,
    }
    result_bytes = canonical_json_bytes(result_payload)

    expected: dict[str, tuple[bytes, str, dict[str, str] | None]] = {
        metadata_keys.source_manifest: (source_manifest_bytes, "application/json", None),
        metadata_keys.canonical_manifest: (canonical_manifest_bytes, "application/json", None),
        metadata_keys.preflight_receipt: (preflight_bytes, "application/json", None),
        metadata_keys.result: (result_bytes, "application/json", None),
    }
    observations_by_key: dict[str, tuple[BinanceFundingObservation, ...]] = {}
    for item in preflight.annual_builds:
        expected[item.canonical_key] = (
            item.parquet_payload,
            "application/vnd.apache.parquet",
            {
                "provider": "binance_usdm",
                "dataset": "fundingRate",
                "source-scope-sha256": preflight.scope_sha256,
                "source-checksum-set-sha256": preflight.checksum_set_sha256,
            },
        )
        expected[item.receipt_key] = (item.receipt_payload, "application/json", None)
        observations_by_key[item.canonical_key] = item.observations
    if len(expected) != 194 or len(set(expected)) != 194:
        raise BinanceFundingMaterializationError(
            f"authorized Funding R2 identity count mismatch: {len(expected)}"
        )
    if any("pionex" in key.lower() for key in expected):
        raise BinanceFundingMaterializationError("Funding materializer attempted a Pionex namespace")

    store = R2Store(
        account_id=os.environ["CLOUDFLARE_ACCOUNT_ID"],
        bucket=os.environ["R2_BUCKET_NAME"],
        access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    )

    actions: dict[str, str] = {}
    for key, (payload, _, _) in expected.items():
        actions[key] = exact_existing_action(
            store.get_bytes_if_exists(key),
            payload,
            key=key,
        )

    write_order = [
        metadata_keys.source_manifest,
        metadata_keys.canonical_manifest,
        metadata_keys.preflight_receipt,
    ]
    for item in preflight.annual_builds:
        write_order.extend((item.canonical_key, item.receipt_key))
    write_order.append(metadata_keys.result)
    if len(write_order) != 194 or len(set(write_order)) != 194:
        raise BinanceFundingMaterializationError("Funding write order must contain 194 unique objects")

    for key in write_order:
        payload, content_type, metadata = expected[key]
        restored = put_or_verify_exact(
            store,
            key=key,
            payload=payload,
            content_type=content_type,
            action=actions[key],
            metadata=metadata,
        )
        if restored != payload:
            raise BinanceFundingMaterializationError(f"Funding R2 byte mismatch after write: {key}")
        if key in observations_by_key:
            if parquet_to_funding(restored) != list(observations_by_key[key]):
                raise BinanceFundingMaterializationError(
                    f"Funding R2 observation round-trip mismatch: {key}"
                )

    uploaded = sum(value == "upload" for value in actions.values())
    verified_existing = sum(value == "verified_existing" for value in actions.values())
    return {
        **result_payload,
        "execution_evidence": {
            "uploaded_object_count": uploaded,
            "verified_existing_object_count": verified_existing,
            "prewrite_exact_conflict_scan_pass": True,
            "all_194_authorized_objects_verified_after_write": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "write"), required=True)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID") or "0")
    parser.add_argument("--execution-marker", default=DEFAULT_EXECUTION_MARKER)
    parser.add_argument("--output-dir", default="artifacts/binance-funding-r2-materialization")
    args = parser.parse_args()
    if not 1 <= args.workers <= 24:
        raise ValueError("workers must be between 1 and 24")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    preflight = run_preflight(workers=args.workers)
    preflight_output = {
        **preflight.preflight_receipt,
        "source_manifest_sha256": hashlib.sha256(
            canonical_json_bytes(preflight.source_manifest)
        ).hexdigest(),
        "canonical_manifest_sha256": hashlib.sha256(
            canonical_json_bytes(preflight.canonical_manifest)
        ).hexdigest(),
        "total_funding_rows": sum(len(item.observations) for item in preflight.annual_builds),
        "total_parquet_bytes": sum(len(item.parquet_payload) for item in preflight.annual_builds),
    }
    (output_dir / "preflight.json").write_text(
        json.dumps(preflight_output, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    if args.mode == "preflight":
        print(json.dumps(preflight_output, sort_keys=True))
        return 0

    result = run_write(
        preflight=preflight,
        marker_path=args.execution_marker,
        run_id=args.run_id,
    )
    (output_dir / "result.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
