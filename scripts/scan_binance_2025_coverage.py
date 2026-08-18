from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from crypto_autopilot.binance_historical import pionex_perp_to_binance_usdm
from crypto_autopilot.binance_vision import BinanceVisionArchiveKey, parse_checksum


DEFAULT_AUTHORITY = "research/receipts/2026-08-17-m1a-pionex.json"
TRADE_INTERVALS = ("15m", "1h", "4h")
MARK_INTERVALS = ("1h",)


def load_candidate_universe(path: str) -> tuple[tuple[str, str], ...]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
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
    if len({pair[0] for pair in pairs}) != 15 or len({pair[1] for pair in pairs}) != 15:
        raise RuntimeError("candidate universe contains duplicate mappings")
    return tuple(pairs)


def fetch_checksum(key: BinanceVisionArchiveKey, *, retries: int = 3, timeout_seconds: float = 15.0) -> dict[str, object]:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = Request(
                key.checksum_url,
                headers={"User-Agent": "qookey-crypto-autopilot-coverage-scan/0.1"},
            )
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - validated Vision URL
                payload = response.read()
            digest, filename = parse_checksum(payload)
            if filename != key.filename:
                raise RuntimeError(
                    f"CHECKSUM filename mismatch for {key.checksum_url}: {filename} != {key.filename}"
                )
            return {
                "status": "AVAILABLE",
                "dataset": key.dataset,
                "frequency": key.frequency,
                "symbol": key.symbol,
                "interval": key.interval,
                "period": key.period,
                "archive_url": key.url,
                "checksum_url": key.checksum_url,
                "archive_filename": key.filename,
                "archive_sha256": digest,
            }
        except HTTPError as exc:
            if exc.code == 404:
                return {
                    "status": "NO_DATA",
                    "dataset": key.dataset,
                    "frequency": key.frequency,
                    "symbol": key.symbol,
                    "interval": key.interval,
                    "period": key.period,
                    "archive_url": key.url,
                    "checksum_url": key.checksum_url,
                    "archive_filename": key.filename,
                    "http_status": 404,
                }
            last_error = exc
            if exc.code not in {408, 425, 429, 500, 502, 503, 504}:
                break
        except (URLError, TimeoutError) as exc:
            last_error = exc
        if attempt + 1 < retries:
            time.sleep(0.5 * (attempt + 1))

    raise RuntimeError(f"coverage scan failed for {key.checksum_url}: {last_error}") from last_error


def build_keys(symbols: tuple[str, ...], year: int) -> tuple[BinanceVisionArchiveKey, ...]:
    keys: list[BinanceVisionArchiveKey] = []
    for symbol in symbols:
        for month in range(1, 13):
            period = f"{year:04d}-{month:02d}"
            for interval in TRADE_INTERVALS:
                keys.append(BinanceVisionArchiveKey("klines", "monthly", symbol, interval, period))
            for interval in MARK_INTERVALS:
                keys.append(BinanceVisionArchiveKey("markPriceKlines", "monthly", symbol, interval, period))
    return tuple(keys)


