from __future__ import annotations

import csv
import io
import json
import zipfile
from urllib.request import Request, urlopen

from crypto_autopilot.binance_funding import BinanceVisionFundingArchiveKey


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "qookey-crypto-autopilot-hype-diagnostic/0.1"})
    with urlopen(request, timeout=30) as response:  # noqa: S310 - frozen HTTPS host
        return response.read()


def main() -> int:
    key = BinanceVisionFundingArchiveKey("HYPEUSDT", "2026-07")
    payload = fetch(key.url)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        text = archive.read(key.csv_filename).decode("utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    header = [cell.strip().lower() for cell in rows[0]]
    if "calc_time" in header:
        time_i = header.index("calc_time")
        interval_i = header.index("funding_interval_hours")
        rate_i = header.index("last_funding_rate")
        rows = rows[1:]
    else:
        time_i, interval_i, rate_i = 0, 1, 2

    values = [
        {
            "time_ms": int(row[time_i]),
            "interval_h": int(float(row[interval_i])),
            "rate": float(row[rate_i]),
        }
        for row in rows
        if row
    ]
    hour_ms = 3_600_000
    anomalies: list[dict[str, object]] = []
    residuals: list[int] = []
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
                    "left": left,
                    "right": right,
                    "delta_ms": delta,
                    "delta_hours": delta / hour_ms,
                    "expected_hours": sorted({int(left["interval_h"]), int(right["interval_h"])}),
                    "nearest_residual_ms": residual,
                    "previous_row": values[index - 1] if index > 0 else None,
                    "next_row": values[index + 2] if index + 2 < len(values) else None,
                }
            )
    print(
        json.dumps(
            {
                "symbol": key.symbol,
                "period": key.period,
                "rows": len(values),
                "first": values[0],
                "last": values[-1],
                "interval_hours": sorted({int(row["interval_h"]) for row in values}),
                "max_abs_residual_ms": max((abs(item) for item in residuals), default=0),
                "anomalies_beyond_10ms": anomalies,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
