from __future__ import annotations

import copy
import unittest

from crypto_autopilot.binance_funding_coverage import (
    COVERAGE_EDGE_CADENCE_JITTER_TOLERANCE_MS,
    BinanceFundingCoverageError,
    attach_funding_boundaries,
    summarize_funding_presence,
    validate_funding_coverage_config,
    validate_source_proof_authority,
)


PERIODS = ("2023-11", "2023-12", "2024-01", "2024-02")


def config_payload() -> dict[str, object]:
    return {
        "status": "PROTOCOL_REFROZEN_AFTER_EDGE_DIAGNOSTIC_BEFORE_COVERAGE_PASS_AUTHORITY",
        "provider": "binance_usdm",
        "delivery": "binance_vision",
        "dataset": "fundingRate",
        "archive_frequency": "monthly",
        "candidate_count": 15,
        "project_history_cap_years": 8,
        "scan_floor_policy": "PROJECT_HISTORY_CAP_ONLY",
        "provider_earliest_month_assumption": None,
        "current_incomplete_month_policy": "DEFER",
        "edge_content_audit_policy": "FIRST_AND_LAST_AVAILABLE_MONTH_PER_SYMBOL",
        "interior_policy": "CHECKSUM_PRESENCE_ONLY",
        "source_proof_default_cadence_jitter_tolerance_ms": 10,
        "coverage_edge_cadence_jitter_tolerance_ms": 50,
        "coverage_edge_diagnostic": {
            "observed_max_abs_residual_ms": 45,
            "tolerance_refrozen_before_coverage_pass_authority": True,
            "raw_timestamps_preserved": True,
            "missing_funding_event_gap_observed": False,
        },
        "funding_onset_may_be_inferred_from_trade_onset": False,
        "archive_presence_is_listing_authority": False,
        "source_switch_authorized": False,
        "r2_writes_authorized": False,
        "funding_materialization_authorized": False,
        "pionex_native_relabel_authorized": False,
        "provider_splicing_authorized": False,
        "backtest_admission_authorized": False,
        "trade_plan_authorized": False,
        "live_trading_authorized": False,
    }


def records(statuses: tuple[str, ...]) -> list[dict[str, object]]:
    return [
        {"symbol": "BTCUSDT", "period": period, "status": status}
        for period, status in zip(PERIODS, statuses, strict=True)
    ]


