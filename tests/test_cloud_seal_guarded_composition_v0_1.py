from __future__ import annotations

import copy
import unittest

from crypto_autopilot.paper.cloud_loop_v0_1 import CloudLoopReviewRequired, SLOT_MS
from crypto_autopilot.paper.cloud_seal_guarded_composition_v0_1 import (
    build_seal_guarded_composition,
)
from test_cloud_paper_composition_v0_1 import (
    FakeClient, MemoryStore, NOW, composition, make_budget_guard,
)


class GuardedCompositionTests(unittest.TestCase):
    def test_disabled_does_not_touch_store_or_provider(self):
        client, store = FakeClient(), MemoryStore()
        base = composition(client, store)
        self.assertIsNone(build_seal_guarded_composition(base))
        self.assertEqual(store.calls, [])
        self.assertEqual(client.calls, [])

    def test_no_trade_and_continuation_use_budgeted_seal_checks(self):
        client, store = FakeClient(), MemoryStore()
        first = build_seal_guarded_composition(composition(client, store), enabled=True)
        result = first.run_slot(
            tick_ms=NOW, previous_slot=None, activation_enabled=True, run_id="fixture-1",
        )
        self.assertEqual(result["state"], "NO_TRADE")
        self.assertEqual(result["account"]["initial_equity_usd"], 10000)

        guard = make_budget_guard(now_ms=NOW + SLOT_MS)
        store.budget_guard = guard
        store.calls.clear()
        second = build_seal_guarded_composition(
            composition(client, store, guard=guard), enabled=True,
        )
        resumed = second.run_slot(
            tick_ms=NOW + SLOT_MS, previous_slot=result["slot_id"],
            activation_enabled=True, run_id="fixture-2",
        )
        self.assertEqual(resumed["state"], "NO_TRADE")
        self.assertEqual(resumed["account"]["initial_equity_usd"], 10000)
        reads = [call for call in store.calls if call[0] == "get"]
        self.assertEqual(guard.attempted_usage().class_b_requests, len(reads))
        self.assertTrue(any(call[1] == "live-run-result" for call in reads))
        self.assertEqual(client.calls, [])

    def test_tampered_prior_seal_stops_before_next_slot_writes(self):
        client, store = FakeClient(), MemoryStore()
        first = build_seal_guarded_composition(composition(client, store), enabled=True)
        result = first.run_slot(
            tick_ms=NOW, previous_slot=None, activation_enabled=True, run_id="fixture-1",
        )
        run_step = store.objects[("live-run-step", result["coordinator"]["step_id"])]
        store.objects[("live-run-result", run_step["request_id"])]["run_id"] = "wrong-run"
        before = copy.deepcopy(store.objects)
        guard = make_budget_guard(now_ms=NOW + SLOT_MS)
        store.budget_guard = guard
        store.calls.clear()
        second = build_seal_guarded_composition(
            composition(client, store, guard=guard), enabled=True,
        )
        with self.assertRaisesRegex(CloudLoopReviewRequired, "COORDINATOR_SEAL_INVALID"):
            second.run_slot(
                tick_ms=NOW + SLOT_MS, previous_slot=result["slot_id"],
                activation_enabled=True, run_id="fixture-2",
            )
        self.assertEqual(store.objects, before)
        self.assertFalse(any(call[0].startswith("put") for call in store.calls))
        self.assertEqual(client.calls, [])


if __name__ == "__main__":
    unittest.main()
