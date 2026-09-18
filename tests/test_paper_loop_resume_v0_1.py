from __future__ import annotations

import copy
import json
import unittest
from dataclasses import asdict
from pathlib import Path

from crypto_autopilot.exchanges.paper import PaperBroker
from crypto_autopilot.paper.account_advance_v0_1 import advance_paper_account
from crypto_autopilot.paper.checkpoint_v0_1 import create_paper_loop_checkpoint
from crypto_autopilot.paper.cycle_v0_1 import prepare_paper_cycle
from crypto_autopilot.paper.lifecycle_batch_v0_1 import (
    simulate_paper_lifecycle_batch,
)
from crypto_autopilot.paper.resume_v0_1 import (
    PaperLoopResumePolicy,
    paper_loop_resume_input_from_dict,
    paper_loop_resume_policy_from_config,
    resume_paper_loop,
)
from crypto_autopilot.paper.session_v0_1 import submit_paper_cycle_session
from crypto_autopilot.risk import plan_position_size


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "paper_loop_resume_v0_1.json"


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
    equity_usd: float,
    as_of_ms: int,
) -> dict[str, object]:
    sizing = plan_position_size(
        direction="LONG",
        equity_usd=equity_usd,
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


def first_session() -> dict[str, object]:
    cycle = prepare_paper_cycle(
        account_input=empty_account(),
        candidate_inputs=(
            candidate(
                symbol="BTC_USDT_PERP",
                family="TREND_FOLLOWING",
                equity_usd=100.0,
                as_of_ms=1_000,
            ),
        ),
    )
    return submit_paper_cycle_session(
        cycle_report=cycle,
        confirmation_cycle_id=cycle["cycle_id"],
        broker=PaperBroker(),
    )


def make_checkpoint(*, keep_open: bool) -> dict[str, object]:
    session = first_session()
    proposal_id = session["paper_execution_evidence"][0]["proposal_id"]
    bars = [
        {
            "time_ms": 2_000,
            "open": 100.0,
            "high": 101.0,
            "low": 99.5,
            "close": 100.5,
            "available_notional_usd": 4_000.0,
        }
    ]
    if not keep_open:
        bars.append(
            {
                "time_ms": 3_000,
                "open": 101.0,
                "high": 106.0,
                "low": 100.5,
                "close": 105.0,
                "available_notional_usd": 4_000.0,
            }
        )

    batch = simulate_paper_lifecycle_batch(
        session_report=session,
        confirmation_session_id=session["session_id"],
        lifecycle_inputs=(
            {
                "proposal_id": proposal_id,
                "target_price": 105.0,
                "bars": bars,
            },
        ),
    )
    next_marks: tuple[object, ...]
    if keep_open:
        next_marks = (
            {
                "symbol": "BTC_USDT_PERP",
                "time_ms": 2_500,
                "price": 100.5,
            },
        )
    else:
        next_marks = ()

    advance = advance_paper_account(
        previous_account_input=empty_account(),
        lifecycle_batch_report=batch,
        confirmation_batch_id=batch["batch_id"],
        next_marks=next_marks,
    )
    return create_paper_loop_checkpoint(
        account_advance_report=advance,
        confirmation_advance_id=advance["advance_id"],
    )


class PaperLoopResumeV01Tests(unittest.TestCase):
    def test_closed_checkpoint_resumes_next_cycle_from_checkpoint_equity(self) -> None:
        checkpoint = make_checkpoint(keep_open=False)
        equity = checkpoint["account_snapshot"]["equity_usd"]
        as_of_ms = checkpoint["account_snapshot"]["as_of_ms"] + 1_000
        next_candidate = candidate(
            symbol="ETH_USDT_PERP",
            family="MEAN_REVERSION",
            equity_usd=equity,
            as_of_ms=as_of_ms,
        )

        report = resume_paper_loop(
            checkpoint_report=checkpoint,
            confirmation_checkpoint_id=checkpoint["checkpoint_id"],
            candidate_inputs=(next_candidate,),
        )

        self.assertEqual(report["state"], "PAPER_LOOP_RESUMED")
        self.assertEqual(
            report["cycle_report"]["account_snapshot_id"],
            checkpoint["next_snapshot_id"],
        )
        self.assertEqual(
            report["cycle_report"]["account_equity_usd"],
            checkpoint["account_snapshot"]["equity_usd"],
        )
        self.assertEqual(
            report["cycle_state"],
            "PAPER_INTENTS_READY_FOR_EXPLICIT_SUBMISSION",
        )
        self.assertEqual(report["broker_submissions_performed"], 0)
        self.assertEqual(report["lifecycle_simulations_performed"], 0)
        self.assertFalse(report["authority"]["live_trading_authorized"])

    def test_open_checkpoint_preserves_existing_exposure_into_resumed_cycle(self) -> None:
        checkpoint = make_checkpoint(keep_open=True)
        equity = checkpoint["account_snapshot"]["equity_usd"]
        as_of_ms = checkpoint["account_snapshot"]["as_of_ms"] + 1_000
        next_candidate = candidate(
            symbol="ETH_USDT_PERP",
            family="MEAN_REVERSION",
            equity_usd=equity,
            as_of_ms=as_of_ms,
        )

        report = resume_paper_loop(
            checkpoint_report=checkpoint,
            confirmation_checkpoint_id=checkpoint["checkpoint_id"],
            candidate_inputs=(next_candidate,),
        )

        self.assertEqual(
            report["cycle_report"]["existing_exposures"],
            checkpoint["portfolio_existing_exposures"],
        )
        self.assertEqual(len(report["cycle_report"]["existing_exposures"]), 1)
        self.assertEqual(
            report["cycle_report"]["existing_exposures"][0]["symbol"],
            "BTC_USDT_PERP",
        )

    def test_no_candidates_is_valid_resumed_no_trade_cycle(self) -> None:
        checkpoint = make_checkpoint(keep_open=False)

        report = resume_paper_loop(
            checkpoint_report=checkpoint,
            confirmation_checkpoint_id=checkpoint["checkpoint_id"],
            candidate_inputs=(),
        )

        self.assertEqual(report["state"], "PAPER_LOOP_RESUMED")
        self.assertEqual(report["cycle_state"], "NO_CANDIDATES")
        self.assertEqual(report["cycle_report"]["candidate_count"], 0)

    def test_exact_checkpoint_id_confirmation_is_required(self) -> None:
        checkpoint = make_checkpoint(keep_open=False)

        with self.assertRaises(ValueError):
            resume_paper_loop(
                checkpoint_report=checkpoint,
                confirmation_checkpoint_id="wrong-checkpoint-id",
                candidate_inputs=(),
            )

    def test_checkpoint_tampering_is_rejected_before_cycle(self) -> None:
        checkpoint = make_checkpoint(keep_open=True)
        tampered = copy.deepcopy(checkpoint)
        tampered["next_account_input"]["marks"][0]["price"] = 100.6

        with self.assertRaises(ValueError):
            resume_paper_loop(
                checkpoint_report=tampered,
                confirmation_checkpoint_id=checkpoint["checkpoint_id"],
                candidate_inputs=(),
            )

    def test_checkpoint_account_policy_is_bound_into_checkpoint_id(self) -> None:
        checkpoint = make_checkpoint(keep_open=False)
        tampered = copy.deepcopy(checkpoint)
        tampered["account_policy"]["insolvency_equity_floor_usd"] = -1000.0

        with self.assertRaises(ValueError):
            resume_paper_loop(
                checkpoint_report=tampered,
                confirmation_checkpoint_id=checkpoint["checkpoint_id"],
                candidate_inputs=(),
            )

    def test_stale_candidate_equity_fails_existing_cycle_sizing_gate(self) -> None:
        checkpoint = make_checkpoint(keep_open=False)
        as_of_ms = checkpoint["account_snapshot"]["as_of_ms"] + 1_000
        stale = candidate(
            symbol="ETH_USDT_PERP",
            family="MEAN_REVERSION",
            equity_usd=100.0,
            as_of_ms=as_of_ms,
        )

        self.assertNotEqual(
            stale["position_sizing_plan"]["equity_usd"],
            checkpoint["account_snapshot"]["equity_usd"],
        )
        with self.assertRaises(ValueError):
            resume_paper_loop(
                checkpoint_report=checkpoint,
                confirmation_checkpoint_id=checkpoint["checkpoint_id"],
                candidate_inputs=(stale,),
            )

    def test_candidate_timestamp_cannot_precede_checkpoint_account(self) -> None:
        checkpoint = make_checkpoint(keep_open=True)
        equity = checkpoint["account_snapshot"]["equity_usd"]
        stale_time = checkpoint["account_snapshot"]["as_of_ms"] - 1
        stale = candidate(
            symbol="ETH_USDT_PERP",
            family="MEAN_REVERSION",
            equity_usd=equity,
            as_of_ms=stale_time,
        )

        with self.assertRaises(ValueError):
            resume_paper_loop(
                checkpoint_report=checkpoint,
                confirmation_checkpoint_id=checkpoint["checkpoint_id"],
                candidate_inputs=(stale,),
            )

    def test_json_round_trip_checkpoint_resumes_identically(self) -> None:
        checkpoint = make_checkpoint(keep_open=False)
        serialized = json.loads(json.dumps(checkpoint))

        first = resume_paper_loop(
            checkpoint_report=checkpoint,
            confirmation_checkpoint_id=checkpoint["checkpoint_id"],
            candidate_inputs=(),
        )
        second = resume_paper_loop(
            checkpoint_report=serialized,
            confirmation_checkpoint_id=serialized["checkpoint_id"],
            candidate_inputs=(),
        )

        self.assertEqual(first["resume_id"], second["resume_id"])
        self.assertEqual(first["cycle_id"], second["cycle_id"])
        self.assertEqual(first["cycle_report"], second["cycle_report"])

    def test_policy_cannot_enable_automatic_provider_persistence_or_live_paths(self) -> None:
        with self.assertRaises(ValueError):
            PaperLoopResumePolicy(automatic_cycle_authorized=True)
        with self.assertRaises(ValueError):
            PaperLoopResumePolicy(automatic_submission_authorized=True)
        with self.assertRaises(ValueError):
            PaperLoopResumePolicy(persistent_state_write_authorized=True)
        with self.assertRaises(ValueError):
            PaperLoopResumePolicy(provider_access_authorized=True)
        with self.assertRaises(ValueError):
            PaperLoopResumePolicy(live_trading_authorized=True)

    def test_machine_readable_input_and_config_are_strict(self) -> None:
        checkpoint = make_checkpoint(keep_open=False)
        payload = {
            "schema": "qookey-paper-loop-resume-input-v0.1",
            "checkpoint_report": checkpoint,
            "candidates": [],
        }

        parsed_checkpoint, candidates = paper_loop_resume_input_from_dict(
            json.loads(json.dumps(payload))
        )
        self.assertEqual(
            parsed_checkpoint["checkpoint_id"],
            checkpoint["checkpoint_id"],
        )
        self.assertEqual(candidates, ())

        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            paper_loop_resume_policy_from_config(config),
            PaperLoopResumePolicy(),
        )
        self.assertFalse(config["authority"]["automatic_cycle_authorized"])

        bad = json.loads(CONFIG.read_text(encoding="utf-8"))
        bad["policy"]["require_cycle_exposure_match"] = "true"
        with self.assertRaises(ValueError):
            paper_loop_resume_policy_from_config(bad)


if __name__ == "__main__":
    unittest.main()
