from __future__ import annotations

import copy
import json
import unittest
from dataclasses import asdict
from pathlib import Path

from crypto_autopilot.exchanges.paper import PaperBroker
from crypto_autopilot.paper.cycle_v0_1 import (
    paper_cycle_report_id_from_mapping,
    prepare_paper_cycle,
)
from crypto_autopilot.paper.session_v0_1 import (
    PaperSubmissionSessionPolicy,
    paper_submission_session_policy_from_config,
    submit_paper_cycle_session,
)
from crypto_autopilot.risk import plan_position_size


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "paper_submission_session_v0_1.json"


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


def account_input() -> dict[str, object]:
    return {
        "schema": "qookey-paper-account-state-input-v0.1",
        "initial_equity_usd": 100.0,
        "records": [],
        "marks": [],
    }


def candidate(
    symbol: str,
    family: str,
    *,
    as_of_ms: int = 1_000,
) -> dict[str, object]:
    sizing = plan_position_size(
        direction="LONG",
        equity_usd=100.0,
        entry_price=100.0,
        stop_price=99.0,
    )
    return {
        "symbol": symbol,
        "strategy_family": family,
        "as_of_ms": as_of_ms,
        "family_validation_report": family_report(family),
        "position_sizing_plan": asdict(sizing),
    }


def ready_cycle(two: bool = False) -> dict[str, object]:
    candidates = [
        candidate("BTC_USDT_PERP", "TREND_FOLLOWING"),
    ]
    if two:
        candidates.append(
            candidate(
                "ETH_USDT_PERP",
                "MEAN_REVERSION",
                as_of_ms=1_001,
            )
        )
    report = prepare_paper_cycle(
        account_input=account_input(),
        candidate_inputs=tuple(candidates),
    )
    assert report["state"] == "PAPER_INTENTS_READY_FOR_EXPLICIT_SUBMISSION"
    return report


