from __future__ import annotations

import copy
import hashlib
import json
import unittest

from crypto_autopilot.research.prospective_shadow_continuity_v0_1 import (
    ContinuityReviewRequired,
    inspect_shadow_batch_continuity,
)
from crypto_autopilot.research.shadow_feature_coverage_v0_1 import (
    inspect_shadow_feature_coverage,
)

HOUR_MS = 3_600_000
BASE = HOUR_MS * 500_000
SYMBOLS = ("BTC_USDT_PERP", "ETH_USDT_PERP", "SOL_USDT_PERP", "ADA_USDT_PERP", "XRP_USDT_PERP")


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()).hexdigest()


def report_fixture(
    index: int,
    *,
    symbols: tuple[str, ...] = SYMBOLS,
    capture_shift_ms: int = 0,
    source_lag_hours: int = 0,
) -> dict[str, object]:
    capture = BASE + index * 4 * HOUR_MS + capture_shift_ms
    markets = []
    for symbol in symbols:
        end = capture // HOUR_MS * HOUR_MS - source_lag_hours * HOUR_MS
        candles = []
        for bar in range(240):
            stamp = end - (240 - bar) * HOUR_MS
            # Same symbol and hour must yield identical immutable OHLCV across runs.
            seed = (stamp // HOUR_MS) % 700 + sum(map(ord, symbol))
            v = float(seed)
            candles.append({
                "time_ms": stamp,
                "open": v, "high": v + 2.0,
                "low": v - 2.0, "close": v + 0.5, "volume": 100.0,
            })
        markets.append({
            "symbol": symbol,
            "candles_60m": candles,
            "candles_sha256": digest(candles),
            "technical": {"available_at_ms": end},
            "structure": {"available_at_ms": end},
            "patterns": {"available_at_ms": end},
            "market_event_radar": {"events": []},
            "universe_market": {"symbol": symbol},
        })
    body = {
        "schema": "qookey-prospective-shadow-collection-run-v0.1",
        "capture_timestamp_ms": capture,
        "context_snapshot": {"provider": "coinpaprika"},
        "regime_observation_input": {
            "time_ms": capture, "available_at_ms": capture,
            "breadth_scope": "TOP5_GOVERNED_SCAN_RESEARCH_PROXY",
            "production_regime_equivalence_claimed": False,
        },
        "universe_summary": {"top5_symbols": list(symbols)},
        "market_evidence": markets,
        "replay_state": {
            "signal_selection_performed_in_collector": False,
            "outcome_evaluation_performed_in_collector": False,
            "future_replay_must_use_only_artifacts_available_at_signal_time": True,
        },
        "comparison_source": {"status": "UNAVAILABLE"},
        "authority": {
            "research_collection_only": True,
            "r2_accessed": False, "d1_accessed": False, "holdout_accessed": False,
            "training_performed": False, "model_promotion_performed": False,
            "candidate_reranking_changed": False,
            "strategy_router_threshold_changed": False,
            "paper_submission_performed": False, "real_money_order_performed": False,
            "live_trading_performed": False, "raw_provider_payload_persisted": False,
        },
    }
    record = {**body, "record_id": digest(body)}
    return {
        "schema": "qookey-prospective-shadow-collection-execution-report-v0.1",
        "status": "PASS",
        "github": {
            "event_name": "schedule", "ref": "refs/heads/main",
            "sha": "a" * 40, "run_id": str(10000 + index), "run_attempt": "1",
        },
        "provider_requests": {"pionex": 8, "coinpaprika": 2, "total": 10},
        "authority": {
            "artifact_only_persistence": True,
            "r2_accessed": False, "d1_accessed": False, "holdout_accessed": False,
            "training_performed": False, "model_promotion_performed": False,
            "paper_submission_performed": False, "real_money_order_performed": False,
            "live_trading_performed": False,
        },
        "collection": record,
    }


def resign(report: dict[str, object]) -> None:
    record = report["collection"]
    record["record_id"] = digest({k: v for k, v in record.items() if k != "record_id"})


class ShadowContinuityTests(unittest.TestCase):
    def test_two_consistent_batches_are_partial_not_mature_or_production(self) -> None:
        earlier, later = report_fixture(0), report_fixture(1)
        result = inspect_shadow_batch_continuity([later, earlier])
        self.assertEqual(result["status"], "PARTIAL_OBSERVATION_ONLY")
        self.assertEqual(result["report_count"], 2)
        self.assertEqual(result["run_ids"], [10000, 10001])
        self.assertEqual(result["observed_gap_count"], 0)
        self.assertEqual(result["context_warmup_state"], "INSUFFICIENT")
        self.assertEqual(result["shared_overlapping_candles_consistent"], 5 * 236)
        self.assertFalse(result["github_run_metadata_authenticated"])
        self.assertFalse(result["source_archive_digests_authenticated"])
        self.assertFalse(result["full_schedule_coverage_proven"])
        self.assertFalse(result["production_eligibility_proven"])
        self.assertFalse(result["execution_authority"])
        self.assertFalse(result["signal_outcome_evaluation_performed"])

    def test_market_churn_and_gaps_do_not_invent_continuity(self) -> None:
        changed = (*SYMBOLS[:4], "LINK_USDT_PERP")
        out = inspect_shadow_batch_continuity([
            report_fixture(0), report_fixture(2, symbols=changed),
        ])
        self.assertEqual(out["status"], "REVIEW_REQUIRED")
        self.assertEqual(out["observed_gap_count"], 1)
        self.assertEqual(out["observed_gaps"][0]["elapsed_minutes"], 480)
        self.assertEqual(out["shared_overlapping_candles_consistent"], 4 * 232)
        self.assertTrue(out["symbol_rotation_allowed"])

    def test_overlapping_candle_revision_requires_review_even_when_hashes_updated(self) -> None:
        earlier, later = report_fixture(0), report_fixture(1)
        candle = later["collection"]["market_evidence"][0]["candles_60m"][0]
        candle["close"] += 8.0
        market = later["collection"]["market_evidence"][0]
        market["candles_sha256"] = digest(market["candles_60m"])
        resign(later)
        with self.assertRaisesRegex(ContinuityReviewRequired, "REVISED_OVERLAPPING_CANDLE"):
            inspect_shadow_batch_continuity([earlier, later])

    def test_tampered_record_or_candle_hash_fails_closed(self) -> None:
        for change in ("record", "candle", "future_candle", "future_feature"):
            report = report_fixture(0)
            if change == "record":
                report["collection"]["capture_timestamp_ms"] += 1
            elif change == "candle":
                report["collection"]["market_evidence"][0]["candles_60m"][0]["volume"] = 900.0
                resign(report)
            elif change == "future_candle":
                market = report["collection"]["market_evidence"][0]
                market["candles_60m"][-1]["time_ms"] += HOUR_MS
                market["candles_sha256"] = digest(market["candles_60m"])
                resign(report)
            else:
                report["collection"]["market_evidence"][0]["technical"]["available_at_ms"] = BASE + 1
                resign(report)
            with self.subTest(change=change), self.assertRaises(ContinuityReviewRequired):
                inspect_shadow_batch_continuity([report])

    def test_refuses_misrepresented_authority_and_context(self) -> None:
        cases = [
            ("event", lambda r: r["github"].update(event_name="workflow_dispatch")),
            ("rerun", lambda r: r["github"].update(run_attempt="2")),
            ("r2", lambda r: r["authority"].update(r2_accessed=True)),
            ("request", lambda r: r["provider_requests"].update(total=11)),
            ("comparison", lambda r: r["collection"]["comparison_source"].update(status="AVAILABLE")),
            ("promotion", lambda r: r["collection"]["authority"].update(model_promotion_performed=True)),
            ("regime", lambda r: r["collection"]["regime_observation_input"].update(
                production_regime_equivalence_claimed=True
            )),
        ]
        for name, change in cases:
            report = report_fixture(0)
            change(report)
            if name in {"comparison", "promotion", "regime"}:
                resign(report)
            with self.subTest(case=name), self.assertRaises(ContinuityReviewRequired):
                inspect_shadow_batch_continuity([report])

    def test_dedup_and_bounds(self) -> None:
        first = report_fixture(0)
        with self.assertRaisesRegex(ContinuityReviewRequired, "DUPLICATE_RUN_ID"):
            inspect_shadow_batch_continuity([first, copy.deepcopy(first)])
        for rows in ([], [first] * 101):
            with self.assertRaisesRegex(ContinuityReviewRequired, "BATCH_COUNT"):
                inspect_shadow_batch_continuity(rows)

    def test_21_context_observations_only_reach_count_not_readiness(self) -> None:
        rows = [report_fixture(i) for i in range(21)]
        got = inspect_shadow_batch_continuity(rows)
        self.assertEqual(got["context_warmup_state"], "COUNT_REACHED_NOT_VALIDATED")
        self.assertEqual(got["status"], "PARTIAL_OBSERVATION_ONLY")
        self.assertFalse(got["production_eligibility_proven"])
        self.assertFalse(got["full_schedule_coverage_proven"])


class ShadowFeatureCoverageV01Tests(unittest.TestCase):
    @staticmethod
    def _with_attested_features(index: int = 0) -> dict[str, object]:
        report = report_fixture(index)
        for row in report["collection"]["market_evidence"]:
            bar_start = row["candles_60m"][-1]["time_ms"]
            bar_close = bar_start + HOUR_MS
            for family in ("technical", "structure", "patterns"):
                row[family]["bar_time_ms"] = bar_start
                row[family]["available_at_ms"] = bar_close
            row["technical"].update({
                "ema20": 100.0,
                "ema50": None,
                "atr14": 0.0,
                "volume_ratio": 1.0,
            })
            row["structure"].update({
                "rolling_previous_high": 110.0,
                "rolling_previous_low": 90.0,
                "market_structure_state": "RANGE",
            })
            row["patterns"].update({
                "liquidity_event": "NONE",
                "fvg_bias": "NONE",
                "order_block_bias": "NONE",
                "macd_divergence": "NONE",
            })
            row["market_event_radar"].update({
                "observed_at_ms": bar_start,
                "available_at_ms": bar_close,
                "features": {"relative_volume": 0.0, "liquidation_imbalance": None},
            })
        resign(report)
        return report

    def test_confirmed_inputs_count_closed_rows_and_explicit_unknowns(self) -> None:
        out = inspect_shadow_feature_coverage([self._with_attested_features()])
        self.assertEqual(out["observed_report_count"], 1)
        self.assertEqual(out["market_snapshot_rows"], 5)
        self.assertEqual(out["closed_60m_input_rows_including_overlap"], 1200)
        self.assertEqual(out["unique_closed_60m_symbol_time_pairs"], 1200)
        self.assertEqual(out["status"], "PARTIAL_RESEARCH_ONLY")
        self.assertEqual(out["timeframes"]["15M"], "NOT_COLLECTED_IN_THIS_REPORT")
        self.assertIsNone(out["costs"]["fees_bps"])
        self.assertFalse(out["source_archive_digests_authenticated"])
        self.assertTrue(out["feature_timestamp_order_validated_for_attested_snapshots"])
        self.assertFalse(out["no_lookahead_verified_for_attested_feature_snapshots"])
        self.assertFalse(out["historical_signal_cutoff_no_lookahead_proven"])
        self.assertFalse(out["signal_outcome_predictive_edge_proven"])
        self.assertFalse(out["authority"]["paper_submission"])

        ema = out["features"]["technical.ema20"]
        self.assertEqual(ema["available"], 5)
        self.assertTrue(ema["complete_coverage_proven"])
        self.assertEqual(ema["point_in_time_coverage_fraction"], 1.0)
        self.assertEqual(
            out["features"]["market_event_radar.relative_volume"]["available"], 5
        )
        self.assertEqual(out["features"]["technical.ema50"]["explicit_null"], 5)
        self.assertEqual(out["features"]["technical.ema50"]["point_in_time_coverage_fraction"], 0.0)
        self.assertEqual(out["features"]["technical.macd_histogram"]["missing"], 5)
        self.assertIsNone(
            out["features"]["technical.macd_histogram"]["point_in_time_coverage_fraction"]
        )
        self.assertEqual(
            out["features"]["market_event_radar.liquidation_imbalance"]["explicit_null"], 5
        )

    def test_attested_timestamp_does_not_validate_feature_computation(self) -> None:
        report = self._with_attested_features()
        # A fabricated but finite value with plausible timestamps is still unverified.
        report["collection"]["market_evidence"][0]["technical"]["ema20"] = 999999.0
        resign(report)
        out = inspect_shadow_feature_coverage([report])
        self.assertTrue(out["feature_timestamp_order_validated_for_attested_snapshots"])
        self.assertFalse(out["no_lookahead_verified_for_attested_feature_snapshots"])
        self.assertFalse(out["historical_signal_cutoff_no_lookahead_proven"])

    def test_unattested_timestamps_never_count_as_feature_coverage(self) -> None:
        report = self._with_attested_features()
        for row in report["collection"]["market_evidence"]:
            del row["technical"]["bar_time_ms"]
        resign(report)
        result = inspect_shadow_feature_coverage([report])
        feature = result["features"]["technical.ema20"]
        self.assertEqual(feature["unattested_time"], 5)
        self.assertEqual(feature["available"], 0)
        self.assertIsNone(feature["point_in_time_coverage_fraction"])
        self.assertFalse(feature["complete_coverage_proven"])

    def test_reject_future_premature_and_mismatched_feature_lineage(self) -> None:
        for kind in ("radar_future", "premature", "source_bar_mismatch", "invalid_value"):
            report = self._with_attested_features()
            row = report["collection"]["market_evidence"][0]
            if kind == "radar_future":
                row["market_event_radar"]["available_at_ms"] = (
                    report["collection"]["capture_timestamp_ms"] + 1
                )
            elif kind == "premature":
                row["technical"]["available_at_ms"] -= 1
            elif kind == "source_bar_mismatch":
                row["patterns"]["bar_time_ms"] -= HOUR_MS
            else:
                row["technical"]["ema20"] = [100.0]
            resign(report)
            with self.subTest(kind=kind), self.assertRaises(ContinuityReviewRequired):
                inspect_shadow_feature_coverage([report])

    def test_invalid_types_and_states_cannot_inflate_verified_coverage(self) -> None:
        cases = [
            ("numeric_as_string", "technical", "ema20", "100.0"),
            ("numeric_bool", "technical", "atr14", False),
            ("numeric_giant_int", "technical", "ema20", 10 ** 400),
            ("enum_as_bool", "structure", "market_structure_state", True),
            ("enum_unrecognized", "patterns", "fvg_bias", "TO_THE_MOON"),
            ("enum_blank", "patterns", "liquidity_event", ""),
            ("radar_numeric_string", "market_event_radar", "relative_volume", "2.0"),
            ("radar_negative_volume", "market_event_radar", "relative_volume", -1.0),
            ("radar_imbalance_range", "market_event_radar", "liquidation_imbalance", 1.2),
        ]
        for label, family, field, value in cases:
            report = self._with_attested_features()
            row = report["collection"]["market_evidence"][0]
            target = row[family]
            if family == "market_event_radar":
                target = target["features"]
            target[field] = value
            resign(report)
            with self.subTest(case=label), self.assertRaises(ContinuityReviewRequired):
                inspect_shadow_feature_coverage([report])

    def test_overlaps_are_not_counted_as_unique_historical_candles(self) -> None:
        first = self._with_attested_features(0)
        second = self._with_attested_features(1)
        out = inspect_shadow_feature_coverage([first, second])
        self.assertEqual(out["market_snapshot_rows"], 10)
        self.assertEqual(out["closed_60m_input_rows_including_overlap"], 2400)
        self.assertEqual(out["unique_closed_60m_symbol_time_pairs"], 1220)
        self.assertFalse(out["temporal_continuity"]["full_schedule_coverage_proven"])

    def test_source_revision_and_untrusted_authority_fail_before_coverage(self) -> None:
        report = self._with_attested_features()
        report["authority"]["paper_submission_performed"] = True
        with self.assertRaises(ContinuityReviewRequired):
            inspect_shadow_feature_coverage([report])


if __name__ == "__main__":
    unittest.main()
