from __future__ import annotations

import json
import unittest
from dataclasses import asdict
from pathlib import Path

from crypto_autopilot.exchanges.paper import PaperBroker
from crypto_autopilot.paper.cycle_v0_1 import (
    PaperCyclePolicy,
    paper_cycle_input_from_dict,
    paper_cycle_policy_from_config,
    prepare_paper_cycle,
)
from crypto_autopilot.paper.execution_v0_1 import (
    paper_execution_evidence,
    prepare_paper_execution,
    submit_paper_execution,
)
from crypto_autopilot.paper.lifecycle_v0_1 import (
    PaperLifecyclePolicy,
    PaperLiquidityBar,
    build_paper_lifecycle_plan,
    lifecycle_evidence,
    simulate_paper_lifecycle,
)
from crypto_autopilot.portfolio.admission_v0_1 import (
    admit_portfolio,
    build_portfolio_proposal,
)
from crypto_autopilot.risk import plan_position_size


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "paper_cycle_orchestrator_v0_1.json"


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


def empty_account() -> dict[str, object]:
    return {
        "schema": "qookey-paper-account-state-input-v0.1",
        "initial_equity_usd": 100.0,
        "records": [],
        "marks": [],
    }


def candidate(
    *,
    symbol: str,
    family: str,
    as_of_ms: int = 1_000,
    direction: str = "LONG",
    sizing_equity_usd: float = 100.0,
) -> dict[str, object]:
    if direction == "LONG":
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=sizing_equity_usd,
            entry_price=100.0,
            stop_price=99.0,
        )
    else:
        sizing = plan_position_size(
            direction="SHORT",
            equity_usd=sizing_equity_usd,
            entry_price=100.0,
            stop_price=101.0,
        )
    return {
        "symbol": symbol,
        "strategy_family": family,
        "as_of_ms": as_of_ms,
        "family_validation_report": family_report(family),
        "position_sizing_plan": asdict(sizing),
    }


def open_account_input() -> dict[str, object]:
    report = family_report("TREND_FOLLOWING")
    sizing = plan_position_size(
        direction="LONG",
        equity_usd=100.0,
        entry_price=100.0,
        stop_price=99.0,
    )
    proposal = build_portfolio_proposal(
        symbol="BTC_USDT_PERP",
        strategy_family="TREND_FOLLOWING",
        family_validation_report=report,
        as_of_ms=1_000,
        sizing_plan=sizing,
    )
    portfolio = admit_portfolio(equity_usd=100.0, proposals=(proposal,))
    decision = prepare_paper_execution(
        symbol="BTC_USDT_PERP",
        strategy_family="TREND_FOLLOWING",
        family_validation_report=report,
        portfolio_admission_report=portfolio,
        as_of_ms=1_000,
        sizing_plan=sizing,
    )
    receipt = submit_paper_execution(decision, PaperBroker())
    execution = paper_execution_evidence(decision, receipt)

    plan = build_paper_lifecycle_plan(
        decision=decision,
        receipt=receipt,
        target_price=105.0,
    )
    result = simulate_paper_lifecycle(
        plan=plan,
        bars=(
            PaperLiquidityBar(
                time_ms=2_000,
                open=100.0,
                high=101.0,
                low=99.5,
                close=100.5,
                available_notional_usd=4_000.0,
            ),
        ),
    )
    lifecycle = lifecycle_evidence(
        plan=plan,
        result=result,
        policy=PaperLifecyclePolicy(),
    )
    return {
        "schema": "qookey-paper-account-state-input-v0.1",
        "initial_equity_usd": 100.0,
        "records": [
            {
                "paper_execution_evidence": execution,
                "paper_lifecycle_report": lifecycle,
            }
        ],
        "marks": [
            {
                "symbol": "BTC_USDT_PERP",
                "time_ms": 3_000,
                "price": 100.5,
            }
        ],
    }