def summarize_symbol(symbol: str, records: list[dict[str, object]]) -> dict[str, object]:
    own = [record for record in records if record["symbol"] == symbol]
    trade = [record for record in own if record["dataset"] == "klines"]
    mark = [record for record in own if record["dataset"] == "markPriceKlines"]

    trade_by_interval: dict[str, dict[str, object]] = {}
    for interval in TRADE_INTERVALS:
        selected = sorted(
            (record for record in trade if record["interval"] == interval),
            key=lambda record: str(record["period"]),
        )
        available = [record for record in selected if record["status"] == "AVAILABLE"]
        missing = [record for record in selected if record["status"] == "NO_DATA"]
        trade_by_interval[interval] = {
            "available_months": [record["period"] for record in available],
            "missing_months": [record["period"] for record in missing],
            "available_count": len(available),
            "missing_count": len(missing),
            "first_available_month": available[0]["period"] if available else None,
            "last_available_month": available[-1]["period"] if available else None,
            "all_12_archives_present": len(available) == 12,
        }

    mark_available = sorted(
        (record for record in mark if record["status"] == "AVAILABLE"),
        key=lambda record: str(record["period"]),
    )
    mark_missing = sorted(
        (record for record in mark if record["status"] == "NO_DATA"),
        key=lambda record: str(record["period"]),
    )
    return {
        "binance_symbol": symbol,
        "trade_klines": trade_by_interval,
        "all_trade_archives_present": all(
            bool(trade_by_interval[interval]["all_12_archives_present"])
            for interval in TRADE_INTERVALS
        ),
        "mark_price_1h": {
            "available_months": [record["period"] for record in mark_available],
            "missing_months": [record["period"] for record in mark_missing],
            "available_count": len(mark_available),
            "missing_count": len(mark_missing),
            "all_12_archives_present": len(mark_available) == 12,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority", default=DEFAULT_AUTHORITY)
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", default="artifacts/binance-2025-coverage-scan.json")
    args = parser.parse_args()
    if args.year < 2020 or args.year > datetime.now(timezone.utc).year:
        raise ValueError("scan year must be between 2020 and the current UTC year")
    if not 1 <= args.workers <= 16:
        raise ValueError("workers must be between 1 and 16")

    pairs = load_candidate_universe(args.authority)
    binance_symbols = tuple(pair[1] for pair in pairs)
    keys = build_keys(binance_symbols, args.year)
    expected_checks = len(pairs) * 12 * (len(TRADE_INTERVALS) + len(MARK_INTERVALS))
    if len(keys) != expected_checks:
        raise RuntimeError("coverage scan key count mismatch")

    records: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(fetch_checksum, key): key for key in keys}
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
    if len(records) != expected_checks:
        raise RuntimeError(f"coverage scan returned {len(records)} checks, expected {expected_checks}")
    if any(record["status"] not in {"AVAILABLE", "NO_DATA"} for record in records):
        raise RuntimeError("coverage scan contains unsupported result status")

    summaries = [summarize_symbol(symbol, records) for symbol in binance_symbols]
    mapping = [
        {"pionex_symbol": pionex_symbol, "binance_symbol": binance_symbol}
        for pionex_symbol, binance_symbol in pairs
    ]
    full_trade_symbols = sorted(
        summary["binance_symbol"] for summary in summaries if summary["all_trade_archives_present"]
    )
    full_mark_symbols = sorted(
        summary["binance_symbol"]
        for summary in summaries
        if summary["mark_price_1h"]["all_12_archives_present"]
    )
    available_count = sum(record["status"] == "AVAILABLE" for record in records)
    no_data_count = sum(record["status"] == "NO_DATA" for record in records)

    payload = {
        "schema": "binance-vision-coverage-scan-v0.1",
        "status": "PASS",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "execution_exchange": "pionex",
        "native_to_execution_exchange": False,
        "may_authorize_pionex_native_history": False,
        "scan_type": "checksum_backed_archive_presence_only",
        "year": args.year,
        "candidate_authority": args.authority,
        "candidate_count": len(pairs),
        "mapping": mapping,
        "datasets": {
            "trade_klines": {"intervals": list(TRADE_INTERVALS), "months": 12},
            "mark_price_klines": {"intervals": list(MARK_INTERVALS), "months": 12},
        },
        "archive_checks": len(records),
        "available_archive_checks": available_count,
        "no_data_archive_checks": no_data_count,
        "full_2025_trade_archive_presence_symbols": full_trade_symbols,
        "full_2025_trade_archive_presence_count": len(full_trade_symbols),
        "full_2025_mark_1h_archive_presence_symbols": full_mark_symbols,
        "full_2025_mark_1h_archive_presence_count": len(full_mark_symbols),
        "symbol_summaries": summaries,
        "records": records,
        "interpretation_boundary": {
            "checksum_presence_proves_full_month_content": False,
            "archive_presence_is_not_candle_audit": True,
            "content_download_and_first_last_gap_audit_required_before_r2_authority": True,
            "no_data_is_not_listing_or_delisting_proof": True,
            "pionex_binance_equivalence_proven": False,
            "large_scale_backfill_authorized": False,
            "live_trading_authorized": False,
        },
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "github_sha": os.getenv("GITHUB_SHA"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "PASS",
                "year": args.year,
                "candidate_count": len(pairs),
                "archive_checks": len(records),
                "available": available_count,
                "no_data": no_data_count,
                "full_trade_symbols": len(full_trade_symbols),
                "full_mark_1h_symbols": len(full_mark_symbols),
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
