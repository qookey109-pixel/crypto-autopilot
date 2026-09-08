from __future__ import annotations

import copy
import unittest

from crypto_autopilot.daily_research_preview import build_daily_research_preview


NOW = "2024-01-01T01:00:00Z"
BAR = 1704069900000


def fixture():
    # Independent oracle for the existing paper report's prohibited capabilities.
    authority = dict.fromkeys((
        "formalTradePlanAuthorized", "pionexDemoAutomationAuthorized", "privateApiUsed",
        "r2ReadsPerformed", "r2WritesPerformed", "holdoutAccessed", "sourceSwitchAuthorized",
        "realMoneyOrderAuthorized", "liveTradingAuthorized",
    ), False)
    report = {
        "schema": "pionex-public-paper-training-run-v0.1",
        "status": "PASS", "mode": "PAPER_TRAINING_ONLY",
        "provider": "pionex_public_futures", "dataClass": "SYNTHETIC_FIXTURE",
        "observedAtUtc": NOW, "authority": authority,
        "latestCandidates": [{
            "symbol": symbol, "score": score, "eligible": True,
            "signal_time_ms": BAR, "reasons": ["eligible_paper_candidate"],
        } for symbol, score in (("BTC_USDT_PERP", 80), ("ETH_USDT_PERP", 90))],
    }
    universe = {
        "provider": "pionex_public_futures", "dataClass": "SYNTHETIC_FIXTURE",
        "observedAtUtc": NOW, "symbols": ["BTC_USDT_PERP", "ETH_USDT_PERP"],
    }
    return report, universe


def preview(report, universe, **kwargs):
    return build_daily_research_preview(
        report, universe, as_of_utc=NOW, minimum_score=65, **kwargs,
    )


class DailyResearchPreviewTests(unittest.TestCase):
    def test_deterministic_ranking_does_not_modify_inputs_or_emit_trade_geometry(self):
        report, universe = fixture()
        before = copy.deepcopy((report, universe))
        result = preview(report, universe)
        self.assertEqual(result, preview(report, universe))
        self.assertEqual((report, universe), before)
        self.assertEqual([row["symbol"] for row in result["rankings"]],
                         ["ETH_USDT_PERP", "BTC_USDT_PERP"])
        self.assertEqual([row["rank"] for row in result["rankings"]], [1, 2])
        self.assertFalse(result["productionReady"])
        self.assertTrue(all(value is False for value in result["authority"].values()))
        for row in result["rankings"]:
            self.assertEqual(set(row), {
                "symbol", "score", "signalTimeMs", "availableAtMs", "reasons", "action", "rank",
            })

    def test_ties_and_limit_are_display_only(self):
        report, universe = fixture()
        report["latestCandidates"][0]["score"] = 90
        report["latestCandidates"].reverse()
        result = preview(report, universe, limit=1)
        self.assertEqual(result["rankings"][0]["symbol"], "BTC_USDT_PERP")
        self.assertEqual(result["eligibleCount"], 2)
        self.assertEqual(result["omittedByDisplayLimit"], 1)

    def test_rejects_production_data_and_provider_substitution(self):
        for target in (0, 1):
            for field, value in (("dataClass", "PRODUCTION"), ("provider", "binance_usdm")):
                with self.subTest(target=target, field=field):
                    inputs = fixture()
                    inputs[target][field] = value
                    self.assertEqual(preview(*inputs)["status"], "BLOCKED")

    def test_every_authority_denial_is_required_and_strict(self):
        for key in fixture()[0]["authority"]:
            for value in (True, 0, "false", None):
                with self.subTest(key=key, value=value):
                    report, universe = fixture()
                    report["authority"][key] = value
                    self.assertEqual(preview(report, universe)["rankings"], [])
                    self.assertEqual(preview(report, universe)["status"], "BLOCKED")
            report, universe = fixture()
            del report["authority"][key]
            self.assertEqual(preview(report, universe)["status"], "BLOCKED")

    def test_stale_future_or_naive_snapshot_blocks_entire_preview(self):
        for target in (0, 1):
            for timestamp in ("2023-12-31T23:59:59Z", "2024-01-01T01:00:01Z",
                              "2024-01-01T01:00:00"):
                with self.subTest(target=target, timestamp=timestamp):
                    inputs = fixture()
                    inputs[target]["observedAtUtc"] = timestamp
                    self.assertEqual(preview(*inputs)["status"], "BLOCKED")

    def test_candidate_exclusion_gates(self):
        cases = (
            ({"symbol": "SOL_USDT_PERP"}, "outside_pionex_preview_universe"),
            ({"signal_time_ms": BAR + 900000}, "candle_not_closed_at_observation"),
            ({"signal_time_ms": BAR - 4500000}, "stale_signal"),
            ({"eligible": False}, "latest_candidate_ineligible"),
            ({"reasons": ["rsi_outside_gate"]}, "inconsistent_candidate_reasons"),
            ({"score": 64.9}, "below_existing_candidate_score_gate"),
        )
        for changes, reason in cases:
            with self.subTest(reason=reason):
                report, universe = fixture()
                report["latestCandidates"][0].update(changes)
                result = preview(report, universe)
                self.assertEqual(len(result["rankings"]), 1)
                self.assertEqual(result["excluded"][0]["reason"], reason)

    def test_no_fallback_to_old_eligible_candidates_or_forced_daily_quota(self):
        report, universe = fixture()
        report["manualPionexDemoSamples"] = copy.deepcopy(report["latestCandidates"])
        for row in report["latestCandidates"]:
            row["eligible"] = False
        result = preview(report, universe)
        self.assertEqual(result["status"], "WAIT_NO_ELIGIBLE_CANDIDATES")
        self.assertEqual(result["rankings"], [])
        report["latestCandidates"] = []
        self.assertEqual(preview(report, universe)["status"], "WAIT_NO_ELIGIBLE_CANDIDATES")

    def test_malformed_candidate_invalidates_entire_batch(self):
        for changes in ({"score": float("nan")}, {"score": float("inf")}, {"score": True},
                        {"eligible": "true"}, {"signal_time_ms": True},
                        {"signal_time_ms": BAR + 1}, {"reasons": []},
                        {"symbol": "BTC_USDT_PERP"}):
            with self.subTest(changes=changes):
                report, universe = fixture()
                report["latestCandidates"][1].update(changes)
                result = preview(report, universe)
                self.assertEqual(result["status"], "BLOCKED")
                self.assertEqual(result["rankings"], [])

    def test_one_hour_boundary_and_close_time_are_inclusive(self):
        report, universe = fixture()
        report["latestCandidates"][0]["signal_time_ms"] = BAR - 3600000
        report["observedAtUtc"] = "2024-01-01T00:00:00Z"
        report["latestCandidates"] = report["latestCandidates"][:1]
        self.assertEqual(preview(report, universe)["status"], "PREVIEW_READY")


if __name__ == "__main__":
    unittest.main()
