from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from crypto_autopilot.binance.pilot_2025 import (
    Binance2025PilotAuthorityError,
    Binance2025SymbolCoverage,
    build_partition_plan,
    combine_and_audit_months,
    load_coverage_authority,
    source_archive_digest,
)
from crypto_autopilot.binance.vision import (
    BinanceVisionArchiveKey,
    BinanceVisionKlineArchive,
    ingest_kline_archive,
)
from crypto_autopilot.storage.parquet import candles_to_parquet, parquet_to_candles
from crypto_autopilot.storage.r2 import R2ObjectReceipt, R2Store


COVERAGE_AUTHORITY = Path("research/receipts/2026-08-18-binance-2025-coverage-scan.json")
BINANCE_INTERVAL_BY_PROJECT = {"15M": "15m", "60M": "1h", "4H": "4h"}
STEP_MS = {"15m": 15 * 60 * 1000, "1h": 60 * 60 * 1000, "4h": 4 * 60 * 60 * 1000}


def canonical_json_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def download(url: str, *, retries: int = 3, timeout_seconds: float = 30.0) -> bytes:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = Request(
                url,
                headers={"User-Agent": "qookey-crypto-autopilot-binance-2025-r2-pilot/0.1"},
            )
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - validated Vision URL
                return response.read()
        except HTTPError as exc:
            last_error = exc
            if exc.code == 404:
                raise RuntimeError(
                    f"coverage authority expected an archive but Binance Vision returned 404: {url}"
                ) from exc
            if exc.code not in {408, 425, 429, 500, 502, 503, 504}:
                break
        except (URLError, TimeoutError) as exc:
            last_error = exc
        if attempt + 1 < retries:
            time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"failed to download {url}: {last_error}") from last_error


def fetch_archive(key: BinanceVisionArchiveKey) -> BinanceVisionKlineArchive:
    archive_bytes = download(key.url)
    checksum_bytes = download(key.checksum_url)
    return ingest_kline_archive(
        key,
        archive_bytes=archive_bytes,
        checksum_payload=checksum_bytes,
    )


def month_bounds_ms(year: int, month: int, interval: str) -> tuple[int, int]:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        next_month = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    step = STEP_MS[interval]
    return int(start.timestamp() * 1000), int(next_month.timestamp() * 1000) - step


def verify_month_content(
    archive: BinanceVisionKlineArchive,
    *,
    allow_partial_start: bool,
) -> None:
    key = archive.key
    month = int(key.period[-2:])
    expected_first, expected_last = month_bounds_ms(2025, month, key.interval)
    first = archive.receipt.first_time_ms
    last = archive.receipt.last_time_ms
    if first is None or last is None or archive.receipt.row_count <= 0:
        raise Binance2025PilotAuthorityError(f"empty source archive: {key.filename}")
    if allow_partial_start:
        if not expected_first <= first <= expected_last:
            raise Binance2025PilotAuthorityError(
                f"partial source first timestamp outside expected month: {key.filename}: {first}"
            )
    elif first != expected_first:
        raise Binance2025PilotAuthorityError(
            f"full-month source does not start at expected boundary: {key.filename}: {first} != {expected_first}"
        )
    if last != expected_last:
        raise Binance2025PilotAuthorityError(
            f"source does not end at expected month boundary: {key.filename}: {last} != {expected_last}"
        )


def r2_receipt_for_existing(store: R2Store, key: str, payload: bytes) -> R2ObjectReceipt:
    return R2ObjectReceipt(
        bucket=store.bucket,
        key=key,
        bytes=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        etag=None,
    )


def put_or_verify_candles(
    store: R2Store,
    *,
    key: str,
    candles,
    source_digest: str,
) -> tuple[R2ObjectReceipt, str]:
    if not key.startswith("market-data/binance_usdm/") or "market-data/pionex/" in key:
        raise Binance2025PilotAuthorityError(f"unsafe Binance R2 canonical key: {key}")
    expected_candles = list(candles)
    parquet = candles_to_parquet(expected_candles)
    existing = store.get_bytes_if_exists(key)
    if existing is not None:
        restored_existing = parquet_to_candles(existing)
        if restored_existing != expected_candles:
            raise Binance2025PilotAuthorityError(
                f"existing Binance canonical object conflicts with source authority: {key}"
            )
        receipt = r2_receipt_for_existing(store, key, existing)
        action = "verified_existing"
    else:
        receipt = store.put_bytes(
            key,
            parquet.payload,
            content_type="application/vnd.apache.parquet",
            metadata={
                "provider": "binance_usdm",
                "delivery": "binance_vision",
                "source-digest": source_digest,
                "source-year": "2025",
            },
        )
        action = "uploaded"

    restored_payload = store.get_bytes_verified(key, expected_sha256=receipt.sha256)
    restored = parquet_to_candles(restored_payload)
    if restored != expected_candles:
        raise Binance2025PilotAuthorityError(f"R2 exact-candle round-trip mismatch: {key}")
    return receipt, action


