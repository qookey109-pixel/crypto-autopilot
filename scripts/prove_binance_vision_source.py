from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from crypto_autopilot.binance_vision import (
    BinanceVisionArchiveKey,
    ingest_kline_archive,
    ingest_mark_price_archive,
)


DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
DEFAULT_PERIOD = "2025-01"


def download(url: str, *, retries: int = 3, timeout_seconds: float = 30.0) -> bytes:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            request = Request(
                url,
                headers={"User-Agent": "qookey-crypto-autopilot-binance-vision-proof/0.1"},
            )
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - fixed URL from validated key
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if isinstance(exc, HTTPError) and exc.code == 404:
                raise RuntimeError(f"required Binance Vision proof archive is missing: {url}") from exc
            if attempt + 1 < retries:
                time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"failed to download Binance Vision proof URL: {url}: {last_error}") from last_error


def month_bounds(period: str) -> tuple[int, int]:
    start = datetime.strptime(period + "-01", "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1)
    else:
        next_month = start.replace(month=start.month + 1)
    return int(start.timestamp() * 1000), int(next_month.timestamp() * 1000) - 1


def prove_archive(key: BinanceVisionArchiveKey) -> dict[str, object]:
    archive_bytes = download(key.url)
    checksum_bytes = download(key.checksum_url)
    if key.dataset == "klines":
        result = ingest_kline_archive(
            key,
            archive_bytes=archive_bytes,
            checksum_payload=checksum_bytes,
        )
    else:
        result = ingest_mark_price_archive(
            key,
            archive_bytes=archive_bytes,
            checksum_payload=checksum_bytes,
        )

    month_start_ms, month_end_ms = month_bounds(key.period)
    expected_step_ms = {
        "15m": 15 * 60 * 1000,
        "1h": 60 * 60 * 1000,
        "4h": 4 * 60 * 60 * 1000,
    }[key.interval]
    expected_rows = (month_end_ms + 1 - month_start_ms) // expected_step_ms
    expected_last_open_ms = month_end_ms + 1 - expected_step_ms

    receipt = result.receipt
    if receipt.first_time_ms != month_start_ms:
        raise RuntimeError(
            f"proof archive does not begin at month boundary: {key.filename}: "
            f"{receipt.first_time_ms} != {month_start_ms}"
        )
    if receipt.last_time_ms != expected_last_open_ms:
        raise RuntimeError(
            f"proof archive does not end at expected last bar: {key.filename}: "
            f"{receipt.last_time_ms} != {expected_last_open_ms}"
        )
    if receipt.row_count != expected_rows:
        raise RuntimeError(
            f"proof archive row count mismatch: {key.filename}: {receipt.row_count} != {expected_rows}"
        )

    return {
        **asdict(receipt),
        "expected_rows": expected_rows,
        "full_month_coverage_verified": True,
        "archive_bytes": len(archive_bytes),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default=DEFAULT_PERIOD)
    parser.add_argument("--symbols", nargs="+", default=list(DEFAULT_SYMBOLS))
    parser.add_argument("--output", default="/tmp/binance-vision-live-proof.json")
    args = parser.parse_args()

    records: list[dict[str, object]] = []
    for symbol in args.symbols:
        records.append(
            prove_archive(
                BinanceVisionArchiveKey("klines", "monthly", symbol.upper(), "15m", args.period)
            )
        )
        records.append(
            prove_archive(
                BinanceVisionArchiveKey("markPriceKlines", "monthly", symbol.upper(), "1h", args.period)
            )
        )

    provider_ids = {record["provider"] for record in records}
    if provider_ids != {"binance_usdm"}:
        raise RuntimeError(f"unexpected provider ids in proof: {provider_ids}")
    if any(record["native_to_pionex"] for record in records):
        raise RuntimeError("Binance Vision proof must never become Pionex-native")
    if any(record["may_authorize_pionex_native_history"] for record in records):
        raise RuntimeError("Binance Vision proof must not authorize Pionex-native history")

    payload = {
        "schema": "binance-vision-live-proof-v0.1",
        "status": "PASS",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "execution_exchange": "pionex",
        "native_to_execution_exchange": False,
        "may_authorize_pionex_native_history": False,
        "period": args.period,
        "symbols": sorted({symbol.upper() for symbol in args.symbols}),
        "archive_count": len(records),
        "records": records,
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "github_sha": os.getenv("GITHUB_SHA"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "live_trading_authorized": False,
        "private_api_used": False,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": payload["status"],
        "provider": payload["provider"],
        "period": payload["period"],
        "symbols": payload["symbols"],
        "archive_count": payload["archive_count"],
        "total_rows": sum(int(record["row_count"]) for record in records),
        "output": str(output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
