from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone

from crypto_autopilot.binance_expansion_plan import (
    BinanceExpansionPlanError,
    build_waves,
    load_capacity_basis,
    load_coverage_windows,
    validate_config,
    validate_existing_2025,
)


EARLIEST = {
    "BTCUSDT": "2020-01-01T00:00:00+00:00",
    "ETHUSDT": "2020-01-01T00:00:00+00:00",
    "SOLUSDT": "2020-09-14T07:00:00+00:00",
    "HYPEUSDT": "2025-05-30T10:30:00+00:00",
    "ADAUSDT": "2020-01-31T08:00:00+00:00",
    "BNBUSDT": "2020-02-10T08:00:00+00:00",
    "UNIUSDT": "2020-09-18T07:00:00+00:00",
    "XRPUSDT": "2020-01-06T08:15:00+00:00",
    "LTCUSDT": "2020-01-09T08:00:00+00:00",
    "LINKUSDT": "2020-01-17T08:00:00+00:00",
    "DOGEUSDT": "2020-07-10T09:00:00+00:00",
    "AAVEUSDT": "2020-10-16T07:00:00+00:00",
    "AVAXUSDT": "2020-09-23T07:00:00+00:00",
    "INJUSDT": "2022-08-17T02:45:00+00:00",
    "SUIUSDT": "2023-05-03T16:00:00+00:00",
}
LATEST = "2026-08-16T20:00:00+00:00"


def ms(text: str) -> int:
    return int(datetime.fromisoformat(text).timestamp() * 1000)


def coverage_payload() -> dict[str, object]:
    return {
        "status": "PASS",
        "stage": "BINANCE_MAX_COVERAGE_DISCOVERY_PASS",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "candidate_count": 15,
        "protocol": {"last_complete_month_scanned": "2026-07"},
        "strategy_price_common_windows": [
            {
                "symbol": symbol,
                "earliest_candle_time_ms": ms(earliest),
                "latest_candle_time_ms": ms(LATEST),
            }
            for symbol, earliest in EARLIEST.items()
        ],
        "authority_boundary": {
            "authorizes_source_switch": False,
            "authorizes_large_scale_backfill": False,
        },
    }


def config_payload() -> dict[str, object]:
    return {
        "status": "PROTOCOL_FROZEN_BEFORE_PLANNING",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "candidate_count": 15,
        "planning_scope": "trade_klines_only",
        "project_intervals": ["15M", "60M", "4H"],
        "source_intervals": ["15m", "1h", "4h"],
        "current_incomplete_year_policy": "DEFER",
        "source_switch_authorized": False,
        "large_scale_backfill_authorized": False,
        "r2_writes_authorized": False,
        "pionex_native_relabel_authorized": False,
        "provider_splicing_authorized": False,
        "silent_interpolation_authorized": False,
        "trade_plan_authorized": False,
        "live_trading_authorized": False,
    }


class BinanceExpansionPlanTests(unittest.TestCase):
    def test_frozen_config_rejects_any_write_authorization(self) -> None:
        validate_config(config_payload())
        changed = copy.deepcopy(config_payload())
        changed["r2_writes_authorized"] = True
        with self.assertRaises(BinanceExpansionPlanError):
            validate_config(changed)

    def test_wave_plan_uses_observed_onsets_and_skips_2025(self) -> None:
        coverage = coverage_payload()
        windows = load_coverage_windows(coverage)
        waves = build_waves(
            coverage,
            windows,
            already_materialized_years=(2025,),
            rows_per_full_market_year=45990,
            bytes_per_row=27.98556232135459,
        )
        self.assertEqual([wave.year for wave in waves], [2024, 2023, 2022, 2021, 2020])
        self.assertEqual([wave.symbol_count for wave in waves], [14, 14, 13, 12, 12])
        self.assertEqual([wave.symbol_months for wave in waves], [168, 164, 149, 144, 104])
        self.assertEqual([wave.object_count for wave in waves], [196, 192, 175, 168, 128])
        self.assertEqual([wave.source_archive_count for wave in waves], [504, 492, 447, 432, 312])
        self.assertEqual(sum(wave.estimated_rows for wave in waves), 2793893)
        self.assertEqual(sum(wave.estimated_parquet_bytes for wave in waves), 78188670)

        wave_2020 = waves[-1]
        by_symbol = {item.symbol: item.months for item in wave_2020.symbol_years}
        self.assertEqual(by_symbol["BTCUSDT"], tuple(range(1, 13)))
        self.assertEqual(by_symbol["BNBUSDT"], tuple(range(2, 13)))
        self.assertEqual(by_symbol["DOGEUSDT"], tuple(range(7, 13)))
        self.assertEqual(by_symbol["AAVEUSDT"], tuple(range(10, 13)))
        self.assertNotIn("INJUSDT", by_symbol)
        self.assertNotIn("SUIUSDT", by_symbol)
        self.assertNotIn("HYPEUSDT", by_symbol)

    def test_capacity_and_existing_authorities_fail_closed(self) -> None:
        capacity = {
            "status": "PASS",
            "stage": "BINANCE_OBSERVED_R2_BUDGET_GATE_PASS",
            "basis": {
                "rows_per_full_market_year": 45990,
                "observed_bytes_per_row": 27.98556232135459,
            },
            "storage_projection": {
                "canonical_only_gb_month": 2.5741120223,
                "canonical_plus_retained_staging_gb_month": 5.1482240446,
                "three_x_capacity_stress_gb_month": 7.722336067,
            },
        }
        rows, bytes_per_row, staging, stress = load_capacity_basis(capacity)
        self.assertEqual(rows, 45990)
        self.assertGreater(bytes_per_row, 27.0)
        self.assertAlmostEqual(staging, 2.0)
        self.assertAlmostEqual(stress, 3.0)

        validate_existing_2025(
            {
                "status": "PASS",
                "stage": "BINANCE_2025_R2_PILOT_PASS",
                "year": 2025,
                "object_count": 206,
                "pionex_namespace_touched": False,
            }
        )
        with self.assertRaises(BinanceExpansionPlanError):
            validate_existing_2025(
                {
                    "status": "PASS",
                    "stage": "BINANCE_2025_R2_PILOT_PASS",
                    "year": 2025,
                    "object_count": 205,
                    "pionex_namespace_touched": False,
                }
            )


if __name__ == "__main__":
    unittest.main()
