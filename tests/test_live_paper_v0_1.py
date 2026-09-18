from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

from crypto_autopilot.exchanges.paper import PaperBroker
from crypto_autopilot.paper.account_advance_v0_1 import advance_paper_account
from crypto_autopilot.paper.checkpoint_v0_1 import create_paper_loop_checkpoint
from crypto_autopilot.paper.cycle_v0_1 import prepare_paper_cycle
from crypto_autopilot.paper.lifecycle_batch_v0_1 import (
    simulate_paper_lifecycle_batch,
)
from crypto_autopilot.paper.live_v0_1 import (
    LivePaperMarketFrame,
    LivePaperPolicy,
    PionexLivePaperFeed,
    initialize_live_paper_state,
    live_paper_policy_from_config,
    run_live_paper_tick,
    verify_live_paper_state,
)
from crypto_autopilot.paper.run_store_v0_1 import LocalPaperRunStore
from crypto_autopilot.paper.session_v0_1 import submit_paper_cycle_session
from crypto_autopilot.risk import plan_position_size


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "live_paper_simulation_v0_1.json"


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


class FakePionexClient:
    def get_order_book(self, symbol: str, *, limit: int = 20) -> SimpleNamespace:
        return SimpleNamespace(
            bids=((99.9, 2.0), (99.8, 3.0)),
            asks=((100.1, 2.5), (100.2, 3.0)),
            update_time_ms=9_999,
        )

    def get_recent_trades(self, symbol: str, *, limit: int = 100):
        return [
            SimpleNamespace(time_ms=9_950, price=100.0),
            SimpleNamespace(time_ms=9_980, price=100.3),
        ]


