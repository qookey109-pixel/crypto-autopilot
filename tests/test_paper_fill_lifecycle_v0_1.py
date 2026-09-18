from __future__ import annotations

import json
import unittest
from dataclasses import asdict
from pathlib import Path

from crypto_autopilot.paper.execution_v0_1 import (
    PaperExecutionDecision,
    PaperExecutionIntent,
    PaperExecutionReceipt,
)
from crypto_autopilot.paper.lifecycle_v0_1 import (
    PaperLifecyclePolicy,
    PaperLiquidityBar,
    build_paper_lifecycle_plan,
    lifecycle_evidence,
    lifecycle_input_from_dict,
    lifecycle_policy_from_config,
    simulate_paper_lifecycle,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "paper_fill_lifecycle_v0_1.json"


def accepted_chain(
    *,
    notional_usd: float = 100.0,
    entry_price: float = 100.0,
    stop_price: float = 95.0,
    as_of_ms: int = 1_000,
):
    intent = PaperExecutionIntent(
        intent_id="paper-v0-1-fixture",
        symbol="BTC_USDT_PERP",
        strategy_family="TREND_FOLLOWING",
        family_validation_report_sha256="a" * 64,
        portfolio_proposal_id="portfolio-v0-1-fixture",
        portfolio_admission_report_sha256="b" * 64,
        direction="LONG",
        as_of_ms=as_of_ms,
        entry_price=entry_price,
        stop_price=stop_price,
        notional_usd=notional_usd,
        target_risk_usd=1.0,
        realized_risk_usd=0.5,
        risk_utilization_fraction=0.5,
    )
    decision = PaperExecutionDecision(
        status="READY_FOR_PAPER_BROKER",
        reason="paper_intent_ready",
        intent=intent,
    )
    receipt = PaperExecutionReceipt(
        status="PAPER_ACCEPTED",
        intent_id=intent.intent_id,
        order_id=intent.intent_id,
        symbol=intent.symbol,
        side=intent.direction,
        notional_usd=intent.notional_usd,
        broker_status="ACCEPTED",
        replayed=False,
    )
    return decision, receipt


def bar(
    time_ms: int,
    *,
    open_: float = 100.0,
    high: float = 101.0,
    low: float = 99.0,
    close: float = 100.0,
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


class PaperFillLifecycleV01Tests(unittest.TestCase):
    def test_full_fill_then_target_close_models_slippage_and_fees(self) -> None:
        decision, receipt = accepted_chain()
        plan = build_paper_lifecycle_plan(
            decision=decision,
            receipt=receipt,
            target_price=105.0,
        )

        result = simulate_paper_lifecycle(
            plan=plan,
            bars=(
                bar(2_000, open_=100.0, high=104.0, low=99.0, close=103.0),
                bar(3_000, open_=103.0, high=106.0, low=102.0, close=105.0),
            ),
        )

        self.assertEqual(result.status, "CLOSED")
        self.assertEqual(result.reason, "TARGET")
        self.assertAlmostEqual(result.filled_notional_usd, 100.0)
        self.assertAlmostEqual(result.fill_fraction, 1.0)
        self.assertEqual(len(result.fills), 1)
        self.assertAlmostEqual(result.fills[0].fill_price, 100.02)
        self.assertAlmostEqual(result.exit_price, 104.979)
        self.assertGreater(result.net_pnl_usd or 0.0, 0.0)
        self.assertGreater(result.entry_fees_usd, 0.0)
        self.assertGreater(result.exit_fee_usd, 0.0)

    def test_partial_fills_across_bars_reach_full_notional(self) -> None:
        decision, receipt = accepted_chain()
        plan = build_paper_lifecycle_plan(
            decision=decision,
            receipt=receipt,
            target_price=110.0,
        )

        result = simulate_paper_lifecycle(
            plan=plan,
            bars=(
                bar(2_000, available=1_000.0),
                bar(3_000, open_=101.0, high=102.0, low=100.0, close=101.0, available=400.0),
                bar(4_000, open_=102.0, high=103.0, low=101.0, close=102.0, available=600.0),
                bar(5_000, open_=103.0, high=111.0, low=102.0, close=110.0, available=0.0),
            ),
        )

        self.assertEqual(result.status, "CLOSED")
        self.assertEqual(result.reason, "TARGET")
        self.assertEqual([fill.notional_usd for fill in result.fills], [50.0, 20.0, 30.0])
        self.assertAlmostEqual(result.filled_notional_usd, 100.0)
        self.assertAlmostEqual(result.fill_fraction, 1.0)

    def test_stop_invalidated_before_first_fill_cancels_without_entry(self) -> None:
        decision, receipt = accepted_chain(stop_price=95.0)
        plan = build_paper_lifecycle_plan(
            decision=decision,
            receipt=receipt,
            target_price=105.0,
        )

        result = simulate_paper_lifecycle(
            plan=plan,
            bars=(
                bar(2_000, open_=94.0, high=96.0, low=93.0, close=95.0),
            ),
        )

        self.assertEqual(result.status, "CANCELLED_UNFILLED")
        self.assertEqual(result.reason, "stop_invalidated_before_first_fill")
        self.assertEqual(result.fills, ())
        self.assertEqual(result.filled_notional_usd, 0.0)

    def test_target_crossed_before_first_fill_does_not_chase(self) -> None:
        decision, receipt = accepted_chain()
        plan = build_paper_lifecycle_plan(
            decision=decision,
            receipt=receipt,
            target_price=105.0,
        )

        result = simulate_paper_lifecycle(
            plan=plan,
            bars=(
                bar(2_000, open_=106.0, high=108.0, low=105.0, close=107.0),
            ),
        )

        self.assertEqual(result.status, "CANCELLED_UNFILLED")
        self.assertEqual(result.reason, "target_crossed_before_first_fill")

    def test_adverse_entry_slippage_does_not_chase_through_target(self) -> None:
        decision, receipt = accepted_chain()
        plan = build_paper_lifecycle_plan(
            decision=decision,
            receipt=receipt,
            target_price=100.01,
        )

        result = simulate_paper_lifecycle(
            plan=plan,
            bars=(
                bar(
                    2_000,
                    open_=100.0,
                    high=100.005,
                    low=99.9,
                    close=100.0,
                    available=4_000.0,
                ),
            ),
        )

        self.assertEqual(result.status, "CANCELLED_UNFILLED")
        self.assertEqual(result.reason, "target_not_above_executable_entry")
        self.assertEqual(result.fills, ())

    def test_partial_position_cancels_remainder_when_additional_fill_would_cross_target(self) -> None:
        decision, receipt = accepted_chain()
        plan = build_paper_lifecycle_plan(
            decision=decision,
            receipt=receipt,
            target_price=101.0,
        )

        result = simulate_paper_lifecycle(
            plan=plan,
            bars=(
                bar(
                    2_000,
                    open_=100.0,
                    high=100.5,
                    low=99.0,
                    close=100.2,
                    available=1_000.0,
                ),
                bar(
                    3_000,
                    open_=100.99,
                    high=100.995,
                    low=100.5,
                    close=100.8,
                    available=5_000.0,
                ),
                bar(
                    4_000,
                    open_=100.8,
                    high=100.9,
                    low=100.4,
                    close=100.7,
                    available=5_000.0,
                ),
            ),
        )

        self.assertEqual(result.status, "OPEN_POSITION")
        self.assertAlmostEqual(result.filled_notional_usd, 50.0)
        self.assertAlmostEqual(result.unfilled_notional_usd, 50.0)
        self.assertTrue(
            any(
                event.kind == "UNFILLED_REMAINDER_CANCELLED"
                and ("reason", "target_not_above_executable_entry") in event.details
                for event in result.events
            )
        )

    def test_same_bar_stop_target_collision_is_stop_first(self) -> None:
        decision, receipt = accepted_chain()
        plan = build_paper_lifecycle_plan(
            decision=decision,
            receipt=receipt,
            target_price=105.0,
        )

        result = simulate_paper_lifecycle(
            plan=plan,
            bars=(
                bar(2_000, open_=100.0, high=106.0, low=94.0, close=101.0),
            ),
        )

        self.assertEqual(result.status, "CLOSED")
        self.assertEqual(result.reason, "STOP_SAME_BAR_COLLISION")
        self.assertLess(result.net_pnl_usd or 0.0, 0.0)

    def test_partial_position_gap_stop_cancels_unfilled_remainder(self) -> None:
        decision, receipt = accepted_chain()
        plan = build_paper_lifecycle_plan(
            decision=decision,
            receipt=receipt,
            target_price=110.0,
        )

        result = simulate_paper_lifecycle(
            plan=plan,
            bars=(
                bar(2_000, available=1_000.0),
                bar(3_000, open_=94.0, high=96.0, low=93.0, close=95.0, available=5_000.0),
            ),
        )

        self.assertEqual(result.status, "CLOSED")
        self.assertEqual(result.reason, "STOP_GAP")
        self.assertAlmostEqual(result.filled_notional_usd, 50.0)
        self.assertAlmostEqual(result.unfilled_notional_usd, 50.0)
        self.assertAlmostEqual(result.fill_fraction, 0.5)
        self.assertTrue(
            any(event.kind == "UNFILLED_REMAINDER_CANCELLED" for event in result.events)
        )

    def test_entry_window_can_leave_partial_open_position(self) -> None:
        decision, receipt = accepted_chain()
        plan = build_paper_lifecycle_plan(
            decision=decision,
            receipt=receipt,
            target_price=110.0,
        )

        result = simulate_paper_lifecycle(
            plan=plan,
            bars=(
                bar(2_000, available=200.0),
                bar(3_000, available=200.0),
                bar(4_000, available=200.0),
                bar(5_000, available=0.0),
            ),
        )

        self.assertEqual(result.status, "OPEN_POSITION")
        self.assertEqual(result.reason, "no_exit_before_end_of_data")
        self.assertAlmostEqual(result.filled_notional_usd, 30.0)
        self.assertAlmostEqual(result.unfilled_notional_usd, 70.0)
        self.assertAlmostEqual(result.fill_fraction, 0.3)
        self.assertTrue(
            any(event.kind == "POSITION_OPEN_PARTIAL" for event in result.events)
        )

    def test_no_future_bar_cancels_unfilled(self) -> None:
        decision, receipt = accepted_chain(as_of_ms=5_000)
        plan = build_paper_lifecycle_plan(
            decision=decision,
            receipt=receipt,
            target_price=105.0,
        )

        result = simulate_paper_lifecycle(
            plan=plan,
            bars=(bar(4_000),),
        )

        self.assertEqual(result.status, "CANCELLED_UNFILLED")
        self.assertEqual(result.reason, "no_future_market_bar")

    def test_close_at_end_of_data_is_explicit_policy_only(self) -> None:
        decision, receipt = accepted_chain()
        plan = build_paper_lifecycle_plan(
            decision=decision,
            receipt=receipt,
            target_price=110.0,
        )

        result = simulate_paper_lifecycle(
            plan=plan,
            bars=(bar(2_000, close=102.0),),
            policy=PaperLifecyclePolicy(close_at_end_of_data=True),
        )

        self.assertEqual(result.status, "CLOSED")
        self.assertEqual(result.reason, "END_OF_DATA")

    def test_lifecycle_plan_binds_exact_accepted_intent_and_target(self) -> None:
        decision, receipt = accepted_chain()
        first = build_paper_lifecycle_plan(
            decision=decision,
            receipt=receipt,
            target_price=105.0,
        )
        second = build_paper_lifecycle_plan(
            decision=decision,
            receipt=receipt,
            target_price=106.0,
        )

        self.assertNotEqual(first.lifecycle_id, second.lifecycle_id)

        bad_receipt = PaperExecutionReceipt(
            status=receipt.status,
            intent_id="different",
            order_id="different",
            symbol=receipt.symbol,
            side=receipt.side,
            notional_usd=receipt.notional_usd,
            broker_status=receipt.broker_status,
            replayed=False,
        )
        with self.assertRaises(ValueError):
            build_paper_lifecycle_plan(
                decision=decision,
                receipt=bad_receipt,
                target_price=105.0,
            )

    def test_bars_must_be_strictly_increasing(self) -> None:
        decision, receipt = accepted_chain()
        plan = build_paper_lifecycle_plan(
            decision=decision,
            receipt=receipt,
            target_price=105.0,
        )

        with self.assertRaises(ValueError):
            simulate_paper_lifecycle(
                plan=plan,
                bars=(bar(3_000), bar(2_000)),
            )

    def test_evidence_preserves_zero_live_authority(self) -> None:
        decision, receipt = accepted_chain()
        policy = PaperLifecyclePolicy()
        plan = build_paper_lifecycle_plan(
            decision=decision,
            receipt=receipt,
            target_price=105.0,
        )
        result = simulate_paper_lifecycle(
            plan=plan,
            bars=(bar(2_000),),
            policy=policy,
        )

        evidence = lifecycle_evidence(plan=plan, result=result, policy=policy)

        self.assertTrue(evidence["authority"]["paper_simulation_only"])
        self.assertFalse(evidence["authority"]["automatic_submission_authorized"])
        self.assertFalse(evidence["authority"]["real_money_order_authorized"])
        self.assertFalse(evidence["authority"]["live_trading_authorized"])

    def test_machine_readable_input_rebuilds_accepted_chain(self) -> None:
        decision, receipt = accepted_chain()
        execution_evidence = {
            "schema": "qookey-paper-execution-evidence-v0.1",
            "decision": {
                "status": decision.status,
                "reason": decision.reason,
                "intent": asdict(decision.intent),
            },
            "receipt": asdict(receipt),
            "authority": {
                "repository_paper_broker_only": True,
                "provider_requests_performed": False,
                "r2_accessed": False,
                "holdout_accessed": False,
                "automatic_submission_authorized": False,
                "short_paper_execution_authorized": False,
                "formal_trade_plan_authorized": False,
                "real_money_order_authorized": False,
                "live_trading_authorized": False,
            },
            "limitations": [],
        }
        payload = {
            "schema": "qookey-paper-fill-lifecycle-input-v0.1",
            "paper_execution_evidence": execution_evidence,
            "target_price": 105.0,
            "bars": [
                {
                    "time_ms": 2000,
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.0,
                    "available_notional_usd": 4000.0,
                }
            ],
        }

        rebuilt_decision, rebuilt_receipt, target, bars = lifecycle_input_from_dict(
            json.loads(json.dumps(payload))
        )

        self.assertEqual(rebuilt_decision, decision)
        self.assertEqual(rebuilt_receipt, receipt)
        self.assertEqual(target, 105.0)
        self.assertEqual(len(bars), 1)

        bad = json.loads(json.dumps(payload))
        bad["bars"][0]["available_notional_usd"] = True
        with self.assertRaises(ValueError):
            lifecycle_input_from_dict(bad)

        bad_replayed = json.loads(json.dumps(payload))
        bad_replayed["paper_execution_evidence"]["receipt"]["replayed"] = "false"
        with self.assertRaises(ValueError):
            lifecycle_input_from_dict(bad_replayed)

        bad_authority = json.loads(json.dumps(payload))
        bad_authority["paper_execution_evidence"]["authority"][
            "provider_requests_performed"
        ] = True
        with self.assertRaises(ValueError):
            lifecycle_input_from_dict(bad_authority)

    def test_versioned_policy_matches_defaults_and_boolean_types_are_strict(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))

        self.assertEqual(lifecycle_policy_from_config(payload), PaperLifecyclePolicy())
        self.assertFalse(payload["lifecycle_behavior"]["funding_modeled"])
        self.assertFalse(payload["authority"]["live_trading_authorized"])

        bad = json.loads(CONFIG.read_text(encoding="utf-8"))
        bad["policy"]["close_at_end_of_data"] = "false"
        with self.assertRaises(ValueError):
            lifecycle_policy_from_config(bad)


if __name__ == "__main__":
    unittest.main()
