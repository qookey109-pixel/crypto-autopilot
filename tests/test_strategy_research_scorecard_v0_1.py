from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from crypto_autopilot.strategy_research_scorecard_v0_1 import (
    StrategyResearchScorecardPolicy,
    build_strategy_research_scorecard,
    scorecard_policy_from_config,
    verify_strategy_research_scorecard,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "strategy_research_scorecard_v0_1.json"


def family_report(
    family: str,
    *,
    state: str = "FAMILY_EVIDENCE_READY_FOR_HUMAN_REVIEW",
    receipt_count: int = 6,
    assets: tuple[str, ...] = (
        "BTC_USDT_PERP",
        "ETH_USDT_PERP",
        "SOL_USDT_PERP",
    ),
    regimes: tuple[str, ...] = ("MIXED", "BTC_CONCENTRATION"),
    directions: tuple[str, ...] = ("LONG", "SHORT"),
    failed_count: int = 0,
) -> dict[str, object]:
    return {
        "schema": "qookey-strategy-family-validation-report-v0.1",
        "family": family,
        "category": "fixture",
        "state": state,
        "reasons": ["fixture"],
        "coverage": {
            "receipt_count": receipt_count,
            "distinct_assets": list(assets),
            "distinct_regimes": list(regimes),
            "directions_observed": list(directions),
            "providers": ["synthetic_fixture"],
            "failed_edge_report_count": failed_count,
        },
        "policy": {
            "minimum_receipts": 6,
            "minimum_distinct_assets": 3,
            "minimum_distinct_regimes": 2,
            "require_single_provider": True,
            "require_all_edge_pass": True,
        },
        "lineage": {
            "edge_report_sha256s": [
                f"{1000 + index:064x}" for index in range(receipt_count)
            ],
            "edge_input_fingerprints": [
                f"{2000 + index:064x}" for index in range(receipt_count)
            ],
        },
        "authority": {
            "research_evidence_only": True,
            "family_registry_mutated": False,
            "strategy_edge_claimed": False,
            "provider_requests_performed": False,
            "r2_accessed": False,
            "holdout_accessed": False,
            "promotion_authority": 0,
            "position_sizing_authorized": False,
            "paper_execution_authorized": False,
            "trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
        "limitations": [],
    }


class StrategyResearchScorecardV01Tests(unittest.TestCase):
    def test_more_generalization_evidence_ranks_higher_for_research_only(self) -> None:
        broad = family_report(
            "TREND_FOLLOWING",
            receipt_count=12,
            assets=(
                "BTC_USDT_PERP",
                "ETH_USDT_PERP",
                "SOL_USDT_PERP",
                "XRP_USDT_PERP",
                "DOGE_USDT_PERP",
                "ADA_USDT_PERP",
            ),
            regimes=(
                "MIXED",
                "BTC_CONCENTRATION",
                "ALT_EXPANSION",
                "BROAD_RISK_OFF",
            ),
        )
        baseline = family_report("BREAKOUT")

        report = build_strategy_research_scorecard((baseline, broad))

        self.assertEqual(report["state"], "RESEARCH_PRIORITY_RANKING_READY")
        self.assertEqual(
            report["research_priority_order"],
            ["TREND_FOLLOWING", "BREAKOUT"],
        )
        rows = {row["family"]: row for row in report["rows"]}
        self.assertEqual(rows["TREND_FOLLOWING"]["research_rank"], 1)
        self.assertEqual(rows["BREAKOUT"]["research_rank"], 2)
        self.assertGreater(
            rows["TREND_FOLLOWING"]["research_score"],
            rows["BREAKOUT"]["research_score"],
        )
        self.assertTrue(report["ranking_performed"])
        self.assertFalse(report["winner_selected"])
        self.assertFalse(report["execution_selection_performed"])
        self.assertFalse(
            report["authority"]["automatic_strategy_selection_authorized"]
        )
        self.assertFalse(report["authority"]["paper_execution_authorized"])
        self.assertFalse(report["authority"]["real_money_order_authorized"])

        self.assertEqual(
            verify_strategy_research_scorecard(report),
            report["scorecard_id"],
        )

    def test_reject_family_is_not_ranked(self) -> None:
        ready = family_report("TREND_FOLLOWING")
        rejected = family_report(
            "MEAN_REVERSION",
            state="REJECT",
            failed_count=1,
        )

        report = build_strategy_research_scorecard((rejected, ready))
        rows = {row["family"]: row for row in report["rows"]}

        self.assertEqual(report["ranked_family_count"], 1)
        self.assertEqual(report["research_priority_order"], ["TREND_FOLLOWING"])
        self.assertFalse(rows["MEAN_REVERSION"]["rankable_for_research"])
        self.assertIsNone(rows["MEAN_REVERSION"]["research_rank"])
        self.assertEqual(rows["MEAN_REVERSION"]["research_score"], 0.0)

    def test_insufficient_family_can_be_prioritized_for_more_research_not_execution(self) -> None:
        report = build_strategy_research_scorecard(
            (
                family_report(
                    "MOMENTUM",
                    state="INSUFFICIENT_GENERALIZATION_COVERAGE",
                    receipt_count=4,
                    assets=("BTC_USDT_PERP", "ETH_USDT_PERP"),
                    regimes=("MIXED",),
                ),
            )
        )
        row = report["rows"][0]
        self.assertTrue(row["rankable_for_research"])
        self.assertEqual(row["research_rank"], 1)
        self.assertLess(row["state_multiplier"], 1.0)
        self.assertFalse(report["authority"]["ranking_is_trade_recommendation"])
        self.assertFalse(report["authority"]["paper_execution_authorized"])

    def test_equal_scores_use_family_name_tie_breaker(self) -> None:
        breakout = family_report("BREAKOUT")
        momentum = family_report("MOMENTUM")

        first = build_strategy_research_scorecard((momentum, breakout))
        second = build_strategy_research_scorecard((breakout, momentum))

        self.assertEqual(first["research_priority_order"], ["BREAKOUT", "MOMENTUM"])
        self.assertEqual(first["research_priority_order"], second["research_priority_order"])
        self.assertEqual(first["scorecard_id"], second["scorecard_id"])

    def test_tampered_scored_row_fails_verification(self) -> None:
        report = build_strategy_research_scorecard(
            (family_report("TREND_FOLLOWING"),)
        )
        tampered = copy.deepcopy(report)
        tampered["rows"][0]["research_score"] = 99.999

        with self.assertRaises(ValueError):
            verify_strategy_research_scorecard(tampered)

    def test_unsafe_family_authority_fails_closed(self) -> None:
        unsafe = family_report("TREND_FOLLOWING")
        unsafe["authority"]["paper_execution_authorized"] = True

        with self.assertRaises(ValueError):
            build_strategy_research_scorecard((unsafe,))

    def test_policy_cannot_enable_selection_or_execution(self) -> None:
        with self.assertRaises(ValueError):
            StrategyResearchScorecardPolicy(
                automatic_strategy_selection_authorized=True
            )
        with self.assertRaises(ValueError):
            StrategyResearchScorecardPolicy(paper_execution_authorized=True)
        with self.assertRaises(ValueError):
            StrategyResearchScorecardPolicy(real_money_order_authorized=True)

    def test_versioned_config_matches_defaults(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            scorecard_policy_from_config(payload),
            StrategyResearchScorecardPolicy(),
        )

        bad = json.loads(CONFIG.read_text(encoding="utf-8"))
        bad["policy"]["winner_selection_authorized"] = True
        with self.assertRaises(ValueError):
            scorecard_policy_from_config(bad)


if __name__ == "__main__":
    unittest.main()
