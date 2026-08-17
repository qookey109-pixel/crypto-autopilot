from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from crypto_autopilot.exchanges.pionex_public import PionexPublicClient  # noqa: E402

ARCHIVE_BASE = "https://data.binance.vision/data/futures/um/daily/klines"
USER_AGENT = "qookey-crypto-autopilot/0.1 pionex-binance-compare-v3"
WINDOW_DAYS = 30
MAX_WORKERS = 8
SYMBOLS = {
    "BTC": ("BTC_USDT_PERP", "BTCUSDT"),
    "ETH": ("ETH_USDT_PERP", "ETHUSDT"),
    "SOL": ("SOL_USDT_PERP", "SOLUSDT"),
    "HYPE": ("HYPE_USDT_PERP", "HYPEUSDT"),
    "ADA": ("ADA_USDT_PERP", "ADAUSDT"),
    "BNB": ("BNB_USDT_PERP", "BNBUSDT"),
    "UNI": ("UNI_USDT_PERP", "UNIUSDT"),
    "XRP": ("XRP_USDT_PERP", "XRPUSDT"),
    "LTC": ("LTC_USDT_PERP", "LTCUSDT"),
    "LINK": ("LINK_USDT_PERP", "LINKUSDT"),
    "DOGE": ("DOGE_USDT_PERP", "DOGEUSDT"),
    "AAVE": ("AAVE_USDT_PERP", "AAVEUSDT"),
    "AVAX": ("AVAX_USDT_PERP", "AVAXUSDT"),
    "INJ": ("INJ_USDT_PERP", "INJUSDT"),
    "SUI": ("SUI_USDT_PERP", "SUIUSDT"),
}
INTERVALS = {
    "15m": ("15M", 15 * 60 * 1000, 1),
    "1h": ("60M", 60 * 60 * 1000, 4),
    "4h": ("4H", 4 * 60 * 60 * 1000, 16),
}


