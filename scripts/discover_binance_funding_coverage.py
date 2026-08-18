from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from crypto_autopilot.binance_coverage import month_periods
from crypto_autopilot.binance_funding import BinanceVisionFundingArchiveKey, ingest_funding_archive
from crypto_autopilot.binance_funding_coverage import (
    attach_funding_boundaries,
    summarize_funding_presence,
    validate_funding_coverage_config,
    validate_source_proof_authority,
)
from crypto_autopilot.binance_historical import pionex_perp_to_binance_usdm
from crypto_autopilot.binance_vision import parse_checksum


DEFAULT_CONFIG = "config/binance_funding_coverage_v0_1.json"
TRANSIENT_HTTP = {408, 425, 429, 500, 502, 503, 504}


def load_json(path: str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def load_candidate_universe(path: str) -> tuple[tuple[str, str], ...]:
    payload = load_json(path)
    if payload.get("stage") != "M1A_COMPLETE" or payload.get("audit", {}).get("pass") is not True:
        raise RuntimeError("M1A authority must be COMPLETE with audit PASS")
    rows = payload.get("selected_universe") or []
    if len(rows) != 15:
        raise RuntimeError(f"expected frozen 15-market M1A universe, got {len(rows)}")
    pairs: list[tuple[str, str]] = []
    for row in rows:
        pionex_symbol = str(row.get("symbol") or "")
        pairs.append((pionex_symbol, pionex_perp_to_binance_usdm(pionex_symbol)))
    if len({left for left, _ in pairs}) != 15 or len({right for _, right in pairs}) != 15:
        raise RuntimeError("candidate universe contains duplicate symbol mappings")
    return tuple(pairs)


def previous_month(value: date) -> date:
    first = value.replace(day=1)
    return (first - timedelta(days=1)).replace(day=1)


def history_cap_floor(today: date, years: int) -> date:
    if years <= 0:
        raise ValueError("history cap years must be positive")
    try:
        return today.replace(year=today.year - years, day=1)
    except ValueError:
        return today.replace(year=today.year - years, month=2, day=1)


def fetch_bytes(
    url: str,
    *,
    allow_not_found: bool,
    retries: int = 3,
    timeout_seconds: float = 20.0,
) -> bytes | None:
    last_error: Exception | None = None
    for attempt in range(retries):
        request = Request(
            url,
            headers={"Accept": "*/*", "User-Agent": "qookey-crypto-autopilot-funding-coverage/0.1"},
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - frozen HTTPS host
                return response.read()
        except HTTPError as exc:
            if allow_not_found and exc.code == 404:
                return None
            last_error = exc
            if exc.code not in TRANSIENT_HTTP:
                break
        except (URLError, TimeoutError) as exc:
            last_error = exc
        if attempt + 1 < retries:
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"fetch failed for {url}: {last_error}") from last_error


def probe_checksum(key: BinanceVisionFundingArchiveKey) -> dict[str, object]:
    payload = fetch_bytes(key.checksum_url, allow_not_found=True)
    base = {
        "dataset": "fundingRate",
        "frequency": "monthly",
        "symbol": key.symbol,
        "period": key.period,
        "archive_url": key.url,
        "checksum_url": key.checksum_url,
        "archive_filename": key.filename,
    }
    if payload is None:
        return {**base, "status": "NO_DATA", "http_status": 404}
    digest, filename = parse_checksum(payload)
    if filename != key.filename:
        raise RuntimeError(
            f"CHECKSUM filename mismatch for {key.checksum_url}: {filename} != {key.filename}"
        )
    return {**base, "status": "AVAILABLE", "archive_sha256": digest}


def probe_many(
    keys: tuple[BinanceVisionFundingArchiveKey, ...],
    *,
    workers: int,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(probe_checksum, key): key for key in keys}
        for future in as_completed(futures):
            records.append(future.result())
    records.sort(key=lambda record: (str(record["symbol"]), str(record["period"])))
    if len(records) != len(keys):
        raise RuntimeError(f"Funding coverage probe count mismatch: {len(records)} != {len(keys)}")
    return records


def audit_archive(key: BinanceVisionFundingArchiveKey) -> dict[str, object]:
    try:
        checksum = fetch_bytes(key.checksum_url, allow_not_found=False)
        archive = fetch_bytes(key.url, allow_not_found=False)
        if checksum is None or archive is None:
            raise RuntimeError("archive disappeared after availability probe")
        return asdict(
            ingest_funding_archive(
                key,
                archive_bytes=archive,
                checksum_payload=checksum,
            ).receipt
        )
    except Exception as exc:
        raise RuntimeError(
            f"Funding edge audit failed for symbol={key.symbol} period={key.period}: {exc}"
        ) from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--output", default="artifacts/binance-funding-coverage.json")
    args = parser.parse_args()

    config = load_json(args.config)
    validate_funding_coverage_config(config)
    source_proof_path = str(config["source_proof_authority"])
    validate_source_proof_authority(load_json(source_proof_path))

    candidate_path = str(config["candidate_authority"])
    pairs = load_candidate_universe(candidate_path)
    symbols = tuple(binance for _, binance in pairs)
    workers = args.workers or int(config.get("workers", 12))
    if not 1 <= workers <= 16:
        raise ValueError("workers must be between 1 and 16")

    now = datetime.now(timezone.utc)
    today = now.date()
    last_complete_month = previous_month(today)
    scan_floor = history_cap_floor(today, int(config["project_history_cap_years"]))
    periods = month_periods(scan_floor.strftime("%Y-%m"), last_complete_month.strftime("%Y-%m"))
    keys = tuple(
        BinanceVisionFundingArchiveKey(symbol=symbol, period=period)
        for symbol in symbols
        for period in periods
    )
    records = probe_many(keys, workers=workers)

    base_summaries = [
        summarize_funding_presence(records, symbol=symbol, ordered_periods=periods)
        for symbol in symbols
    ]

    audit_keys: dict[tuple[str, str], BinanceVisionFundingArchiveKey] = {}
    edge_plan: dict[str, dict[str, tuple[str, str] | None]] = {}
    for summary in base_summaries:
        symbol = str(summary["symbol"])
        plan: dict[str, tuple[str, str] | None] = {"first": None, "last": None}
        first_period = summary.get("first_available_period")
        last_period = summary.get("last_available_period")
        if first_period is not None:
            key = BinanceVisionFundingArchiveKey(symbol, str(first_period))
            audit_keys[key.identity] = key
            plan["first"] = key.identity
        if last_period is not None:
            key = BinanceVisionFundingArchiveKey(symbol, str(last_period))
            audit_keys[key.identity] = key
            plan["last"] = key.identity
        edge_plan[symbol] = plan

    audited: dict[tuple[str, str], dict[str, object]] = {}
    with ThreadPoolExecutor(max_workers=min(workers, 8)) as executor:
        futures = {executor.submit(audit_archive, key): key for key in audit_keys.values()}
        for future in as_completed(futures):
            receipt = future.result()
            audited[(str(receipt["symbol"]), str(receipt["period"]))] = receipt

    summaries: list[dict[str, object]] = []
    pair_by_binance = {binance: pionex for pionex, binance in pairs}
    for summary in base_summaries:
        symbol = str(summary["symbol"])
        plan = edge_plan[symbol]
        attached = attach_funding_boundaries(
            summary,
            first_receipt=audited.get(plan["first"]) if plan["first"] else None,
            last_receipt=audited.get(plan["last"]) if plan["last"] else None,
        )
        attached["pionex_symbol"] = pair_by_binance[symbol]
        summaries.append(attached)
    summaries.sort(key=lambda row: str(row["symbol"]))

    available_symbols = [row for row in summaries if row["first_available_period"] is not None]
    internal_gap_symbols = [
        str(row["symbol"])
        for row in summaries
        if row["missing_periods_within_observed_span"]
    ]

    payload = {
        "schema": "binance-funding-max-coverage-discovery-v0.1",
        "execution_status": "PASS",
        "coverage_status": "COMPLETE",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "execution_exchange": "pionex",
        "native_to_execution_exchange": False,
        "may_authorize_pionex_native_history": False,
        "dataset": "fundingRate",
        "frequency": "monthly",
        "candidate_authority": candidate_path,
        "source_proof_authority": source_proof_path,
        "candidate_count": len(pairs),
        "project_history_cap_years": int(config["project_history_cap_years"]),
        "scan_floor_policy": str(config["scan_floor_policy"]),
        "provider_earliest_month_assumption": None,
        "effective_scan_floor_month": scan_floor.strftime("%Y-%m"),
        "last_complete_month_scanned": last_complete_month.strftime("%Y-%m"),
        "current_incomplete_month_deferred": today.strftime("%Y-%m"),
        "monthly_archive_checks": len(records),
        "monthly_available_checks": sum(record["status"] == "AVAILABLE" for record in records),
        "monthly_no_data_checks": sum(record["status"] == "NO_DATA" for record in records),
        "audited_edge_archive_count": len(audited),
        "symbols_with_observed_funding_coverage": len(available_symbols),
        "symbols_without_observed_funding_coverage": len(summaries) - len(available_symbols),
        "symbols_with_internal_monthly_presence_gap": internal_gap_symbols,
        "symbol_summaries": summaries,
        "monthly_records": records,
        "interpretation_boundary": {
            "coverage_boundary_discovery_complete": True,
            "edge_archives_checksum_schema_and_cadence_audited": True,
            "interior_archive_presence_checksum_backed": True,
            "full_interior_content_continuity_proven": False,
            "archive_presence_is_listing_or_delisting_proof": False,
            "funding_onset_inferred_from_trade_onset": False,
            "current_incomplete_month_included": False,
            "proves_funding_r2_materialization": False,
            "funding_materialization_authorized": False,
            "source_switch_authorized": False,
            "pionex_native_relabel_authorized": False,
            "backtest_admission_authorized": False,
            "r2_writes_performed": False,
            "live_trading_authorized": False,
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "execution_status": "PASS",
                "checks": len(records),
                "available": payload["monthly_available_checks"],
                "no_data": payload["monthly_no_data_checks"],
                "covered_symbols": payload["symbols_with_observed_funding_coverage"],
                "internal_gap_symbols": internal_gap_symbols,
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
