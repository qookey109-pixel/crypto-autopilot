from __future__ import annotations

import json
from pathlib import Path
import unittest

from crypto_autopilot.history.pionex_reach_v0_3 import (
    ReachRejected,
    _require_fixed_scope,
    discover_all,
    discover_interval,
    stamp,
)
from crypto_autopilot.models import Candle


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/pionex_historical_reach_v0_3.json"


def candle(time_ms: int, price: float = 100.0) -> Candle:
    return Candle(
        time_ms=time_ms,
        open=price,
        high=price + 1.0,
        low=price - 1.0,
        close=price + 0.25,
        volume=10.0,
    )


def series(interval_ms: int, count: int, end_ms: int) -> list[Candle]:
    start = end_ms - (count - 1) * interval_ms
    return [candle(start + i * interval_ms, 100.0 + i * 0.001) for i in range(count)]


class FakeClient:
    def __init__(self, data: dict[str, list[Candle]]) -> None:
        self.data = data
        self.calls: list[tuple[str, str, int, int | None]] = []

    def get_klines(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        end_time_ms: int | None = None,
    ) -> list[Candle]:
        self.calls.append((symbol, interval, limit, end_time_ms))
        rows = self.data[interval]
        eligible = [row for row in rows if end_time_ms is None or row.time_ms <= end_time_ms]
        return eligible[-limit:]


class TruncatingClient(FakeClient):
    def get_klines(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        end_time_ms: int | None = None,
    ) -> list[Candle]:
        rows = super().get_klines(
            symbol,
            interval,
            limit=limit,
            end_time_ms=end_time_ms,
        )
        if limit == 500 and len(self.calls) == 1:
            return rows[-10:]
        return rows


class PionexHistoricalReachV03Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.cutoff = stamp(self.config["cutoff_exclusive_utc"])

    def test_config_keeps_discovery_read_only_and_public(self) -> None:
        _require_fixed_scope(self.config)
        self.assertTrue(self.config["authority"]["public_pionex_reads"])
        self.assertFalse(self.config["authority"]["api_key_required"])
        self.assertFalse(self.config["authority"]["r2_read"])
        self.assertFalse(self.config["authority"]["r2_write"])
        self.assertFalse(self.config["authority"]["holdout_access"])
        self.assertFalse(self.config["authority"]["live_trading"])
        self.assertEqual(self.config["documented_max_records_per_interval"], 10_000)
        self.assertEqual(self.config["maximum_requests"], 63)

    def test_short_page_plus_empty_probe_proves_provider_earliest(self) -> None:
        step = 4 * 60 * 60 * 1000
        rows = series(step, 1_200, self.cutoff - step)
        client = FakeClient({"4H": rows})
        progress = {"requests": 0}
        result = discover_interval(self.config, client, "4H", progress)

        self.assertEqual(result.classification, "PROVIDER_EARLIEST_REACHED")
        self.assertEqual(result.records_observed, 1_200)
        self.assertEqual(result.data_pages, 3)
        self.assertEqual(result.requests, 4)
        self.assertTrue(result.continuity_verified)
        self.assertEqual(result.earliest_time_ms, rows[0].time_ms)
        self.assertEqual(result.latest_time_ms, rows[-1].time_ms)

    def test_documented_cap_stops_at_exactly_ten_thousand(self) -> None:
        step = 4 * 60 * 60 * 1000
        rows = series(step, 11_000, self.cutoff - step)
        client = FakeClient({"4H": rows})
        progress = {"requests": 0}
        result = discover_interval(self.config, client, "4H", progress)

        self.assertEqual(result.classification, "DOCUMENTED_RECORD_CAP_REACHED")
        self.assertEqual(result.records_observed, 10_000)
        self.assertEqual(result.data_pages, 20)
        self.assertEqual(result.requests, 20)
        self.assertEqual(len(client.calls), 20)

    def test_short_page_with_earlier_data_fails_closed(self) -> None:
        step = 4 * 60 * 60 * 1000
        rows = series(step, 1_200, self.cutoff - step)
        client = TruncatingClient({"4H": rows})
        with self.assertRaisesRegex(ReachRejected, "short page did not prove"):
            discover_interval(self.config, client, "4H", {"requests": 0})

    def test_gap_or_invalid_page_fails_closed(self) -> None:
        step = 4 * 60 * 60 * 1000
        rows = series(step, 600, self.cutoff - step)
        del rows[-20]
        client = FakeClient({"4H": rows})
        with self.assertRaisesRegex(ReachRejected, "missing, duplicate, unordered"):
            discover_interval(self.config, client, "4H", {"requests": 0})

    def test_no_data_at_cutoff_is_not_called_earliest(self) -> None:
        client = FakeClient({"4H": []})
        with self.assertRaisesRegex(ReachRejected, "no data at discovery cutoff"):
            discover_interval(self.config, client, "4H", {"requests": 0})

    def test_scope_change_that_could_cross_holdout_is_rejected(self) -> None:
        changed = json.loads(json.dumps(self.config))
        changed["cutoff_exclusive_utc"] = "2026-09-04T00:00:00Z"
        with self.assertRaisesRegex(ReachRejected, "cutoff changed"):
            _require_fixed_scope(changed)

    def test_all_interval_report_contains_metadata_not_candles(self) -> None:
        steps = {
            "15M": 15 * 60 * 1000,
            "60M": 60 * 60 * 1000,
            "4H": 4 * 60 * 60 * 1000,
        }
        data = {
            interval: series(step, 600, self.cutoff - step)
            for interval, step in steps.items()
        }
        report = discover_all(self.config, FakeClient(data))
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(len(report["intervals"]), 3)
        self.assertFalse(report["candles_persisted"])
        self.assertFalse(report["r2_accessed"])
        self.assertFalse(report["holdout_accessed"])
        self.assertFalse(report["api_key_used"])
        self.assertNotIn("candles", json.dumps(report).lower().replace("candles_persisted", ""))

    def test_workflow_is_manual_secret_free_and_has_no_schedule(self) -> None:
        workflow = (
            ROOT / ".github/workflows/pionex-historical-reach-v0-3.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("secrets.", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("requirements/ci-constraints.txt", workflow)


if __name__ == "__main__":
    unittest.main()
