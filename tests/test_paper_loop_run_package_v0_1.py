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
from crypto_autopilot.paper.integrity_v0_1 import audit_paper_loop_integrity
from crypto_autopilot.paper.lifecycle_batch_v0_1 import (
    simulate_paper_lifecycle_batch,
)
from crypto_autopilot.paper.resume_v0_1 import resume_paper_loop
from crypto_autopilot.paper.run_package_v0_1 import (
    PaperLoopRunPackagePolicy,
    build_paper_loop_run_package,
    paper_loop_run_package_input_from_dict,
    paper_loop_run_package_policy_from_config,
    verify_paper_loop_run_package,
)
from crypto_autopilot.paper.session_v0_1 import submit_paper_cycle_session
from crypto_autopilot.risk import plan_position_size


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "paper_loop_run_package_v0_1.json"


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
    resume = resume_paper_loop(
        checkpoint_report=start_checkpoint,
        confirmation_checkpoint_id=start_checkpoint["checkpoint_id"],
        candidate_inputs=(
            candidate(
                symbol=symbol,
                family="MEAN_REVERSION",
                equity_usd=start_checkpoint["account_snapshot"]["equity_usd"],
                as_of_ms=candidate_as_of_ms,
            ),
        ),
    )
    cycle = resume["cycle_report"]
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


def package_inputs() -> tuple[dict[str, object], dict[str, object]]:
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
    rounds = [first, second]
    integrity_input = {
        "schema": "qookey-paper-loop-integrity-input-v0.1",
        "expected_start_checkpoint_id": start["checkpoint_id"],
        "expected_terminal_checkpoint_id": second["end_checkpoint"][
            "checkpoint_id"
        ],
        "rounds": rounds,
    }
    integrity_report = audit_paper_loop_integrity(
        expected_start_checkpoint_id=start["checkpoint_id"],
        expected_terminal_checkpoint_id=second["end_checkpoint"]["checkpoint_id"],
        rounds=tuple(rounds),
    )
    return integrity_input, integrity_report


