from __future__ import annotations

import copy
import json
import unittest
from dataclasses import asdict
from pathlib import Path

from crypto_autopilot.exchanges.paper import PaperBroker
from crypto_autopilot.paper.account_v0_1 import materialize_paper_account
from crypto_autopilot.paper.cycle_v0_1 import prepare_paper_cycle
from crypto_autopilot.paper.lifecycle_batch_v0_1 import (
    PaperLifecycleBatchPolicy,
    paper_lifecycle_batch_input_from_dict,
    paper_lifecycle_batch_policy_from_config,
    simulate_paper_lifecycle_batch,
)
from crypto_autopilot.paper.session_v0_1 import submit_paper_cycle_session
from crypto_autopilot.risk import plan_position_size


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "paper_lifecycle_batch_v0_1.json"


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
    as_of_ms: int,
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


def ready_session(*, two: bool = False) -> dict[str, object]:
    candidates = [
        candidate(
            "BTC_USDT_PERP",
            "TREND_FOLLOWING",
            as_of_ms=1_000,
        )
    ]
    if two:
        candidates.append(
            candidate(
                "ETH_USDT_PERP",
                "MEAN_REVERSION",
                as_of_ms=1_001,
            )
        )
    cycle = prepare_paper_cycle(
        account_input=account_input(),
        candidate_inputs=tuple(candidates),
    )
    return submit_paper_cycle_session(
        cycle_report=cycle,
        confirmation_cycle_id=cycle["cycle_id"],
        broker=PaperBroker(),
    )


