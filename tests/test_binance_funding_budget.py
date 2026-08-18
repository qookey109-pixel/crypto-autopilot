from __future__ import annotations

import copy
import unittest

from crypto_autopilot.binance_funding_budget import (
    BinanceFundingBudgetError,
    coverage_shape,
    project_funding_budget,
    validate_budget_config,
)


BOUNDARIES = {
    "AAVEUSDT": ("2020-10", "2026-07", 70),
    "ADAUSDT": ("2020-01", "2026-07", 79),
    "AVAXUSDT": ("2020-09", "2026-07", 71),
    "BNBUSDT": ("2020-02", "2026-07", 78),
    "BTCUSDT": ("2020-01", "2026-07", 79),
    "DOGEUSDT": ("2020-07", "2026-07", 73),
    "ETHUSDT": ("2020-01", "2026-07", 79),
    "HYPEUSDT": ("2025-05", "2026-07", 15),
    "INJUSDT": ("2022-08", "2026-07", 48),
    "LINKUSDT": ("2020-01", "2026-07", 79),
    "LTCUSDT": ("2020-01", "2026-07", 79),
    "SOLUSDT": ("2020-09", "2026-07", 71),
    "SUIUSDT": ("2023-05", "2026-07", 39),
    "UNIUSDT": ("2020-09", "2026-07", 71),
    "XRPUSDT": ("2020-01", "2026-07", 79),
}


def coverage_payload() -> dict[str, object]:
    return {
        "status": "PASS",
        "stage": "BINANCE_FUNDING_COVERAGE_DISCOVERY_PASS",
        "scan": {
            "monthly_available_checks": 1010,
            "symbols_with_observed_funding_coverage": 15,
            "symbols_with_internal_monthly_presence_gap": [],
        },
        "symbol_boundaries": {
            symbol: {
                "first_available_period": first,
                "last_available_period": last,
                "available_months": count,
                "internal_missing_months": [],
            }
            for symbol, (first, last, count) in BOUNDARIES.items()
        },
    }


def config_payload() -> dict[str, object]:
    return {
        "status": "PROTOCOL_FROZEN_BEFORE_BUDGET_MEASUREMENT",
        "provider": "binance_usdm",
        "dataset": "fundingRate",
        "bytes_per_row_policy": "MAX_OF_PROOF_SYMBOL_MONTH_PARQUET_BYTES_PER_ROW",
        "row_projection_policy": "ASSUME_ONE_HOUR_FUNDING_FOR_EVERY_CALENDAR_HOUR_IN_EVERY_AVAILABLE_MONTH",
        "minimum_funding_interval_hours_for_budget": 1,
        "retained_staging_multiplier": 2.0,
        "capacity_stress_multiplier": 3.0,
        "operation_stress_multiplier": 3,
        "source_switch_authorized": False,
        "r2_writes_authorized": False,
        "funding_materialization_authorized": False,
        "pionex_native_relabel_authorized": False,
        "provider_splicing_authorized": False,
        "backtest_admission_authorized": False,
        "trade_plan_authorized": False,
        "live_trading_authorized": False,
    }


class BinanceFundingBudgetTests(unittest.TestCase):
    def test_coverage_shape_matches_frozen_1010_month_scope(self) -> None:
        months, days, objects = coverage_shape(coverage_payload())
        self.assertEqual(months, 1010)
        self.assertEqual(days, 30735)
        self.assertEqual(objects, 95)

    def test_budget_protocol_fails_closed_on_write_or_weaker_row_projection(self) -> None:
        validate_budget_config(config_payload())
        changed = copy.deepcopy(config_payload())
        changed["r2_writes_authorized"] = True
        with self.assertRaises(BinanceFundingBudgetError):
            validate_budget_config(changed)
        changed = copy.deepcopy(config_payload())
        changed["minimum_funding_interval_hours_for_budget"] = 8
        with self.assertRaises(BinanceFundingBudgetError):
            validate_budget_config(changed)

    def test_one_hour_projection_is_737640_rows_and_95_annual_objects(self) -> None:
        projected = project_funding_budget(
            coverage_authority=coverage_payload(),
            calibration_max_bytes_per_row=100.0,
            trade_three_x_storage_gb=7.722336067,
            trade_three_x_class_a_requests=672000,
            trade_three_x_class_b_requests=420000,
            storage_warn_gb=8.0,
            class_a_warn_requests=750000,
            class_b_warn_requests=7500000,
        )
        self.assertEqual(projected.projected_rows, 737640)
        self.assertEqual(projected.annual_canonical_objects, 95)
        self.assertEqual(projected.planned_class_a_requests, 194)
        self.assertEqual(projected.three_x_class_a_requests, 582)
        self.assertAlmostEqual(projected.canonical_gb, 0.073764)
        self.assertAlmostEqual(projected.combined_trade_plus_funding_three_x_storage_gb, 7.943628067)
        self.assertFalse(projected.material_budget_change)

    def test_projection_marks_material_when_combined_stress_reaches_warn(self) -> None:
        projected = project_funding_budget(
            coverage_authority=coverage_payload(),
            calibration_max_bytes_per_row=150.0,
            trade_three_x_storage_gb=7.722336067,
            trade_three_x_class_a_requests=672000,
            trade_three_x_class_b_requests=420000,
            storage_warn_gb=8.0,
            class_a_warn_requests=750000,
            class_b_warn_requests=7500000,
        )
        self.assertTrue(projected.material_budget_change)

    def test_internal_gap_or_changed_month_count_fails_closed(self) -> None:
        changed = coverage_payload()
        changed["symbol_boundaries"]["BTCUSDT"]["internal_missing_months"] = ["2024-02"]
        with self.assertRaises(BinanceFundingBudgetError):
            coverage_shape(changed)

        changed = coverage_payload()
        changed["scan"]["monthly_available_checks"] = 1009
        with self.assertRaises(BinanceFundingBudgetError):
            coverage_shape(changed)


if __name__ == "__main__":
    unittest.main()
