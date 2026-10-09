from __future__ import annotations

import copy
import hashlib
import json
import unittest

from crypto_autopilot.research.prospective_shadow_continuity_v0_1 import (
    ContinuityReviewRequired,
    inspect_shadow_batch_continuity,
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


if __name__ == "__main__":
    unittest.main()
