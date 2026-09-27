from __future__ import annotations

import unittest
from dataclasses import dataclass

from crypto_autopilot.paper.cloud_loop_v0_1 import (
    CloudLoopReviewRequired, run_cloud_step, slot_id,
)
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
        self.assertEqual(first["coordinator"]["provider_requests_performed"], 0)
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