def fetch_symbol_archives(
    coverage: Binance2025SymbolCoverage,
    *,
    workers: int,
) -> dict[tuple[str, int], BinanceVisionKlineArchive]:
    keys = [
        BinanceVisionArchiveKey(
            "klines",
            "monthly",
            coverage.symbol,
            interval,
            f"2025-{month:02d}",
        )
        for interval in ("15m", "1h", "4h")
        for month in coverage.months
    ]
    results: dict[tuple[str, int], BinanceVisionKlineArchive] = {}
    with ThreadPoolExecutor(max_workers=min(workers, len(keys))) as executor:
        futures = {executor.submit(fetch_archive, key): key for key in keys}
        for future in as_completed(futures):
            key = futures[future]
            archive = future.result()
            month = int(key.period[-2:])
            allow_partial = coverage.symbol == "HYPEUSDT" and month == 5
            verify_month_content(archive, allow_partial_start=allow_partial)
            results[(key.interval, month)] = archive
    if len(results) != len(keys):
        raise Binance2025PilotAuthorityError(
            f"source archive result count mismatch for {coverage.symbol}: {len(results)} != {len(keys)}"
        )
    return results


def source_record(archive: BinanceVisionKlineArchive) -> dict[str, object]:
    return {
        "symbol": archive.key.symbol,
        "interval": archive.key.interval,
        "period": archive.key.period,
        "filename": archive.key.filename,
        "source_url": archive.key.url,
        "checksum_url": archive.key.checksum_url,
        "archive_sha256": archive.receipt.archive_sha256,
        "rows": archive.receipt.row_count,
        "first_time_ms": archive.receipt.first_time_ms,
        "last_time_ms": archive.receipt.last_time_ms,
        "audit_ok": archive.receipt.audit_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coverage-authority", default=str(COVERAGE_AUTHORITY))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID") or "local")
    parser.add_argument("--output-dir", default="artifacts/binance-2025-r2-pilot")
    args = parser.parse_args()
    if not 1 <= args.workers <= 16:
        raise ValueError("workers must be between 1 and 16")

    coverage = load_coverage_authority(args.coverage_authority)
    plan = build_partition_plan(coverage)
    plans_by_symbol: dict[str, list] = {}
    for item in plan:
        plans_by_symbol.setdefault(item.symbol, []).append(item)

    store = R2Store(
        account_id=os.environ["CLOUDFLARE_ACCOUNT_ID"],
        bucket=os.environ["R2_BUCKET_NAME"],
        access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    )

    source_records: list[dict[str, object]] = []
    object_records: list[dict[str, object]] = []
    first_last_by_symbol_interval: dict[str, dict[str, dict[str, int]]] = {}

    for coverage_item in coverage:
        archives = fetch_symbol_archives(coverage_item, workers=args.workers)
        symbol_sources = [source_record(archive) for archive in archives.values()]
        symbol_sources.sort(key=lambda row: (str(row["interval"]), str(row["period"])))
        source_records.extend(symbol_sources)

        for partition in plans_by_symbol[coverage_item.symbol]:
            binance_interval = BINANCE_INTERVAL_BY_PROJECT[partition.interval]
            selected = tuple(archives[(binance_interval, month)] for month in partition.source_months)
            source_items = tuple(
                (archive.key.filename, archive.receipt.archive_sha256)
                for archive in selected
            )
            source_digest = source_archive_digest(source_items)
            if partition.interval == "15M":
                candles = selected[0].candles
            else:
                candles = combine_and_audit_months(
                    tuple(archive.candles for archive in selected),
                    interval=partition.interval,
                )
            if not candles:
                raise Binance2025PilotAuthorityError(f"empty partition planned for {partition.r2_key}")

            receipt, action = put_or_verify_candles(
                store,
                key=partition.r2_key,
                candles=candles,
                source_digest=source_digest,
            )
            first_time = candles[0].time_ms
            last_time = candles[-1].time_ms
            first_last_by_symbol_interval.setdefault(partition.symbol, {})[partition.interval] = {
                "first_time_ms": min(
                    first_time,
                    first_last_by_symbol_interval.get(partition.symbol, {})
                    .get(partition.interval, {})
                    .get("first_time_ms", first_time),
                ),
                "last_time_ms": max(
                    last_time,
                    first_last_by_symbol_interval.get(partition.symbol, {})
                    .get(partition.interval, {})
                    .get("last_time_ms", last_time),
                ),
            }
            object_records.append(
                {
                    "provider": "binance_usdm",
                    "delivery": "binance_vision",
                    "symbol": partition.symbol,
                    "interval": partition.interval,
                    "year": partition.year,
                    "month": partition.month,
                    "source_months": list(partition.source_months),
                    "source_archive_count": len(selected),
                    "source_archive_digest": source_digest,
                    "rows": len(candles),
                    "first_time_ms": first_time,
                    "last_time_ms": last_time,
                    "r2_key": partition.r2_key,
                    "r2_bytes": receipt.bytes,
                    "r2_sha256": receipt.sha256,
                    "r2_action": action,
                    "exact_candle_equality_verified": True,
                }
            )

    object_records.sort(key=lambda row: (str(row["symbol"]), str(row["interval"]), int(row["month"] or 0)))
    source_records.sort(key=lambda row: (str(row["symbol"]), str(row["interval"]), str(row["period"])))
    if len(object_records) != 206:
        raise Binance2025PilotAuthorityError(f"expected 206 R2 objects, got {len(object_records)}")
    if len(source_records) != 528:
        raise Binance2025PilotAuthorityError(f"expected 528 verified source archives, got {len(source_records)}")
    if len({str(row["r2_key"]) for row in object_records}) != 206:
        raise Binance2025PilotAuthorityError("duplicate R2 object keys in pilot result")
    if any("market-data/pionex/" in str(row["r2_key"]) for row in object_records):
        raise Binance2025PilotAuthorityError("Pionex namespace was touched by Binance pilot")

    uploaded = sum(row["r2_action"] == "uploaded" for row in object_records)
    verified_existing = sum(row["r2_action"] == "verified_existing" for row in object_records)
    total_rows = sum(int(row["rows"]) for row in object_records)
    total_parquet_bytes = sum(int(row["r2_bytes"]) for row in object_records)
    created_at = datetime.now(timezone.utc)

    manifest = {
        "schema": "binance-2025-r2-pilot-manifest-v0.1",
        "status": "PASS",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "execution_exchange": "pionex",
        "native_to_execution_exchange": False,
        "may_authorize_pionex_native_history": False,
        "year": 2025,
        "coverage_authority": args.coverage_authority,
        "source_archive_count": len(source_records),
        "object_count": len(object_records),
        "uploaded_object_count": uploaded,
        "verified_existing_object_count": verified_existing,
        "total_rows": total_rows,
        "total_parquet_bytes": total_parquet_bytes,
        "source_archives": source_records,
        "objects": object_records,
        "first_last_by_symbol_interval": first_last_by_symbol_interval,
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "github_sha": os.getenv("GITHUB_SHA"),
        "generated_at_utc": created_at.isoformat(),
        "private_api_used": False,
        "live_trading_authorized": False,
    }
    manifest_bytes = canonical_json_bytes(manifest)
    manifest_key = (
        "manifests/historical/binance_usdm/"
        f"year={created_at.year:04d}/month={created_at.month:02d}/"
        f"binance-2025-pilot-{args.run_id}.json"
    )
    manifest_upload = store.put_bytes(manifest_key, manifest_bytes, content_type="application/json")
    store.get_bytes_verified(manifest_key, expected_sha256=manifest_upload.sha256)

    receipt = {
        "schema": "binance-2025-r2-pilot-receipt-v0.1",
        "status": "PASS",
        "stage": "BINANCE_2025_R2_PILOT_PASS",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "execution_exchange": "pionex",
        "native_to_execution_exchange": False,
        "may_authorize_pionex_native_history": False,
        "year": 2025,
        "coverage_authority": args.coverage_authority,
        "source_archive_count": len(source_records),
        "object_count": len(object_records),
        "uploaded_object_count": uploaded,
        "verified_existing_object_count": verified_existing,
        "total_rows": total_rows,
        "total_parquet_bytes": total_parquet_bytes,
        "manifest_key": manifest_key,
        "manifest_sha256": manifest_upload.sha256,
        "all_source_checksum_verified": True,
        "all_source_candle_audits_passed": True,
        "all_annual_cross_month_audits_passed": True,
        "all_r2_sha_verified": True,
        "all_parquet_decoded": True,
        "all_exact_candle_equality_verified": True,
        "pionex_namespace_touched": False,
        "hype_pre_may_synthetic_data_created": False,
        "private_api_used": False,
        "live_trading_authorized": False,
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "github_sha": os.getenv("GITHUB_SHA"),
        "generated_at_utc": created_at.isoformat(),
        "first_last_by_symbol_interval": first_last_by_symbol_interval,
    }
    receipt_bytes = canonical_json_bytes(receipt)
    receipt_key = f"receipts/historical/binance_usdm/binance-2025-pilot-{args.run_id}.json"
    receipt_upload = store.put_bytes(receipt_key, receipt_bytes, content_type="application/json")
    store.get_bytes_verified(receipt_key, expected_sha256=receipt_upload.sha256)
    receipt["r2_receipt_key"] = receipt_key
    receipt["r2_receipt_sha256"] = receipt_upload.sha256

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "binance-2025-r2-pilot-manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "binance-2025-r2-pilot-receipt.json").write_text(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "source_archives": len(source_records),
                "objects": len(object_records),
                "uploaded": uploaded,
                "verified_existing": verified_existing,
                "total_rows": total_rows,
                "total_parquet_bytes": total_parquet_bytes,
                "manifest_key": manifest_key,
                "receipt_key": receipt_key,
                "output_dir": str(output_dir),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
