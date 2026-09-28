from __future__ import annotations

import unittest
from dataclasses import asdict, dataclass

from crypto_autopilot.features.market import OrderBookSnapshot, PublicTrade
from crypto_autopilot.paper.cloud_loop_v0_1 import (
    CloudLoopReviewRequired,
    CompleteTapePionexFeed,
    run_cloud_step,
    slot_id,
)
from crypto_autopilot.paper.live_v0_1 import LivePaperMarketFrame, LivePaperPolicy
from crypto_autopilot.risk import plan_position_size
from crypto_autopilot.paper.run_store_v0_1 import PaperRunObjectAlreadyExistsError


@dataclass
class Receipt:
    replayed: bool


class MemoryStore:
    def __init__(self):
        self.objects = {}

    def get_json(self, kind, object_id):
        return self.objects.get((kind, object_id))

    def list_json_ids(self, kind):
        return tuple(sorted(
            object_id for (stored_kind, object_id) in self.objects
            if stored_kind == kind
        ))

    def put_json(self, kind, object_id, payload):
        key = (kind, object_id)
        if key in self.objects:
            if self.objects[key] != dict(payload):
                raise ValueError("immutable collision")
            return Receipt(True)
        self.objects[key] = dict(payload)
        return Receipt(False)

    def put_json_if_absent(self, kind, object_id, payload):
        key = (kind, object_id)
        if key in self.objects:
            raise PaperRunObjectAlreadyExistsError("already claimed")
        self.objects[key] = dict(payload)
        return Receipt(False)


class NeverCalledFeed:
    def fetch_frame(self, *args, **kwargs):
        raise AssertionError("NO_TRADE heartbeat must not request trade frames")


REGISTRY = {
    "schema": "qookey-cloud-paper-strategy-registry-v0.1",
    "status": "EMPTY_NO_ELIGIBLE_STRATEGIES",
    "strategies": [],
}


def step(store, tick, previous):
    return run_cloud_step(
        tick_ms=tick, previous_slot=previous, store=store,
        feed=NeverCalledFeed(), market_supplier=lambda: {
            "context_status": "REGIME_UNAVAILABLE", "provider_requests_performed": 8,
            "candidate_specs": [],
        },
        candidate_supplier=lambda market, state: [],
        strategy_registry=REGISTRY, before_external=lambda: None,
    )


