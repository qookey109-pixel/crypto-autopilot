from __future__ import annotations

import copy
import json
import unittest
from dataclasses import asdict
from pathlib import Path

from crypto_autopilot.exchanges.paper import PaperBroker
from crypto_autopilot.paper.account_advance_v0_1 import (
    PaperAccountAdvancePolicy,
    advance_paper_account,
    paper_account_advance_input_from_dict,
    paper_account_advance_policy_from_config,
)
from crypto_autopilot.paper.account_v0_1 import (
    materialize_paper_account,
    paper_account_input_from_dict,
)
from crypto_autopilot.paper.cycle_v0_1 import prepare_paper_cycle
from crypto_autopilot.paper.lifecycle_batch_v0_1 import (
    simulate_paper_lifecycle_batch,
)
from crypto_autopilot.paper.lifecycle_v0_1 import PaperLifecyclePolicy
from crypto_autopilot.paper.session_v0_1 import submit_paper_cycle_session
from crypto_autopilot.risk import plan_position_size


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "paper_account_advance_v0_1.json"


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


def empty_account_input() -> dict[str, object]:
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


def ready_session(
    *,
    symbol: str = "BTC_USDT_PERP",
    family: str = "TREND_FOLLOWING",
    as_of_ms: int = 1_000,
) -> dict[str, object]:
    cycle = prepare_paper_cycle(
        account_input=empty_account_input(),
        candidate_inputs=(candidate(symbol, family, as_of_ms=as_of_ms),),
    )
    return submit_paper_cycle_session(
        cycle_report=cycle,
        confirmation_cycle_id=cycle["cycle_id"],
        broker=PaperBroker(),
    )


def batch_for_session(
    session: dict[str, object],
    *,
    target_price: float = 105.0,
    bars: list[dict[str, object]],
    lifecycle_policy: PaperLifecyclePolicy = PaperLifecyclePolicy(),
) -> dict[str, object]:
    proposal_id = session["paper_execution_evidence"][0]["proposal_id"]
    return simulate_paper_lifecycle_batch(
        session_report=session,
        confirmation_session_id=session["session_id"],
        lifecycle_inputs=(
            {
                "proposal_id": proposal_id,
                "target_price": target_price,
                "bars": bars,
            },
        ),
        lifecycle_policy=lifecycle_policy,
    )


def open_bars(start_ms: int = 2_000) -> list[dict[str, object]]:
    return [
        {
            "time_ms": start_ms,
            "open": 100.0,
            "high": 101.0,
            "low": 99.5,
            "close": 100.5,
            "available_notional_usd": 4_000.0,
        }
    ]


def closed_bars(start_ms: int = 2_000) -> list[dict[str, object]]:
    return [
        *open_bars(start_ms),
        {
            "time_ms": start_ms + 1_000,
            "open": 101.0,
            "high": 106.0,
            "low": 100.5,
            "close": 105.0,
            "available_notional_usd": 4_000.0,
        },
    ]


def account_input_from_batch(
    batch: dict[str, object],
    *,
    marks: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "schema": "qookey-paper-account-state-input-v0.1",
        "initial_equity_usd": 100.0,
        "records": batch["account_records"],
        "marks": [] if marks is None else marks,
    }


