from __future__ import annotations

import json
from pathlib import Path
import unittest

from crypto_autopilot.history.pionex_150_history_plan_v0_1 import (
    HistoryPlanRejected,
    build_plan,
    validate_config,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/pionex_150_history_plan_v0_1.json"


def universe_report() -> dict[str, object]:
    markets = []
    for index in range(1, 151):
        if index <= 30:
            profile = "FULL_INTRADAY"
        elif index <= 110:
            profile = "MULTISCALE_RESEARCH"
        else:
            profile = "BREADTH_BACKGROUND"
        markets.append(
            {
                "selection_rank": index,
                "symbol": f"COIN{index}_USDT_PERP",
                "history_profile": profile,
            }
        )
    return {
        "schema": "pionex-research-universe-run-report-v0.1",
        "status": "PASS",
        "provider": "pionex_public_futures",
        "selected_market_count": len(markets),
        "markets": markets,
        "r2_accessed": False,
        "holdout_accessed": False,
    }


def reach_report() -> dict[str, object]:
    intervals = []
    for interval, records, classification in (
        ("15M", 10_000, "DOCUMENTED_RECORD_CAP_REACHED"),
        ("60M", 10_000, "DOCUMENTED_RECORD_CAP_REACHED"),
        ("4H", 8_000, "PROVIDER_EARLIEST_REACHED"),
        ("1D", 2_000, "PROVIDER_EARLIEST_REACHED"),
        ("1W", 300, "PROVIDER_EARLIEST_REACHED"),
    ):
        intervals.append(
            {
                "interval": interval,
                "classification": classification,
                "records_observed": records,
                "continuity_verified": True,
            }
        )
    return {
        "schema": "pionex-historical-reach-run-report-v0.3",
        "status": "PASS",
        "symbol": "BTC_USDT_PERP",
        "intervals": intervals,
        "r2_accessed": False,
        "holdout_accessed": False,
    }


class Pionex150HistoryPlanV01Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_config_is_prepared_only(self) -> None:
        validate_config(self.config)
        self.assertFalse(self.config["authority"]["public_pionex_requests"])
        self.assertFalse(self.config["authority"]["r2_write"])
        self.assertFalse(self.config["authority"]["historical_materialization"])
        self.assertFalse(self.config["authority"]["live_trading"])

    def test_planner_computes_tiered_request_upper_bound(self) -> None:
        plan = build_plan(
            self.config,
            universe_report=universe_report(),
            reach_report=reach_report(),
        )
        self.assertEqual(plan["selected_market_count"], 150)
        self.assertEqual(
            plan["history_profile_counts"],
            {
                "BREADTH_BACKGROUND": 40,
                "FULL_INTRADAY": 30,
                "MULTISCALE_RESEARCH": 80,
            },
        )
        self.assertEqual(plan["market_interval_job_count"], 550)
        self.assertEqual(plan["request_upper_bound"], 11_550)
        self.assertEqual(plan["provider_requests_performed"], 0)
        self.assertFalse(plan["historical_materialization_authorized"])

    def test_btc_reach_is_never_per_market_listing_proof(self) -> None:
        plan = build_plan(
            self.config,
            universe_report=universe_report(),
            reach_report=reach_report(),
        )
        first = plan["markets"][0]
        self.assertTrue(plan["btc_reach_used_as_provider_reference_only"])
        self.assertFalse(plan["per_market_listing_history_inferred_from_btc"])
        self.assertTrue(plan["each_market_earliest_boundary_must_be_proven"])
        self.assertTrue(
            all(job["market_earliest_boundary_proven"] is False for job in first["interval_jobs"])
        )

    def test_reach_report_must_cover_exact_intervals(self) -> None:
        report = reach_report()
        report["intervals"] = report["intervals"][:-1]
        with self.assertRaisesRegex(HistoryPlanRejected, "exact required intervals"):
            build_plan(
                self.config,
                universe_report=universe_report(),
                reach_report=report,
            )

    def test_universe_below_150_fails_closed(self) -> None:
        report = universe_report()
        report["markets"] = report["markets"][:149]
        report["selected_market_count"] = 149
        with self.assertRaisesRegex(HistoryPlanRejected, "at least 150"):
            build_plan(
                self.config,
                universe_report=report,
                reach_report=reach_report(),
            )

    def test_duplicate_symbol_fails_closed(self) -> None:
        report = universe_report()
        report["markets"][1]["symbol"] = report["markets"][0]["symbol"]
        with self.assertRaisesRegex(HistoryPlanRejected, "duplicate universe symbol"):
            build_plan(
                self.config,
                universe_report=report,
                reach_report=reach_report(),
            )

    def test_forbidden_boundary_in_input_fails(self) -> None:
        report = reach_report()
        report["holdout_accessed"] = True
        with self.assertRaisesRegex(HistoryPlanRejected, "forbidden boundary"):
            build_plan(
                self.config,
                universe_report=universe_report(),
                reach_report=report,
            )


if __name__ == "__main__":
    unittest.main()
