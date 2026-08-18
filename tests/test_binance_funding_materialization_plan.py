from __future__ import annotations

import copy
import unittest

from crypto_autopilot.binance_funding_materialization_plan import (
    BinanceFundingMaterializationPlanError,
    build_materialization_scope,
    validate_authorities,
    validate_plan_config,
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


def coverage() -> dict[str, object]:
    return {
        "status": "PASS",
        "stage": "BINANCE_FUNDING_COVERAGE_DISCOVERY_PASS",
        "scan": {
            "monthly_available_checks": 1010,
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
        "authority_boundary": {"authorizes_live_trading": False},
    }


def config() -> dict[str, object]:
    return {
        "status": "PROTOCOL_FROZEN_BEFORE_EXPLICIT_MATERIALIZATION_AUTHORITY",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "dataset": "fundingRate",
        "candidate_count": 15,
        "expected_available_symbol_months": 1010,
        "expected_annual_canonical_objects": 95,
        "canonical_partition": "annual_per_symbol",
        "source_checksum_required": True,
        "all_source_archives_must_pass_preflight_before_first_r2_write": True,
        "source_archive_revision_policy": "FAIL_CLOSED_REQUIRE_EXPLICIT_REVIEW",
        "existing_canonical_object_policy": "VERIFY_EXACT_OR_FAIL_NO_OVERWRITE",
        "existing_receipt_policy": "VERIFY_EXACT_OR_FAIL_NO_OVERWRITE",
        "raw_funding_timestamp_policy": "PRESERVE_EXACT_SOURCE_CALC_TIME",
        "source_declared_interval_policy": "PRESERVE_EXACT_SOURCE_FUNDING_INTERVAL_HOURS",
        "materialization_cadence_jitter_tolerance_ms": 50,
        "annual_cross_month_cadence_audit_required": True,
        "parquet_compression": "zstd",
        "preflight_source_archives_stored_in_r2": False,
        "planned_global_metadata_objects": 4,
        "writer_must_require_explicit_authority_receipt": True,
        "planning_r2_writes_authorized": False,
        "funding_materialization_authorized": False,
        "source_switch_authorized": False,
        "pionex_native_relabel_authorized": False,
        "provider_splicing_authorized": False,
        "historical_universe_membership_authorized": False,
        "backtest_admission_authorized": False,
        "trade_plan_authorized": False,
        "live_trading_authorized": False,
    }


class FundingMaterializationPlanTests(unittest.TestCase):
    def test_exact_scope_is_15_symbols_1010_months_95_objects(self) -> None:
        scope = build_materialization_scope(coverage())
        self.assertEqual(scope.symbol_count, 15)
        self.assertEqual(scope.symbol_months, 1010)
        self.assertEqual(scope.canonical_objects, 95)
        hype_2025 = next(item for item in scope.annual_scopes if item.symbol == "HYPEUSDT" and item.year == 2025)
        self.assertEqual(hype_2025.months, tuple(range(5, 13)))
        btc_2020 = next(item for item in scope.annual_scopes if item.symbol == "BTCUSDT" and item.year == 2020)
        self.assertEqual(btc_2020.months, tuple(range(1, 13)))
        self.assertIn("market-data/binance_usdm/", btc_2020.canonical_key)
        self.assertNotIn("pionex", btc_2020.canonical_key.lower())

    def test_planning_config_cannot_authorize_writes(self) -> None:
        validate_plan_config(config())
        changed = copy.deepcopy(config())
        changed["funding_materialization_authorized"] = True
        with self.assertRaises(BinanceFundingMaterializationPlanError):
            validate_plan_config(changed)
        changed = copy.deepcopy(config())
        changed["planning_r2_writes_authorized"] = True
        with self.assertRaises(BinanceFundingMaterializationPlanError):
            validate_plan_config(changed)

    def test_upstream_authorities_must_pass_without_live_authority(self) -> None:
        budget = {
            "status": "PASS",
            "stage": "BINANCE_FUNDING_R2_BUDGET_NO_MATERIAL_CHANGE",
            "determination": "NO_MATERIAL_BUDGET_CHANGE",
            "authority_boundary": {"authorizes_live_trading": False},
        }
        source = {
            "status": "PASS",
            "stage": "BINANCE_FUNDING_SOURCE_PROOF_PASS",
            "authority_boundary": {"authorizes_live_trading": False},
        }
        validate_authorities(coverage(), budget, source)
        changed = copy.deepcopy(budget)
        changed["determination"] = "MATERIAL_CHANGE_REVIEW_REQUIRED"
        with self.assertRaises(BinanceFundingMaterializationPlanError):
            validate_authorities(coverage(), changed, source)

    def test_internal_gap_fails_closed(self) -> None:
        changed = coverage()
        changed["symbol_boundaries"]["BTCUSDT"]["internal_missing_months"] = ["2024-02"]
        with self.assertRaises(BinanceFundingMaterializationPlanError):
            build_materialization_scope(changed)


if __name__ == "__main__":
    unittest.main()
