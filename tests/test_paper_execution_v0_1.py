from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from crypto_autopilot.exchanges.paper import PaperBroker
from crypto_autopilot.paper.execution_v0_1 import (
    PaperExecutionPolicy,
    paper_execution_evidence,
    paper_execution_policy_from_config,
    prepare_paper_execution,
    submit_paper_execution,
)
from crypto_autopilot.portfolio.admission_v0_1 import (
    admit_portfolio,
    build_portfolio_proposal,
)
from crypto_autopilot.risk import plan_position_size


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "paper_execution_v0_1.json"


def family_report(
    *,
    family: str = "TREND_FOLLOWING",
    state: str = "FAMILY_EVIDENCE_READY_FOR_HUMAN_REVIEW",
    coverage_tag: str = "fixture-a",
) -> dict[str, object]:
    return {
        "schema": "qookey-strategy-family-validation-report-v0.1",
        "family": family,
        "category": "DIRECTIONAL",
        "state": state,
        "reasons": ["all_family_generalization_gates_pass"],
        "coverage": {
            "receipt_count": 6,
            "distinct_assets": ["BTC_USDT_PERP", "ETH_USDT_PERP", "SOL_USDT_PERP"],
            "distinct_regimes": ["BTC_CONCENTRATION", "MIXED"],
            "directions_observed": ["LONG"],
            "providers": ["synthetic_fixture"],
            "failed_edge_report_count": 0,
            "fixture_tag": coverage_tag,
        },
        "policy": {},
        "lineage": {
            "edge_report_sha256s": ["a" * 64],
            "edge_input_fingerprints": ["b" * 64],
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


def portfolio_report_for(
    *,
    symbol: str,
    family: str,
    report: dict[str, object],
    sizing,
    as_of_ms: int,
) -> dict[str, object]:
    item = build_portfolio_proposal(
        symbol=symbol,
        strategy_family=family,
        family_validation_report=report,
        as_of_ms=as_of_ms,
        sizing_plan=sizing,
    )
    return admit_portfolio(equity_usd=100.0, proposals=(item,))


class PaperExecutionV01Tests(unittest.TestCase):
    def test_ready_long_intent_uses_approved_risk_notional_exactly(self) -> None:
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
        )
        report = family_report()
        portfolio = portfolio_report_for(
            symbol="BTC_USDT_PERP",
            family="TREND_FOLLOWING",
            report=report,
            sizing=sizing,
            as_of_ms=1_000,
        )

        decision = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=report,
            portfolio_admission_report=portfolio,
            as_of_ms=1_000,
            sizing_plan=sizing,
        )

        self.assertEqual(decision.status, "READY_FOR_PAPER_BROKER")
        self.assertIsNotNone(decision.intent)
        assert decision.intent is not None
        self.assertEqual(decision.intent.notional_usd, sizing.approved_notional_usd)
        self.assertEqual(decision.intent.stop_price, sizing.stop_price)
        self.assertEqual(decision.intent.realized_risk_usd, sizing.realized_risk_usd)
        self.assertEqual(decision.intent.notional_usd, 100.0)
        self.assertTrue(decision.intent.portfolio_proposal_id.startswith("portfolio-v0-1-"))

    def test_submission_reuses_existing_repository_paper_broker_idempotency(self) -> None:
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
        )
        report = family_report()
        portfolio = portfolio_report_for(
            symbol="ETH_USDT_PERP",
            family="TREND_FOLLOWING",
            report=report,
            sizing=sizing,
            as_of_ms=2_000,
        )
        decision = prepare_paper_execution(
            symbol="ETH_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=report,
            portfolio_admission_report=portfolio,
            as_of_ms=2_000,
            sizing_plan=sizing,
        )
        broker = PaperBroker()

        first = submit_paper_execution(decision, broker)
        second = submit_paper_execution(decision, broker)

        self.assertEqual(first.order_id, second.order_id)
        self.assertFalse(first.replayed)
        self.assertTrue(second.replayed)
        self.assertEqual(len(broker.orders), 1)
        self.assertEqual(broker.orders[0].notional_usd, sizing.approved_notional_usd)

    def test_family_review_not_ready_blocks_before_portfolio(self) -> None:
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
        )
        bad_report = family_report(state="INSUFFICIENT_GENERALIZATION_COVERAGE")
        valid_report = family_report()
        valid_portfolio = portfolio_report_for(
            symbol="BTC_USDT_PERP",
            family="TREND_FOLLOWING",
            report=valid_report,
            sizing=sizing,
            as_of_ms=1_000,
        )

        decision = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=bad_report,
            portfolio_admission_report=valid_portfolio,
            as_of_ms=1_000,
            sizing_plan=sizing,
        )

        self.assertEqual(decision.status, "NO_EXECUTION")
        self.assertEqual(decision.reason, "family_review_not_ready")

    def test_portfolio_must_admit_exact_reconstructed_proposal(self) -> None:
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
        )
        report = family_report()
        unrelated_sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=98.0,
        )
        unrelated_portfolio = portfolio_report_for(
            symbol="BTC_USDT_PERP",
            family="TREND_FOLLOWING",
            report=report,
            sizing=unrelated_sizing,
            as_of_ms=1_000,
        )

        decision = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=report,
            portfolio_admission_report=unrelated_portfolio,
            as_of_ms=1_000,
            sizing_plan=sizing,
        )

        self.assertEqual(decision.status, "NO_EXECUTION")
        self.assertEqual(decision.reason, "portfolio_proposal_not_admitted")

    def test_portfolio_review_required_blocks_paper_execution(self) -> None:
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
        )
        report = family_report()
        portfolio = portfolio_report_for(
            symbol="BTC_USDT_PERP",
            family="TREND_FOLLOWING",
            report=report,
            sizing=sizing,
            as_of_ms=1_000,
        )
        portfolio["state"] = "PORTFOLIO_REVIEW_REQUIRED"
        portfolio["admitted_proposal_ids"] = []
        portfolio["rejected_proposal_ids"] = list(
            portfolio.get("admitted_proposal_ids", [])
        )

        decision = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=report,
            portfolio_admission_report=portfolio,
            as_of_ms=1_000,
            sizing_plan=sizing,
        )

        self.assertEqual(decision.status, "NO_EXECUTION")
        self.assertEqual(decision.reason, "portfolio_not_admitted")

    def test_family_and_portfolio_lineage_are_bound_into_intent_id(self) -> None:
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
        )
        report = family_report()
        portfolio = portfolio_report_for(
            symbol="BTC_USDT_PERP",
            family="TREND_FOLLOWING",
            report=report,
            sizing=sizing,
            as_of_ms=1_000,
        )
        portfolio_variant = copy.deepcopy(portfolio)
        portfolio_variant["fixture_tag"] = "different-portfolio-lineage"

        first = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=report,
            portfolio_admission_report=portfolio,
            as_of_ms=1_000,
            sizing_plan=sizing,
        )
        second = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=report,
            portfolio_admission_report=portfolio_variant,
            as_of_ms=1_000,
            sizing_plan=sizing,
        )

        assert first.intent is not None
        assert second.intent is not None
        self.assertNotEqual(first.intent.intent_id, second.intent.intent_id)
        self.assertNotEqual(
            first.intent.portfolio_admission_report_sha256,
            second.intent.portfolio_admission_report_sha256,
        )

    def test_family_mismatch_or_unregistered_family_fails_closed(self) -> None:
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
        )
        valid_report = family_report()
        portfolio = portfolio_report_for(
            symbol="BTC_USDT_PERP",
            family="TREND_FOLLOWING",
            report=valid_report,
            sizing=sizing,
            as_of_ms=1_000,
        )

        mismatch = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="MOMENTUM",
            family_validation_report=family_report(family="TREND_FOLLOWING"),
            portfolio_admission_report=portfolio,
            as_of_ms=1_000,
            sizing_plan=sizing,
        )
        unknown = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="UNKNOWN",
            family_validation_report=family_report(family="UNKNOWN"),
            portfolio_admission_report=portfolio,
            as_of_ms=1_000,
            sizing_plan=sizing,
        )

        self.assertEqual(mismatch.reason, "family_validation_family_mismatch")
        self.assertEqual(unknown.reason, "unregistered_strategy_family")

    def test_sizing_must_be_ready(self) -> None:
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=101.0,
        )
        valid_sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
        )
        report = family_report()
        portfolio = portfolio_report_for(
            symbol="BTC_USDT_PERP",
            family="TREND_FOLLOWING",
            report=report,
            sizing=valid_sizing,
            as_of_ms=1_000,
        )

        decision = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=report,
            portfolio_admission_report=portfolio,
            as_of_ms=1_000,
            sizing_plan=sizing,
        )

        self.assertEqual(decision.status, "NO_EXECUTION")
        self.assertEqual(decision.reason, "position_sizing_not_ready")

    def test_short_research_sizing_does_not_open_short_paper_execution(self) -> None:
        sizing = plan_position_size(
            direction="SHORT",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=101.0,
        )
        report = family_report()
        portfolio = portfolio_report_for(
            symbol="BTC_USDT_PERP",
            family="TREND_FOLLOWING",
            report=report,
            sizing=sizing,
            as_of_ms=1_000,
        )

        decision = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=report,
            portfolio_admission_report=portfolio,
            as_of_ms=1_000,
            sizing_plan=sizing,
        )

        self.assertEqual(decision.status, "NO_EXECUTION")
        self.assertEqual(decision.reason, "short_paper_execution_not_authorized")

    def test_family_and_portfolio_authority_must_remain_closed(self) -> None:
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
        )
        report = family_report()
        portfolio = portfolio_report_for(
            symbol="BTC_USDT_PERP",
            family="TREND_FOLLOWING",
            report=report,
            sizing=sizing,
            as_of_ms=1_000,
        )

        bad_family = copy.deepcopy(report)
        bad_family["authority"]["promotion_authority"] = 1
        family_decision = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=bad_family,
            portfolio_admission_report=portfolio,
            as_of_ms=1_000,
            sizing_plan=sizing,
        )
        self.assertEqual(
            family_decision.reason,
            "family_validation_promotion_authority_nonzero",
        )

        bad_portfolio = copy.deepcopy(portfolio)
        bad_portfolio["authority"]["paper_execution_authorized"] = True
        portfolio_decision = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=report,
            portfolio_admission_report=bad_portfolio,
            as_of_ms=1_000,
            sizing_plan=sizing,
        )
        self.assertEqual(
            portfolio_decision.reason,
            "portfolio_admission_authority_not_closed:paper_execution_authorized",
        )

    def test_evidence_keeps_live_and_automatic_paths_closed(self) -> None:
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
        )
        report = family_report()
        portfolio = portfolio_report_for(
            symbol="BTC_USDT_PERP",
            family="TREND_FOLLOWING",
            report=report,
            sizing=sizing,
            as_of_ms=1_000,
        )
        decision = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=report,
            portfolio_admission_report=portfolio,
            as_of_ms=1_000,
            sizing_plan=sizing,
        )
        receipt = submit_paper_execution(decision, PaperBroker())

        evidence = paper_execution_evidence(decision, receipt)

        self.assertFalse(evidence["authority"]["automatic_submission_authorized"])
        self.assertFalse(evidence["authority"]["short_paper_execution_authorized"])
        self.assertFalse(evidence["authority"]["real_money_order_authorized"])
        self.assertFalse(evidence["authority"]["live_trading_authorized"])

    def test_versioned_config_matches_default_policy(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        policy = paper_execution_policy_from_config(payload)

        self.assertEqual(policy, PaperExecutionPolicy())
        self.assertTrue(payload["behavior"]["require_portfolio_admission"])
        self.assertTrue(
            payload["authority"]["repository_paper_broker_long_authorized"]
        )
        self.assertFalse(payload["authority"]["automatic_submission_authorized"])
        self.assertFalse(payload["authority"]["live_trading_authorized"])

    def test_config_policy_booleans_are_strict(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        payload["behavior"]["require_portfolio_admission"] = "true"

        with self.assertRaises(ValueError):
            paper_execution_policy_from_config(payload)


if __name__ == "__main__":
    unittest.main()