def request_bytes(url: str, timeout: float = 25.0, retries: int = 3) -> bytes:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={"Accept": "*/*", "User-Agent": USER_AGENT})
            with urlopen(req, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS host
                return response.read()
        except HTTPError as exc:
            if exc.code == 404:
                raise
            last_error = exc
        except URLError as exc:
            last_error = exc
        if attempt + 1 < retries:
            time.sleep(0.5 * (attempt + 1))
    assert last_error is not None
    raise last_error


def archive_url(symbol: str, day: date) -> str:
    ds = day.isoformat()
    filename = f"{symbol}-15m-{ds}.zip"
    return f"{ARCHIVE_BASE}/{symbol}/15m/{filename}"


def latest_btc_archive_day() -> date:
    today = datetime.now(timezone.utc).date()
    for offset in range(1, 8):
        candidate = today - timedelta(days=offset)
        try:
            request_bytes(archive_url("BTCUSDT", candidate) + ".CHECKSUM")
            return candidate
        except HTTPError as exc:
            if exc.code != 404:
                raise
    raise RuntimeError("No recent BTCUSDT Binance USD-M daily archive found")


def normalize_timestamp_ms(raw: int) -> int:
    return raw // 1000 if raw >= 10**15 else raw


def load_binance_day(symbol: str, day: date) -> tuple[dict[int, dict[str, float]], str] | None:
    url = archive_url(symbol, day)
    try:
        checksum_text = request_bytes(url + ".CHECKSUM").decode("utf-8").strip()
        payload = request_bytes(url)
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise
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


def load_binance_windows(days: list[date]) -> tuple[dict[str, dict[int, dict[str, float]]], dict[str, object]]:
    rows_by_symbol: dict[str, dict[int, dict[str, float]]] = {name: {} for name in SYMBOLS}
    meta: dict[str, object] = {}

    available_symbols: list[tuple[str, str]] = []
    for name, (_, binance_symbol) in SYMBOLS.items():
        try:
            request_bytes(archive_url(binance_symbol, days[-1]) + ".CHECKSUM")
            available_symbols.append((name, binance_symbol))
        except HTTPError as exc:
            if exc.code == 404:
                meta[name] = {
                    "available_on_end_day": False,
                    "available_days": 0,
                    "missing_days": len(days),
                    "archive_sha256": [],
                }
            else:
                raise

    futures = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for name, binance_symbol in available_symbols:
            for day in days:
                futures[pool.submit(load_binance_day, binance_symbol, day)] = (name, day)
        for future in as_completed(futures):
            name, day = futures[future]
            result = future.result()
            if name not in meta:
                meta[name] = {
                    "available_on_end_day": True,
                    "available_days": 0,
                    "missing_days": 0,
                    "archive_sha256": [],
                }
            symbol_meta = meta[name]
            assert isinstance(symbol_meta, dict)
            if result is None:
                symbol_meta["missing_days"] = int(symbol_meta["missing_days"]) + 1
                continue
            rows, sha256 = result
            rows_by_symbol[name].update(rows)
            symbol_meta["available_days"] = int(symbol_meta["available_days"]) + 1
            sha_rows = symbol_meta["archive_sha256"]
            assert isinstance(sha_rows, list)
            sha_rows.append({"day": day.isoformat(), "sha256": sha256})

    return rows_by_symbol, meta


def load_pionex_window(symbol: str, interval: str, start_ms: int, end_ms: int) -> dict[int, dict[str, float]]:
    client = PionexPublicClient(timeout_seconds=25)
    cursor = end_ms
    rows: dict[int, dict[str, float]] = {}
    for _ in range(100):
        candles = client.get_klines(symbol, interval, limit=500, end_time_ms=cursor)
        if not candles:
            break
        earliest = min(c.time_ms for c in candles)
        for c in candles:
            if start_ms <= c.time_ms <= end_ms:
                rows[c.time_ms] = {
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume,
                }
        if earliest <= start_ms:
            break
        cursor = earliest - 1
        time.sleep(0.08)
    return rows


def aggregate_15m(rows: dict[int, dict[str, float]], interval_ms: int, factor: int) -> dict[int, dict[str, float]]:
    if factor == 1:
        return dict(rows)
    grouped: dict[int, list[tuple[int, dict[str, float]]]] = {}
    for ts, row in rows.items():
        bucket = (ts // interval_ms) * interval_ms
        grouped.setdefault(bucket, []).append((ts, row))

    out: dict[int, dict[str, float]] = {}
    step_ms = 15 * 60 * 1000
    for bucket, items in grouped.items():
        items.sort(key=lambda item: item[0])
        expected_ts = [bucket + i * step_ms for i in range(factor)]
        if [ts for ts, _ in items] != expected_ts:
            continue
        values = [row for _, row in items]
        out[bucket] = {
            "open": values[0]["open"],
            "high": max(row["high"] for row in values),
            "low": min(row["low"] for row in values),
            "close": values[-1]["close"],
            "volume": sum(row["volume"] for row in values),
        }
    return out


def bps(a: float, b: float) -> float:
    mid = (abs(a) + abs(b)) / 2.0
    return 0.0 if mid == 0 else abs(a - b) / mid * 10_000.0


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
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


def compare_rows(
    symbol: str,
    interval_name: str,
    pionex: dict[int, dict[str, float]],
    binance: dict[int, dict[str, float]],
    expected_rows: int,
) -> dict[str, object]:
    common = sorted(set(pionex) & set(binance))
    if not common:
        return {
            "symbol": symbol,
            "interval": interval_name,
            "expected_rows": expected_rows,
            "pionex_rows": len(pionex),
            "binance_rows": len(binance),
            "common_rows": 0,
            "status": "UNAVAILABLE",
        }

    fields = ("open", "high", "low", "close")
    diffs = {field: [] for field in fields}
    exact_close = 0
    exact_ohlc = 0
    direction_matches = 0
    p_returns: list[float] = []
    b_returns: list[float] = []

    for ts in common:
        p = pionex[ts]
        b = binance[ts]
        for field in fields:
            diffs[field].append(bps(p[field], b[field]))
        if p["close"] == b["close"]:
            exact_close += 1
        if all(p[field] == b[field] for field in fields):
            exact_ohlc += 1
        p_delta = p["close"] - p["open"]
        b_delta = b["close"] - b["open"]
        p_dir = 0 if p_delta == 0 else (1 if p_delta > 0 else -1)
        b_dir = 0 if b_delta == 0 else (1 if b_delta > 0 else -1)
        if p_dir == b_dir:
            direction_matches += 1

    for prev_ts, ts in zip(common, common[1:]):
        p_prev = pionex[prev_ts]["close"]
        b_prev = binance[prev_ts]["close"]
        if p_prev > 0 and b_prev > 0:
            p_returns.append(math.log(pionex[ts]["close"] / p_prev))
            b_returns.append(math.log(binance[ts]["close"] / b_prev))

    close_diffs = diffs["close"]
    corr = correlation(p_returns, b_returns)
    p95 = percentile(close_diffs, 0.95)
    max_diff = max(close_diffs)
    coverage = len(common) / expected_rows
    near_same = (
        coverage >= 0.999
        and corr is not None
        and corr >= 0.995
        and p95 is not None
        and p95 <= 5.0
        and max_diff <= 20.0
    )
    return {
        "symbol": symbol,
        "interval": interval_name,
        "expected_rows": expected_rows,
        "pionex_rows": len(pionex),
        "binance_rows": len(binance),
        "common_rows": len(common),
        "timestamp_overlap_ratio_vs_expected": coverage,
        "exact_close_ratio": exact_close / len(common),
        "exact_ohlc_ratio": exact_ohlc / len(common),
        "close_abs_diff_bps": {
            "mean": statistics.fmean(close_diffs),
            "median": statistics.median(close_diffs),
            "p95": p95,
            "max": max_diff,
            "share_le_0_1bps": sum(v <= 0.1 for v in close_diffs) / len(close_diffs),
            "share_le_1bps": sum(v <= 1.0 for v in close_diffs) / len(close_diffs),
            "share_le_5bps": sum(v <= 5.0 for v in close_diffs) / len(close_diffs),
            "share_le_10bps": sum(v <= 10.0 for v in close_diffs) / len(close_diffs),
        },
        "ohlc_abs_diff_bps_mean": {field: statistics.fmean(values) for field, values in diffs.items()},
        "candle_direction_agreement": direction_matches / len(common),
        "close_log_return_correlation": corr,
        "near_same_gate": near_same,
        "status": "PASS" if near_same else "REVIEW",
    }


def main() -> None:
    end_day = latest_btc_archive_day()
    start_day = end_day - timedelta(days=WINDOW_DAYS - 1)
    days = [start_day + timedelta(days=i) for i in range(WINDOW_DAYS)]
    start_dt = datetime(start_day.year, start_day.month, start_day.day, tzinfo=timezone.utc)
    end_dt_exclusive = datetime(end_day.year, end_day.month, end_day.day, tzinfo=timezone.utc) + timedelta(days=1)
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt_exclusive.timestamp() * 1000) - 1

    binance_15m, binance_meta = load_binance_windows(days)
    results: list[dict[str, object]] = []

    for name, (pionex_symbol, _) in SYMBOLS.items():
        base_rows = binance_15m[name]
        if not base_rows:
            for interval_name, (_, interval_ms, _) in INTERVALS.items():
                expected = WINDOW_DAYS * (24 * 60 * 60 * 1000 // interval_ms)
                results.append(
                    {
                        "symbol": name,
                        "interval": interval_name,
                        "expected_rows": expected,
                        "pionex_rows": 0,
                        "binance_rows": 0,
                        "common_rows": 0,
                        "status": "BINANCE_USDM_UNAVAILABLE",
                    }
                )
            continue

        for interval_name, (pionex_interval, interval_ms, factor) in INTERVALS.items():
            pionex_rows = load_pionex_window(pionex_symbol, pionex_interval, start_ms, end_ms)
            binance_rows = aggregate_15m(base_rows, interval_ms, factor)
            expected = WINDOW_DAYS * (24 * 60 * 60 * 1000 // interval_ms)
            results.append(compare_rows(name, interval_name, pionex_rows, binance_rows, expected))

    comparable = [row for row in results if row.get("status") not in {"BINANCE_USDM_UNAVAILABLE", "UNAVAILABLE"}]
    unavailable_symbols = sorted(
        name for name in SYMBOLS if not bool(cast_dict(binance_meta.get(name)).get("available_on_end_day", False))
    )
    all_near_same = bool(comparable) and all(bool(row.get("near_same_gate")) for row in comparable)
    payload = {
        "proof": "PIONEX_BINANCE_30D_15SYMBOL_EQUIVALENCE_V3",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "authentication": "none",
        "scope": {
            "window_days": WINDOW_DAYS,
            "start_day_utc": start_day.isoformat(),
            "end_day_utc": end_day.isoformat(),
            "pionex_market": "PERP",
            "binance_market": "USD-M Futures",
            "binance_source": "official data.binance.vision daily 15m Kline archives with SHA-256 verification",
            "higher_intervals": "Binance 1h/4h reconstructed from checksum-verified 15m; Pionex uses native 60M/4H",
            "symbols": list(SYMBOLS),
            "intervals": list(INTERVALS),
        },
        "binance_availability": binance_meta,
        "results": results,
        "summary": {
            "requested_symbols": len(SYMBOLS),
            "binance_available_symbols": len(SYMBOLS) - len(unavailable_symbols),
            "binance_unavailable_symbols": unavailable_symbols,
            "comparable_interval_results": len(comparable),
            "near_same_passes": sum(bool(row.get("near_same_gate")) for row in comparable),
            "all_comparable_near_same": all_near_same,
            "weighted_exact_close_ratio": weighted_ratio(comparable, "exact_close_ratio"),
            "weighted_exact_ohlc_ratio": weighted_ratio(comparable, "exact_ohlc_ratio"),
        },
        "status": "PASS" if all_near_same else "REVIEW_REQUIRED",
    }
    output = Path("pionex-binance-comparison.json")
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


def cast_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def weighted_ratio(rows: list[dict[str, object]], key: str) -> float | None:
    numerator = 0.0
    denominator = 0
    for row in rows:
        common = int(row.get("common_rows") or 0)
        ratio = row.get(key)
        if common and isinstance(ratio, (int, float)):
            numerator += float(ratio) * common
            denominator += common
    return numerator / denominator if denominator else None


if __name__ == "__main__":
    main()