class PaperSubmissionSessionV01Tests(unittest.TestCase):
    def test_single_ready_cycle_submits_explicitly_and_emits_execution_evidence(self) -> None:
        cycle = ready_cycle()
        broker = PaperBroker()

        report = submit_paper_cycle_session(
            cycle_report=cycle,
            confirmation_cycle_id=cycle["cycle_id"],
            broker=broker,
        )

        self.assertEqual(report["state"], "PAPER_SESSION_ACCEPTED")
        self.assertEqual(report["intent_count"], 1)
        self.assertEqual(report["new_submission_count"], 1)
        self.assertEqual(report["replayed_submission_count"], 0)
        self.assertEqual(report["broker_order_count_after"], 1)
        self.assertEqual(len(broker.orders), 1)
        evidence = report["paper_execution_evidence"][0]["paper_execution_evidence"]
        self.assertEqual(evidence["receipt"]["status"], "PAPER_ACCEPTED")
        self.assertFalse(evidence["authority"]["automatic_submission_authorized"])
        self.assertFalse(report["authority"]["live_trading_authorized"])

    def test_replay_is_idempotent_and_keeps_same_session_id(self) -> None:
        cycle = ready_cycle()
        broker = PaperBroker()

        first = submit_paper_cycle_session(
            cycle_report=cycle,
            confirmation_cycle_id=cycle["cycle_id"],
            broker=broker,
        )
        second = submit_paper_cycle_session(
            cycle_report=cycle,
            confirmation_cycle_id=cycle["cycle_id"],
            broker=broker,
        )

        self.assertEqual(first["session_id"], second["session_id"])
        self.assertEqual(second["new_submission_count"], 0)
        self.assertEqual(second["replayed_submission_count"], 1)
        self.assertEqual(len(broker.orders), 1)
        self.assertTrue(second["receipts"][0]["receipt"]["replayed"])

    def test_two_intent_session_preflights_complete_basket(self) -> None:
        cycle = ready_cycle(two=True)
        broker = PaperBroker()

        report = submit_paper_cycle_session(
            cycle_report=cycle,
            confirmation_cycle_id=cycle["cycle_id"],
            broker=broker,
        )

        self.assertEqual(report["intent_count"], 2)
        self.assertEqual(report["new_submission_count"], 2)
        self.assertEqual(len(broker.orders), 2)
        proposal_ids = [row["proposal_id"] for row in report["receipts"]]
        self.assertEqual(proposal_ids, sorted(proposal_ids))

    def test_partial_matching_replay_submits_only_missing_intent(self) -> None:
        cycle = ready_cycle(two=True)
        first_decision = cycle["paper_execution_decisions"][0]["decision"]
        first_intent = first_decision["intent"]
        broker = PaperBroker()
        broker.submit_long(
            order_id=first_intent["intent_id"],
            symbol=first_intent["symbol"],
            notional_usd=first_intent["notional_usd"],
        )

        report = submit_paper_cycle_session(
            cycle_report=cycle,
            confirmation_cycle_id=cycle["cycle_id"],
            broker=broker,
        )

        self.assertEqual(report["new_submission_count"], 1)
        self.assertEqual(report["replayed_submission_count"], 1)
        self.assertEqual(len(broker.orders), 2)

    def test_exact_cycle_id_confirmation_is_required_before_mutation(self) -> None:
        cycle = ready_cycle()
        broker = PaperBroker()

        with self.assertRaises(ValueError):
            submit_paper_cycle_session(
                cycle_report=cycle,
                confirmation_cycle_id="wrong-cycle-id",
                broker=broker,
            )

        self.assertEqual(broker.orders, [])

    def test_tampered_cycle_contents_fail_recomputed_id_before_mutation(self) -> None:
        cycle = ready_cycle()
        tampered = copy.deepcopy(cycle)
        tampered["prepared_intents"][0]["symbol"] = "ETH_USDT_PERP"
        broker = PaperBroker()

        with self.assertRaises(ValueError):
            submit_paper_cycle_session(
                cycle_report=tampered,
                confirmation_cycle_id=cycle["cycle_id"],
                broker=broker,
            )

        self.assertEqual(broker.orders, [])

    def test_prepared_intent_mismatch_fails_closed(self) -> None:
        cycle = ready_cycle()
        tampered = copy.deepcopy(cycle)
        tampered["prepared_intents"][0]["notional_usd"] = 99.0
        tampered["cycle_id"] = paper_cycle_report_id_from_mapping(tampered)
        broker = PaperBroker()

        with self.assertRaises(ValueError):
            submit_paper_cycle_session(
                cycle_report=tampered,
                confirmation_cycle_id=tampered["cycle_id"],
                broker=broker,
            )

        self.assertEqual(broker.orders, [])

    def test_existing_broker_payload_collision_fails_preflight(self) -> None:
        cycle = ready_cycle()
        intent = cycle["paper_execution_decisions"][0]["decision"]["intent"]
        broker = PaperBroker()
        broker.submit_long(
            order_id=intent["intent_id"],
            symbol=intent["symbol"],
            notional_usd=intent["notional_usd"] + 1.0,
        )

        with self.assertRaises(ValueError):
            submit_paper_cycle_session(
                cycle_report=cycle,
                confirmation_cycle_id=cycle["cycle_id"],
                broker=broker,
            )

        self.assertEqual(len(broker.orders), 1)
        self.assertEqual(broker.orders[0].notional_usd, intent["notional_usd"] + 1.0)

    def test_cycle_not_ready_for_submission_is_rejected(self) -> None:
        cycle = ready_cycle()
        cycle["state"] = "CYCLE_REVIEW_REQUIRED"
        cycle["explicit_submission_allowed"] = False
        cycle["cycle_id"] = paper_cycle_report_id_from_mapping(cycle)

        with self.assertRaises(ValueError):
            submit_paper_cycle_session(
                cycle_report=cycle,
                confirmation_cycle_id=cycle["cycle_id"],
                broker=PaperBroker(),
            )

    def test_policy_cannot_enable_automatic_scheduled_live_or_persistent_paths(self) -> None:
        with self.assertRaises(ValueError):
            PaperSubmissionSessionPolicy(automatic_submission_authorized=True)
        with self.assertRaises(ValueError):
            PaperSubmissionSessionPolicy(scheduled_submission_authorized=True)
        with self.assertRaises(ValueError):
            PaperSubmissionSessionPolicy(persistent_broker_state_authorized=True)
        with self.assertRaises(ValueError):
            PaperSubmissionSessionPolicy(live_trading_authorized=True)

    def test_versioned_config_matches_defaults_and_types_are_strict(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            paper_submission_session_policy_from_config(payload),
            PaperSubmissionSessionPolicy(),
        )
        self.assertTrue(payload["policy"]["explicit_paper_submission_authorized"])
        self.assertFalse(payload["policy"]["automatic_submission_authorized"])
        self.assertFalse(payload["authority"]["real_money_order_authorized"])

        bad = json.loads(CONFIG.read_text(encoding="utf-8"))
        bad["policy"]["maximum_intents"] = True
        with self.assertRaises(ValueError):
            paper_submission_session_policy_from_config(bad)


if __name__ == "__main__":
    unittest.main()
