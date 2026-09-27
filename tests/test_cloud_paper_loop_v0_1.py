from __future__ import annotations

import unittest
from dataclasses import dataclass

from crypto_autopilot.features.market import OrderBookSnapshot, PublicTrade
from crypto_autopilot.paper.cloud_loop_v0_1 import (
    CloudLoopReviewRequired,
    CompleteTapePionexFeed,
    run_cloud_step,
    slot_id,
)
from crypto_autopilot.paper.live_v0_1 import LivePaperPolicy
from crypto_autopilot.paper.run_store_v0_1 import PaperRunObjectAlreadyExistsError


@dataclass
class Receipt:
    replayed: bool


class MemoryStore:
    def __init__(self):
        self.objects = {}

    def get_json(self, kind, object_id):
        return self.objects.get((kind, object_id))

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
        self.assertEqual(first["operation_counts"]["r2_write_attempts"], 9)
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
                feed=NeverCalledFeed(), market_supplier=lambda: {},
                candidate_supplier=inject, strategy_registry=REGISTRY,
                before_external=lambda: None,
            )

    def test_missing_prior_commit_stops_before_market(self):
        store = MemoryStore()
        called = []
        with self.assertRaisesRegex(CloudLoopReviewRequired, "PREVIOUS_RESULT"):
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
