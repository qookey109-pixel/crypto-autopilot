from __future__ import annotations

import hashlib
import json
import math
import unittest
from pathlib import Path

from crypto_autopilot.historical import INTERVAL_MS
from crypto_autopilot.models import Candle
from crypto_autopilot.paper.simulation_funding_v0_1 import (
    END_MS,
    FUNDING_EXECUTION_SHA256,
    FUNDING_PROTOCOL_SHA256,
    FUNDING_REPORT_SCHEMA,
    START_MS,
    SimulationFundingError,
    load_verified_funding,
    run_readiness_with_verified_funding,
)
from crypto_autopilot.paper.simulation_readiness_v0_3 import (
    COVERAGE,
    INTERVALS,
    RECEIPT_SCHEMA,
    SYMBOL,
    V0_2_CONFIG_SHA256,
    V0_2_NAMESPACE,
)
from crypto_autopilot.storage.parquet import candles_to_parquet

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/simulation_funding_admission_v0_1.json"
RECEIPT = ROOT / "research/receipts/2026-09-11-simulation-funding-admission-v0-1-prepared.json"
CONFIG_SHA256 = "b9871ca38bcb69d0850effc4ea56c9e43ff710e798a73966425b000f83521f6c"


def funding_report() -> dict[str, object]:
    observations = [
        {
            "symbol": SYMBOL,
            "funding_time_ms": time_ms,
            "funding_rate": 0.0001,
        }
        for time_ms in range(START_MS, END_MS, INTERVAL_MS["15M"])
    ]
    return {
        "schema": FUNDING_REPORT_SCHEMA,
        "status": "PASS",
        "protocol_config_sha256": FUNDING_PROTOCOL_SHA256,
        "execution_config_sha256": FUNDING_EXECUTION_SHA256,
        "run_id": "34560000000",
        "run_attempt": "1",
        "event": "workflow_dispatch",
        "head_ref": "refs/heads/main",
        "repository": "qookey109-pixel/crypto-autopilot",
        "api_key_used": False,
        "private_api_used": False,
        "raw_provider_payloads_persisted": False,
        "r2_accessed": False,
        "holdout_accessed": False,
        "simulation_data_admission_authorized": False,
        "formal_backtest_admission_authorized": False,
        "real_money_orders_authorized": False,
        "live_trading_authorized": False,
        "provider": "pionex_public_futures",
        "symbol": SYMBOL,
        "window_start_utc": "2026-08-01T00:00:00Z",
        "window_end_exclusive_utc": "2026-08-28T00:00:00Z",
        "requests": 1,
        "left_boundary_reached": True,
        "first_time_ms": observations[0]["funding_time_ms"],
        "last_time_ms": observations[-1]["funding_time_ms"],
        "observation_count": len(observations),
        "observations": observations,
        "automatic_retries": 0,
    }


def encoded_kline_sample():
    payloads, details = {}, []
    run_id = "github-123456789-1"
    for interval in INTERVALS:
        step = INTERVAL_MS[interval]
        count = (END_MS - START_MS) // step
        candles = [
            Candle(
                time_ms=START_MS + index * step,
                open=100.0 + index * 0.05,
                high=100.05 + index * 0.05,
                low=99.50 + index * 0.05,
                close=100.04 + index * 0.05,
                volume=100.0,
            )
            for index in range(count)
        ]
        parquet = candles_to_parquet(candles)
        payloads[interval] = parquet.payload
        details.append(
            {
                "interval": interval,
                "rows": count,
                "first_time_ms": START_MS,
                "last_time_ms": END_MS - step,
                "bytes": len(parquet.payload),
                "sha256": hashlib.sha256(parquet.payload).hexdigest(),
                "key": f"{V0_2_NAMESPACE}/run={run_id}/{interval}.parquet",
            }
        )
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "PASS",
        "run_id": run_id,
        "provider": "pionex_public_futures",
        "symbol": SYMBOL,
        "config_sha256": V0_2_CONFIG_SHA256,
        "coverage_claim": COVERAGE,
        "start_utc": "2026-08-01T00:00:00Z",
        "end_exclusive_utc": "2026-08-28T00:00:00Z",
        "intervals": details,
        "holdout_accessed": False,
        "live_trading_authorized": False,
    }
    return payloads, receipt


class SimulationFundingV01Tests(unittest.TestCase):
    def test_exact_pass_report_converts_to_canonical_points(self) -> None:
        report = funding_report()
        points = load_verified_funding(report)
        self.assertEqual(len(points), report["observation_count"])
        self.assertEqual(points[0].symbol, SYMBOL)
        self.assertEqual(points[0].time_ms, START_MS)
        self.assertTrue(all(math.isfinite(point.rate) for point in points))

    def test_funding_report_drift_fails_closed(self) -> None:
        for key, value in (
            ("protocol_config_sha256", "0" * 64),
            ("holdout_accessed", True),
            ("simulation_data_admission_authorized", True),
            ("live_trading_authorized", True),
        ):
            report = funding_report()
            report[key] = value
            with self.assertRaises(SimulationFundingError, msg=key):
                load_verified_funding(report)

        report = funding_report()
        report["observations"][1]["funding_time_ms"] = report["observations"][0]["funding_time_ms"]
        with self.assertRaisesRegex(SimulationFundingError, "strictly increasing"):
            load_verified_funding(report)

    def test_verified_funding_reaches_canonical_backtest_without_ready_claim(self) -> None:
        payloads, kline_receipt = encoded_kline_sample()
        result = run_readiness_with_verified_funding(
            payloads,
            kline_receipt,
            funding_report(),
        )
        self.assertEqual(result["status"], "FUNDING_PIPELINE_PASS_NOT_ADMITTED")
        self.assertTrue(result["pipeline_exercised"])
        self.assertTrue(result["funding_data_ready"])
        self.assertFalse(result["full_simulation_ready"])
        self.assertNotIn("historical_funding_evidence_missing", result["blockers"])
        self.assertIn("production_simulation_data_admission_not_authorized", result["blockers"])
        self.assertGreater(result["result"].metrics.total_funding_usd, 0)

    def test_prepared_config_is_sha_bound_and_authorizes_no_production(self) -> None:
        config_bytes = CONFIG.read_bytes()
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        config = json.loads(config_bytes)
        self.assertEqual(hashlib.sha256(config_bytes).hexdigest(), CONFIG_SHA256)
        self.assertEqual(receipt["config_sha256"], CONFIG_SHA256)
        self.assertTrue(config["authority"]["synthetic_fixture_validation"])
        for key, value in config["authority"].items():
            if key != "synthetic_fixture_validation":
                self.assertFalse(value, key)


if __name__ == "__main__":
    unittest.main()