def lifecycle_input(
    proposal_id: str,
    *,
    target_price: float = 105.0,
    bars: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    if bars is None:
        bars = [
            {
                "time_ms": 2_000,
                "open": 100.0,
                "high": 101.0,
                "low": 99.5,
                "close": 100.5,
                "available_notional_usd": 4_000.0,
            },
            {
                "time_ms": 3_000,
                "open": 101.0,
                "high": 106.0,
                "low": 100.5,
                "close": 105.0,
                "available_notional_usd": 4_000.0,
            },
        ]
    return {
        "proposal_id": proposal_id,
        "target_price": target_price,
        "bars": bars,
    }


class PaperLifecycleBatchV01Tests(unittest.TestCase):
    def test_single_session_batch_closes_and_emits_account_record(self) -> None:
        session = ready_session()
        proposal_id = session["paper_execution_evidence"][0]["proposal_id"]

        report = simulate_paper_lifecycle_batch(
            session_report=session,
            confirmation_session_id=session["session_id"],
            lifecycle_inputs=(lifecycle_input(proposal_id),),
        )

        self.assertEqual(report["state"], "PAPER_LIFECYCLE_BATCH_COMPLETE")
        self.assertEqual(report["intent_count"], 1)
        self.assertEqual(report["status_counts"]["CLOSED"], 1)
        self.assertEqual(len(report["account_records"]), 1)
        self.assertEqual(report["provider_requests_performed"], 0)
        self.assertEqual(report["persistent_state_writes_performed"], 0)
        self.assertFalse(report["authority"]["live_trading_authorized"])

    def test_two_intent_batch_supports_mixed_closed_and_cancelled_results(self) -> None:
        session = ready_session(two=True)
        proposal_ids = [
            row["proposal_id"] for row in session["paper_execution_evidence"]
        ]
        closed = lifecycle_input(proposal_ids[0])
        cancelled = lifecycle_input(
            proposal_ids[1],
            bars=[
                {
                    "time_ms": 2_100,
                    "open": 98.0,
                    "high": 98.5,
                    "low": 97.5,
                    "close": 98.0,
                    "available_notional_usd": 4_000.0,
                }
            ],
        )

        report = simulate_paper_lifecycle_batch(
            session_report=session,
            confirmation_session_id=session["session_id"],
            lifecycle_inputs=(closed, cancelled),
        )

        self.assertEqual(report["status_counts"]["CLOSED"], 1)
        self.assertEqual(report["status_counts"]["CANCELLED_UNFILLED"], 1)
        self.assertEqual(len(report["account_records"]), 2)

        snapshot = materialize_paper_account(
            initial_equity_usd=100.0,
            records=tuple(report["account_records"]),
            marks=(),
        )
        self.assertEqual(snapshot.closed_position_count, 1)
        self.assertEqual(snapshot.cancelled_order_count, 1)
        self.assertEqual(snapshot.open_position_count, 0)

    def test_lifecycle_input_order_does_not_change_batch_id(self) -> None:
        session = ready_session(two=True)
        proposal_ids = [
            row["proposal_id"] for row in session["paper_execution_evidence"]
        ]
        first_input = lifecycle_input(proposal_ids[0])
        second_input = lifecycle_input(
            proposal_ids[1],
            bars=[
                {
                    "time_ms": 2_100,
                    "open": 98.0,
                    "high": 98.5,
                    "low": 97.5,
                    "close": 98.0,
                    "available_notional_usd": 4_000.0,
                }
            ],
        )

        first = simulate_paper_lifecycle_batch(
            session_report=session,
            confirmation_session_id=session["session_id"],
            lifecycle_inputs=(first_input, second_input),
        )
        second = simulate_paper_lifecycle_batch(
            session_report=session,
            confirmation_session_id=session["session_id"],
            lifecycle_inputs=(second_input, first_input),
        )

        self.assertEqual(first["batch_id"], second["batch_id"])
        self.assertEqual(first["results"], second["results"])
        self.assertEqual(first["account_records"], second["account_records"])

    def test_exact_session_id_confirmation_is_required(self) -> None:
        session = ready_session()
        proposal_id = session["paper_execution_evidence"][0]["proposal_id"]

        with self.assertRaises(ValueError):
            simulate_paper_lifecycle_batch(
                session_report=session,
                confirmation_session_id="wrong-session-id",
                lifecycle_inputs=(lifecycle_input(proposal_id),),
            )

    def test_missing_or_unknown_lifecycle_input_fails_closed(self) -> None:
        session = ready_session(two=True)
        proposal_ids = [
            row["proposal_id"] for row in session["paper_execution_evidence"]
        ]

        with self.assertRaises(ValueError):
            simulate_paper_lifecycle_batch(
                session_report=session,
                confirmation_session_id=session["session_id"],
                lifecycle_inputs=(lifecycle_input(proposal_ids[0]),),
            )

        with self.assertRaises(ValueError):
            simulate_paper_lifecycle_batch(
                session_report=session,
                confirmation_session_id=session["session_id"],
                lifecycle_inputs=(
                    lifecycle_input(proposal_ids[0]),
                    lifecycle_input("unknown-proposal"),
                ),
            )

    def test_tampered_session_execution_evidence_is_rejected(self) -> None:
        session = ready_session()
        proposal_id = session["paper_execution_evidence"][0]["proposal_id"]
        tampered = copy.deepcopy(session)
        evidence = tampered["paper_execution_evidence"][0][
            "paper_execution_evidence"
        ]
        evidence["decision"]["intent"]["symbol"] = "ETH_USDT_PERP"

        with self.assertRaises(ValueError):
            simulate_paper_lifecycle_batch(
                session_report=tampered,
                confirmation_session_id=session["session_id"],
                lifecycle_inputs=(lifecycle_input(proposal_id),),
            )

    def test_session_authority_must_remain_closed(self) -> None:
        session = ready_session()
        proposal_id = session["paper_execution_evidence"][0]["proposal_id"]
        tampered = copy.deepcopy(session)
        tampered["authority"]["scheduled_submission_authorized"] = True

        with self.assertRaises(ValueError):
            simulate_paper_lifecycle_batch(
                session_report=tampered,
                confirmation_session_id=session["session_id"],
                lifecycle_inputs=(lifecycle_input(proposal_id),),
            )

    def test_target_and_bar_numeric_types_are_strict(self) -> None:
        session = ready_session()
        proposal_id = session["paper_execution_evidence"][0]["proposal_id"]

        bad_target = lifecycle_input(proposal_id)
        bad_target["target_price"] = "105.0"
        with self.assertRaises(ValueError):
            simulate_paper_lifecycle_batch(
                session_report=session,
                confirmation_session_id=session["session_id"],
                lifecycle_inputs=(bad_target,),
            )

        bad_bar = lifecycle_input(proposal_id)
        bad_bar["bars"][0]["open"] = "100.0"
        with self.assertRaises(ValueError):
            simulate_paper_lifecycle_batch(
                session_report=session,
                confirmation_session_id=session["session_id"],
                lifecycle_inputs=(bad_bar,),
            )

    def test_policy_cannot_enable_automatic_provider_persistent_or_live_paths(self) -> None:
        with self.assertRaises(ValueError):
            PaperLifecycleBatchPolicy(
                automatic_lifecycle_simulation_authorized=True
            )
        with self.assertRaises(ValueError):
            PaperLifecycleBatchPolicy(
                scheduled_lifecycle_simulation_authorized=True
            )
        with self.assertRaises(ValueError):
            PaperLifecycleBatchPolicy(provider_access_authorized=True)
        with self.assertRaises(ValueError):
            PaperLifecycleBatchPolicy(persistent_state_write_authorized=True)
        with self.assertRaises(ValueError):
            PaperLifecycleBatchPolicy(live_trading_authorized=True)

    def test_machine_readable_input_and_config_are_strict(self) -> None:
        session = ready_session()
        proposal_id = session["paper_execution_evidence"][0]["proposal_id"]
        payload = {
            "schema": "qookey-paper-lifecycle-batch-input-v0.1",
            "session_report": session,
            "lifecycle_inputs": [lifecycle_input(proposal_id)],
        }

        parsed_session, parsed_inputs = paper_lifecycle_batch_input_from_dict(
            json.loads(json.dumps(payload))
        )
        self.assertEqual(parsed_session["session_id"], session["session_id"])
        self.assertEqual(len(parsed_inputs), 1)

        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            paper_lifecycle_batch_policy_from_config(config),
            PaperLifecycleBatchPolicy(),
        )
        self.assertTrue(
            config["policy"]["explicit_lifecycle_simulation_authorized"]
        )
        self.assertFalse(
            config["policy"]["automatic_lifecycle_simulation_authorized"]
        )

        bad = json.loads(CONFIG.read_text(encoding="utf-8"))
        bad["policy"]["maximum_intents"] = True
        with self.assertRaises(ValueError):
            paper_lifecycle_batch_policy_from_config(bad)


if __name__ == "__main__":
    unittest.main()
