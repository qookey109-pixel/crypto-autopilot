from __future__ import annotations

import json
import tempfile
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
from crypto_autopilot.paper.live_v0_1 import (
    LivePaperMarketFrame,
    initialize_live_paper_state,
)
from crypto_autopilot.paper.run_coordinator_v0_1 import (
    coordinate_live_paper_run_step,
)
from crypto_autopilot.paper.run_recovery_v0_1 import (
    LivePaperRunRecoveryPolicy,
    live_paper_run_recovery_policy_from_config,
    reconcile_live_paper_run,
)
from crypto_autopilot.paper.run_store_v0_1 import LocalPaperRunStore
from crypto_autopilot.paper.session_v0_1 import submit_paper_cycle_session
from crypto_autopilot.risk import plan_position_size


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "live_paper_run_recovery_v0_1.json"


def _family_report(family: str) -> dict[str, object]:
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


def _empty_account() -> dict[str, object]:
    return {
        "schema": "qookey-paper-account-state-input-v0.1",
        "initial_equity_usd": 100.0,
        "records": [],
        "marks": [],
    }


def _candidate(*, equity_usd: float, as_of_ms: int) -> dict[str, object]:
    sizing = plan_position_size(
        direction="LONG",
        equity_usd=equity_usd,
        entry_price=100.0,
        stop_price=99.0,
    )
    return {
        "symbol": "BTC_USDT_PERP",
        "strategy_family": "TREND_FOLLOWING",
        "as_of_ms": as_of_ms,
        "family_validation_report": _family_report("TREND_FOLLOWING"),
        "position_sizing_plan": asdict(sizing),
    }


def _bootstrap_state() -> tuple[dict[str, object], dict[str, object]]:
    account = _empty_account()
    cycle = prepare_paper_cycle(
        account_input=account,
        candidate_inputs=(
            {
                **_candidate(equity_usd=100.0, as_of_ms=1_000),
                "symbol": "BOOT_USDT_PERP",
            },
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
                    },
                    {
                        "time_ms": 3_000,
                        "open": 101.0,
                        "high": 106.0,
                        "low": 100.5,
                        "close": 105.0,
                        "available_notional_usd": 4_000.0,
                    },
                ],
            },
        ),
    )
    advance = advance_paper_account(
        previous_account_input=account,
        lifecycle_batch_report=batch,
        confirmation_batch_id=batch["batch_id"],
        next_marks=(),
    )
    checkpoint = create_paper_loop_checkpoint(
        account_advance_report=advance,
        confirmation_advance_id=advance["advance_id"],
    )
    state = initialize_live_paper_state(checkpoint_report=checkpoint)
    spec = {
        "candidate": _candidate(
            equity_usd=float(checkpoint["account_snapshot"]["equity_usd"]),
            as_of_ms=4_000,
        ),
        "target_price": 105.0,
    }
    return state, spec


class _Feed:
    def __init__(self, tick_time_ms: int) -> None:
        self.tick_time_ms = tick_time_ms
        self.calls = 0

    def fetch_frame(
        self,
        symbol: str,
        *,
        tick_time_ms: int,
        since_ms: int,
    ) -> LivePaperMarketFrame:
        self.calls += 1
        if tick_time_ms != self.tick_time_ms:
            raise AssertionError("unexpected fixture tick")
        return LivePaperMarketFrame(
            provider="FIXTURE_PUBLIC",
            symbol=symbol,
            time_ms=tick_time_ms,
            source_time_ms=tick_time_ms - 1,
            open=100.0,
            high=101.0,
            low=99.5,
            close=100.5,
            mark_price=100.5,
            available_notional_usd=4_000.0,
            provider_request_count=2,
            source_trade_count=4,
        )


def _delete_object(root: Path, kind: str, object_id: str) -> None:
    path = root / kind / f"{object_id}.json"
    if path.exists():
        path.unlink()


