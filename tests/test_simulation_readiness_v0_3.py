from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from crypto_autopilot.historical import INTERVAL_MS
from crypto_autopilot.models import Candle
from crypto_autopilot.paper.simulation_readiness_v0_3 import (
    COVERAGE,
    END_MS,
    INTERVALS,
    RECEIPT_SCHEMA,
    START_MS,
    SYMBOL,
    V0_2_CONFIG_SHA256,
    V0_2_NAMESPACE,
    SimulationReadinessError,
    generate_plans,
    load_verified_sample,
    run_readiness,
)
from crypto_autopilot.storage.parquet import candles_to_parquet

ROOT = Path(__file__).resolve().parents[1]


def sample() -> dict[str, list[Candle]]:
    result = {}
    for interval in INTERVALS:
        step = INTERVAL_MS[interval]
        count = (END_MS - START_MS) // step
        result[interval] = [
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
    return result


def encode(source):
    run_id = "github-123456789-1"
    payloads, details = {}, []
    for interval in INTERVALS:
        candles = source[interval]
        parquet = candles_to_parquet(candles)
        payloads[interval] = parquet.payload
        details.append(
            {
                "interval": interval,
                "rows": len(candles),
                "first_time_ms": candles[0].time_ms,
                "last_time_ms": candles[-1].time_ms,
                "bytes": len(parquet.payload),
                "sha256": hashlib.sha256(parquet.payload).hexdigest(),
                "key": f"{V0_2_NAMESPACE}/run={run_id}/{interval}.parquet",
            }
        )
    return payloads, {
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


class SimulationReadinessV03Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candles = sample()
        cls.payloads, cls.receipt = encode(cls.candles)

    def test_verified_parquet_is_required_and_hash_bound(self):
        decoded = load_verified_sample(self.payloads, self.receipt)
        self.assertEqual(tuple(decoded), INTERVALS)
        bad = dict(self.payloads)
        bad["15M"] = bad["15M"][:-1] + bytes([bad["15M"][-1] ^ 1])
        with self.assertRaisesRegex(SimulationReadinessError, "SHA-256"):
            load_verified_sample(bad, self.receipt)

    def test_missing_interval_or_bad_receipt_fails_closed(self):
        missing = dict(self.payloads)
        missing.pop("4H")
        with self.assertRaisesRegex(SimulationReadinessError, "three V0.2"):
            load_verified_sample(missing, self.receipt)
        bad_receipt = dict(self.receipt)
        bad_receipt["holdout_accessed"] = True
        with self.assertRaisesRegex(SimulationReadinessError, "holdout_accessed"):
            load_verified_sample(self.payloads, bad_receipt)

    def test_plans_are_candle_derived_and_causal(self):
        plans = generate_plans(self.candles)
        self.assertGreater(len(plans), 0)
        self.assertTrue(all(plan.plan_id.startswith("simulation-v0.3-") for plan in plans))
        last = self.candles["15M"][-1]
        changed = {key: list(value) for key, value in self.candles.items()}
        changed["15M"][-1] = Candle(
            last.time_ms,
            last.open,
            last.high + 5.0,
            last.low - 5.0,
            last.close - 0.01,
            last.volume * 5.0,
        )
        revised = generate_plans(changed)
        self.assertEqual(
            tuple(plan for plan in plans if plan.signal_time_ms < last.time_ms),
            tuple(plan for plan in revised if plan.signal_time_ms < last.time_ms),
        )

    def test_pipeline_pass_is_kline_only_not_full_ready(self):
        report = run_readiness(self.payloads, self.receipt)
        self.assertEqual(report["status"], "PIPELINE_PASS_KLINE_ONLY")
        self.assertTrue(report["pipeline_exercised"])
        self.assertFalse(report["full_simulation_ready"])
        self.assertGreater(report["generated_plan_count"], 0)
        self.assertGreater(report["executed_trade_count"], 0)
        self.assertIn("historical_funding_evidence_missing", report["blockers"])
        result = report["result"]
        self.assertTrue(all(t.entry_time_ms > t.signal_time_ms for t in result.trades))

    def test_prepared_contract_does_not_authorize_production(self):
        config_bytes = (ROOT / "config/simulation_readiness_v0_3.json").read_bytes()
        config = json.loads(config_bytes)
        receipt = json.loads(
            (ROOT / "research/receipts/2026-09-11-simulation-readiness-v0-3-prepared.json").read_bytes()
        )
        self.assertEqual(hashlib.sha256(config_bytes).hexdigest(), receipt["config_sha256"])
        self.assertTrue(config["authority"]["synthetic_fixture_validation"])
        for key, value in config["authority"].items():
            if key != "synthetic_fixture_validation":
                self.assertFalse(value, key)


if __name__ == "__main__":
    unittest.main()
