from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from crypto_autopilot.binance_funding import (
    BinanceVisionFundingArchive,
    BinanceVisionFundingArchiveKey,
    combine_funding_archives,
    funding_to_parquet,
    ingest_funding_archive,
    parquet_to_funding,
)
from crypto_autopilot.binance_funding_materialization_plan_v0_2 import build_v0_2_scope
from crypto_autopilot.binance.funding_materializer_v0_2 import (
    AUTHORITY_PATH,
    CADENCE_TOLERANCE_MS,
    CONFIG_PATH,
    FundingChecksumRecord,
    checksum_set_sha256,
    source_keys_from_scope,
    validate_runtime_authority,
)
from crypto_autopilot.binance.vision import parse_checksum


COVERAGE_PATH = "research/receipts/2026-08-18-binance-funding-coverage.json"


class FundingPreflightError(RuntimeError):
    pass


def load_json(path: str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise FundingPreflightError(f"expected JSON object: {path}")
    return payload


def fetch_bytes(url: str, *, attempts: int = 4, timeout_seconds: float = 45.0) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = Request(
            url,
            headers={
                "Accept": "*/*",
                "User-Agent": "qookey-crypto-autopilot-funding-v0.2-preflight/1.0",
            },
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - frozen Binance Vision HTTPS source
                return response.read()
        except HTTPError as exc:
            last_error = exc
            if exc.code not in {408, 425, 429, 500, 502, 503, 504}:
                break
        except (URLError, TimeoutError) as exc:
            last_error = exc
        if attempt + 1 < attempts:
            time.sleep(1.0 * (attempt + 1))
    raise FundingPreflightError(f"failed to fetch {url}: {last_error}") from last_error


def fetch_and_audit(
    key: BinanceVisionFundingArchiveKey,
) -> tuple[FundingChecksumRecord, BinanceVisionFundingArchive]:
    checksum_payload = fetch_bytes(key.checksum_url)
    expected_sha256, filename = parse_checksum(checksum_payload)
    if filename != key.filename:
        raise FundingPreflightError(
            f"Funding CHECKSUM filename mismatch for {key.identity}: {filename}"
        )
    archive_payload = fetch_bytes(key.url)
    audited = ingest_funding_archive(
        key,
        archive_bytes=archive_payload,
        checksum_payload=checksum_payload,
        cadence_jitter_tolerance_ms=CADENCE_TOLERANCE_MS,
    )
    if audited.receipt.archive_sha256 != expected_sha256:
        raise FundingPreflightError(f"Funding checksum mismatch after ingest: {key.identity}")
    return FundingChecksumRecord(key.symbol, key.period, expected_sha256), audited


def run_preflight(*, workers: int) -> dict[str, object]:
    config = load_json(CONFIG_PATH)
    authority = load_json(AUTHORITY_PATH)
    coverage = load_json(COVERAGE_PATH)
    scope = build_v0_2_scope(coverage)
    scope_sha, expected_checksum_sha = validate_runtime_authority(
        config=config,
        authority=authority,
        scope=scope,
    )
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
                raise FundingPreflightError(f"Funding source audit failed for {key.identity}: {exc}") from exc
            checksum_records.append(checksum_record)
            archives[key.identity] = archive

    checksum_records.sort(key=lambda row: (row.symbol, row.period))
    if len(checksum_records) != 1003 or len(archives) != 1003:
        raise FundingPreflightError(
            f"Funding V0.2 expected 1,003 audited archives, got {len(archives)}"
        )
    observed_checksum_sha = checksum_set_sha256(tuple(checksum_records))
    if observed_checksum_sha != expected_checksum_sha:
        raise FundingPreflightError(
            "Funding V0.2 official source checksum-set changed; explicit source revision review is required"
        )

    annual_rows: list[dict[str, object]] = []
    total_funding_rows = 0
    total_parquet_bytes = 0
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
        restored = parquet_to_funding(artifact.payload)
        if restored != list(observations):
            raise FundingPreflightError(
                f"Funding annual Parquet round-trip mismatch: {annual.symbol} {annual.year}"
            )
        total_funding_rows += artifact.rows
        total_parquet_bytes += len(artifact.payload)
        annual_rows.append(
            {
                "symbol": annual.symbol,
                "year": annual.year,
                "months": list(annual.months),
                "source_archive_count": annual.source_archive_count,
                "rows": artifact.rows,
                "first_time_ms": artifact.first_time_ms,
                "last_time_ms": artifact.last_time_ms,
                "parquet_bytes": len(artifact.payload),
                "parquet_sha256": artifact.sha256,
                "canonical_key": annual.canonical_key,
                "partition_receipt_key": annual.receipt_key,
            }
        )

    annual_rows.sort(key=lambda row: (str(row["symbol"]), int(row["year"])))
    if len(annual_rows) != 94:
        raise FundingPreflightError(
            f"Funding V0.2 expected 94 annual builds, got {len(annual_rows)}"
        )
    if any(row["symbol"] == "HYPEUSDT" and row["year"] == 2026 for row in annual_rows):
        raise FundingPreflightError("HYPEUSDT 2026 escaped V0.2 preflight scope")

    return {
        "schema": "binance-funding-r2-materialization-preflight-v0.2",
        "status": "PASS",
        "stage": "BINANCE_FUNDING_R2_V0_2_FULL_PREFLIGHT_PASS",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "dataset": "fundingRate",
        "canonical_scope_sha256": scope_sha,
        "source_checksum_set_sha256": observed_checksum_sha,
        "source_archive_count": len(checksum_records),
        "annual_canonical_object_count": len(annual_rows),
        "annual_partition_receipt_count": len(annual_rows),
        "planned_run_metadata_objects": 4,
        "planned_total_r2_object_identities": 192,
        "total_funding_rows": total_funding_rows,
        "total_local_parquet_bytes": total_parquet_bytes,
        "cadence_jitter_tolerance_ms": CADENCE_TOLERANCE_MS,
        "all_source_checksums_match_authorized_set": True,
        "all_source_content_audits_pass": True,
        "all_annual_cross_month_audits_pass": True,
        "all_annual_parquet_round_trips_pass": True,
        "hypeusdt_2026_deferred": True,
        "r2_credentials_used": False,
        "r2_client_constructed": False,
        "r2_writes_performed": False,
        "source_switch_authorized": False,
        "provider_splicing_authorized": False,
        "interpolation_authorized": False,
        "pionex_native_relabel_authorized": False,
        "backtest_admission_authorized": False,
        "trade_plan_authorized": False,
        "live_trading_authorized": False,
        "source_checksums": [
            {
                "symbol": row.symbol,
                "period": row.period,
                "archive_sha256": row.archive_sha256,
            }
            for row in checksum_records
        ],
        "annual_builds": annual_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument(
        "--output",
        default="artifacts/binance-funding-r2-v0-2/preflight.json",
    )
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 24:
        raise ValueError("workers must be between 1 and 24")

    result = run_preflight(workers=args.workers)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "stage": result["stage"],
                "source_archive_count": result["source_archive_count"],
                "annual_canonical_object_count": result["annual_canonical_object_count"],
                "total_funding_rows": result["total_funding_rows"],
                "total_local_parquet_bytes": result["total_local_parquet_bytes"],
                "canonical_scope_sha256": result["canonical_scope_sha256"],
                "source_checksum_set_sha256": result["source_checksum_set_sha256"],
                "r2_writes_performed": False,
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