class PaperLoopRunPackageV01Tests(unittest.TestCase):
    def test_builds_self_verifying_portable_package(self) -> None:
        integrity_input, integrity_report = package_inputs()

        package = build_paper_loop_run_package(
            integrity_input=integrity_input,
            integrity_report=integrity_report,
            confirmation_integrity_id=integrity_report["integrity_id"],
        )

        self.assertEqual(package["state"], "PORTABLE_RUN_PACKAGE_READY")
        self.assertEqual(package["round_count"], 2)
        self.assertEqual(len(package["stage_manifest"]), 2)
        self.assertTrue(
            all(len(row["stages"]) == 6 for row in package["stage_manifest"])
        )
        self.assertEqual(
            package["terminal_checkpoint"]["checkpoint_id"],
            package["terminal_checkpoint_id"],
        )
        self.assertEqual(
            verify_paper_loop_run_package(package),
            package["package_id"],
        )
        self.assertEqual(package["executions_performed"], 0)
        self.assertFalse(package["authority"]["package_is_execution_authority"])
        self.assertFalse(package["authority"]["live_trading_authorized"])

    def test_same_inputs_produce_same_package_id(self) -> None:
        integrity_input, integrity_report = package_inputs()

        first = build_paper_loop_run_package(
            integrity_input=integrity_input,
            integrity_report=integrity_report,
            confirmation_integrity_id=integrity_report["integrity_id"],
        )
        second = build_paper_loop_run_package(
            integrity_input=integrity_input,
            integrity_report=integrity_report,
            confirmation_integrity_id=integrity_report["integrity_id"],
        )

        self.assertEqual(first["package_id"], second["package_id"])
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])

    def test_json_round_trip_remains_fully_verifiable(self) -> None:
        integrity_input, integrity_report = package_inputs()
        package = build_paper_loop_run_package(
            integrity_input=integrity_input,
            integrity_report=integrity_report,
            confirmation_integrity_id=integrity_report["integrity_id"],
        )
        serialized = json.loads(json.dumps(package))

        self.assertEqual(
            verify_paper_loop_run_package(serialized),
            serialized["package_id"],
        )

    def test_wrong_integrity_confirmation_is_rejected(self) -> None:
        integrity_input, integrity_report = package_inputs()

        with self.assertRaises(ValueError):
            build_paper_loop_run_package(
                integrity_input=integrity_input,
                integrity_report=integrity_report,
                confirmation_integrity_id="wrong-integrity-id",
            )

    def test_transcript_tampering_is_rejected_by_reaudit(self) -> None:
        integrity_input, integrity_report = package_inputs()
        tampered = copy.deepcopy(integrity_input)
        tampered["rounds"][0]["session_report"]["session_id"] = "tampered"

        with self.assertRaises(ValueError):
            build_paper_loop_run_package(
                integrity_input=tampered,
                integrity_report=integrity_report,
                confirmation_integrity_id=integrity_report["integrity_id"],
            )

    def test_integrity_proof_tampering_is_rejected(self) -> None:
        integrity_input, integrity_report = package_inputs()
        tampered = copy.deepcopy(integrity_report)
        tampered["net_equity_change_usd"] += 1.0

        with self.assertRaises(ValueError):
            build_paper_loop_run_package(
                integrity_input=integrity_input,
                integrity_report=tampered,
                confirmation_integrity_id=integrity_report["integrity_id"],
            )

    def test_package_manifest_tampering_is_rejected(self) -> None:
        integrity_input, integrity_report = package_inputs()
        package = build_paper_loop_run_package(
            integrity_input=integrity_input,
            integrity_report=integrity_report,
            confirmation_integrity_id=integrity_report["integrity_id"],
        )
        tampered = copy.deepcopy(package)
        tampered["stage_manifest"][0]["stages"][0]["sha256"] = "0" * 64

        with self.assertRaises(ValueError):
            verify_paper_loop_run_package(tampered)

    def test_terminal_checkpoint_tampering_is_rejected(self) -> None:
        integrity_input, integrity_report = package_inputs()
        package = build_paper_loop_run_package(
            integrity_input=integrity_input,
            integrity_report=integrity_report,
            confirmation_integrity_id=integrity_report["integrity_id"],
        )
        tampered = copy.deepcopy(package)
        tampered["terminal_checkpoint"]["next_snapshot_id"] = "tampered"

        with self.assertRaises(ValueError):
            verify_paper_loop_run_package(tampered)

    def test_policy_cannot_disable_proof_or_enable_execution_paths(self) -> None:
        with self.assertRaises(ValueError):
            PaperLoopRunPackagePolicy(require_integrity_reaudit=False)
        with self.assertRaises(ValueError):
            PaperLoopRunPackagePolicy(include_full_transcript=False)
        with self.assertRaises(ValueError):
            PaperLoopRunPackagePolicy(persistent_state_write_authorized=True)
        with self.assertRaises(ValueError):
            PaperLoopRunPackagePolicy(provider_access_authorized=True)
        with self.assertRaises(ValueError):
            PaperLoopRunPackagePolicy(execution_authorized=True)
        with self.assertRaises(ValueError):
            PaperLoopRunPackagePolicy(live_trading_authorized=True)

    def test_machine_readable_input_and_config_are_strict(self) -> None:
        integrity_input, integrity_report = package_inputs()
        payload = {
            "schema": "qookey-paper-loop-run-package-input-v0.1",
            "integrity_input": integrity_input,
            "integrity_report": integrity_report,
        }
        parsed_input, parsed_report = paper_loop_run_package_input_from_dict(
            json.loads(json.dumps(payload))
        )
        self.assertEqual(
            parsed_report["integrity_id"],
            integrity_report["integrity_id"],
        )
        self.assertEqual(
            parsed_input["expected_start_checkpoint_id"],
            integrity_input["expected_start_checkpoint_id"],
        )

        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            paper_loop_run_package_policy_from_config(config),
            PaperLoopRunPackagePolicy(),
        )
        self.assertFalse(config["authority"]["package_is_execution_authority"])

        bad = json.loads(CONFIG.read_text(encoding="utf-8"))
        bad["policy"]["execution_authorized"] = "false"
        with self.assertRaises(ValueError):
            paper_loop_run_package_policy_from_config(bad)


if __name__ == "__main__":
    unittest.main()
