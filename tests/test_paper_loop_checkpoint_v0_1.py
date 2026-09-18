from __future__ import annotations

import copy
import json
import unittest
from dataclasses import asdict
from pathlib import Path

from crypto_autopilot.exchanges.paper import PaperBroker
from crypto_autopilot.paper.account_advance_v0_1 import advance_paper_account
from crypto_autopilot.paper.checkpoint_v0_1 import (
    PaperLoopCheckpointPolicy,
    create_paper_loop_checkpoint,
    paper_loop_checkpoint_policy_from_config,
)
from crypto_autopilot.paper.cycle_v0_1 import prepare_paper_cycle
from crypto_autopilot.paper.lifecycle_batch_v0_1 import (
    simulate_paper_lifecycle_batch,
)
from crypto_autopilot.paper.session_v0_1 import submit_paper_cycle_session
from crypto_autopilot.risk import plan_position_size


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "paper_loop_checkpoint_v0_1.json"


def family_report() -> dict[str, object]:
    return {
        "schema": "qookey-strategy-family-validation-report-v0.1",
        "family": "TREND_FOLLOWING",
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


def cycle_candidate() -> dict[str, object]:
    sizing = plan_position_size(
        direction="LONG",
        equity_usd=100.0,
        entry_price=100.0,
        stop_price=99.0,
    )
    return {
        "symbol": "BTC_USDT_PERP",
        "strategy_family": "TREND_FOLLOWING",
        "as_of_ms": 1_000,
        "family_validation_report": family_report(),
        "position_sizing_plan": asdict(sizing),
    }


def make_advance(
    *,
    bars: list[dict[str, object]],
    next_marks: tuple[object, ...] = (),
) -> dict[str, object]:
    cycle = prepare_paper_cycle(
        account_input=empty_account(),
        candidate_inputs=(cycle_candidate(),),
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
                "bars": bars,
            },
        ),
    )
    return advance_paper_account(
        previous_account_input=empty_account(),
        lifecycle_batch_report=batch,
        confirmation_batch_id=batch["batch_id"],
        next_marks=next_marks,
    )


def closed_bars() -> list[dict[str, object]]:
    return [
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


def open_bars() -> list[dict[str, object]]:
    return [closed_bars()[0]]


class PaperLoopCheckpointV01Tests(unittest.TestCase):
    def test_closed_account_checkpoint_is_deterministic_and_next_cycle_ready(self) -> None:
        advance = make_advance(bars=closed_bars())

        first = create_paper_loop_checkpoint(
            account_advance_report=advance,
            confirmation_advance_id=advance["advance_id"],
        )
        second = create_paper_loop_checkpoint(
            account_advance_report=advance,
            confirmation_advance_id=advance["advance_id"],
        )

        self.assertEqual(first, second)
        self.assertEqual(first["state"], "PAPER_LOOP_CHECKPOINT_READY")
        self.assertTrue(first["next_cycle_allowed"])
        self.assertEqual(first["next_snapshot_id"], advance["next_snapshot_id"])
        self.assertEqual(first["next_account_input"], advance["next_account_input"])
        self.assertEqual(first["persistent_state_writes_performed"], 0)
        self.assertFalse(first["authority"]["live_trading_authorized"])

    def test_open_account_checkpoint_reconciles_portfolio_exposure(self) -> None:
        advance = make_advance(
            bars=open_bars(),
            next_marks=(
                {
                    "symbol": "BTC_USDT_PERP",
                    "time_ms": 2_500,
                    "price": 100.5,
                },
            ),
        )

        checkpoint = create_paper_loop_checkpoint(
            account_advance_report=advance,
            confirmation_advance_id=advance["advance_id"],
        )

        self.assertTrue(checkpoint["next_cycle_allowed"])
        self.assertEqual(len(checkpoint["portfolio_existing_exposures"]), 1)
        self.assertEqual(
            checkpoint["portfolio_existing_exposures"],
            advance["portfolio_existing_exposures"],
        )
        self.assertEqual(
            checkpoint["account_snapshot"]["open_position_count"],
            1,
        )

    def test_exact_advance_id_confirmation_is_required(self) -> None:
        advance = make_advance(bars=closed_bars())

        with self.assertRaises(ValueError):
            create_paper_loop_checkpoint(
                account_advance_report=advance,
                confirmation_advance_id="wrong-advance-id",
            )

    def test_tampered_next_account_input_is_rejected_by_rematerialization(self) -> None:
        advance = make_advance(bars=closed_bars())
        tampered = copy.deepcopy(advance)
        tampered["next_account_input"]["initial_equity_usd"] = 200.0

        with self.assertRaises(ValueError):
            create_paper_loop_checkpoint(
                account_advance_report=tampered,
                confirmation_advance_id=advance["advance_id"],
            )

    def test_tampered_exposure_list_is_rejected(self) -> None:
        advance = make_advance(
            bars=open_bars(),
            next_marks=(
                {
                    "symbol": "BTC_USDT_PERP",
                    "time_ms": 2_500,
                    "price": 100.5,
                },
            ),
        )
        tampered = copy.deepcopy(advance)
        tampered["portfolio_existing_exposures"][0]["notional_usd"] += 1.0

        with self.assertRaises(ValueError):
            create_paper_loop_checkpoint(
                account_advance_report=tampered,
                confirmation_advance_id=advance["advance_id"],
            )

    def test_advance_summary_tampering_invalidates_advance_id(self) -> None:
        advance = make_advance(bars=closed_bars())
        tampered = copy.deepcopy(advance)
        tampered["added_record_count"] = 2

        with self.assertRaises(ValueError):
            create_paper_loop_checkpoint(
                account_advance_report=tampered,
                confirmation_advance_id=advance["advance_id"],
            )

    def test_policy_cannot_enable_persistence_provider_auto_cycle_or_live(self) -> None:
        with self.assertRaises(ValueError):
            PaperLoopCheckpointPolicy(persistent_state_write_authorized=True)
        with self.assertRaises(ValueError):
            PaperLoopCheckpointPolicy(provider_access_authorized=True)
        with self.assertRaises(ValueError):
            PaperLoopCheckpointPolicy(automatic_cycle_authorized=True)
        with self.assertRaises(ValueError):
            PaperLoopCheckpointPolicy(live_trading_authorized=True)

    def test_versioned_config_matches_defaults_and_types_are_strict(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            paper_loop_checkpoint_policy_from_config(payload),
            PaperLoopCheckpointPolicy(),
        )
        self.assertTrue(payload["policy"]["include_next_account_input"])
        self.assertFalse(payload["authority"]["persistent_state_write_authorized"])

        bad = json.loads(CONFIG.read_text(encoding="utf-8"))
        bad["policy"]["require_exposure_reconciliation"] = "true"
        with self.assertRaises(ValueError):
            paper_loop_checkpoint_policy_from_config(bad)


if __name__ == "__main__":
    unittest.main()
