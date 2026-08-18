from __future__ import annotations

import copy
import unittest
from datetime import datetime

from crypto_autopilot.historical_universe import (
    HistoricalUniverseIndex,
    record_from_partition_receipt,
)
from crypto_autopilot.historical_universe_review import (
    HistoricalUniverseLongHorizonReviewError,
    build_membership_contract,
    review_target_wave,
    validate_review_config,
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


def config_payload() -> dict[str, object]:
    return {
        "status": "PROTOCOL_FROZEN_BEFORE_REVIEW",
        "execution_exchange": "pionex",
        "research_provider": "binance_usdm",
        "market_type": "perp",
        "target_wave": "W1",
        "target_year": 2024,
        "required_intervals": ["15M", "60M", "4H"],
        "review_policy": {
            "coverage_receipt_is_backtest_membership_authority": False,
            "first_observed_candle_is_listing_authority": False,
            "future_binance_partition_records_native_to_pionex": False,
            "pionex_current_universe_backprojection_allowed": False,
            "provider_splicing_allowed": False,
            "silent_interpolation_allowed": False,
            "verified_partition_receipts_required_before_membership": True,
            "all_three_intervals_required_before_default_membership": True,
            "acquisition_scope_may_be_reviewed_before_partition_materialization": True,
        },
        "post_materialization_record_policy": {
            "provider": "binance_usdm",
            "market_type": "perp",
            "native": False,
            "evidence_type": "verified_partition_receipt",
            "audit_ok_required": True,
            "actual_first_last_required": True,
            "source_sha256_required": True,
        },
        "source_switch_authorized": False,
        "wave_materialization_authorized": False,
        "backtest_admission_authorized": False,
        "pionex_native_relabel_authorized": False,
        "trade_plan_authorized": False,
        "live_trading_authorized": False,
    }


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


def staged_plan_payload() -> dict[str, object]:
    return {
        "status": "PASS",
        "stage": "BINANCE_STAGED_MULTIYEAR_EXPANSION_PLAN_PASS",
        "provider": "binance_usdm",
        "execution_exchange": "pionex",
        "planning_result": {
            "waves": [
                {
                    "wave_id": "W1",
                    "year": 2024,
                    "symbol_count": 14,
                    "symbol_months": 168,
                    "materialization_authorized": False,
                }
            ]
        },
        "authority_boundary": {"authorizes_any_wave_materialization": False},
    }


class HistoricalUniverseLongHorizonReviewTests(unittest.TestCase):
    def test_review_matches_w1_and_excludes_hype(self) -> None:
        result = review_target_wave(coverage_payload(), staged_plan_payload(), config_payload())
        self.assertEqual(result.target_wave, "W1")
        self.assertEqual(result.target_year, 2024)
        self.assertEqual(result.symbol_count, 14)
        self.assertEqual(result.symbol_months, 168)
        self.assertEqual(result.full_year_symbol_count, 14)
        self.assertEqual(result.excluded_symbols, ("HYPEUSDT",))
        self.assertTrue(all(scope.months == tuple(range(1, 13)) for scope in result.scopes))

    def test_review_protocol_fails_closed_on_native_relabel(self) -> None:
        validate_review_config(config_payload())
        changed = copy.deepcopy(config_payload())
        changed["post_materialization_record_policy"]["native"] = True
        with self.assertRaises(HistoricalUniverseLongHorizonReviewError):
            validate_review_config(changed)

    def test_review_protocol_fails_closed_on_coverage_as_membership(self) -> None:
        changed = copy.deepcopy(config_payload())
        changed["review_policy"]["coverage_receipt_is_backtest_membership_authority"] = True
        with self.assertRaises(HistoricalUniverseLongHorizonReviewError):
            validate_review_config(changed)

    def test_future_binance_partition_receipt_remains_proxy_and_never_pionex_native(self) -> None:
        payload = {
            "status": "PASS",
            "provider": "binance_usdm",
            "market_type": "perp",
            "symbol": "BTCUSDT",
            "interval": "15M",
            "actual_first_ms": 1000,
            "actual_last_ms": 2000,
            "audit_ok": True,
        }
        record = record_from_partition_receipt(
            payload,
            source_ref="future-w1-receipt",
            source_sha256="a" * 64,
            native=False,
        )
        self.assertIsNotNone(record)
        assert record is not None
        index = HistoricalUniverseIndex([record])
        self.assertEqual(index.available_symbols_at(1500, provider="binance_usdm", native_only=True), ())
        self.assertEqual(index.available_symbols_at(1500, provider="pionex", native_only=False), ())
        self.assertEqual(
            index.available_symbols_at(
                1500,
                provider="binance_usdm",
                required_intervals=("15M",),
                native_only=False,
            ),
            ("BTCUSDT",),
        )

    def test_membership_contract_requires_partition_evidence(self) -> None:
        contract = build_membership_contract(config_payload())
        self.assertFalse(contract["coverage_receipt_can_create_membership"])
        self.assertFalse(contract["pionex_provider_record_creation_allowed"])
        self.assertFalse(contract["native_pionex_backtest_admission_authorized"])
        self.assertTrue(contract["audit_ok_required"])
        self.assertTrue(contract["actual_first_last_required"])
        self.assertTrue(contract["source_sha256_required"])


if __name__ == "__main__":
    unittest.main()