class BinanceFundingCoverageTests(unittest.TestCase):
    def test_config_freezes_source_proof_and_long_horizon_tolerances_separately(self) -> None:
        self.assertEqual(COVERAGE_EDGE_CADENCE_JITTER_TOLERANCE_MS, 50)
        validate_funding_coverage_config(config_payload())
        changed = copy.deepcopy(config_payload())
        changed["source_proof_default_cadence_jitter_tolerance_ms"] = 50
        with self.assertRaises(BinanceFundingCoverageError):
            validate_funding_coverage_config(changed)
        changed = copy.deepcopy(config_payload())
        changed["coverage_edge_cadence_jitter_tolerance_ms"] = 51
        with self.assertRaises(BinanceFundingCoverageError):
            validate_funding_coverage_config(changed)
        changed = copy.deepcopy(config_payload())
        changed["coverage_edge_diagnostic"]["observed_max_abs_residual_ms"] = 46
        with self.assertRaises(BinanceFundingCoverageError):
            validate_funding_coverage_config(changed)

    def test_config_fails_closed_on_any_materialization_or_onset_inference(self) -> None:
        validate_funding_coverage_config(config_payload())
        for field in (
            "r2_writes_authorized",
            "funding_materialization_authorized",
            "source_switch_authorized",
            "backtest_admission_authorized",
        ):
            changed = copy.deepcopy(config_payload())
            changed[field] = True
            with self.assertRaises(BinanceFundingCoverageError):
                validate_funding_coverage_config(changed)
        changed = copy.deepcopy(config_payload())
        changed["funding_onset_may_be_inferred_from_trade_onset"] = True
        with self.assertRaises(BinanceFundingCoverageError):
            validate_funding_coverage_config(changed)

    def test_source_proof_must_pass_without_write_authority(self) -> None:
        proof = {
            "status": "PASS",
            "stage": "BINANCE_FUNDING_SOURCE_PROOF_PASS",
            "provider": "binance_usdm",
            "delivery": "binance_vision",
            "dataset": "fundingRate",
            "frequency": "monthly",
            "authority_boundary": {
                "authorizes_funding_r2_writes": False,
                "authorizes_source_switch": False,
                "authorizes_provider_splicing": False,
                "authorizes_pionex_native_relabeling": False,
                "authorizes_backtest_admission": False,
                "authorizes_live_trading": False,
            },
        }
        validate_source_proof_authority(proof)
        bad = copy.deepcopy(proof)
        bad["authority_boundary"]["authorizes_funding_r2_writes"] = True
        with self.assertRaises(BinanceFundingCoverageError):
            validate_source_proof_authority(bad)

    def test_presence_summary_detects_onset_and_internal_gap(self) -> None:
        summary = summarize_funding_presence(
            records(("NO_DATA", "AVAILABLE", "NO_DATA", "AVAILABLE")),
            symbol="BTCUSDT",
            ordered_periods=PERIODS,
        )
        self.assertEqual(summary["first_available_period"], "2023-12")
        self.assertEqual(summary["last_available_period"], "2024-02")
        self.assertEqual(summary["missing_periods_within_observed_span"], ["2024-01"])
        self.assertFalse(summary["continuous_archive_presence_within_observed_span"])

    def test_presence_summary_does_not_treat_pre_onset_no_data_as_gap(self) -> None:
        summary = summarize_funding_presence(
            records(("NO_DATA", "NO_DATA", "AVAILABLE", "AVAILABLE")),
            symbol="BTCUSDT",
            ordered_periods=PERIODS,
        )
        self.assertEqual(summary["first_available_period"], "2024-01")
        self.assertEqual(summary["missing_periods_within_observed_span"], [])
        self.assertTrue(summary["continuous_archive_presence_within_observed_span"])

    def test_boundary_attachment_uses_audited_raw_funding_times(self) -> None:
        summary = summarize_funding_presence(
            records(("NO_DATA", "NO_DATA", "AVAILABLE", "AVAILABLE")),
            symbol="BTCUSDT",
            ordered_periods=PERIODS,
        )
        first = {
            "audit_ok": True,
            "first_time_ms": 1704067200003,
            "last_time_ms": 1706716800000,
            "interval_hours": [8],
        }
        last = {
            "audit_ok": True,
            "first_time_ms": 1706745600000,
            "last_time_ms": 1709164800002,
            "interval_hours": [4, 8],
        }
        attached = attach_funding_boundaries(summary, first_receipt=first, last_receipt=last)
        self.assertEqual(attached["earliest_funding_time_ms"], 1704067200003)
        self.assertEqual(attached["latest_funding_time_ms"], 1709164800002)
        self.assertEqual(attached["observed_edge_interval_hours"], [4, 8])

    def test_no_available_months_produces_no_boundary_authority(self) -> None:
        summary = summarize_funding_presence(
            records(("NO_DATA", "NO_DATA", "NO_DATA", "NO_DATA")),
            symbol="BTCUSDT",
            ordered_periods=PERIODS,
        )
        attached = attach_funding_boundaries(summary, first_receipt=None, last_receipt=None)
        self.assertIsNone(attached["earliest_funding_time_ms"])
        self.assertIsNone(attached["latest_funding_time_ms"])

    def test_missing_or_duplicate_period_records_fail_closed(self) -> None:
        with self.assertRaises(BinanceFundingCoverageError):
            summarize_funding_presence(
                records(("NO_DATA", "AVAILABLE", "AVAILABLE", "AVAILABLE"))[:-1],
                symbol="BTCUSDT",
                ordered_periods=PERIODS,
            )
        duplicate = records(("NO_DATA", "AVAILABLE", "AVAILABLE", "AVAILABLE"))
        duplicate.append(dict(duplicate[-1]))
        with self.assertRaises(BinanceFundingCoverageError):
            summarize_funding_presence(duplicate, symbol="BTCUSDT", ordered_periods=PERIODS)


if __name__ == "__main__":
    unittest.main()
