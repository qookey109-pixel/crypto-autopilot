from __future__ import annotations

import json
import unittest
from pathlib import Path

from crypto_autopilot.portfolio.admission_v0_1 import (
    PortfolioExposure,
    PortfolioPolicy,
    admit_portfolio,
    build_portfolio_proposal,
    portfolio_policy_from_config,
)
from crypto_autopilot.risk import plan_position_size


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "portfolio_admission_v0_1.json"


def family_report(family: str) -> dict[str, object]:
    return {
        "schema": "qookey-strategy-family-validation-report-v0.1",
        "family": family,
        "category": "fixture",
        "state": "FAMILY_EVIDENCE_READY_FOR_HUMAN_REVIEW",
        "reasons": ["all_family_generalization_gates_pass"],
        "coverage": {},
        "policy": {},
        "lineage": {},
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


def proposal(
    *,
    symbol: str,
    family: str,
    direction: str = "LONG",
    as_of_ms: int = 1_000,
):
    if direction == "LONG":
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
        )
    else:
        sizing = plan_position_size(
            direction="SHORT",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=101.0,
        )
    return build_portfolio_proposal(
        symbol=symbol,
        strategy_family=family,
        family_validation_report=family_report(family),
        as_of_ms=as_of_ms,
        sizing_plan=sizing,
    )


