from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from crypto_autopilot.binance.coverage import (
    SERIES,
    attach_audited_boundaries,
    build_archive_keys,
    daily_periods,
    month_periods,
    summarize_presence,
    summarize_symbol_boundaries,
)
from crypto_autopilot.binance_historical import pionex_perp_to_binance_usdm
from crypto_autopilot.binance.vision import (
    BinanceVisionArchiveKey,
    ingest_kline_archive,
    ingest_mark_price_archive,
    parse_checksum,
)


DEFAULT_CONFIG = "config/binance_max_coverage_v0_1.json"
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
        binance_symbol = pionex_perp_to_binance_usdm(pionex_symbol)
        pairs.append((pionex_symbol, binance_symbol))
    if len({left for left, _ in pairs}) != 15 or len({right for _, right in pairs}) != 15:
        raise RuntimeError("candidate universe contains duplicate mappings")
    return tuple(pairs)


def fetch_bytes(
    url: str,
    *,
    allow_not_found: bool,
    retries: int = 3,
    timeout_seconds: float = 20.0,
) -> bytes | None:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = Request(
                url,
                headers={"User-Agent": "qookey-crypto-autopilot-max-coverage/0.1"},
            )
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
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


def probe_checksum(key: BinanceVisionArchiveKey) -> dict[str, object]:
    payload = fetch_bytes(key.checksum_url, allow_not_found=True)
    base = {
        "dataset": key.dataset,
        "frequency": key.frequency,
        "symbol": key.symbol,
        "interval": key.interval,
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


def audit_archive(key: BinanceVisionArchiveKey) -> dict[str, object]:
    checksum_payload = fetch_bytes(key.checksum_url, allow_not_found=False)
    archive_bytes = fetch_bytes(key.url, allow_not_found=False)
    if checksum_payload is None or archive_bytes is None:
        raise RuntimeError(f"archive disappeared after availability probe: {key.identity}")

    if key.dataset == "klines":
        receipt = ingest_kline_archive(
            key,
            archive_bytes=archive_bytes,
            checksum_payload=checksum_payload,
        ).receipt
    else:
        receipt = ingest_mark_price_archive(
            key,
            archive_bytes=archive_bytes,
            checksum_payload=checksum_payload,
        ).receipt
    return asdict(receipt)


def previous_month(period_date: date) -> date:
    first = period_date.replace(day=1)
    return (first - timedelta(days=1)).replace(day=1)


def history_cap_floor(today: date, years: int) -> date:
    if years <= 0:
        raise ValueError("history cap years must be positive")
    try:
        return today.replace(year=today.year - years, day=1)
    except ValueError:
        return today.replace(year=today.year - years, month=2, day=1)


def probe_many(
    keys: tuple[BinanceVisionArchiveKey, ...],
    *,
    workers: int,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(probe_checksum, key): key for key in keys}
        for future in as_completed(futures):
            records.append(future.result())
    records.sort(
        key=lambda record: (
            str(record["symbol"]),
            str(record["dataset"]),
            str(record["interval"]),
            str(record["period"]),
        )
    )
    if len(records) != len(keys):
        raise RuntimeError(f"probe count mismatch: observed={len(records)} expected={len(keys)}")
    return records


def receipt_key(receipt: dict[str, object]) -> tuple[str, str, str, str, str]:
    return (
        str(receipt["dataset"]),
        str(receipt["frequency"]),
        str(receipt["symbol"]),
        str(receipt["interval"]),
        str(receipt["period"]),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--output", default="artifacts/binance-max-coverage-discovery.json")
    args = parser.parse_args()

    config = load_json(args.config)
    if config.get("status") != "PROTOCOL_FROZEN_BEFORE_DISCOVERY":
        raise RuntimeError("coverage protocol must be frozen before live discovery")
    if config.get("provider") != "binance_usdm" or config.get("delivery") != "binance_vision":
        raise RuntimeError("coverage protocol provider/delivery mismatch")
    if config.get("source_switch_authorized") is not False:
        raise RuntimeError("coverage discovery must not authorize source switching")
    if config.get("large_scale_backfill_authorized") is not False:
        raise RuntimeError("coverage discovery must not authorize large-scale backfill")
    if config.get("current_month_daily_extension") is not True:
        raise RuntimeError("current-month daily extension must remain enabled")

    authority = str(config["candidate_authority"])
    pairs = load_candidate_universe(authority)
    symbols = tuple(binance for _, binance in pairs)

    configured_series = tuple(
        (str(row["dataset"]), str(row["interval"])) for row in config.get("series", [])
    )
    if configured_series != SERIES:
        raise RuntimeError(f"coverage series must remain frozen as {SERIES}")

    workers = args.workers or int(config.get("workers", 12))
    if not 1 <= workers <= 16:
        raise ValueError("workers must be between 1 and 16")

    now = datetime.now(timezone.utc)
    today = now.date()
    last_complete_month = previous_month(today)
    if config.get("scan_floor_policy") != "PROJECT_HISTORY_CAP_ONLY":
        raise RuntimeError("coverage discovery must not assume a provider onset month")
    if config.get("provider_earliest_month_assumption") is not None:
        raise RuntimeError("provider earliest month must remain unassumed")
    scan_floor = history_cap_floor(today, int(config["project_history_cap_years"]))

    monthly_periods = month_periods(
        scan_floor.strftime("%Y-%m"),
        last_complete_month.strftime("%Y-%m"),
    )
    monthly_keys = build_archive_keys(symbols, frequency="monthly", periods=monthly_periods)
    monthly_records = probe_many(monthly_keys, workers=workers)

    yesterday = today - timedelta(days=1)
    current_month_start = today.replace(day=1)
    current_daily_periods = daily_periods(current_month_start, yesterday)
    daily_keys = build_archive_keys(
        symbols,
        frequency="daily",
        periods=current_daily_periods,
    )
    daily_records = probe_many(daily_keys, workers=workers) if daily_keys else []

    monthly_summaries: list[dict[str, object]] = []
    daily_summaries: dict[tuple[str, str, str], dict[str, object]] = {}
    for symbol in symbols:
        for dataset, interval in SERIES:
            monthly_summaries.append(
                summarize_presence(
                    monthly_records,
                    symbol=symbol,
                    dataset=dataset,
                    interval=interval,
                    ordered_periods=monthly_periods,
                )
            )
            if current_daily_periods:
                daily_summaries[(symbol, dataset, interval)] = summarize_presence(
                    daily_records,
                    symbol=symbol,
                    dataset=dataset,
                    interval=interval,
                    ordered_periods=current_daily_periods,
                )

    audit_keys: dict[tuple[str, str, str, str, str], BinanceVisionArchiveKey] = {}
    edge_plan: dict[
        tuple[str, str, str],
        dict[str, tuple[str, str, str, str, str] | None],
    ] = {}
    for summary in monthly_summaries:
        symbol = str(summary["symbol"])
        dataset = str(summary["dataset"])
        interval = str(summary["interval"])
        identity = (symbol, dataset, interval)
        plan: dict[str, tuple[str, str, str, str, str] | None] = {
            "first": None,
            "last_monthly": None,
            "latest_daily": None,
        }
        first_month = summary.get("first_available_period")
        last_month = summary.get("last_available_period")
        if first_month is not None:
            key = BinanceVisionArchiveKey(dataset, "monthly", symbol, interval, str(first_month))
            audit_keys[key.identity] = key
            plan["first"] = key.identity
        if last_month is not None:
            key = BinanceVisionArchiveKey(dataset, "monthly", symbol, interval, str(last_month))
            audit_keys[key.identity] = key
            plan["last_monthly"] = key.identity

        daily_summary = daily_summaries.get(identity)
        if daily_summary is not None:
            first_day = daily_summary.get("first_available_period")
            last_day = daily_summary.get("last_available_period")
            if first_month is None and first_day is not None:
                key = BinanceVisionArchiveKey(dataset, "daily", symbol, interval, str(first_day))
                audit_keys[key.identity] = key
                plan["first"] = key.identity
            if last_day is not None:
                key = BinanceVisionArchiveKey(dataset, "daily", symbol, interval, str(last_day))
                audit_keys[key.identity] = key
                plan["latest_daily"] = key.identity
        edge_plan[identity] = plan

    audited_receipts: dict[tuple[str, str, str, str, str], dict[str, object]] = {}
    with ThreadPoolExecutor(max_workers=min(workers, 8)) as executor:
        futures = {executor.submit(audit_archive, key): key for key in audit_keys.values()}
        for future in as_completed(futures):
            receipt = future.result()
            audited_receipts[receipt_key(receipt)] = receipt

    series_summaries: list[dict[str, object]] = []
    for summary in monthly_summaries:
        identity = (
            str(summary["symbol"]),
            str(summary["dataset"]),
            str(summary["interval"]),
        )
        plan = edge_plan[identity]
        first_receipt = audited_receipts.get(plan["first"]) if plan["first"] else None
        last_receipt = (
            audited_receipts.get(plan["last_monthly"]) if plan["last_monthly"] else None
        )
        latest_daily_receipt = (
            audited_receipts.get(plan["latest_daily"]) if plan["latest_daily"] else None
        )
        attached = attach_audited_boundaries(
            summary,
            first_receipt=first_receipt,
            last_receipt=last_receipt,
            latest_daily_receipt=latest_daily_receipt,
        )
        attached["current_month_daily_presence"] = daily_summaries.get(identity)
        series_summaries.append(attached)

    symbol_summaries = [
        summarize_symbol_boundaries(symbol, series_summaries) for symbol in symbols
    ]
    mapping = [
        {"pionex_symbol": pionex, "binance_symbol": binance} for pionex, binance in pairs
    ]
    trade_common_count = sum(
        bool(summary["trade_common_window"]["available"]) for summary in symbol_summaries
    )
    strategy_common_count = sum(
        bool(summary["strategy_price_common_window"]["available"])
        for summary in symbol_summaries
    )

    payload = {
        "schema": "binance-vision-max-coverage-discovery-v0.1",
        "execution_status": "PASS",
        "coverage_status": "COMPLETE",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "execution_exchange": "pionex",
        "native_to_execution_exchange": False,
        "may_authorize_pionex_native_history": False,
        "candidate_authority": authority,
        "candidate_count": len(pairs),
        "mapping": mapping,
        "project_history_cap_years": int(config["project_history_cap_years"]),
        "scan_floor_policy": str(config["scan_floor_policy"]),
        "provider_earliest_month_assumption": None,
        "effective_scan_floor_month": scan_floor.strftime("%Y-%m"),
        "last_complete_month_scanned": last_complete_month.strftime("%Y-%m"),
        "current_month_daily_extension_through": (
            yesterday.isoformat() if current_daily_periods else None
        ),
        "series": [
            {"dataset": dataset, "interval": interval} for dataset, interval in SERIES
        ],
        "monthly_archive_checks": len(monthly_records),
        "monthly_available_checks": sum(
            record["status"] == "AVAILABLE" for record in monthly_records
        ),
        "monthly_no_data_checks": sum(
            record["status"] == "NO_DATA" for record in monthly_records
        ),
        "current_month_daily_checks": len(daily_records),
        "current_month_daily_available_checks": sum(
            record["status"] == "AVAILABLE" for record in daily_records
        ),
        "current_month_daily_no_data_checks": sum(
            record["status"] == "NO_DATA" for record in daily_records
        ),
        "audited_edge_archive_count": len(audited_receipts),
        "trade_common_window_symbol_count": trade_common_count,
        "strategy_price_common_window_symbol_count": strategy_common_count,
        "symbol_summaries": symbol_summaries,
        "monthly_records": monthly_records,
        "current_month_daily_records": daily_records,
        "interpretation_boundary": {
            "coverage_boundary_discovery_complete": True,
            "edge_archives_checksum_and_content_audited": True,
            "interior_archive_presence_checksum_backed": True,
            "full_interior_content_continuity_proven": False,
            "archive_presence_is_not_listing_or_delisting_proof": True,
            "funding_coverage_evaluated": False,
            "open_interest_coverage_evaluated": False,
            "pionex_binance_equivalence_proven": False,
            "source_switch_authorized": False,
            "large_scale_backfill_authorized": False,
            "r2_writes_performed": False,
            "live_trading_authorized": False,
        },
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "github_sha": os.getenv("GITHUB_SHA"),
        "generated_at_utc": now.isoformat(),
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "execution_status": "PASS",
                "coverage_status": "COMPLETE",
                "candidates": len(pairs),
                "monthly_checks": len(monthly_records),
                "daily_checks": len(daily_records),
                "audited_edges": len(audited_receipts),
                "trade_common_symbols": trade_common_count,
                "strategy_price_common_symbols": strategy_common_count,
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