class CloudPaperLoopTests(unittest.TestCase):
    def test_synthetic_qualified_candidate_opens_closes_and_advances_account(self):
        store = MemoryStore()
        symbol = "BTC_USDT_PERP"
        strategy_id = "synthetic-ci-only"
        candidate = {
            "symbol": symbol,
            "strategy_family": "TREND_FOLLOWING",
            "as_of_ms": 419000,
            "family_validation_report": {
                "schema": "qookey-strategy-family-validation-report-v0.1",
                "family": "TREND_FOLLOWING",
                "category": "fixture",
                "state": "FAMILY_EVIDENCE_READY_FOR_HUMAN_REVIEW",
                "reasons": ["synthetic_ci_fixture"],
                "coverage": {}, "policy": {}, "lineage": {},
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
            },
            "position_sizing_plan": asdict(plan_position_size(
                direction="LONG", equity_usd=10000.0,
                entry_price=100.0, stop_price=99.0,
            )),
        }
        spec = {"strategy_id": strategy_id, "candidate": candidate, "target_price": 105.0}

        class Frames:
            def __init__(self):
                self.frames = {
                    420000: LivePaperMarketFrame(
                        provider="FIXTURE_PUBLIC", symbol=symbol, time_ms=420000,
                        source_time_ms=419999, open=100.0, high=101.0, low=99.5,
                        close=100.5, mark_price=100.5, available_notional_usd=4000.0,
                        provider_request_count=2, source_trade_count=4,
                    ),
                    1320000: LivePaperMarketFrame(
                        provider="FIXTURE_PUBLIC", symbol=symbol, time_ms=1320000,
                        source_time_ms=1319999, open=100.5, high=106.0, low=100.0,
                        close=105.0, mark_price=105.0, available_notional_usd=4000.0,
                        provider_request_count=2, source_trade_count=4,
                    ),
                }

            def fetch_frame(self, symbol, *, tick_time_ms, since_ms):
                return self.frames[tick_time_ms]

        registry = {
            "schema": "qookey-cloud-paper-strategy-registry-v0.1",
            "status": "SYNTHETIC_TEST_ONLY",
            "strategies": [{"strategy_id": strategy_id}],
        }
        def supplier(market, state):
            return (spec,) if not state["active_session"] else ()
        first = run_cloud_step(
            tick_ms=420000, previous_slot=None, store=store, feed=Frames(),
            market_supplier=lambda: {"context_status": "REGIME_UNAVAILABLE",
                                     "provider_requests_performed": 0},
            candidate_supplier=supplier, strategy_registry=registry,
            before_external=lambda: None,
        )
        self.assertEqual(first["state"], "COMMITTED")
        self.assertEqual(first["account"]["open_position_count"], 1)

        second = run_cloud_step(
            tick_ms=1320000, previous_slot="0", store=store, feed=Frames(),
            market_supplier=lambda: {"context_status": "REGIME_UNAVAILABLE",
                                     "provider_requests_performed": 0},
            candidate_supplier=supplier, strategy_registry=registry,
            before_external=lambda: None,
        )
        self.assertEqual(second["state"], "COMMITTED")
        self.assertEqual(second["account"]["open_position_count"], 0)
        self.assertGreater(second["account"]["realized_closed_net_pnl_usd"], 0)

        third = run_cloud_step(
            tick_ms=2220000, previous_slot="1", store=store, feed=Frames(),
            market_supplier=lambda: {"context_status": "REGIME_UNAVAILABLE",
                                     "provider_requests_performed": 0},
            candidate_supplier=lambda market, state: (),
            strategy_registry=registry, before_external=lambda: None,
        )
        self.assertEqual(third["state"], "NO_TRADE")
        self.assertEqual(third["coordinator"]["sequence"], 3)
        self.assertEqual(third["account"]["open_position_count"], 0)

    def test_only_quarter_hour_utc_slots_are_valid(self):
        self.assertEqual(slot_id(420000), "0")
        self.assertEqual(slot_id(1320000), "1")
        with self.assertRaisesRegex(CloudLoopReviewRequired, "OFF_SCHEDULE"):
            slot_id(420001)

    def test_empty_registry_runs_audited_no_trade_and_restarts(self):
        store = MemoryStore()
        first = step(store, 420000, None)
        self.assertEqual(first["state"], "NO_TRADE")
        self.assertEqual(first["reason"], "NO_ELIGIBLE_STRATEGY")
        self.assertEqual(first["account"]["initial_equity_usd"], 10000.0)
        self.assertEqual(first["account"]["open_position_count"], 0)
        self.assertEqual(first["operation_counts"]["provider_requests"], 8)
        self.assertEqual(first["operation_counts"]["r2_write_attempts"], 10)
        replay = step(store, 420000, None)
        self.assertEqual(replay["state"], "REPLAYED")
        self.assertEqual(replay["provider_requests_performed"], 0)
        second = step(store, 1320000, "0")
        self.assertEqual(second["state"], "NO_TRADE")
        self.assertEqual(second["coordinator"]["sequence"], 2)
        self.assertEqual(second["account"]["initial_equity_usd"], 10000.0)

    def test_empty_registry_rejects_injected_production_candidate(self):
        store = MemoryStore()
        def inject(market, state):
            return ({"strategy_id": "synthetic-test-only"},)
        with self.assertRaisesRegex(CloudLoopReviewRequired, "EMPTY_PRODUCTION"):
            run_cloud_step(
                tick_ms=420000, previous_slot=None, store=store,
                feed=NeverCalledFeed(), market_supplier=lambda: {"provider_requests_performed": 0},
                candidate_supplier=inject, strategy_registry=REGISTRY,
                before_external=lambda: None,
            )

    def test_genesis_rejects_orphan_paper_state_before_market(self):
        store = MemoryStore()
        store.put_json("live-state", "orphan-state", {"state_id": "orphan-state"})
        called = []
        with self.assertRaisesRegex(CloudLoopReviewRequired, "GENESIS_LEDGER_NOT_EMPTY"):
            run_cloud_step(
                tick_ms=420000, previous_slot=None, store=store,
                feed=NeverCalledFeed(),
                market_supplier=lambda: called.append(True) or {},
                candidate_supplier=lambda market, state: [],
                strategy_registry=REGISTRY, before_external=lambda: None,
            )
        self.assertEqual(called, [])

    def test_orphan_state_in_nonempty_ledger_blocks_before_market(self):
        store = MemoryStore()
        step(store, 420000, None)
        store.put_json("live-state", "orphan-state", {"state_id": "orphan-state"})
        called = []
        with self.assertRaisesRegex(
            CloudLoopReviewRequired, "LEDGER_STATE_RESULT_COVERAGE_MISMATCH"
        ):
            run_cloud_step(
                tick_ms=1320000, previous_slot="0", store=store,
                feed=NeverCalledFeed(),
                market_supplier=lambda: called.append(True) or {},
                candidate_supplier=lambda market, state: [],
                strategy_registry=REGISTRY, before_external=lambda: None,
            )
        self.assertEqual(called, [])

    def test_latest_committed_slot_is_required_after_restart(self):
        store = MemoryStore()
        step(store, 420000, None)
        called = []
        with self.assertRaisesRegex(CloudLoopReviewRequired, "PREVIOUS_SLOT_REQUIRED"):
            run_cloud_step(
                tick_ms=1320000, previous_slot=None, store=store,
                feed=NeverCalledFeed(),
                market_supplier=lambda: called.append(True) or {},
                candidate_supplier=lambda market, state: [],
                strategy_registry=REGISTRY, before_external=lambda: None,
            )
        self.assertEqual(called, [])

    def test_stale_predecessor_cannot_skip_latest_commit(self):
        store = MemoryStore()
        step(store, 420000, None)
        step(store, 1320000, "0")
        called = []
        with self.assertRaisesRegex(CloudLoopReviewRequired, "PREVIOUS_SLOT_MISMATCH"):
            run_cloud_step(
                tick_ms=2220000, previous_slot="0", store=store,
                feed=NeverCalledFeed(),
                market_supplier=lambda: called.append(True) or {},
                candidate_supplier=lambda market, state: [],
                strategy_registry=REGISTRY, before_external=lambda: None,
            )
        self.assertEqual(called, [])

    def test_missing_prior_commit_stops_before_market(self):
        store = MemoryStore()
        called = []
        with self.assertRaisesRegex(CloudLoopReviewRequired, "PREVIOUS_SLOT_MISMATCH"):
            run_cloud_step(
                tick_ms=1320000, previous_slot="0", store=store,
                feed=NeverCalledFeed(),
                market_supplier=lambda: called.append(True) or {},
                candidate_supplier=lambda market, state: [],
                strategy_registry=REGISTRY, before_external=lambda: None,
            )
        self.assertEqual(called, [])