class PortfolioAdmissionV01Tests(unittest.TestCase):
    def test_balanced_three_route_basket_is_admitted(self) -> None:
        proposals = (
            proposal(symbol="BTC_USDT_PERP", family="TREND_FOLLOWING"),
            proposal(symbol="ETH_USDT_PERP", family="MOMENTUM"),
            proposal(symbol="SOL_USDT_PERP", family="MEAN_REVERSION"),
        )

        report = admit_portfolio(equity_usd=100.0, proposals=proposals)

        self.assertEqual(report["state"], "PORTFOLIO_ADMITTED")
        self.assertEqual(report["admitted_proposal_ids"], [p.proposal_id for p in proposals])
        self.assertEqual(report["rejected_proposal_ids"], [])
        self.assertAlmostEqual(report["metrics"]["total_realized_risk_fraction"], 0.03)
        self.assertAlmostEqual(report["metrics"]["gross_notional_fraction"], 3.0)
        self.assertFalse(report["ranking_performed"])
        self.assertFalse(report["subset_selection_performed"])

    def test_risk_ready_three_x_single_symbol_is_rejected_by_portfolio_notional_cap(self) -> None:
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.8,
        )
        item = build_portfolio_proposal(
            symbol="BTC_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=family_report("TREND_FOLLOWING"),
            as_of_ms=1_000,
            sizing_plan=sizing,
        )

        self.assertEqual(sizing.status, "SIZING_READY")
        self.assertAlmostEqual(sizing.approved_notional_usd, 300.0)

        report = admit_portfolio(equity_usd=100.0, proposals=(item,))

        self.assertEqual(report["state"], "PORTFOLIO_REVIEW_REQUIRED")
        self.assertIn("symbol_notional_above_cap:BTC_USDT_PERP", report["reasons"])

    def test_proposals_must_share_portfolio_equity_basis(self) -> None:
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=200.0,
            entry_price=100.0,
            stop_price=99.0,
        )
        item = build_portfolio_proposal(
            symbol="BTC_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=family_report("TREND_FOLLOWING"),
            as_of_ms=1_000,
            sizing_plan=sizing,
        )

        with self.assertRaises(ValueError):
            admit_portfolio(equity_usd=100.0, proposals=(item,))

    def test_symbol_concentration_rejects_entire_explicit_basket(self) -> None:
        proposals = (
            proposal(symbol="BTC_USDT_PERP", family="TREND_FOLLOWING"),
            proposal(symbol="BTC_USDT_PERP", family="MEAN_REVERSION"),
        )

        report = admit_portfolio(equity_usd=100.0, proposals=proposals)

        self.assertEqual(report["state"], "PORTFOLIO_REVIEW_REQUIRED")
        self.assertIn(
            "symbol_realized_risk_above_cap:BTC_USDT_PERP",
            report["reasons"],
        )
        self.assertEqual(report["admitted_proposal_ids"], [])
        self.assertEqual(
            report["rejected_proposal_ids"], [p.proposal_id for p in proposals]
        )

    def test_directional_strategy_overlap_cap_is_enforced(self) -> None:
        proposals = (
            proposal(symbol="BTC_USDT_PERP", family="TREND_FOLLOWING"),
            proposal(symbol="ETH_USDT_PERP", family="BREAKOUT"),
            proposal(symbol="SOL_USDT_PERP", family="MOMENTUM"),
        )

        report = admit_portfolio(equity_usd=100.0, proposals=proposals)

        self.assertEqual(report["state"], "PORTFOLIO_REVIEW_REQUIRED")
        self.assertIn("overlap_group_risk_above_cap:DIRECTIONAL", report["reasons"])

    def test_existing_exposure_is_counted_before_new_proposals(self) -> None:
        existing = (
            PortfolioExposure(
                exposure_id="open-btc",
                symbol="BTC_USDT_PERP",
                strategy_family="TREND_FOLLOWING",
                direction="LONG",
                notional_usd=100.0,
                realized_risk_usd=1.0,
            ),
        )
        proposals = (
            proposal(symbol="BTC_USDT_PERP", family="MEAN_REVERSION"),
        )

        report = admit_portfolio(
            equity_usd=100.0,
            proposals=proposals,
            existing_exposures=existing,
        )

        self.assertEqual(report["state"], "PORTFOLIO_REVIEW_REQUIRED")
        self.assertEqual(report["existing_exposure_count"], 1)
        self.assertIn(
            "symbol_realized_risk_above_cap:BTC_USDT_PERP",
            report["reasons"],
        )

    def test_opposing_directions_same_symbol_fail_closed(self) -> None:
        proposals = (
            proposal(symbol="BTC_USDT_PERP", family="TREND_FOLLOWING", direction="LONG"),
            proposal(symbol="BTC_USDT_PERP", family="MEAN_REVERSION", direction="SHORT"),
        )
        policy = PortfolioPolicy(
            maximum_total_realized_risk_fraction=0.05,
            maximum_symbol_realized_risk_fraction=0.05,
            maximum_overlap_group_realized_risk_fraction=0.05,
            maximum_gross_notional_fraction=5.0,
            maximum_symbol_notional_fraction=5.0,
            maximum_routes_per_symbol=2,
        )

        report = admit_portfolio(
            equity_usd=100.0,
            proposals=proposals,
            policy=policy,
        )

        self.assertEqual(report["state"], "PORTFOLIO_REVIEW_REQUIRED")
        self.assertIn(
            "opposing_directions_same_symbol:BTC_USDT_PERP",
            report["reasons"],
        )

    def test_route_count_cap_is_enforced_without_family_ranking(self) -> None:
        proposals = (
            proposal(symbol="BTC_USDT_PERP", family="TREND_FOLLOWING"),
            proposal(symbol="BTC_USDT_PERP", family="MOMENTUM"),
            proposal(symbol="BTC_USDT_PERP", family="BREAKOUT"),
        )
        policy = PortfolioPolicy(
            maximum_total_realized_risk_fraction=0.10,
            maximum_symbol_realized_risk_fraction=0.10,
            maximum_overlap_group_realized_risk_fraction=0.10,
            maximum_gross_notional_fraction=10.0,
            maximum_symbol_notional_fraction=10.0,
            maximum_routes_per_symbol=2,
        )

        report = admit_portfolio(
            equity_usd=100.0,
            proposals=proposals,
            policy=policy,
        )

        self.assertEqual(report["state"], "PORTFOLIO_REVIEW_REQUIRED")
        self.assertIn("routes_per_symbol_above_cap:BTC_USDT_PERP", report["reasons"])
        self.assertFalse(report["ranking_performed"])
        self.assertFalse(report["subset_selection_performed"])

    def test_family_validation_and_sizing_must_be_ready(self) -> None:
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
        )
        report = family_report("TREND_FOLLOWING")
        report["state"] = "INSUFFICIENT_GENERALIZATION_COVERAGE"

        with self.assertRaises(ValueError):
            build_portfolio_proposal(
                symbol="BTC_USDT_PERP",
                strategy_family="TREND_FOLLOWING",
                family_validation_report=report,
                as_of_ms=1_000,
                sizing_plan=sizing,
            )

        bad_sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=101.0,
        )
        with self.assertRaises(ValueError):
            build_portfolio_proposal(
                symbol="BTC_USDT_PERP",
                strategy_family="TREND_FOLLOWING",
                family_validation_report=family_report("TREND_FOLLOWING"),
                as_of_ms=1_000,
                sizing_plan=bad_sizing,
            )

    def test_duplicate_proposal_ids_fail_closed(self) -> None:
        item = proposal(symbol="BTC_USDT_PERP", family="TREND_FOLLOWING")
        with self.assertRaises(ValueError):
            admit_portfolio(equity_usd=100.0, proposals=(item, item))

    def test_empty_basket_is_explicit_no_proposals(self) -> None:
        report = admit_portfolio(equity_usd=100.0, proposals=())
        self.assertEqual(report["state"], "NO_PROPOSALS")
        self.assertEqual(report["admitted_proposal_ids"], [])

    def test_versioned_config_matches_frozen_policy(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        policy = portfolio_policy_from_config(payload)

        self.assertEqual(policy, PortfolioPolicy())
        self.assertFalse(payload["behavior"]["ranking_performed"])
        self.assertFalse(payload["behavior"]["subset_optimizer_present"])
        self.assertFalse(payload["authority"]["live_trading_authorized"])
        self.assertEqual(set(payload["overlap_groups"]), {"DIRECTIONAL", "RANGE"})

    def test_config_boolean_types_are_strict(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        payload["policy"]["automatic_subset_selection_authorized"] = "false"

        with self.assertRaises(ValueError):
            portfolio_policy_from_config(payload)


if __name__ == "__main__":
    unittest.main()
