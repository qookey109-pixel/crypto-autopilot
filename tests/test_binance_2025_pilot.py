from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from crypto_autopilot.binance_2025_pilot import (
    Binance2025PilotAuthorityError,
    Binance2025SymbolCoverage,
    build_partition_plan,
    combine_and_audit_months,
    load_coverage_authority,
    source_archive_digest,
)
from crypto_autopilot.models import Candle


FULL_SYMBOLS = (
    "AAVEUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "BNBUSDT",
    "BTCUSDT",
    "DOGEUSDT",
    "ETHUSDT",
    "INJUSDT",
    "LINKUSDT",
    "LTCUSDT",
    "SOLUSDT",
    "SUIUSDT",
    "UNIUSDT",
    "XRPUSDT",
)


def authority_payload() -> dict:
    months = [f"2025-{month:02d}" for month in range(5, 13)]
    return {
        "status": "PASS",
        "stage": "BINANCE_2025_COVERAGE_SCAN_PASS",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "native_to_execution_exchange": False,
        "may_authorize_pionex_native_history": False,
        "year": 2025,
        "candidate_count": 15,
        "coverage_summary": {
            "full_2025_trade_archive_presence_symbols": list(FULL_SYMBOLS),
        },
        "partial_coverage": {
            "HYPEUSDT": {
                "trade_15m_available_months": months,
                "trade_1h_available_months": months,
                "trade_4h_available_months": months,
            }
        },
    }


class Binance2025PilotTests(unittest.TestCase):
    def write_authority(self, payload: dict) -> Path:
        temp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        with temp:
            json.dump(payload, temp)
        return Path(temp.name)

    def test_coverage_authority_resolves_14_full_and_hype_partial(self) -> None:
        path = self.write_authority(authority_payload())
        coverage = load_coverage_authority(path)
        self.assertEqual(len(coverage), 15)
        by_symbol = {item.symbol: item.months for item in coverage}
        self.assertEqual(by_symbol["BTCUSDT"], tuple(range(1, 13)))
        self.assertEqual(by_symbol["HYPEUSDT"], tuple(range(5, 13)))

    def test_partition_plan_is_206_provider_separated_objects(self) -> None:
        path = self.write_authority(authority_payload())
        coverage = load_coverage_authority(path)
        plans = build_partition_plan(coverage)
        self.assertEqual(len(plans), 206)
        self.assertEqual(len({plan.r2_key for plan in plans}), 206)
        self.assertTrue(all(plan.r2_key.startswith("market-data/binance_usdm/") for plan in plans))
        self.assertTrue(all("market-data/pionex/" not in plan.r2_key for plan in plans))

        btc = [plan for plan in plans if plan.symbol == "BTCUSDT"]
        hype = [plan for plan in plans if plan.symbol == "HYPEUSDT"]
        self.assertEqual(sum(plan.interval == "15M" for plan in btc), 12)
        self.assertEqual(sum(plan.interval == "15M" for plan in hype), 8)
        self.assertEqual(sum(plan.interval in {"60M", "4H"} for plan in btc), 2)
        self.assertEqual(sum(plan.interval in {"60M", "4H"} for plan in hype), 2)

    def test_bad_authority_fails_closed(self) -> None:
        payload = authority_payload()
        payload["native_to_execution_exchange"] = True
        path = self.write_authority(payload)
        with self.assertRaises(Binance2025PilotAuthorityError):
            load_coverage_authority(path)

        payload = authority_payload()
        payload["partial_coverage"]["HYPEUSDT"]["trade_1h_available_months"] = ["2025-06"]
        path = self.write_authority(payload)
        with self.assertRaises(Binance2025PilotAuthorityError):
            load_coverage_authority(path)

    def test_annual_combine_accepts_contiguous_month_boundaries(self) -> None:
        step = 60 * 60 * 1000
        first = tuple(
            Candle(time_ms=index * step, open=100, high=101, low=99, close=100.5, volume=1)
            for index in range(3)
        )
        second = tuple(
            Candle(time_ms=index * step, open=100, high=101, low=99, close=100.5, volume=1)
            for index in range(3, 6)
        )
        combined = combine_and_audit_months((first, second), interval="60M")
        self.assertEqual(len(combined), 6)
        self.assertEqual(combined[0].time_ms, 0)
        self.assertEqual(combined[-1].time_ms, 5 * step)

    def test_annual_combine_rejects_gap_between_months(self) -> None:
        step = 4 * 60 * 60 * 1000
        first = (
            Candle(time_ms=0, open=100, high=101, low=99, close=100.5, volume=1),
            Candle(time_ms=step, open=100, high=101, low=99, close=100.5, volume=1),
        )
        second = (
            Candle(time_ms=3 * step, open=100, high=101, low=99, close=100.5, volume=1),
        )
        with self.assertRaises(Binance2025PilotAuthorityError):
            combine_and_audit_months((first, second), interval="4H")

    def test_source_archive_digest_is_order_independent_and_validated(self) -> None:
        a = ("a.zip", "a" * 64)
        b = ("b.zip", "b" * 64)
        self.assertEqual(source_archive_digest((a, b)), source_archive_digest((b, a)))
        with self.assertRaises(ValueError):
            source_archive_digest((("bad.zip", "not-sha"),))

    def test_symbol_coverage_requires_sorted_unique_months(self) -> None:
        with self.assertRaises(ValueError):
            Binance2025SymbolCoverage("BTCUSDT", (2, 1))
        with self.assertRaises(ValueError):
            Binance2025SymbolCoverage("BTCUSDT", (1, 1))


if __name__ == "__main__":
    unittest.main()