class PaperCycleOrchestratorV01Tests(unittest.TestCase):
    def test_empty_account_single_candidate_prepares_intent_without_submission(self) -> None:
        report = prepare_paper_cycle(
            account_input=empty_account(),
            candidate_inputs=(
                candidate(
                    symbol="BTC_USDT_PERP",
                    family="TREND_FOLLOWING",
                ),
            ),
        )

        self.assertEqual(
            report["state"],
            "PAPER_INTENTS_READY_FOR_EXPLICIT_SUBMISSION",
        )
        self.assertTrue(report["explicit_submission_required"])
        self.assertTrue(report["explicit_submission_allowed"])
        self.assertEqual(report["broker_submissions_performed"], 0)
        self.assertEqual(report["lifecycle_simulations_performed"], 0)
        self.assertEqual(len(report["prepared_intents"]), 1)
        self.assertEqual(
            report["paper_execution_decisions"][0]["decision"]["status"],
            "READY_FOR_PAPER_BROKER",
        )

    def test_candidate_input_order_does_not_change_cycle_id(self) -> None:
        btc = candidate(
            symbol="BTC_USDT_PERP",
            family="TREND_FOLLOWING",
        )
        eth = candidate(
            symbol="ETH_USDT_PERP",
            family="MEAN_REVERSION",
        )

        first = prepare_paper_cycle(
            account_input=empty_account(),
            candidate_inputs=(btc, eth),
        )
        second = prepare_paper_cycle(
            account_input=empty_account(),
            candidate_inputs=(eth, btc),
        )

        self.assertEqual(first["state"], second["state"])
        self.assertEqual(first["cycle_id"], second["cycle_id"])
        self.assertEqual(first["prepared_intents"], second["prepared_intents"])

    def test_same_symbol_basket_is_rejected_by_portfolio_before_intents(self) -> None:
        report = prepare_paper_cycle(
            account_input=empty_account(),
            candidate_inputs=(
                candidate(
                    symbol="BTC_USDT_PERP",
                    family="TREND_FOLLOWING",
                ),
                candidate(
                    symbol="BTC_USDT_PERP",
                    family="MEAN_REVERSION",
                ),
            ),
        )

        self.assertEqual(report["state"], "PORTFOLIO_REVIEW_REQUIRED")
        self.assertFalse(report.get("explicit_submission_allowed", False))
        self.assertEqual(report["prepared_intents"], [])
        self.assertTrue(
            any(
                reason.startswith("symbol_realized_risk_above_cap:BTC_USDT_PERP")
                for reason in report["reasons"]
            )
        )

    def test_short_candidate_keeps_entire_cycle_review_required(self) -> None:
        report = prepare_paper_cycle(
            account_input=empty_account(),
            candidate_inputs=(
                candidate(
                    symbol="BTC_USDT_PERP",
                    family="TREND_FOLLOWING",
                    direction="SHORT",
                ),
            ),
        )

        self.assertEqual(report["state"], "CYCLE_REVIEW_REQUIRED")
        self.assertFalse(report["explicit_submission_allowed"])
        self.assertEqual(
            report["paper_execution_decisions"][0]["decision"]["reason"],
            "short_paper_execution_not_authorized",
        )

    def test_no_candidates_is_explicit_non_execution_state(self) -> None:
        report = prepare_paper_cycle(
            account_input=empty_account(),
            candidate_inputs=(),
        )

        self.assertEqual(report["state"], "NO_CANDIDATES")
        self.assertEqual(report["prepared_intents"], [])
        self.assertEqual(report["broker_submissions_performed"], 0)

    def test_account_existing_exposure_feeds_next_portfolio_gate(self) -> None:
        report = prepare_paper_cycle(
            account_input=open_account_input(),
            candidate_inputs=(
                candidate(
                    symbol="BTC_USDT_PERP",
                    family="MEAN_REVERSION",
                    as_of_ms=3_000,
                    sizing_equity_usd=100.43,
                ),
            ),
        )

        self.assertEqual(report["state"], "PORTFOLIO_REVIEW_REQUIRED")
        self.assertEqual(len(report["existing_exposures"]), 1)
        self.assertEqual(report["existing_exposures"][0]["symbol"], "BTC_USDT_PERP")

    def test_candidate_timestamp_cannot_precede_account_snapshot(self) -> None:
        with self.assertRaises(ValueError):
            prepare_paper_cycle(
                account_input=open_account_input(),
                candidate_inputs=(
                    candidate(
                        symbol="ETH_USDT_PERP",
                        family="MEAN_REVERSION",
                        as_of_ms=2_999,
                    ),
                ),
            )

    def test_candidate_sizing_equity_must_match_account_equity(self) -> None:
        with self.assertRaises(ValueError):
            prepare_paper_cycle(
                account_input=empty_account(),
                candidate_inputs=(
                    candidate(
                        symbol="BTC_USDT_PERP",
                        family="TREND_FOLLOWING",
                        sizing_equity_usd=200.0,
                    ),
                ),
            )

    def test_candidate_limit_and_partial_readiness_policy_fail_closed(self) -> None:
        six = tuple(
            candidate(
                symbol=f"ASSET_{index}",
                family="TREND_FOLLOWING",
                as_of_ms=1_000 + index,
            )
            for index in range(6)
        )
        with self.assertRaises(ValueError):
            prepare_paper_cycle(
                account_input=empty_account(),
                candidate_inputs=six,
            )

        with self.assertRaises(ValueError):
            PaperCyclePolicy(require_all_intents_ready=False)

        with self.assertRaises(ValueError):
            PaperCyclePolicy(automatic_broker_submission_authorized=True)

    def test_machine_readable_input_and_config_are_strict(self) -> None:
        payload = {
            "schema": "qookey-paper-cycle-input-v0.1",
            "account_input": empty_account(),
            "candidates": [
                candidate(
                    symbol="BTC_USDT_PERP",
                    family="TREND_FOLLOWING",
                )
            ],
        }
        account_input, candidates = paper_cycle_input_from_dict(
            json.loads(json.dumps(payload))
        )
        self.assertEqual(account_input["schema"], "qookey-paper-account-state-input-v0.1")
        self.assertEqual(len(candidates), 1)

        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            paper_cycle_policy_from_config(config),
            PaperCyclePolicy(),
        )
        self.assertFalse(config["authority"]["automatic_broker_submission_authorized"])

        bad = json.loads(CONFIG.read_text(encoding="utf-8"))
        bad["policy"]["automatic_broker_submission_authorized"] = "false"
        with self.assertRaises(ValueError):
            paper_cycle_policy_from_config(bad)


if __name__ == "__main__":
    unittest.main()
