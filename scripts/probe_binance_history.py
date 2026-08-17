from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zipfile import ZipFile


ARCHIVE_BASE = "https://data.binance.vision/data"
USER_AGENT = "qookey-crypto-autopilot/0.1 binance-history-probe"
SOURCES = {
    "binance_spot": {
        "path": "spot/monthly/klines",
        "start_year": 2017,
    },
    "binance_usdm_futures": {
        "path": "futures/um/monthly/klines",
        "start_year": 2019,
    },
}
SYMBOLS = ("BTCUSDT", "ETHUSDT")
INTERVALS = ("15m", "1h", "4h")


def _request_bytes(url: str, *, timeout_seconds: float = 20.0) -> bytes:
    request = Request(
        url,
        headers={"Accept": "*/*", "User-Agent": USER_AGENT},
    )
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - fixed HTTPS host
        return response.read()


def _month_iter(start_year: int, end_year: int, end_month: int):
    year = start_year
    month = 1
    while (year, month) <= (end_year, end_month):
        yield year, month
        month += 1
        if month == 13:
            month = 1
            year += 1


def archive_url(source_path: str, symbol: str, interval: str, year: int, month: int) -> str:
    filename = f"{symbol}-{interval}-{year:04d}-{month:02d}.zip"
    return f"{ARCHIVE_BASE}/{source_path}/{symbol}/{interval}/{filename}"


def find_earliest_archive(
    source_path: str,
    symbol: str,
    interval: str,
    *,
    start_year: int,
    now: datetime,
) -> str:
    for year, month in _month_iter(start_year, now.year, now.month):
        url = archive_url(source_path, symbol, interval, year, month)
        try:
            _request_bytes(f"{url}.CHECKSUM")
        except HTTPError as exc:
            if exc.code == 404:
                continue
            raise
        return url
    raise RuntimeError(f"No Binance archive found for {symbol} {interval}")


def _normalize_timestamp_ms(raw: int) -> int:
    # Binance Spot archives changed from millisecond to microsecond timestamps
    # beginning in 2025. Keep the project Candle convention in milliseconds.
    return raw // 1000 if raw >= 10**15 else raw


def inspect_archive(url: str) -> dict[str, object]:
    payload = _request_bytes(url)
    checksum_text = _request_bytes(f"{url}.CHECKSUM").decode("utf-8").strip()
    expected_sha256 = checksum_text.split()[0].lower()
    actual_sha256 = hashlib.sha256(payload).hexdigest()
    if actual_sha256 != expected_sha256:
        raise RuntimeError(f"Checksum mismatch for {url}")

    with ZipFile(io.BytesIO(payload)) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        if len(names) != 1:
            raise RuntimeError(f"Expected exactly one CSV in {url}, got {names}")
        with archive.open(names[0]) as raw_csv:
            reader = csv.reader(io.TextIOWrapper(raw_csv, encoding="utf-8"))
            first_open_ms: int | None = None
            last_open_ms: int | None = None
            rows = 0
            for row in reader:
                if not row:
                    continue
                open_ms = _normalize_timestamp_ms(int(row[0]))
                if first_open_ms is None:
                    first_open_ms = open_ms
                last_open_ms = open_ms
                rows += 1

    if rows == 0 or first_open_ms is None or last_open_ms is None:
        raise RuntimeError(f"Empty Binance archive: {url}")

    filename = url.rsplit("/", 1)[-1]
    month = filename.rsplit("-", 2)[-2] + "-" + filename.rsplit("-", 1)[-1].removesuffix(".zip")
    return {
        "archive": filename,
        "archive_month": month,
        "archive_bytes": len(payload),
        "rows": rows,
        "first_open_time_ms": first_open_ms,
        "first_open_time_utc": datetime.fromtimestamp(first_open_ms / 1000, tz=timezone.utc).isoformat(),
        "last_open_time_ms": last_open_ms,
        "last_open_time_utc": datetime.fromtimestamp(last_open_ms / 1000, tz=timezone.utc).isoformat(),
        "sha256": actual_sha256,
        "checksum_verified": True,
    }


def run_probe() -> dict[str, object]:
    now = datetime.now(timezone.utc)
    results: list[dict[str, object]] = []
    for source_name, source in SOURCES.items():
        for symbol in SYMBOLS:
            for interval in INTERVALS:
                url = find_earliest_archive(
                    str(source["path"]),
                    symbol,
                    interval,
                    start_year=int(source["start_year"]),
                    now=now,
                )
                inspection = inspect_archive(url)
                results.append(
                    {
                        "source": source_name,
                        "symbol": symbol,
                        "interval": interval,
                        **inspection,
                    }
                )

    return {
        "proof": "BINANCE_PUBLIC_HISTORY_DEPTH_PROBE_V1",
        "created_at": now.isoformat(),
        "authentication": "none",
        "scope": {
            "symbols": list(SYMBOLS),
            "intervals": list(INTERVALS),
            "sources": list(SOURCES),
            "method": "official Binance Public Data monthly Kline archives; earliest existing archive only",
        },
        "results": results,
        "status": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe Binance public historical Kline depth")
    parser.add_argument("--output", help="Optional JSON output path")
    args = parser.parse_args()

    result = run_probe()
    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
