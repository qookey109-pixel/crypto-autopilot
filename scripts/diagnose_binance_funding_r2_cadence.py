from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from crypto_autopilot.binance_funding import (
    BinanceVisionFundingArchiveKey,
    _cadence_residual_ms,
    _parse_observations,
    _rows_from_archive,
    _verify_checksum,
    ingest_funding_archive,
)
from crypto_autopilot.binance_funding_materialization_plan import build_materialization_scope
from crypto_autopilot.binance_funding_materializer import source_keys_from_scope


COVERAGE = "research/receipts/2026-08-18-binance-funding-coverage.json"
OUTPUT = "artifacts/binance-funding-r2-cadence-diagnostic.json"


def load_json(path: str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected object: {path}")
    return payload


def fetch_bytes(url: str, *, attempts: int = 3, timeout_seconds: float = 30.0) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = Request(
            url,
            headers={"Accept": "*/*", "User-Agent": "qookey-funding-r2-diagnostic/0.1"},
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - frozen HTTPS host
                return response.read()
        except HTTPError as exc:
            last_error = exc
            if exc.code not in {408, 425, 429, 500, 502, 503, 504}:
                break
        except (URLError, TimeoutError) as exc:
            last_error = exc
        if attempt + 1 < attempts:
            time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last_error}") from last_error


def inspect(key: BinanceVisionFundingArchiveKey) -> dict[str, object] | None:
    checksum = fetch_bytes(key.checksum_url)
    archive = fetch_bytes(key.url)
    try:
        ingest_funding_archive(
            key,
            archive_bytes=archive,
            checksum_payload=checksum,
            cadence_jitter_tolerance_ms=50,
        )
        return None
    except Exception as original:
        archive_sha = _verify_checksum(
            key,
            archive_bytes=archive,
            checksum_payload=checksum,
        )
        observations = _parse_observations(key, _rows_from_archive(key, archive))
        anomalies: list[dict[str, object]] = []
        residuals: list[int] = []
        for index, (left, right) in enumerate(zip(observations, observations[1:])):
            residual = _cadence_residual_ms(left, right)
            residuals.append(residual)
            if abs(residual) > 50:
                anomalies.append(
                    {
                        "index": index,
                        "left_time_ms": left.funding_time_ms,
                        "right_time_ms": right.funding_time_ms,
                        "delta_ms": right.funding_time_ms - left.funding_time_ms,
                        "left_interval_hours": left.funding_interval_hours,
                        "right_interval_hours": right.funding_interval_hours,
                        "residual_ms": residual,
                        "left_rate": left.rate,
                        "right_rate": right.rate,
                    }
                )
        return {
            "symbol": key.symbol,
            "period": key.period,
            "status": "RAW_RESIDUAL_DIAGNOSTIC",
            "error_50ms": str(original),
            "rows": len(observations),
            "interval_hours": sorted({item.funding_interval_hours for item in observations}),
            "first_time_ms": observations[0].funding_time_ms,
            "last_time_ms": observations[-1].funding_time_ms,
            "residual_count_above_50ms": len(anomalies),
            "max_abs_residual_ms": max((abs(value) for value in residuals), default=0),
            "anomalies": anomalies[:20],
            "archive_sha256": archive_sha,
        }


def main() -> int:
    scope = build_materialization_scope(load_json(COVERAGE))
    keys = source_keys_from_scope(scope)
    failures: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(inspect, key): key for key in keys}
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                failures.append(result)
    failures.sort(key=lambda row: (str(row["symbol"]), str(row["period"])))
    payload = {
        "schema": "binance-funding-r2-cadence-diagnostic-v0.1",
        "source_archive_count": len(keys),
        "failure_count_at_50ms": len(failures),
        "failures": failures,
        "diagnostic_only": True,
        "changes_frozen_tolerance": False,
        "r2_writes_performed": False,
    }
    output = Path(OUTPUT)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
