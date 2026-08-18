from __future__ import annotations

import csv
import io
import json
import zipfile
from collections import Counter
from urllib.request import Request, urlopen

from crypto_autopilot.binance_funding import BinanceVisionFundingArchiveKey


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "qookey-crypto-autopilot/0.1"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - frozen HTTPS host
        return response.read()


def rows_for(symbol: str) -> list[tuple[int, int, float]]:
    key = BinanceVisionFundingArchiveKey(symbol, "2024-01")
    payload = fetch(key.url)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        text = archive.read(key.csv_filename).decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    header = [cell.strip().lower() for cell in rows[0]]
    if "calc_time" in header:
        time_i = header.index("calc_time")
        int_i = header.index("funding_interval_hours")
        rate_i = header.index("last_funding_rate")
        rows = rows[1:]
    else:
        time_i, int_i, rate_i = 0, 1, 2
    return [(int(row[time_i]), int(float(row[int_i])), float(row[rate_i])) for row in rows if row]


def main() -> int:
    hour_ms = 3_600_000
    for symbol in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        rows = rows_for(symbol)
        residuals: list[int] = []
        anomalies: list[dict[str, int]] = []
        for left, right in zip(rows, rows[1:]):
            delta = right[0] - left[0]
            expected_options = [left[1] * hour_ms, right[1] * hour_ms]
            residual = min((delta - expected for expected in expected_options), key=abs)
            residuals.append(residual)
            if residual != 0:
                anomalies.append(
                    {
                        "left_ms": left[0],
                        "right_ms": right[0],
                        "left_interval_h": left[1],
                        "right_interval_h": right[1],
                        "delta_ms": delta,
                        "nearest_residual_ms": residual,
                    }
                )
        print(
            json.dumps(
                {
                    "symbol": symbol,
                    "rows": len(rows),
                    "interval_hours": sorted({row[1] for row in rows}),
                    "nonzero_residual_count": sum(value != 0 for value in residuals),
                    "max_abs_residual_ms": max((abs(value) for value in residuals), default=0),
                    "residual_counts": Counter(residuals).most_common(12),
                    "first_anomalies": anomalies[:12],
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
