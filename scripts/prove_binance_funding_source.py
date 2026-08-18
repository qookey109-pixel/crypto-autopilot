from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from crypto_autopilot.binance_funding import (
    FUNDING_CADENCE_JITTER_TOLERANCE_MS,
    BinanceVisionFundingArchiveKey,
    ingest_funding_archive,
)


def fetch_bytes(url: str, *, attempts: int = 3, timeout_seconds: float = 30.0) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        req = Request(
            url,
            headers={"Accept": "*/*", "User-Agent": "qookey-crypto-autopilot/0.1"},
        )
        try:
            with urlopen(req, timeout=timeout_seconds) as response:  # noqa: S310 - frozen HTTPS host
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last_error}") from last_error


def load_config(path: str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("status") != "PROTOCOL_FROZEN_BEFORE_LIVE_PROOF":
        raise RuntimeError("funding protocol must be frozen before live proof")
    if payload.get("provider") != "binance_usdm" or payload.get("delivery") != "binance_vision":
        raise RuntimeError("funding provider/delivery mismatch")
    if payload.get("dataset") != "fundingRate" or payload.get("archive_frequency") != "monthly":
        raise RuntimeError("funding source must remain monthly Binance Vision fundingRate")
    if int(payload.get("cadence_jitter_tolerance_ms") or -1) != FUNDING_CADENCE_JITTER_TOLERANCE_MS:
        raise RuntimeError("funding cadence jitter tolerance config/code mismatch")
    for field in (
        "source_switch_authorized",
        "r2_writes_authorized",
        "pionex_native_relabel_authorized",
        "provider_splicing_authorized",
        "backtest_admission_authorized",
        "trade_plan_authorized",
        "live_trading_authorized",
    ):
        if payload.get(field) is not False:
            raise RuntimeError(f"{field} must remain false during source proof")
    return payload


def max_cadence_residual_ms(observations: tuple[object, ...]) -> int:
    hour_ms = 3_600_000
    residuals: list[int] = []
    for left, right in zip(observations, observations[1:]):
        delta = right.funding_time_ms - left.funding_time_ms
        expected = {
            left.funding_interval_hours * hour_ms,
            right.funding_interval_hours * hour_ms,
        }
        residuals.append(min(abs(delta - item) for item in expected))
    return max(residuals, default=0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/binance_funding_v0_1.json")
    parser.add_argument("--output", default="artifacts/binance-funding-source-proof.json")
    args = parser.parse_args()

    config = load_config(args.config)
    period = str(config["proof_period"])
    symbols = tuple(str(item) for item in config["proof_symbols"])
    if symbols != ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        raise RuntimeError("V0.1 proof symbols changed after protocol freeze")

    receipts: list[dict[str, object]] = []
    total_rows = 0
    proof_max_jitter_ms = 0
    for symbol in symbols:
        key = BinanceVisionFundingArchiveKey(symbol=symbol, period=period)
        checksum = fetch_bytes(key.checksum_url)
        archive = fetch_bytes(key.url)
        result = ingest_funding_archive(
            key,
            archive_bytes=archive,
            checksum_payload=checksum,
        )
        receipt = result.receipt
        observed_jitter = max_cadence_residual_ms(result.observations)
        if observed_jitter > FUNDING_CADENCE_JITTER_TOLERANCE_MS:
            raise RuntimeError("accepted Funding archive exceeded frozen cadence jitter tolerance")
        proof_max_jitter_ms = max(proof_max_jitter_ms, observed_jitter)
        total_rows += receipt.row_count
        receipts.append(
            {
                "symbol": receipt.symbol,
                "period": receipt.period,
                "source_url": receipt.source_url,
                "checksum_url": receipt.checksum_url,
                "archive_filename": receipt.archive_filename,
                "archive_sha256": receipt.archive_sha256,
                "row_count": receipt.row_count,
                "first_time_ms": receipt.first_time_ms,
                "last_time_ms": receipt.last_time_ms,
                "interval_hours": list(receipt.interval_hours),
                "min_rate": receipt.min_rate,
                "max_rate": receipt.max_rate,
                "max_abs_cadence_residual_ms": observed_jitter,
                "cadence_anomalies_beyond_tolerance": receipt.cadence_anomalies,
                "audit_ok": receipt.audit_ok,
            }
        )

    payload = {
        "schema": "binance-funding-source-proof-v0.1",
        "execution_status": "PASS",
        "stage": "BINANCE_FUNDING_SOURCE_PROOF_PASS",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "execution_exchange": "pionex",
        "native_to_execution_exchange": False,
        "may_authorize_pionex_native_history": False,
        "dataset": "fundingRate",
        "frequency": "monthly",
        "period": period,
        "symbol_count": len(symbols),
        "symbols": list(symbols),
        "total_rows": total_rows,
        "cadence_jitter_tolerance_ms": FUNDING_CADENCE_JITTER_TOLERANCE_MS,
        "proof_scope_max_abs_cadence_residual_ms": proof_max_jitter_ms,
        "raw_timestamps_preserved": True,
        "timestamps_rounded_or_interpolated": False,
        "receipts": receipts,
        "interpretation_boundary": {
            "proves_monthly_funding_archive_path": True,
            "proves_checksum_and_archive_schema_for_proof_scope": True,
            "proves_bounded_source_timestamp_jitter_for_proof_scope": True,
            "proves_long_horizon_15_symbol_coverage": False,
            "proves_r2_materialization": False,
            "source_switch_authorized": False,
            "r2_writes_performed": False,
            "backtest_admission_authorized": False,
            "live_trading_authorized": False,
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "execution_status": "PASS",
                "rows": total_rows,
                "proof_max_jitter_ms": proof_max_jitter_ms,
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
