from __future__ import annotations

import hashlib
import json
import math
import unittest
from pathlib import Path

from crypto_autopilot.features.market import FundingRateObservation
from crypto_autopilot.history.pionex_funding_history import (
    PionexFundingHistoryRejected,
    collect_bounded_funding_history,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/pionex_funding_history_v0_1.json"
RECEIPT = ROOT / "research/receipts/2026-09-11-pionex-funding-history-v0-1-prepared.json"

HOUR = 60 * 60 * 1000
START = 1_785_542_400_000
END = 1_787_875_200_000


class FakeClient:
    def __init__(self, pages=None, error_on_call=None):
        self.pages = list(pages or [])
        self.error_on_call = error_on_call
        self.calls = []

    def get_funding_rates(self, symbol, *, limit=100, end_time_ms=None):
        self.calls.append((symbol, limit, end_time_ms))
        if self.error_on_call == len(self.calls):
            raise RuntimeError("provider down")
        if not self.pages:
            return []
        return list(self.pages.pop(0))


def point(time_ms, rate=0.0001, symbol="BTC_USDT_PERP"):
    return FundingRateObservation(symbol, time_ms, rate)


def config():
    return json.loads(CONFIG.read_text())


class PionexFundingHistoryV01Tests(unittest.TestCase):
    def test_one_page_crosses_left_boundary_without_cadence_assumption(self):
        client = FakeClient(
            [[
                point(START - 8 * HOUR, 0.0003),
                point(START, 0.0001),
                point(START + 7 * HOUR, -0.0002),
                point(START + 19 * HOUR, 0.0),
                point(END - HOUR, 0.0004),
            ]]
        )
        result = collect_bounded_funding_history(config(), client)
        self.assertTrue(result.left_boundary_reached)
        self.assertEqual(result.requests, 1)
        self.assertEqual(
            [item.funding_time_ms for item in result.observations],
            [START, START + 7 * HOUR, START + 19 * HOUR, END - HOUR],
        )
        self.assertEqual(client.calls[0], ("BTC_USDT_PERP", 500, END - 1))

    def test_paginates_from_oldest_minus_one_until_start_is_crossed(self):
        client = FakeClient(
            [
                [point(START + 16 * HOUR), point(START + 24 * HOUR)],
                [point(START - HOUR), point(START + HOUR)],
            ]
        )
        result = collect_bounded_funding_history(config(), client)
        self.assertEqual(result.requests, 2)
        self.assertEqual(client.calls[1][2], START + 16 * HOUR - 1)
        self.assertEqual(
            [item.funding_time_ms for item in result.observations],
            [START + HOUR, START + 16 * HOUR, START + 24 * HOUR],
        )

    def test_duplicate_timestamp_fails_closed(self):
        client = FakeClient([[point(START - HOUR), point(START), point(START)]])
        with self.assertRaisesRegex(PionexFundingHistoryRejected, "duplicate"):
            collect_bounded_funding_history(config(), client)

    def test_nonfinite_rate_fails_closed(self):
        client = FakeClient([[point(START - HOUR), point(START, math.inf)]])
        with self.assertRaisesRegex(PionexFundingHistoryRejected, "non-finite"):
            collect_bounded_funding_history(config(), client)

    def test_timestamp_beyond_request_cursor_fails_closed(self):
        client = FakeClient([[point(END)]])
        with self.assertRaisesRegex(PionexFundingHistoryRejected, "request cursor"):
            collect_bounded_funding_history(config(), client)

    def test_provider_failure_has_no_retry(self):
        client = FakeClient(error_on_call=1)
        with self.assertRaisesRegex(PionexFundingHistoryRejected, "request 1"):
            collect_bounded_funding_history(config(), client)
        self.assertEqual(len(client.calls), 1)

    def test_unproven_left_boundary_rejects_after_request_budget(self):
        client = FakeClient(
            [
                [point(START + 20 * HOUR)],
                [point(START + 10 * HOUR)],
                [point(START + HOUR)],
            ]
        )
        with self.assertRaisesRegex(PionexFundingHistoryRejected, "request budget exhausted"):
            collect_bounded_funding_history(config(), client)
        self.assertEqual(len(client.calls), 3)

    def test_prepared_receipt_binds_config_and_authorizes_no_production(self):
        config_bytes = CONFIG.read_bytes()
        cfg = json.loads(config_bytes)
        receipt = json.loads(RECEIPT.read_text())
        self.assertEqual(hashlib.sha256(config_bytes).hexdigest(), receipt["config_sha256"])
        self.assertTrue(cfg["authority"]["synthetic_fixture_validation"])
        for key, value in cfg["authority"].items():
            if key != "synthetic_fixture_validation":
                self.assertFalse(value, key)
        self.assertFalse(cfg["completeness"]["fixed_cadence_assumption"])
        self.assertFalse(cfg["completeness"]["zero_funding_fill"])


if __name__ == "__main__":
    unittest.main()