class LivePaperV01Tests(unittest.TestCase):
    def test_open_position_advances_on_later_tick_and_hits_target(self) -> None:
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
                ),
                ("BTC_USDT_PERP", 6_000): frame(
                    symbol="BTC_USDT_PERP",
                    tick=6_000,
                    open_=100.5,
                    high=106.0,
                    low=100.0,
                    close=105.0,
                    mark=105.0,
                ),
            }
        )

        first = run_live_paper_tick(
            state=state,
            tick_time_ms=5_000,
            candidate_specs=(spec,),
            feed=feed,
        )
        self.assertEqual(first["state"], "LIVE_PAPER_POSITION_OPEN")
        first_state = first["next_state"]
        self.assertIsNotNone(first_state["active_session"])
        self.assertEqual(first["provider_requests_performed"], 2)
        self.assertFalse(first["authority"]["real_money_order_authorized"])
        self.assertFalse(first["authority"]["live_real_trading_authorized"])
        verify_live_paper_state(first_state)

        second = run_live_paper_tick(
            state=first_state,
            tick_time_ms=6_000,
            candidate_specs=(),
            feed=feed,
        )
        self.assertEqual(second["state"], "LIVE_PAPER_POSITION_UPDATED")
        self.assertIsNone(second["next_state"]["active_session"])
        self.assertNotEqual(second["checkpoint_id"], first["checkpoint_id"])
        self.assertEqual(
            second["next_state"]["checkpoint_report"]["account_snapshot"][
                "open_position_count"
            ],
            0,
        )
        self.assertEqual(
            second["next_state"]["checkpoint_report"]["account_snapshot"][
                "closed_position_count"
            ],
            2,
        )
        verify_live_paper_state(second["next_state"])

    def test_active_session_blocks_overlapping_new_cycle(self) -> None:
        checkpoint = bootstrap_checkpoint()
        state = initialize_live_paper_state(checkpoint_report=checkpoint)
        equity = checkpoint["account_snapshot"]["equity_usd"]
        btc = {
            "candidate": candidate(
                symbol="BTC_USDT_PERP",
                family="TREND_FOLLOWING",
                equity_usd=equity,
                as_of_ms=4_000,
            ),
            "target_price": 110.0,
        }
        eth = {
            "candidate": candidate(
                symbol="ETH_USDT_PERP",
                family="MEAN_REVERSION",
                equity_usd=equity,
                as_of_ms=5_500,
            ),
            "target_price": 110.0,
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
                ),
                ("BTC_USDT_PERP", 6_000): frame(
                    symbol="BTC_USDT_PERP",
                    tick=6_000,
                    open_=100.5,
                    high=102.0,
                    low=100.0,
                    close=101.0,
                    mark=101.0,
                ),
            }
        )
        first = run_live_paper_tick(
            state=state,
            tick_time_ms=5_000,
            candidate_specs=(btc,),
            feed=feed,
        )
        second = run_live_paper_tick(
            state=first["next_state"],
            tick_time_ms=6_000,
            candidate_specs=(eth,),
            feed=feed,
        )

        self.assertEqual(second["state"], "ACTIVE_SESSION_BLOCKS_NEW_CYCLE")
        self.assertIsNone(second["cycle_id"])
        self.assertIsNotNone(second["next_state"]["active_session"])
        self.assertEqual([item[0] for item in feed.calls].count("ETH_USDT_PERP"), 0)

    def test_local_persistence_is_deterministic_and_replay_safe(self) -> None:
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
        frames = {
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

        with tempfile.TemporaryDirectory() as tmp:
            store = LocalPaperRunStore(Path(tmp).resolve())
            first = run_live_paper_tick(
                state=state,
                tick_time_ms=5_000,
                candidate_specs=(spec,),
                feed=SequenceFeed(frames),
                store=store,
            )
            second = run_live_paper_tick(
                state=state,
                tick_time_ms=5_000,
                candidate_specs=(spec,),
                feed=SequenceFeed(frames),
                store=store,
            )

            self.assertEqual(first["next_state_id"], second["next_state_id"])
            self.assertFalse(first["storage_receipt"]["receipt"]["replayed"])
            self.assertTrue(second["storage_receipt"]["receipt"]["replayed"])
            loaded = store.get_json("live-state", first["next_state_id"])
            self.assertEqual(loaded, first["next_state"])

    def test_public_pionex_feed_normalizes_visible_depth_without_private_api(self) -> None:
        feed = PionexLivePaperFeed(
            FakePionexClient(),  # type: ignore[arg-type]
            policy=LivePaperPolicy(maximum_source_age_ms=500),
        )
        result = feed.fetch_frame(
            "BTC_USDT_PERP",
            tick_time_ms=10_000,
            since_ms=9_900,
        )

        self.assertEqual(result.provider, "PIONEX_PUBLIC")
        self.assertEqual(result.time_ms, 10_000)
        self.assertAlmostEqual(result.mark_price, 100.0)
        self.assertAlmostEqual(
            result.available_notional_usd,
            100.1 * 2.5 + 100.2 * 3.0,
        )
        self.assertEqual(result.provider_request_count, 2)
        self.assertEqual(result.source_trade_count, 2)

    def test_state_tampering_and_non_advancing_tick_fail_closed(self) -> None:
        checkpoint = bootstrap_checkpoint()
        state = initialize_live_paper_state(checkpoint_report=checkpoint)

        tampered = json.loads(json.dumps(state))
        tampered["authority"]["real_money_order_authorized"] = True
        with self.assertRaises(ValueError):
            verify_live_paper_state(tampered)

        with self.assertRaises(ValueError):
            run_live_paper_tick(
                state=state,
                tick_time_ms=state["last_tick_ms"],
                candidate_specs=(),
                feed=SequenceFeed({}),
            )

    def test_policy_config_allows_live_paper_but_not_real_trading(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(live_paper_policy_from_config(payload), LivePaperPolicy())
        self.assertTrue(payload["authority"]["public_live_market_data_authorized"])
        self.assertTrue(payload["authority"]["live_paper_simulation_authorized"])
        self.assertFalse(payload["authority"]["real_money_order_authorized"])
        self.assertFalse(payload["authority"]["live_real_trading_authorized"])

        bad = json.loads(CONFIG.read_text(encoding="utf-8"))
        bad["policy"]["live_real_trading_authorized"] = True
        with self.assertRaises(ValueError):
            live_paper_policy_from_config(bad)


if __name__ == "__main__":
    unittest.main()
