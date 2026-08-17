from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import statistics
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from crypto_autopilot.exchanges.pionex_public import PionexPublicClient  # noqa: E402


ARCHIVE_BASE = "https://data.binance.vision/data/futures/um/daily/klines"
USER_AGENT = "qookey-crypto-autopilot/0.1 pionex-binance-compare"
SYMBOLS = {
    "BTC": ("BTC_USDT_PERP", "BTCUSDT"),
    "ETH": ("ETH_USDT_PERP", "ETHUSDT"),
    "SOL": ("SOL_USDT_PERP", "SOLUSDT"),
}
INTERVALS = {
    "15m": ("15M", "15m", 15 * 60 * 1000),
    "1h": ("60M", "1h", 60 * 60 * 1000),
    "4h": ("4H", "4h", 4 * 60 * 60 * 1000),
}


def request_bytes(url: str, timeout: float = 20.0) -> bytes:
    req = Request(url, headers={"Accept": "*/*", "User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS host
        return response.read()


def archive_url(symbol: str, interval: str, day: date) -> str:
    ds = day.isoformat()
    filename = f"{symbol}-{interval}-{ds}.zip"
    return f"{ARCHIVE_BASE}/{symbol}/{interval}/{filename}"


def find_latest_common_archive_day() -> date:
    today = datetime.now(timezone.utc).date()
    for offset in range(1, 8):
        candidate = today - timedelta(days=offset)
        all_present = True
        for _, binance_symbol in SYMBOLS.values():
            for _, binance_interval, _ in INTERVALS.values():
                try:
                    request_bytes(archive_url(binance_symbol, binance_interval, candidate) + ".CHECKSUM")
                except HTTPError as exc:
                    if exc.code == 404:
                        all_present = False
                        break
                    raise
            if not all_present:
                break
        if all_present:
            return candidate
    raise RuntimeError("No common Binance USD-M daily archive day found in the last 7 days")


def normalize_timestamp_ms(raw: int) -> int:
    return raw // 1000 if raw >= 10**15 else raw


def load_binance_archive(symbol: str, interval: str, day: date) -> tuple[dict[int, dict[str, float]], str]:
    url = archive_url(symbol, interval, day)
    payload = request_bytes(url)
    checksum_text = request_bytes(url + ".CHECKSUM").decode("utf-8").strip()
    expected_sha256 = checksum_text.split()[0].lower()
    actual_sha256 = hashlib.sha256(payload).hexdigest()
    if actual_sha256 != expected_sha256:
        raise RuntimeError(f"Checksum mismatch for {url}")

    rows: dict[int, dict[str, float]] = {}
    with ZipFile(io.BytesIO(payload)) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        if len(names) != 1:
            raise RuntimeError(f"Expected one CSV in {url}, got {names}")
        with archive.open(names[0]) as raw_csv:
            reader = csv.reader(io.TextIOWrapper(raw_csv, encoding="utf-8"))
            for row in reader:
                if not row:
                    continue
                try:
                    ts = normalize_timestamp_ms(int(row[0]))
                except ValueError:
                    continue
                rows[ts] = {
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                }
    return rows, actual_sha256


def load_pionex_day(symbol: str, interval: str, interval_ms: int, day: date) -> dict[int, dict[str, float]]:
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    start_ms = int(start.timestamp() * 1000)
    end_ms = start_ms + 24 * 60 * 60 * 1000 - 1
    candles = PionexPublicClient(timeout_seconds=20).get_klines(
        symbol, interval, limit=500, end_time_ms=end_ms
    )
    return {
        c.time_ms: {
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
        }
        for c in candles
        if start_ms <= c.time_ms < start_ms + 24 * 60 * 60 * 1000
        and c.time_ms + interval_ms <= start_ms + 24 * 60 * 60 * 1000
    }


def bps(a: float, b: float) -> float:
    mid = (abs(a) + abs(b)) / 2.0
    return 0.0 if mid == 0 else abs(a - b) / mid * 10_000.0


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * p
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - pos) + ordered[hi] * (pos - lo)


def correlation(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    if denx == 0 or deny == 0:
        return None
    return num / (denx * deny)


def compare_pair(
    pionex_symbol: str,
    binance_symbol: str,
    pionex_interval: str,
    binance_interval: str,
    interval_ms: int,
    day: date,
) -> dict[str, object]:
    pionex = load_pionex_day(pionex_symbol, pionex_interval, interval_ms, day)
    binance, archive_sha256 = load_binance_archive(binance_symbol, binance_interval, day)
    common = sorted(set(pionex) & set(binance))
    if not common:
        raise RuntimeError(
            f"No common candles for {pionex_symbol}/{binance_symbol} {pionex_interval}/{binance_interval} on {day}"
        )

    field_diffs: dict[str, list[float]] = {field: [] for field in ("open", "high", "low", "close")}
    p_returns: list[float] = []
    b_returns: list[float] = []
    direction_matches = 0

    for ts in common:
        p = pionex[ts]
        b = binance[ts]
        for field in field_diffs:
            field_diffs[field].append(bps(float(p[field]), float(b[field])))
        p_delta = float(p["close"]) - float(p["open"])
        b_delta = float(b["close"]) - float(b["open"])
        p_dir = 0 if p_delta == 0 else (1 if p_delta > 0 else -1)
        b_dir = 0 if b_delta == 0 else (1 if b_delta > 0 else -1)
        if p_dir == b_dir:
            direction_matches += 1

    for prev_ts, ts in zip(common, common[1:]):
        p_prev = float(pionex[prev_ts]["close"])
        p_now = float(pionex[ts]["close"])
        b_prev = float(binance[prev_ts]["close"])
        b_now = float(binance[ts]["close"])
        if p_prev > 0 and b_prev > 0:
            p_returns.append(math.log(p_now / p_prev))
            b_returns.append(math.log(b_now / b_prev))

    close_diffs = field_diffs["close"]
    expected_rows = 24 * 60 * 60 * 1000 // interval_ms
    return {
        "day_utc": day.isoformat(),
        "pionex_symbol": pionex_symbol,
        "binance_symbol": binance_symbol,
        "pionex_interval": pionex_interval,
        "binance_interval": binance_interval,
        "expected_rows": expected_rows,
        "pionex_rows": len(pionex),
        "binance_rows": len(binance),
        "common_rows": len(common),
        "timestamp_overlap_ratio_vs_expected": len(common) / expected_rows,
        "binance_archive_sha256": archive_sha256,
        "ohlc_abs_diff_bps_mean": {
            field: statistics.fmean(values) for field, values in field_diffs.items()
        },
        "close_abs_diff_bps": {
            "mean": statistics.fmean(close_diffs),
            "median": statistics.median(close_diffs),
            "p95": percentile(close_diffs, 0.95),
            "max": max(close_diffs),
        },
        "candle_direction_agreement": direction_matches / len(common),
        "close_log_return_correlation": correlation(p_returns, b_returns),
        "note": "Volume is intentionally not compared because exchange-specific traded volume should differ.",
    }


def main() -> None:
    day = find_latest_common_archive_day()
    results: list[dict[str, object]] = []
    for _, (pionex_symbol, binance_symbol) in SYMBOLS.items():
        for _, (p_interval, b_interval, interval_ms) in INTERVALS.items():
            results.append(
                compare_pair(
                    pionex_symbol,
                    binance_symbol,
                    p_interval,
                    b_interval,
                    interval_ms,
                    day,
                )
            )

    payload = {
        "proof": "PIONEX_BINANCE_PUBLIC_MARKET_COMPARISON_V2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "authentication": "none",
        "scope": {
            "comparison_day_utc": day.isoformat(),
            "pionex_market": "PERP",
            "binance_market": "USD-M Futures",
            "binance_source": "official data.binance.vision daily Kline archives",
            "symbols": list(SYMBOLS),
            "intervals": list(INTERVALS),
            "closed_candles_only": True,
        },
        "results": results,
        "status": "PASS",
    }
    output = Path("pionex-binance-comparison.json")
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
