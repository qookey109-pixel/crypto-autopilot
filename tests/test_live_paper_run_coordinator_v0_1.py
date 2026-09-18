from __future__ import annotations

import copy
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
    live_paper_tick_report_id_from_mapping,
)
from crypto_autopilot.paper.run_coordinator_v0_1 import (
    LivePaperRunCoordinatorPolicy,
    coordinate_live_paper_run_step,
    live_paper_run_coordinator_input_from_dict,
    live_paper_run_coordinator_policy_from_config,
    verify_live_paper_run_step,
)
from crypto_autopilot.paper.run_store_v0_1 import LocalPaperRunStore
from crypto_autopilot.paper.session_v0_1 import submit_paper_cycle_session
from crypto_autopilot.risk import plan_position_size


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "live_paper_run_coordinator_v0_1.json"


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
                symbol="BOOT_USDT_PERP",
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
        previous_account_input=empty_account(),
        lifecycle_batch_report=batch,
        confirmation_batch_id=batch["batch_id"],
        next_marks=(),
    )
    return create_paper_loop_checkpoint(
        account_advance_report=advance,
        confirmation_advance_id=advance["advance_id"],
    )


class SequenceFeed:
    def __init__(self, frames: dict[tuple[str, int], LivePaperMarketFrame]) -> None:
        self.frames = frames
        self.calls: list[tuple[str, int, int]] = []

    def fetch_frame(
        self,
        symbol: str,
        *,
        tick_time_ms: int,
        since_ms: int,
    ) -> LivePaperMarketFrame:
        self.calls.append((symbol, tick_time_ms, since_ms))
        return self.frames[(symbol, tick_time_ms)]


def frame(
    *,
    symbol: str,
    tick: int,
    open_: float,
    high: float,
    low: float,
    close: float,
    mark: float,
) -> LivePaperMarketFrame:
    return LivePaperMarketFrame(
        provider="FIXTURE_PUBLIC",
        symbol=symbol,
        time_ms=tick,
        source_time_ms=tick - 1,
        open=open_,
        high=high,
        low=low,
        close=close,
        mark_price=mark,
        available_notional_usd=4_000.0,
        provider_request_count=2,
        source_trade_count=4,
    )


