from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone

from crypto_autopilot.binance_coverage import month_periods
from crypto_autopilot.binance_funding import BinanceVisionFundingArchiveKey
from crypto_autopilot.binance_funding_coverage import summarize_funding_presence
from crypto_autopilot.binance_vision import parse_checksum
from discover_binance_funding_coverage import (
    fetch_bytes,
    history_cap_floor,
    load_candidate_universe,
    load_json,
    previous_month,
    probe_many,
)


def raw_rows(key: BinanceVisionFundingArchiveKey) -> list[dict[str, object]]:
    checksum = fetch_bytes(key.checksum_url, allow_not_found=False)
    archive_bytes = fetch_bytes(key.url, allow_not_found=False)
    if checksum is None or archive_bytes is None:
        raise RuntimeError(f"edge archive disappeared: {key.identity}")
    expected_sha, filename = parse_checksum(checksum)
    actual_sha = hashlib.sha256(archive_bytes).hexdigest()
    if filename != key.filename or expected_sha != actual_sha:
        raise RuntimeError(f"edge checksum mismatch: {key.identity}")
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        if names != [key.csv_filename]:
            raise RuntimeError(f"unexpected edge CSV member: {key.identity} {names}")
        text = archive.read(names[0]).decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    header = [cell.strip().lower() for cell in rows[0]]
    if "calc_time" in header:
        time_i = header.index("calc_time")
        interval_i = header.index("funding_interval_hours")
        rate_i = header.index("last_funding_rate")
        rows = rows[1:]
    else:
        time_i, interval_i, rate_i = 0, 1, 2
    return [
        {
            "time_ms": int(row[time_i]),
            "interval_h": int(float(row[interval_i])),
            "rate": float(row[rate_i]),
        }
        for row in rows
        if row
    ]


def diagnose(key: BinanceVisionFundingArchiveKey) -> dict[str, object]:
    values = raw_rows(key)
    hour_ms = 3_600_000
    residuals: list[int] = []
    anomalies: list[dict[str, object]] = []
    for index, (left, right) in enumerate(zip(values, values[1:])):
        delta = int(right["time_ms"]) - int(left["time_ms"])
        expected = {
            int(left["interval_h"]) * hour_ms,
            int(right["interval_h"]) * hour_ms,
        }
        residual = min((delta - item for item in expected), key=abs)
        residuals.append(residual)
        if abs(residual) > 10:
            anomalies.append(
                {
                    "index": index,
                    "left_time_ms": left["time_ms"],
                    "right_time_ms": right["time_ms"],
                    "left_interval_h": left["interval_h"],
                    "right_interval_h": right["interval_h"],
                    "delta_ms": delta,
                    "nearest_residual_ms": residual,
                }
            )
    return {
        "symbol": key.symbol,
        "period": key.period,
        "rows": len(values),
        "first_time_ms": values[0]["time_ms"],
        "last_time_ms": values[-1]["time_ms"],
        "interval_hours": sorted({int(row["interval_h"]) for row in values}),
        "max_abs_residual_ms": max((abs(item) for item in residuals), default=0),
        "anomalies_beyond_10ms": anomalies,
    }


def main() -> int:
    config = load_json("config/binance_funding_coverage_v0_1.json")
    pairs = load_candidate_universe(str(config["candidate_authority"]))
    symbols = tuple(binance for _, binance in pairs)
    today = datetime.now(timezone.utc).date()
    floor = history_cap_floor(today, int(config["project_history_cap_years"]))
    last_month = previous_month(today)
    periods = month_periods(floor.strftime("%Y-%m"), last_month.strftime("%Y-%m"))
    keys = tuple(
        BinanceVisionFundingArchiveKey(symbol, period)
        for symbol in symbols
        for period in periods
    )
    records = probe_many(keys, workers=int(config.get("workers", 12)))
    summaries = [
        summarize_funding_presence(records, symbol=symbol, ordered_periods=periods)
        for symbol in symbols
    ]
    edge_keys: dict[tuple[str, str], BinanceVisionFundingArchiveKey] = {}
    for summary in summaries:
        symbol = str(summary["symbol"])
        for field in ("first_available_period", "last_available_period"):
            period = summary.get(field)
            if period is not None:
                key = BinanceVisionFundingArchiveKey(symbol, str(period))
                edge_keys[key.identity] = key

    results = [diagnose(key) for key in sorted(edge_keys.values(), key=lambda item: item.identity)]
    results.sort(key=lambda row: (-int(row["max_abs_residual_ms"]), str(row["symbol"]), str(row["period"])))
    anomaly_edges = [row for row in results if int(row["max_abs_residual_ms"]) > 10]
    print(
        json.dumps(
            {
                "scan_floor": floor.strftime("%Y-%m"),
                "last_complete_month": last_month.strftime("%Y-%m"),
                "monthly_checks": len(records),
                "available_checks": sum(row["status"] == "AVAILABLE" for row in records),
                "no_data_checks": sum(row["status"] == "NO_DATA" for row in records),
                "edge_archive_count": len(results),
                "max_abs_residual_ms_across_edges": max(
                    (int(row["max_abs_residual_ms"]) for row in results),
                    default=0,
                ),
                "edges_beyond_10ms_count": len(anomaly_edges),
                "edges_beyond_10ms": anomaly_edges,
                "top_edge_residuals": results[:20],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
