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
from crypto_autopilot.paper.integrity_v0_1 import (
    PaperLoopIntegrityPolicy,
    audit_paper_loop_integrity,
    paper_loop_integrity_input_from_dict,
    paper_loop_integrity_policy_from_config,
)
from crypto_autopilot.paper.lifecycle_batch_v0_1 import (
    simulate_paper_lifecycle_batch,
)
from crypto_autopilot.paper.resume_v0_1 import resume_paper_loop
from crypto_autopilot.paper.session_v0_1 import submit_paper_cycle_session
from crypto_autopilot.risk import plan_position_size


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "paper_loop_integrity_v0_1.json"


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


def bootstrap_checkpoint() -> dict[str, object]:
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
    session = submit_paper_cycle_session(
        cycle_report=cycle,
        confirmation_cycle_id=cycle["cycle_id"],
        broker=PaperBroker(),
    )
    proposal_id = session["paper_execution_evidence"][0]["proposal_id"]
    batch = simulate_paper_lifecycle_batch(
        session_report=session,
        confirmation_session_id=session["session_id"],
        lifecycle_inputs=(
            {
                "proposal_id": proposal_id,
                "target_price": 105.0,
                "bars": [
                    {
                        "time_ms": 2_000,
                        "open": 100.0,
                        "high": 101.0,
                        "low": 99.5,
                        "close": 100.5,
                        "available_notional_usd": 4_000.0,
                    }
                ],
            },
        ),
    )
    advance = advance_paper_account(
        previous_account_input=empty_account(),
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
    return create_paper_loop_checkpoint(
        account_advance_report=advance,
        confirmation_advance_id=advance["advance_id"],
    )


def closed_bars(start_ms: int) -> list[dict[str, object]]:
    return [
        {
            "time_ms": start_ms,
            "open": 100.0,
            "high": 101.0,
            "low": 99.5,
            "close": 100.5,
            "available_notional_usd": 4_000.0,
        },
        {
            "time_ms": start_ms + 1_000,
            "open": 101.0,
            "high": 106.0,
            "low": 100.5,
            "close": 105.0,
            "available_notional_usd": 4_000.0,
        },
    ]


def complete_round(
    start_checkpoint: dict[str, object],
    *,
    symbol: str,
    candidate_as_of_ms: int,
    bar_start_ms: int,
    next_mark_time_ms: int,
) -> dict[str, object]:
    equity = start_checkpoint["account_snapshot"]["equity_usd"]
    resume = resume_paper_loop(
        checkpoint_report=start_checkpoint,
        confirmation_checkpoint_id=start_checkpoint["checkpoint_id"],
        candidate_inputs=(
            candidate(
                symbol=symbol,
                family="MEAN_REVERSION",
                equity_usd=equity,
                as_of_ms=candidate_as_of_ms,
            ),
        ),
    )
    cycle = resume["cycle_report"]
    assert cycle["state"] == "PAPER_INTENTS_READY_FOR_EXPLICIT_SUBMISSION"

    session = submit_paper_cycle_session(
        cycle_report=cycle,
        confirmation_cycle_id=cycle["cycle_id"],
        broker=PaperBroker(),
    )
    proposal_id = session["paper_execution_evidence"][0]["proposal_id"]
    batch = simulate_paper_lifecycle_batch(
        session_report=session,
        confirmation_session_id=session["session_id"],
        lifecycle_inputs=(
            {
                "proposal_id": proposal_id,
                "target_price": 105.0,
                "bars": closed_bars(bar_start_ms),
            },
        ),
    )
    advance = advance_paper_account(
        previous_account_input=start_checkpoint["next_account_input"],
        lifecycle_batch_report=batch,
        confirmation_batch_id=batch["batch_id"],
        next_marks=(
            {
                "symbol": "BTC_USDT_PERP",
                "time_ms": next_mark_time_ms,
                "price": 100.5,
            },
        ),
    )
    end_checkpoint = create_paper_loop_checkpoint(
        account_advance_report=advance,
        confirmation_advance_id=advance["advance_id"],
    )
    return {
        "start_checkpoint": start_checkpoint,
        "resume_report": resume,
        "session_report": session,
        "lifecycle_batch_report": batch,
        "account_advance_report": advance,
        "end_checkpoint": end_checkpoint,
    }


def two_round_transcript() -> tuple[dict[str, object], list[dict[str, object]]]:
    start = bootstrap_checkpoint()
    first = complete_round(
        start,
        symbol="ETH_USDT_PERP",
        candidate_as_of_ms=3_500,
        bar_start_ms=4_000,
        next_mark_time_ms=5_500,
    )
    second = complete_round(
        first["end_checkpoint"],
        symbol="SOL_USDT_PERP",
        candidate_as_of_ms=6_500,
        bar_start_ms=7_000,
        next_mark_time_ms=8_500,
    )
    return start, [first, second]


class PaperLoopIntegrityV01Tests(unittest.TestCase):
    def test_two_forward_rounds_pass_and_preserve_open_exposure(self) -> None:
        start, rounds = two_round_transcript()
        terminal = rounds[-1]["end_checkpoint"]

        report = audit_paper_loop_integrity(
            expected_start_checkpoint_id=start["checkpoint_id"],
            expected_terminal_checkpoint_id=terminal["checkpoint_id"],
            rounds=tuple(rounds),
        )

        self.assertEqual(report["state"], "MULTI_CYCLE_INTEGRITY_PASS")
        self.assertEqual(report["round_count"], 2)
        self.assertEqual(report["unique_forward_intent_count"], 2)
        self.assertEqual(report["start_checkpoint_id"], start["checkpoint_id"])
        self.assertEqual(
            report["terminal_checkpoint_id"],
            terminal["checkpoint_id"],
        )
        self.assertEqual(report["executions_performed"], 0)
        self.assertEqual(report["provider_requests_performed"], 0)
        self.assertFalse(report["authority"]["live_trading_authorized"])

        for round_item in rounds:
            self.assertEqual(
                round_item["resume_report"]["cycle_report"]["existing_exposures"],
                round_item["start_checkpoint"]["portfolio_existing_exposures"],
            )
            self.assertEqual(
                round_item["start_checkpoint"]["portfolio_existing_exposures"][0][
                    "symbol"
                ],
                "BTC_USDT_PERP",
            )

    def test_same_transcript_replay_produces_same_integrity_id(self) -> None:
        start, rounds = two_round_transcript()
        terminal = rounds[-1]["end_checkpoint"]

        first = audit_paper_loop_integrity(
            expected_start_checkpoint_id=start["checkpoint_id"],
            expected_terminal_checkpoint_id=terminal["checkpoint_id"],
            rounds=tuple(rounds),
        )
        second = audit_paper_loop_integrity(
            expected_start_checkpoint_id=start["checkpoint_id"],
            expected_terminal_checkpoint_id=terminal["checkpoint_id"],
            rounds=tuple(rounds),
        )

        self.assertEqual(first["integrity_id"], second["integrity_id"])
        self.assertEqual(first["transcript_sha256"], second["transcript_sha256"])
        self.assertEqual(first["rounds"], second["rounds"])

    def test_json_round_trip_preserves_integrity_id(self) -> None:
        start, rounds = two_round_transcript()
        payload = json.loads(
            json.dumps(
                {
                    "schema": "qookey-paper-loop-integrity-input-v0.1",
                    "expected_start_checkpoint_id": start["checkpoint_id"],
                    "expected_terminal_checkpoint_id": rounds[-1]["end_checkpoint"][
                        "checkpoint_id"
                    ],
                    "rounds": rounds,
                }
            )
        )
        parsed_start, parsed_terminal, parsed_rounds = (
            paper_loop_integrity_input_from_dict(payload)
        )

        original = audit_paper_loop_integrity(
            expected_start_checkpoint_id=start["checkpoint_id"],
            expected_terminal_checkpoint_id=rounds[-1]["end_checkpoint"][
                "checkpoint_id"
            ],
            rounds=tuple(rounds),
        )
        replayed = audit_paper_loop_integrity(
            expected_start_checkpoint_id=parsed_start,
            expected_terminal_checkpoint_id=parsed_terminal,
            rounds=parsed_rounds,
        )

        self.assertEqual(original["integrity_id"], replayed["integrity_id"])

    def test_cross_round_checkpoint_payload_must_chain_exactly(self) -> None:
        start, rounds = two_round_transcript()
        tampered = copy.deepcopy(rounds)
        tampered[1]["start_checkpoint"] = copy.deepcopy(start)

        with self.assertRaises(ValueError):
            audit_paper_loop_integrity(
                expected_start_checkpoint_id=start["checkpoint_id"],
                expected_terminal_checkpoint_id=rounds[-1]["end_checkpoint"][
                    "checkpoint_id"
                ],
                rounds=tuple(tampered),
            )

    def test_stage_id_tampering_is_rejected(self) -> None:
        start, rounds = two_round_transcript()
        tampered = copy.deepcopy(rounds)
        tampered[0]["session_report"]["session_id"] = "paper-session-v0-1-tampered"

        with self.assertRaises(ValueError):
            audit_paper_loop_integrity(
                expected_start_checkpoint_id=start["checkpoint_id"],
                expected_terminal_checkpoint_id=rounds[-1]["end_checkpoint"][
                    "checkpoint_id"
                ],
                rounds=tuple(tampered),
            )

    def test_wrong_start_or_terminal_anchor_is_rejected(self) -> None:
        start, rounds = two_round_transcript()
        terminal = rounds[-1]["end_checkpoint"]["checkpoint_id"]

        with self.assertRaises(ValueError):
            audit_paper_loop_integrity(
                expected_start_checkpoint_id="wrong-start",
                expected_terminal_checkpoint_id=terminal,
                rounds=tuple(rounds),
            )
        with self.assertRaises(ValueError):
            audit_paper_loop_integrity(
                expected_start_checkpoint_id=start["checkpoint_id"],
                expected_terminal_checkpoint_id="wrong-terminal",
                rounds=tuple(rounds),
            )

    def test_single_round_is_not_multi_cycle_integrity(self) -> None:
        start, rounds = two_round_transcript()

        with self.assertRaises(ValueError):
            audit_paper_loop_integrity(
                expected_start_checkpoint_id=start["checkpoint_id"],
                expected_terminal_checkpoint_id=rounds[0]["end_checkpoint"][
                    "checkpoint_id"
                ],
                rounds=(rounds[0],),
            )

    def test_policy_cannot_disable_lineage_gates_or_enable_execution_paths(self) -> None:
        with self.assertRaises(ValueError):
            PaperLoopIntegrityPolicy(require_exact_checkpoint_chaining=False)
        with self.assertRaises(ValueError):
            PaperLoopIntegrityPolicy(require_unique_forward_intent_ids=False)
        with self.assertRaises(ValueError):
            PaperLoopIntegrityPolicy(provider_access_authorized=True)
        with self.assertRaises(ValueError):
            PaperLoopIntegrityPolicy(persistent_state_write_authorized=True)
        with self.assertRaises(ValueError):
            PaperLoopIntegrityPolicy(automatic_execution_authorized=True)
        with self.assertRaises(ValueError):
            PaperLoopIntegrityPolicy(live_trading_authorized=True)

    def test_versioned_config_matches_defaults_and_types_are_strict(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            paper_loop_integrity_policy_from_config(payload),
            PaperLoopIntegrityPolicy(),
        )
        self.assertTrue(payload["policy"]["require_unique_forward_intent_ids"])
        self.assertFalse(payload["authority"]["automatic_execution_authorized"])

        bad = json.loads(CONFIG.read_text(encoding="utf-8"))
        bad["policy"]["minimum_rounds"] = True
        with self.assertRaises(ValueError):
            paper_loop_integrity_policy_from_config(bad)


if __name__ == "__main__":
    unittest.main()