class LivePaperRunCoordinatorV01Tests(unittest.TestCase):
    def _first_fixture(self):
        checkpoint = bootstrap_checkpoint()
        state = initialize_live_paper_state(checkpoint_report=checkpoint)
        equity = checkpoint["account_snapshot"]["equity_usd"]
        spec = {
            "candidate": candidate(
                symbol="BTC_USDT_PERP",
                family="TREND_FOLLOWING",
                equity_usd=equity,
                as_of_ms=4_000,
            ),
            "target_price": 105.0,
        }
        feed = SequenceFeed(
            {
                ("BTC_USDT_PERP", 5_000): frame(
                    symbol="BTC_USDT_PERP",
                    tick=5_000,
                    open_=100.0,
                    high=101.0,
                    low=99.5,
                    close=100.5,
                    mark=100.5,
                )
            }
        )
        return state, spec, feed

    def test_first_step_persists_restartable_append_only_evidence(self) -> None:
        state, spec, feed = self._first_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalPaperRunStore(Path(tmp).resolve())
            report = coordinate_live_paper_run_step(
                run_name="primary-live-paper",
                tick_time_ms=5_000,
                candidate_specs=(spec,),
                feed=feed,
                store=store,
                initial_state=state,
            )

            self.assertEqual(report["state"], "LIVE_PAPER_RUN_STEP_COMMITTED")
            self.assertEqual(report["sequence"], 1)
            self.assertEqual(report["provider_requests_performed"], 2)
            self.assertEqual(len(feed.calls), 1)
            step = report["run_step"]
            self.assertEqual(
                verify_live_paper_run_step(step),
                report["step_id"],
            )
            self.assertEqual(
                live_paper_tick_report_id_from_mapping(step["tick_report"]),
                step["tick_id"],
            )
            self.assertIsNotNone(
                store.get_json("live-run", report["run_id"])
            )
            self.assertIsNotNone(
                store.get_json("live-state", step["previous_state_id"])
            )
            self.assertIsNotNone(
                store.get_json("live-state", step["next_state_id"])
            )
            self.assertIsNotNone(
                store.get_json("live-tick", step["tick_id"])
            )
            self.assertIsNotNone(
                store.get_json("live-run-step", step["step_id"])
            )
            self.assertIsNotNone(
                store.get_json("live-run-result", step["request_id"])
            )
            self.assertFalse(
                report["authority"]["automatic_schedule_authorized"]
            )
            self.assertFalse(
                report["authority"]["scorecard_auto_selection_authorized"]
            )
            self.assertFalse(report["authority"]["live_real_trading_authorized"])

    def test_continuation_loads_persisted_state_and_closes_position(self) -> None:
        state, spec, first_feed = self._first_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalPaperRunStore(Path(tmp).resolve())
            first = coordinate_live_paper_run_step(
                run_name="primary-live-paper",
                tick_time_ms=5_000,
                candidate_specs=(spec,),
                feed=first_feed,
                store=store,
                initial_state=state,
            )
            second_feed = SequenceFeed(
                {
                    ("BTC_USDT_PERP", 6_000): frame(
                        symbol="BTC_USDT_PERP",
                        tick=6_000,
                        open_=100.5,
                        high=106.0,
                        low=100.0,
                        close=105.0,
                        mark=105.0,
                    )
                }
            )

            second = coordinate_live_paper_run_step(
                run_name="primary-live-paper",
                tick_time_ms=6_000,
                candidate_specs=(),
                feed=second_feed,
                store=store,
                previous_step=first["run_step"],
            )

            self.assertEqual(second["sequence"], 2)
            self.assertEqual(
                second["run_step"]["previous_step_id"],
                first["step_id"],
            )
            self.assertEqual(second["provider_requests_performed"], 2)
            next_state = second["run_step"]["tick_report"]["next_state"]
            self.assertIsNone(next_state["active_session"])
            self.assertEqual(
                next_state["checkpoint_report"]["account_snapshot"][
                    "open_position_count"
                ],
                0,
            )

    def test_completed_request_replay_makes_no_new_provider_call(self) -> None:
        state, spec, first_feed = self._first_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalPaperRunStore(Path(tmp).resolve())
            first = coordinate_live_paper_run_step(
                run_name="primary-live-paper",
                tick_time_ms=5_000,
                candidate_specs=(spec,),
                feed=first_feed,
                store=store,
                initial_state=state,
            )
            replay_feed = SequenceFeed({})

            replay = coordinate_live_paper_run_step(
                run_name="primary-live-paper",
                tick_time_ms=5_000,
                candidate_specs=(spec,),
                feed=replay_feed,
                store=store,
                initial_state=state,
            )

            self.assertEqual(replay["state"], "COMMITTED_STEP_REPLAYED")
            self.assertEqual(replay["step_id"], first["step_id"])
            self.assertEqual(replay["provider_requests_performed"], 0)
            self.assertEqual(replay["persistent_objects_created"], 0)
            self.assertEqual(replay_feed.calls, [])

    def test_continuation_requires_persisted_previous_state(self) -> None:
        state, spec, feed = self._first_fixture()
        with tempfile.TemporaryDirectory() as first_tmp, tempfile.TemporaryDirectory() as second_tmp:
            first_store = LocalPaperRunStore(Path(first_tmp).resolve())
            first = coordinate_live_paper_run_step(
                run_name="primary-live-paper",
                tick_time_ms=5_000,
                candidate_specs=(spec,),
                feed=feed,
                store=first_store,
                initial_state=state,
            )
            empty_store = LocalPaperRunStore(Path(second_tmp).resolve())

            with self.assertRaises(ValueError):
                coordinate_live_paper_run_step(
                    run_name="primary-live-paper",
                    tick_time_ms=6_000,
                    candidate_specs=(),
                    feed=SequenceFeed({}),
                    store=empty_store,
                    previous_step=first["run_step"],
                )

    def test_tampered_tick_report_fails_run_step_verification(self) -> None:
        state, spec, feed = self._first_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalPaperRunStore(Path(tmp).resolve())
            report = coordinate_live_paper_run_step(
                run_name="primary-live-paper",
                tick_time_ms=5_000,
                candidate_specs=(spec,),
                feed=feed,
                store=store,
                initial_state=state,
            )
            tampered = copy.deepcopy(report["run_step"])
            tampered["tick_report"]["provider_requests_performed"] += 1

            with self.assertRaises(ValueError):
                verify_live_paper_run_step(tampered)

    def test_tick_report_id_verifier_rejects_real_authority_tamper(self) -> None:
        state, spec, feed = self._first_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalPaperRunStore(Path(tmp).resolve())
            report = coordinate_live_paper_run_step(
                run_name="primary-live-paper",
                tick_time_ms=5_000,
                candidate_specs=(spec,),
                feed=feed,
                store=store,
                initial_state=state,
            )
            tick = copy.deepcopy(report["run_step"]["tick_report"])
            tick["authority"]["real_money_order_authorized"] = True

            with self.assertRaises(ValueError):
                live_paper_tick_report_id_from_mapping(tick)

    def test_policy_cannot_enable_schedule_auto_selection_or_real_trading(self) -> None:
        with self.assertRaises(ValueError):
            LivePaperRunCoordinatorPolicy(automatic_schedule_authorized=True)
        with self.assertRaises(ValueError):
            LivePaperRunCoordinatorPolicy(
                automatic_candidate_generation_authorized=True
            )
        with self.assertRaises(ValueError):
            LivePaperRunCoordinatorPolicy(scorecard_auto_selection_authorized=True)
        with self.assertRaises(ValueError):
            LivePaperRunCoordinatorPolicy(private_exchange_api_authorized=True)
        with self.assertRaises(ValueError):
            LivePaperRunCoordinatorPolicy(real_money_order_authorized=True)
        with self.assertRaises(ValueError):
            LivePaperRunCoordinatorPolicy(live_real_trading_authorized=True)

    def test_machine_config_and_input_contract_are_strict(self) -> None:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            live_paper_run_coordinator_policy_from_config(config),
            LivePaperRunCoordinatorPolicy(),
        )

        state, spec, _ = self._first_fixture()
        payload = {
            "schema": "qookey-live-paper-run-coordinator-input-v0.1",
            "run_name": "primary-live-paper",
            "tick_time_ms": 5_000,
            "candidate_specs": [spec],
            "initial_state": state,
            "previous_step_id": None,
        }
        parsed = live_paper_run_coordinator_input_from_dict(payload)
        self.assertEqual(parsed[0], "primary-live-paper")
        self.assertEqual(parsed[1], 5_000)
        self.assertEqual(len(parsed[2]), 1)
        self.assertIsNotNone(parsed[3])
        self.assertIsNone(parsed[4])

        bad = json.loads(CONFIG.read_text(encoding="utf-8"))
        bad["policy"]["automatic_schedule_authorized"] = True
        with self.assertRaises(ValueError):
            live_paper_run_coordinator_policy_from_config(bad)


if __name__ == "__main__":
    unittest.main()
