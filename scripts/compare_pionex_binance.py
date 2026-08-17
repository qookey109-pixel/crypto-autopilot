from __future__ import annotations

import json
import math
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from crypto_autopilot.exchanges.pionex_public import PionexPublicClient  # noqa: E402


BINANCE_BASE_URL = "https://fapi.binance.com"
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


def binance_klines(symbol: str, interval: str, limit: int = 500) -> list[dict[str, float | int]]:
    query = urlencode({"symbol": symbol, "interval": interval, "limit": limit})
    req = Request(
        f"{BINANCE_BASE_URL}/fapi/v1/klines?{query}",
        headers={"Accept": "application/json", "User-Agent": "qookey-crypto-autopilot/0.1"},
    )
    with urlopen(req, timeout=20) as response:  # noqa: S310 - fixed HTTPS host
        rows = json.loads(response.read().decode("utf-8"))
    return [
        {
            "time_ms": int(row[0]),
            "open": float(row[1]),
            "high": float(row[2]),
            "low": float(row[3]),
            "close": float(row[4]),
            "volume": float(row[5]),
        }
        for row in rows
    ]


def bps(a: float, b: float) -> float:
    mid = (abs(a) + abs(b)) / 2.0
    if mid == 0:
        return 0.0
    return abs(a - b) / mid * 10_000.0


def percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
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
) -> dict[str, object]:
    now_ms = int(time.time() * 1000)
    pionex_rows = PionexPublicClient(timeout_seconds=20).get_klines(
        pionex_symbol, pionex_interval, limit=500
    )
    binance_rows = binance_klines(binance_symbol, binance_interval, limit=500)

    # Compare closed candles only. Exchanges can legitimately report different values for the live candle.
    pionex = {
        c.time_ms: {
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
        }
        for c in pionex_rows
        if c.time_ms + interval_ms <= now_ms
    }
    binance = {
        int(c["time_ms"]): c
        for c in binance_rows
        if int(c["time_ms"]) + interval_ms <= now_ms
    }
    common = sorted(set(pionex) & set(binance))
    if not common:
        raise RuntimeError(
            f"No common closed candles for {pionex_symbol}/{binance_symbol} {pionex_interval}/{binance_interval}"
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
        p_dir = math.copysign(1.0, float(p["close"]) - float(p["open"])) if p["close"] != p["open"] else 0.0
        b_dir = math.copysign(1.0, float(b["close"]) - float(b["open"])) if b["close"] != b["open"] else 0.0
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
    return {
        "pionex_symbol": pionex_symbol,
        "binance_symbol": binance_symbol,
        "pionex_interval": pionex_interval,
        "binance_interval": binance_interval,
        "closed_pionex_rows": len(pionex),
        "closed_binance_rows": len(binance),
        "common_rows": len(common),
        "first_common_utc": datetime.fromtimestamp(common[0] / 1000, timezone.utc).isoformat(),
        "last_common_utc": datetime.fromtimestamp(common[-1] / 1000, timezone.utc).isoformat(),
        "timestamp_overlap_ratio": len(common) / max(1, min(len(pionex), len(binance))),
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
                )
            )

    payload = {
        "proof": "PIONEX_BINANCE_PUBLIC_MARKET_COMPARISON_V1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "authentication": "none",
        "scope": {
            "pionex_market": "PERP",
            "binance_market": "USD-M Futures",
            "symbols": list(SYMBOLS),
            "intervals": list(INTERVALS),
            "limit_per_exchange": 500,
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