class PaperAccountAdvanceV01Tests(unittest.TestCase):
    def test_empty_account_adds_closed_batch_record(self) -> None:
        session = ready_session()
        batch = batch_for_session(session, bars=closed_bars())

        report = advance_paper_account(
            previous_account_input=empty_account_input(),
            lifecycle_batch_report=batch,
            confirmation_batch_id=batch["batch_id"],
            next_marks=(),
        )

        self.assertEqual(report["state"], "ACCOUNT_ADVANCED")
        self.assertEqual(report["added_record_count"], 1)
        self.assertEqual(report["replaced_record_count"], 0)
        self.assertEqual(report["unchanged_record_count"], 0)
        self.assertEqual(report["total_record_count"], 1)
        self.assertEqual(
            report["account"]["snapshot"]["closed_position_count"],
            1,
        )
        self.assertEqual(report["account"]["snapshot"]["open_position_count"], 0)
        self.assertFalse(report["authority"]["persistent_state_write_authorized"])

    def test_open_record_is_replaced_by_forward_closed_lifecycle(self) -> None:
        session = ready_session()
        open_batch = batch_for_session(session, bars=open_bars())
        previous = account_input_from_batch(
            open_batch,
            marks=[
                {
                    "symbol": "BTC_USDT_PERP",
                    "time_ms": 2_500,
                    "price": 100.5,
                }
            ],
        )
        closed_batch = batch_for_session(session, bars=closed_bars())

        report = advance_paper_account(
            previous_account_input=previous,
            lifecycle_batch_report=closed_batch,
            confirmation_batch_id=closed_batch["batch_id"],
            next_marks=(),
        )

        self.assertEqual(report["replaced_record_count"], 1)
        self.assertEqual(report["added_record_count"], 0)
        self.assertEqual(report["total_record_count"], 1)
        self.assertEqual(report["account"]["snapshot"]["open_position_count"], 0)
        self.assertEqual(report["account"]["snapshot"]["closed_position_count"], 1)

    def test_identical_batch_replay_is_no_change_and_does_not_double_count(self) -> None:
        session = ready_session()
        batch = batch_for_session(session, bars=closed_bars())
        previous = account_input_from_batch(batch)

        initial, records, marks = paper_account_input_from_dict(previous)
        before = materialize_paper_account(
            initial_equity_usd=initial,
            records=records,
            marks=marks,
        )

        report = advance_paper_account(
            previous_account_input=previous,
            lifecycle_batch_report=batch,
            confirmation_batch_id=batch["batch_id"],
            next_marks=(),
        )

        self.assertEqual(report["state"], "ACCOUNT_ADVANCE_NO_CHANGE")
        self.assertEqual(report["unchanged_record_count"], 1)
        self.assertEqual(report["added_record_count"], 0)
        self.assertEqual(report["replaced_record_count"], 0)
        self.assertEqual(report["next_snapshot_id"], before.snapshot_id)
        self.assertEqual(report["total_record_count"], 1)

    def test_existing_intent_cannot_change_lifecycle_id(self) -> None:
        session = ready_session()
        open_batch = batch_for_session(session, target_price=105.0, bars=open_bars())
        previous = account_input_from_batch(
            open_batch,
            marks=[
                {
                    "symbol": "BTC_USDT_PERP",
                    "time_ms": 2_500,
                    "price": 100.5,
                }
            ],
        )
        retargeted = batch_for_session(
            session,
            target_price=106.0,
            bars=closed_bars(),
        )

        with self.assertRaises(ValueError):
            advance_paper_account(
                previous_account_input=previous,
                lifecycle_batch_report=retargeted,
                confirmation_batch_id=retargeted["batch_id"],
                next_marks=(),
            )

    def test_lifecycle_event_time_cannot_regress(self) -> None:
        session = ready_session()
        closed_batch = batch_for_session(session, bars=closed_bars())
        previous = account_input_from_batch(closed_batch)
        older_open = batch_for_session(session, bars=open_bars())

        with self.assertRaises(ValueError):
            advance_paper_account(
                previous_account_input=previous,
                lifecycle_batch_report=older_open,
                confirmation_batch_id=older_open["batch_id"],
                next_marks=(
                    {
                        "symbol": "BTC_USDT_PERP",
                        "time_ms": 3_500,
                        "price": 100.5,
                    },
                ),
            )

    def test_same_event_time_with_different_report_is_rejected(self) -> None:
        session = ready_session()
        first = batch_for_session(
            session,
            bars=open_bars(),
            lifecycle_policy=PaperLifecyclePolicy(entry_slippage_bps=2.0),
        )
        previous = account_input_from_batch(
            first,
            marks=[
                {
                    "symbol": "BTC_USDT_PERP",
                    "time_ms": 2_500,
                    "price": 100.5,
                }
            ],
        )
        changed_policy = batch_for_session(
            session,
            bars=open_bars(),
            lifecycle_policy=PaperLifecyclePolicy(entry_slippage_bps=3.0),
        )

        with self.assertRaises(ValueError):
            advance_paper_account(
                previous_account_input=previous,
                lifecycle_batch_report=changed_policy,
                confirmation_batch_id=changed_policy["batch_id"],
                next_marks=(
                    {
                        "symbol": "BTC_USDT_PERP",
                        "time_ms": 3_000,
                        "price": 100.5,
                    },
                ),
            )

    def test_unrelated_previous_record_is_preserved_when_new_intent_is_added(self) -> None:
        btc_session = ready_session()
        btc_batch = batch_for_session(btc_session, bars=closed_bars())
        previous = account_input_from_batch(btc_batch)

        eth_session = ready_session(
            symbol="ETH_USDT_PERP",
            family="MEAN_REVERSION",
            as_of_ms=4_000,
        )
        eth_batch = batch_for_session(
            eth_session,
            bars=closed_bars(start_ms=5_000),
        )

        report = advance_paper_account(
            previous_account_input=previous,
            lifecycle_batch_report=eth_batch,
            confirmation_batch_id=eth_batch["batch_id"],
            next_marks=(),
        )

        self.assertEqual(report["added_record_count"], 1)
        self.assertEqual(report["total_record_count"], 2)
        self.assertEqual(
            report["account"]["snapshot"]["closed_position_count"],
            2,
        )
        self.assertEqual(
            report["next_account_input"]["initial_equity_usd"],
            100.0,
        )

    def test_open_next_state_requires_exact_current_marks(self) -> None:
        session = ready_session()
        batch = batch_for_session(session, bars=open_bars())

        with self.assertRaises(ValueError):
            advance_paper_account(
                previous_account_input=empty_account_input(),
                lifecycle_batch_report=batch,
                confirmation_batch_id=batch["batch_id"],
                next_marks=(),
            )

        report = advance_paper_account(
            previous_account_input=empty_account_input(),
            lifecycle_batch_report=batch,
            confirmation_batch_id=batch["batch_id"],
            next_marks=(
                {
                    "symbol": "BTC_USDT_PERP",
                    "time_ms": 2_500,
                    "price": 100.5,
                },
            ),
        )
        self.assertEqual(report["account"]["snapshot"]["open_position_count"], 1)
        self.assertEqual(len(report["portfolio_existing_exposures"]), 1)

    def test_exact_batch_id_and_batch_contents_are_revalidated(self) -> None:
        session = ready_session()
        batch = batch_for_session(session, bars=closed_bars())

        with self.assertRaises(ValueError):
            advance_paper_account(
                previous_account_input=empty_account_input(),
                lifecycle_batch_report=batch,
                confirmation_batch_id="wrong-batch-id",
                next_marks=(),
            )

        tampered = copy.deepcopy(batch)
        tampered["results"][0]["reason"] = "tampered"
        with self.assertRaises(ValueError):
            advance_paper_account(
                previous_account_input=empty_account_input(),
                lifecycle_batch_report=tampered,
                confirmation_batch_id=batch["batch_id"],
                next_marks=(),
            )

    def test_policy_cannot_enable_provider_persistence_or_live_paths(self) -> None:
        with self.assertRaises(ValueError):
            PaperAccountAdvancePolicy(persistent_state_write_authorized=True)
        with self.assertRaises(ValueError):
            PaperAccountAdvancePolicy(provider_access_authorized=True)
        with self.assertRaises(ValueError):
            PaperAccountAdvancePolicy(live_trading_authorized=True)
        with self.assertRaises(ValueError):
            PaperAccountAdvancePolicy(
                reject_lifecycle_id_change_for_existing_intent=False
            )

    def test_machine_readable_input_and_config_are_strict(self) -> None:
        session = ready_session()
        batch = batch_for_session(session, bars=closed_bars())
        payload = {
            "schema": "qookey-paper-account-advance-input-v0.1",
            "previous_account_input": empty_account_input(),
            "lifecycle_batch_report": batch,
            "next_marks": [],
        }

        previous, parsed_batch, marks = paper_account_advance_input_from_dict(
            json.loads(json.dumps(payload))
        )
        self.assertEqual(previous["schema"], "qookey-paper-account-state-input-v0.1")
        self.assertEqual(parsed_batch["batch_id"], batch["batch_id"])
        self.assertEqual(marks, ())

        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            paper_account_advance_policy_from_config(config),
            PaperAccountAdvancePolicy(),
        )
        self.assertFalse(config["authority"]["persistent_state_write_authorized"])

        bad = json.loads(CONFIG.read_text(encoding="utf-8"))
        bad["policy"]["allow_identical_record_replay"] = "true"
        with self.assertRaises(ValueError):
            paper_account_advance_policy_from_config(bad)


if __name__ == "__main__":
    unittest.main()
