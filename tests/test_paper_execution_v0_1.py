from __future__ import annotations

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


class PaperExecutionV01Tests(unittest.TestCase):
    def test_ready_long_intent_uses_approved_risk_notional_exactly(self) -> None:
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.8,
        )

        decision = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=family_report(),
            as_of_ms=1_000,
            sizing_plan=sizing,
        )

        self.assertEqual(decision.status, "READY_FOR_PAPER_BROKER")
        self.assertIsNotNone(decision.intent)
        assert decision.intent is not None
        self.assertEqual(decision.intent.notional_usd, sizing.approved_notional_usd)
        self.assertEqual(decision.intent.stop_price, sizing.stop_price)
        self.assertEqual(decision.intent.realized_risk_usd, sizing.realized_risk_usd)
        self.assertEqual(decision.intent.notional_usd, 300.0)

    def test_submission_reuses_existing_repository_paper_broker_idempotency(self) -> None:
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
        )
        decision = prepare_paper_execution(
            symbol="ETH_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=family_report(),
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

    def test_family_review_not_ready_blocks_paper_intent(self) -> None:
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
        )

        decision = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=family_report(
                state="INSUFFICIENT_GENERALIZATION_COVERAGE"
            ),
            as_of_ms=1_000,
            sizing_plan=sizing,
        )

        self.assertEqual(decision.status, "NO_EXECUTION")
        self.assertEqual(decision.reason, "family_review_not_ready")

    def test_family_validation_lineage_is_bound_into_intent_id(self) -> None:
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
        )

        first = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=family_report(coverage_tag="a"),
            as_of_ms=1_000,
            sizing_plan=sizing,
        )
        second = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=family_report(coverage_tag="b"),
            as_of_ms=1_000,
            sizing_plan=sizing,
        )

        assert first.intent is not None
        assert second.intent is not None
        self.assertNotEqual(first.intent.intent_id, second.intent.intent_id)
        self.assertNotEqual(
            first.intent.family_validation_report_sha256,
            second.intent.family_validation_report_sha256,
        )

    def test_family_mismatch_or_unregistered_family_fails_closed(self) -> None:
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
        )

        mismatch = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="MOMENTUM",
            family_validation_report=family_report(family="TREND_FOLLOWING"),
            as_of_ms=1_000,
            sizing_plan=sizing,
        )
        unknown = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="UNKNOWN",
            family_validation_report=family_report(family="UNKNOWN"),
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

        decision = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=family_report(),
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

        decision = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=family_report(),
            as_of_ms=1_000,
            sizing_plan=sizing,
        )

        self.assertEqual(decision.status, "NO_EXECUTION")
        self.assertEqual(decision.reason, "short_paper_execution_not_authorized")

    def test_family_validation_authority_must_remain_closed(self) -> None:
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
        )
        report = family_report()
        authority = dict(report["authority"])
        authority["promotion_authority"] = 1
        report["authority"] = authority

        decision = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=report,
            as_of_ms=1_000,
            sizing_plan=sizing,
        )

        self.assertEqual(decision.status, "NO_EXECUTION")
        self.assertEqual(
            decision.reason, "family_validation_promotion_authority_nonzero"
        )

    def test_evidence_keeps_live_and_automatic_paths_closed(self) -> None:
        sizing = plan_position_size(
            direction="LONG",
            equity_usd=100.0,
            entry_price=100.0,
            stop_price=99.0,
        )
        decision = prepare_paper_execution(
            symbol="BTC_USDT_PERP",
            strategy_family="TREND_FOLLOWING",
            family_validation_report=family_report(),
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
        self.assertTrue(
            payload["authority"]["repository_paper_broker_long_authorized"]
        )
        self.assertFalse(payload["authority"]["automatic_submission_authorized"])
        self.assertFalse(payload["authority"]["live_trading_authorized"])

    def test_config_policy_booleans_are_strict(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        payload["authority"]["live_trading_authorized"] = "false"

        with self.assertRaises(ValueError):
            paper_execution_policy_from_config(payload)


if __name__ == "__main__":
    unittest.main()
