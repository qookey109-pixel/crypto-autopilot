from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from crypto_autopilot.exchanges.paper import PaperBroker
from crypto_autopilot.paper.account_v0_1 import (
    PaperAccountPolicy,
    PaperMark,
    materialize_paper_account,
    paper_account_input_from_dict,
    paper_account_policy_from_config,
    paper_account_evidence,
    portfolio_exposures_from_account,
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
CONFIG = ROOT / "config" / "paper_account_state_v0_1.json"


def family_report(family: str = "TREND_FOLLOWING") -> dict[str, object]:
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


def lifecycle_record(
    *,
    symbol: str = "BTC_USDT_PERP",
    family: str = "TREND_FOLLOWING",
    as_of_ms: int = 1_000,
    target_price: float = 105.0,
    bars: tuple[PaperLiquidityBar, ...],
) -> dict[str, object]:
    report = family_report(family)
    sizing = plan_position_size(
        direction="LONG",
        equity_usd=100.0,
        entry_price=100.0,
        stop_price=99.0,
    )
    proposal = build_portfolio_proposal(
        symbol=symbol,
        strategy_family=family,
        family_validation_report=report,
        as_of_ms=as_of_ms,
        sizing_plan=sizing,
    )
    portfolio = admit_portfolio(equity_usd=100.0, proposals=(proposal,))
    decision = prepare_paper_execution(
        symbol=symbol,
        strategy_family=family,
        family_validation_report=report,
        portfolio_admission_report=portfolio,
        as_of_ms=as_of_ms,
        sizing_plan=sizing,
    )
    receipt = submit_paper_execution(decision, PaperBroker())
    execution = paper_execution_evidence(decision, receipt)

    plan = build_paper_lifecycle_plan(
        decision=decision,
        receipt=receipt,
        target_price=target_price,
    )
    result = simulate_paper_lifecycle(plan=plan, bars=bars)
    lifecycle = lifecycle_evidence(
        plan=plan,
        result=result,
        policy=PaperLifecyclePolicy(),
    )
    return {
        "paper_execution_evidence": execution,
        "paper_lifecycle_report": lifecycle,
    }


def bar(
    time_ms: int,
    *,
    open_: float = 100.0,
    high: float = 101.0,
    low: float = 99.5,
    close: float = 100.5,
    available: float = 4_000.0,
) -> PaperLiquidityBar:
    return PaperLiquidityBar(
        time_ms=time_ms,
        open=open_,
        high=high,
        low=low,
        close=close,
        available_notional_usd=available,
    )


class PaperAccountStateV01Tests(unittest.TestCase):
    def test_empty_account_is_active_and_deterministic(self) -> None:
        first = materialize_paper_account(initial_equity_usd=100.0, records=())
        second = materialize_paper_account(initial_equity_usd=100.0, records=())

        self.assertEqual(first, second)
        self.assertEqual(first.status, "ACCOUNT_ACTIVE")
        self.assertEqual(first.cash_usd, 100.0)
        self.assertEqual(first.equity_usd, 100.0)
        self.assertEqual(first.open_position_count, 0)

    def test_open_position_updates_cash_and_mark_to_market_equity(self) -> None:
        record = lifecycle_record(bars=(bar(2_000),))
        snapshot = materialize_paper_account(
            initial_equity_usd=100.0,
            records=(record,),
            marks=(PaperMark("BTC_USDT_PERP", 3_000, 100.5),),
        )

        self.assertEqual(snapshot.status, "ACCOUNT_ACTIVE")
        self.assertEqual(snapshot.open_position_count, 1)
        self.assertEqual(snapshot.closed_position_count, 0)
        position = snapshot.open_positions[0]
        self.assertEqual(position.symbol, "BTC_USDT_PERP")
        self.assertEqual(position.strategy_family, "TREND_FOLLOWING")
        self.assertGreater(position.unrealized_gross_pnl_usd, 0.0)
        self.assertGreater(position.portfolio_stop_risk_usd, 0.0)
        self.assertLess(snapshot.cash_usd, 100.0)
        self.assertGreater(snapshot.equity_usd, snapshot.cash_usd)

    def test_closed_and_cancelled_lifecycles_rebuild_realized_state(self) -> None:
        closed = lifecycle_record(
            symbol="BTC_USDT_PERP",
            bars=(
                bar(2_000),
                bar(
                    3_000,
                    open_=101.0,
                    high=106.0,
                    low=100.0,
                    close=105.0,
                ),
            ),
        )
        cancelled = lifecycle_record(
            symbol="ETH_USDT_PERP",
            as_of_ms=4_000,
            bars=(
                bar(
                    5_000,
                    open_=98.0,
                    high=98.5,
                    low=97.0,
                    close=98.0,
                ),
            ),
        )

        snapshot = materialize_paper_account(
            initial_equity_usd=100.0,
            records=(closed, cancelled),
        )

        self.assertEqual(snapshot.open_position_count, 0)
        self.assertEqual(snapshot.closed_position_count, 1)
        self.assertEqual(snapshot.cancelled_order_count, 1)
        self.assertEqual(snapshot.cash_usd, snapshot.equity_usd)
        self.assertNotEqual(snapshot.realized_closed_net_pnl_usd, 0.0)

    def test_marks_must_be_fresh_exact_and_inside_protective_boundaries(self) -> None:
        record = lifecycle_record(bars=(bar(2_000),))

        with self.assertRaises(ValueError):
            materialize_paper_account(
                initial_equity_usd=100.0,
                records=(record,),
                marks=(),
            )

        with self.assertRaises(ValueError):
            materialize_paper_account(
                initial_equity_usd=100.0,
                records=(record,),
                marks=(PaperMark("BTC_USDT_PERP", 1_500, 100.5),),
            )

        with self.assertRaises(ValueError):
            materialize_paper_account(
                initial_equity_usd=100.0,
                records=(record,),
                marks=(PaperMark("BTC_USDT_PERP", 3_000, 99.0),),
            )

        with self.assertRaises(ValueError):
            materialize_paper_account(
                initial_equity_usd=100.0,
                records=(record,),
                marks=(
                    PaperMark("BTC_USDT_PERP", 3_000, 100.5),
                    PaperMark("ETH_USDT_PERP", 3_000, 100.0),
                ),
            )

    def test_multiple_open_symbols_require_one_coherent_mark_timestamp(self) -> None:
        btc = lifecycle_record(symbol="BTC_USDT_PERP", bars=(bar(2_000),))
        eth = lifecycle_record(
            symbol="ETH_USDT_PERP",
            as_of_ms=1_100,
            bars=(bar(2_100),),
        )

        with self.assertRaises(ValueError):
            materialize_paper_account(
                initial_equity_usd=100.0,
                records=(btc, eth),
                marks=(
                    PaperMark("BTC_USDT_PERP", 3_000, 100.5),
                    PaperMark("ETH_USDT_PERP", 3_100, 100.5),
                ),
            )

        snapshot = materialize_paper_account(
            initial_equity_usd=100.0,
            records=(btc, eth),
            marks=(
                PaperMark("BTC_USDT_PERP", 3_200, 100.5),
                PaperMark("ETH_USDT_PERP", 3_200, 100.5),
            ),
        )
        self.assertEqual(snapshot.open_position_count, 2)
        self.assertEqual(snapshot.as_of_ms, 3_200)

    def test_duplicate_lifecycle_or_intent_fails_closed(self) -> None:
        record = lifecycle_record(bars=(bar(2_000),))

        with self.assertRaises(ValueError):
            materialize_paper_account(
                initial_equity_usd=100.0,
                records=(record, record),
                marks=(PaperMark("BTC_USDT_PERP", 3_000, 100.5),),
            )

    def test_tampered_paper_receipt_notional_is_rejected(self) -> None:
        record = lifecycle_record(bars=(bar(2_000),))
        tampered = copy.deepcopy(record)
        tampered["paper_execution_evidence"]["receipt"]["notional_usd"] = 99.0

        with self.assertRaises(ValueError):
            materialize_paper_account(
                initial_equity_usd=100.0,
                records=(tampered,),
                marks=(PaperMark("BTC_USDT_PERP", 3_000, 100.5),),
            )

    def test_tampered_lifecycle_accounting_is_rejected(self) -> None:
        record = lifecycle_record(bars=(bar(2_000),))
        tampered = copy.deepcopy(record)
        tampered["paper_lifecycle_report"]["result"]["filled_notional_usd"] = 90.0

        with self.assertRaises(ValueError):
            materialize_paper_account(
                initial_equity_usd=100.0,
                records=(tampered,),
                marks=(PaperMark("BTC_USDT_PERP", 3_000, 100.5),),
            )

    def test_open_account_exposure_feeds_portfolio_admission(self) -> None:
        record = lifecycle_record(bars=(bar(2_000),))
        snapshot = materialize_paper_account(
            initial_equity_usd=100.0,
            records=(record,),
            marks=(PaperMark("BTC_USDT_PERP", 3_000, 100.5),),
        )
        existing = portfolio_exposures_from_account(snapshot)

        report = family_report("MEAN_REVERSION")
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=snapshot.equity_usd,
            entry_price=100.0,
            stop_price=99.0,
        )
        proposal = build_portfolio_proposal(
            symbol="BTC_USDT_PERP",
            strategy_family="MEAN_REVERSION",
            family_validation_report=report,
            as_of_ms=3_000,
            sizing_plan=sizing,
        )
        admission = admit_portfolio(
            equity_usd=snapshot.equity_usd,
            proposals=(proposal,),
            existing_exposures=existing,
        )

        self.assertEqual(len(existing), 1)
        self.assertEqual(existing[0].symbol, "BTC_USDT_PERP")
        self.assertEqual(admission["state"], "PORTFOLIO_REVIEW_REQUIRED")
        self.assertTrue(
            any(
                reason.startswith("symbol_realized_risk_above_cap:BTC_USDT_PERP")
                for reason in admission["reasons"]
            )
        )

    def test_insolvent_account_cannot_export_new_portfolio_capacity(self) -> None:
        catastrophic = lifecycle_record(
            bars=(
                bar(2_000),
                bar(
                    3_000,
                    open_=1.0,
                    high=1.1,
                    low=0.9,
                    close=1.0,
                ),
            ),
        )
        snapshot = materialize_paper_account(
            initial_equity_usd=50.0,
            records=(catastrophic,),
        )

        self.assertEqual(snapshot.status, "ACCOUNT_INSOLVENT")
        with self.assertRaises(ValueError):
            portfolio_exposures_from_account(snapshot)

    def test_machine_readable_input_and_evidence_remain_offline(self) -> None:
        record = lifecycle_record(bars=(bar(2_000),))
        payload = {
            "schema": "qookey-paper-account-state-input-v0.1",
            "initial_equity_usd": 100.0,
            "records": [record],
            "marks": [
                {
                    "symbol": "BTC_USDT_PERP",
                    "time_ms": 3000,
                    "price": 100.5,
                }
            ],
        }

        initial, records, marks = paper_account_input_from_dict(
            json.loads(json.dumps(payload))
        )
        snapshot = materialize_paper_account(
            initial_equity_usd=initial,
            records=records,
            marks=marks,
        )
        evidence = paper_account_evidence(snapshot, PaperAccountPolicy())

        self.assertFalse(evidence["authority"]["persistent_state_written"])
        self.assertFalse(evidence["authority"]["real_money_order_authorized"])
        self.assertFalse(evidence["authority"]["live_trading_authorized"])

        bad = json.loads(json.dumps(payload))
        bad["marks"][0]["price"] = True
        with self.assertRaises(ValueError):
            paper_account_input_from_dict(bad)

        bad_string = json.loads(json.dumps(payload))
        bad_string["marks"][0]["price"] = "100.5"
        with self.assertRaises(ValueError):
            paper_account_input_from_dict(bad_string)

    def test_versioned_policy_matches_defaults_and_strict_types(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            paper_account_policy_from_config(payload),
            PaperAccountPolicy(),
        )
        self.assertFalse(payload["accounting"]["derivatives_notional_debits_cash"])
        self.assertFalse(payload["authority"]["persistent_state_write_authorized"])

        bad = json.loads(CONFIG.read_text(encoding="utf-8"))
        bad["policy"]["require_single_mark_timestamp"] = "true"
        with self.assertRaises(ValueError):
            paper_account_policy_from_config(bad)


if __name__ == "__main__":
    unittest.main()