class LivePaperRunRecoveryV01Tests(unittest.TestCase):
    def _committed_run(
        self,
        root: Path,
        *,
        tick_time_ms: int = 5_000,
    ) -> tuple[LocalPaperRunStore, dict[str, object], dict[str, object], dict[str, object]]:
        state, spec = _bootstrap_state()
        store = LocalPaperRunStore(root)
        report = coordinate_live_paper_run_step(
            run_name="recovery-fixture",
            tick_time_ms=tick_time_ms,
            candidate_specs=(spec,),
            feed=_Feed(tick_time_ms),
            store=store,
            initial_state=state,
        )
        return store, state, spec, report

    def test_consistent_run_audits_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, _, _, committed = self._committed_run(Path(tmp).resolve())
            recovery = reconcile_live_paper_run(
                run_id=committed["run_id"],
                store=store,
            )

            self.assertEqual(recovery["state"], "RUN_CONSISTENT")
            self.assertEqual(recovery["step_count"], 1)
            self.assertEqual(recovery["repairable_request_ids"], [])
            self.assertEqual(recovery["repaired_request_ids"], [])
            self.assertEqual(recovery["result_seal_writes_performed"], 0)
            self.assertEqual(recovery["provider_requests_performed"], 0)
            self.assertEqual(recovery["live_market_data_requests_performed"], 0)
            self.assertFalse(
                recovery["authority"]["account_state_mutation_authorized"]
            )

    def test_missing_result_seal_is_repairable_without_provider_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            store, _, _, committed = self._committed_run(root)
            step = committed["run_step"]
            request_id = step["request_id"]
            _delete_object(root, "live-run-result", request_id)

            audit = reconcile_live_paper_run(
                run_id=committed["run_id"],
                store=store,
            )
            self.assertEqual(audit["state"], "MISSING_RESULT_SEALS_REPAIRABLE")
            self.assertEqual(audit["repairable_request_ids"], [request_id])
            self.assertEqual(audit["result_seal_writes_performed"], 0)

            repaired = reconcile_live_paper_run(
                run_id=committed["run_id"],
                store=store,
                repair_missing_result_seals=True,
            )
            self.assertEqual(repaired["state"], "MISSING_RESULT_SEALS_REPAIRED")
            self.assertEqual(repaired["repaired_request_ids"], [request_id])
            self.assertEqual(repaired["provider_requests_performed"], 0)
            self.assertEqual(repaired["live_market_data_requests_performed"], 0)
            self.assertEqual(repaired["account_state_mutations_performed"], 0)
            self.assertEqual(repaired["step_state_tick_rewrites_performed"], 0)
            self.assertEqual(repaired["result_seal_writes_performed"], 1)
            self.assertIsNotNone(store.get_json("live-run-result", request_id))

            final = reconcile_live_paper_run(
                run_id=committed["run_id"],
                store=store,
            )
            self.assertEqual(final["state"], "RUN_CONSISTENT")

    def test_missing_tick_evidence_requires_review_and_is_not_repaired(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            store, _, _, committed = self._committed_run(root)
            step = committed["run_step"]
            _delete_object(root, "live-tick", step["tick_id"])
            _delete_object(root, "live-run-result", step["request_id"])

            recovery = reconcile_live_paper_run(
                run_id=committed["run_id"],
                store=store,
                repair_missing_result_seals=True,
            )

            self.assertEqual(recovery["state"], "REVIEW_REQUIRED")
            self.assertEqual(recovery["result_seal_writes_performed"], 0)
            self.assertTrue(
                any(
                    issue.startswith("incomplete_step_evidence:")
                    for issue in recovery["issues"]
                )
            )
            self.assertIsNone(
                store.get_json("live-run-result", step["request_id"])
            )

    def test_two_valid_sequence_one_steps_are_a_fork_and_require_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            state, spec = _bootstrap_state()
            store = LocalPaperRunStore(root)

            first = coordinate_live_paper_run_step(
                run_name="recovery-fixture",
                tick_time_ms=5_000,
                candidate_specs=(spec,),
                feed=_Feed(5_000),
                store=store,
                initial_state=state,
            )
            second = coordinate_live_paper_run_step(
                run_name="recovery-fixture",
                tick_time_ms=5_100,
                candidate_specs=(spec,),
                feed=_Feed(5_100),
                store=store,
                initial_state=state,
            )
            self.assertNotEqual(first["step_id"], second["step_id"])
            self.assertEqual(first["run_id"], second["run_id"])

            recovery = reconcile_live_paper_run(
                run_id=first["run_id"],
                store=store,
                repair_missing_result_seals=True,
            )
            self.assertEqual(recovery["state"], "REVIEW_REQUIRED")
            self.assertEqual(recovery["result_seal_writes_performed"], 0)
            self.assertTrue(
                any(
                    issue.startswith("duplicate_step_sequence:")
                    for issue in recovery["issues"]
                )
            )

    def test_empty_header_and_initial_state_can_be_retried_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            store, _, _, committed = self._committed_run(root)
            step = committed["run_step"]

            _delete_object(root, "live-run-step", step["step_id"])
            _delete_object(root, "live-run-result", step["request_id"])
            _delete_object(root, "live-tick", step["tick_id"])
            _delete_object(root, "live-state", step["next_state_id"])

            recovery = reconcile_live_paper_run(
                run_id=committed["run_id"],
                store=store,
            )
            self.assertEqual(
                recovery["state"],
                "RUN_EMPTY_RETRY_FROM_INITIAL_STATE_SAFE",
            )
            self.assertEqual(recovery["step_count"], 0)

    def test_policy_cannot_enable_provider_state_rewrite_or_real_trading(self) -> None:
        with self.assertRaises(ValueError):
            LivePaperRunRecoveryPolicy(provider_access_authorized=True)
        with self.assertRaises(ValueError):
            LivePaperRunRecoveryPolicy(live_market_data_access_authorized=True)
        with self.assertRaises(ValueError):
            LivePaperRunRecoveryPolicy(account_state_mutation_authorized=True)
        with self.assertRaises(ValueError):
            LivePaperRunRecoveryPolicy(step_state_tick_rewrite_authorized=True)
        with self.assertRaises(ValueError):
            LivePaperRunRecoveryPolicy(automatic_schedule_authorized=True)
        with self.assertRaises(ValueError):
            LivePaperRunRecoveryPolicy(real_money_order_authorized=True)
        with self.assertRaises(ValueError):
            LivePaperRunRecoveryPolicy(live_real_trading_authorized=True)

    def test_versioned_config_matches_default_policy(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            live_paper_run_recovery_policy_from_config(payload),
            LivePaperRunRecoveryPolicy(),
        )

        bad = json.loads(CONFIG.read_text(encoding="utf-8"))
        bad["policy"]["step_state_tick_rewrite_authorized"] = True
        with self.assertRaises(ValueError):
            live_paper_run_recovery_policy_from_config(bad)


if __name__ == "__main__":
    unittest.main()