TICK = 1_790_000_000_000

class TapeClient:
    def __init__(self, trades):
        self.trades = trades
        self.calls = []
    def get_order_book(self, symbol, *, limit):
        self.calls.append("book")
        return OrderBookSnapshot(symbol=symbol, bids=((100.0, 2.0),),
                                 asks=((101.0, 3.0),), update_time_ms=TICK-1000)
    def get_recent_trades(self, symbol, *, limit):
        self.calls.append(("trades", limit))
        return self.trades


def trade(identifier, time_ms):
    return PublicTrade(symbol="BTC_USDT_PERP", trade_id=str(identifier),
                       price=100.0, size=1.0, side="BUY", time_ms=time_ms)


class CompleteTapeFeedTests(unittest.TestCase):
    def test_full_since_window_builds_frame_with500_limit(self):
        client = TapeClient([trade(1, TICK-2000), trade(2, TICK-500)])
        feed = CompleteTapePionexFeed(
            client=client, policy=LivePaperPolicy(), before_request=lambda: None)
        frame = feed.fetch_frame("BTC_USDT_PERP", tick_time_ms=TICK,
                                 since_ms=TICK-1000)
        self.assertEqual(frame.source_trade_count, 1)
        self.assertEqual(frame.provider_request_count, 2)
        self.assertEqual(client.calls[1], ("trades", 500))

    def test_gap_and_saturated_pages_fail_closed(self):
        for rows, reason in (
            ([trade(1, TICK-500)], "TRADE_TAPE_GAP"),
            ([trade(i, TICK-i) for i in range(500)], "TRADE_TAPE_PAGE_SATURATED"),
        ):
            feed = CompleteTapePionexFeed(
                client=TapeClient(rows), policy=LivePaperPolicy(),
                before_request=lambda: None)
            with self.assertRaisesRegex(CloudLoopReviewRequired, reason):
                feed.fetch_frame("BTC_USDT_PERP", tick_time_ms=TICK,
                                 since_ms=TICK-1000)

    def test_budget_guard_runs_before_each_provider_request(self):
        client = TapeClient([])
        calls = []
        def reject():
            calls.append("budget")
            if len(calls) == 2:
                raise CloudLoopReviewRequired("BLOCKED_BUDGET")
        feed = CompleteTapePionexFeed(
            client=client, policy=LivePaperPolicy(), before_request=reject)
        with self.assertRaisesRegex(CloudLoopReviewRequired, "BLOCKED_BUDGET"):
            feed.fetch_frame("BTC_USDT_PERP", tick_time_ms=TICK, since_ms=TICK-1000)
        self.assertEqual(client.calls, ["book"])
