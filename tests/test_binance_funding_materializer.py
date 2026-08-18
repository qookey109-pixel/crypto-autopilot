from __future__ import annotations

import copy
import unittest

from crypto_autopilot.binance_funding_materialization_plan import build_materialization_scope
from crypto_autopilot.binance_funding_materializer import (
    EXPECTED_CHECKSUM_SET_SHA256,
    EXPECTED_SCOPE_SHA256,
    BinanceFundingMaterializationError,
    FundingChecksumRecord,
    canonical_scope_sha256,
    checksum_set_sha256,
    run_metadata_keys,
    source_keys_from_scope,
    validate_authority_bundle,
    validate_execution_marker,
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
    }


def materialization_authority() -> dict[str, object]:
    return {
        "status": "PASS",
        "stage": "BINANCE_FUNDING_R2_MATERIALIZATION_AUTHORIZED",
        "authority_type": "STORAGE_MATERIALIZATION_ONLY",
        "provider": "binance_usdm",
        "dataset": "fundingRate",
        "authorized_scope": {
            "canonical_scope_sha256": EXPECTED_SCOPE_SHA256,
            "source_archive_count": 1010,
            "annual_canonical_objects": 95,
            "planned_total_r2_write_objects": 194,
        },
        "authorized_actions": {
            "funding_materialization_authorized": True,
            "r2_writes_authorized": True,
        },
        "explicitly_not_authorized": {
            "source_switch_authorized": False,
            "provider_splicing_authorized": False,
            "pionex_native_relabel_authorized": False,
            "historical_universe_membership_authorized": False,
            "backtest_admission_authorized": False,
            "automatic_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }


def amendment() -> dict[str, object]:
    return {
        "status": "PASS",
        "stage": "BINANCE_FUNDING_R2_MATERIALIZATION_AUTHORITY_CHECKSUM_SET_BOUND",
        "authorized_scope_sha256": EXPECTED_SCOPE_SHA256,
        "authorized_source_archive_count": 1010,
        "required_checksum_set_sha256": EXPECTED_CHECKSUM_SET_SHA256,
        "permissions": {
            "funding_materialization_authorized": True,
            "r2_writes_authorized_for_original_exact_scope_only": True,
            "source_switch_authorized": False,
            "provider_splicing_authorized": False,
            "pionex_native_relabel_authorized": False,
            "historical_universe_membership_authorized": False,
            "backtest_admission_authorized": False,
            "automatic_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }


def checksum_authority() -> dict[str, object]:
    return {
        "status": "PASS",
        "stage": "BINANCE_FUNDING_SOURCE_CHECKSUM_SET_FROZEN",
        "available_archive_count": 1010,
        "checksum_set_sha256": EXPECTED_CHECKSUM_SET_SHA256,
    }


class FundingMaterializerGateTests(unittest.TestCase):
    def test_real_scope_shape_matches_frozen_scope_hash(self) -> None:
        scope = build_materialization_scope(coverage())
        self.assertEqual(scope.symbol_count, 15)
        self.assertEqual(scope.symbol_months, 1010)
        self.assertEqual(scope.canonical_objects, 95)
        self.assertEqual(canonical_scope_sha256(scope), EXPECTED_SCOPE_SHA256)
        keys = source_keys_from_scope(scope)
        self.assertEqual(len(keys), 1010)
        self.assertEqual(keys[0].identity, ("AAVEUSDT", "2020-10"))
        self.assertEqual(keys[-1].identity, ("XRPUSDT", "2026-07"))

    def test_authority_bundle_requires_storage_only_permissions(self) -> None:
        scope = build_materialization_scope(coverage())
        scope_sha, checksum_sha = validate_authority_bundle(
            materialization_authority=materialization_authority(),
            amendment=amendment(),
            checksum_set_authority=checksum_authority(),
            scope=scope,
        )
        self.assertEqual(scope_sha, EXPECTED_SCOPE_SHA256)
        self.assertEqual(checksum_sha, EXPECTED_CHECKSUM_SET_SHA256)

        changed = copy.deepcopy(materialization_authority())
        changed["explicitly_not_authorized"]["live_trading_authorized"] = True
        with self.assertRaises(BinanceFundingMaterializationError):
            validate_authority_bundle(
                materialization_authority=changed,
                amendment=amendment(),
                checksum_set_authority=checksum_authority(),
                scope=scope,
            )

    def test_checksum_set_digest_is_order_independent_and_revision_sensitive(self) -> None:
        records = [
            FundingChecksumRecord("BTCUSDT", "2024-01", "a" * 64),
            FundingChecksumRecord("ETHUSDT", "2024-01", "b" * 64),
        ]
        left = checksum_set_sha256(records)
        right = checksum_set_sha256(reversed(records))
        self.assertEqual(left, right)
        changed = [records[0], FundingChecksumRecord("ETHUSDT", "2024-01", "c" * 64)]
        self.assertNotEqual(left, checksum_set_sha256(changed))

    def test_execution_marker_must_pin_all_authorities_and_no_trade_permission(self) -> None:
        marker = {
            "status": "EXECUTE_AUTHORIZED_FUNDING_R2_MATERIALIZATION",
            "execute": True,
            "provider": "binance_usdm",
            "dataset": "fundingRate",
            "canonical_scope_sha256": EXPECTED_SCOPE_SHA256,
            "source_checksum_set_sha256": EXPECTED_CHECKSUM_SET_SHA256,
            "materialization_authority": "research/receipts/2026-08-18-binance-funding-materialization-authority.json",
            "authority_amendment": "research/receipts/2026-08-18-binance-funding-materialization-authority-amendment.json",
            "checksum_set_authority": "research/receipts/2026-08-18-binance-funding-source-checksum-set.json",
            "source_switch_authorized": False,
            "pionex_native_relabel_authorized": False,
            "backtest_admission_authorized": False,
            "trade_plan_authorized": False,
            "live_trading_authorized": False,
        }
        validate_execution_marker(
            marker,
            scope_sha256=EXPECTED_SCOPE_SHA256,
            checksum_set_sha256_value=EXPECTED_CHECKSUM_SET_SHA256,
        )
        marker["trade_plan_authorized"] = True
        with self.assertRaises(BinanceFundingMaterializationError):
            validate_execution_marker(
                marker,
                scope_sha256=EXPECTED_SCOPE_SHA256,
                checksum_set_sha256_value=EXPECTED_CHECKSUM_SET_SHA256,
            )

    def test_run_metadata_is_exactly_four_provider_separated_objects(self) -> None:
        keys = run_metadata_keys("123456")
        self.assertEqual(len(keys.all), 4)
        self.assertEqual(len(set(keys.all)), 4)
        self.assertTrue(all("binance_usdm" in key for key in keys.all))
        self.assertTrue(all("pionex" not in key.lower() for key in keys.all))


if __name__ == "__main__":
    unittest.main()
