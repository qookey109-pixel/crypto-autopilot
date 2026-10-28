from __future__ import annotations

import copy
import unittest
from dataclasses import replace

from crypto_autopilot.paper.cloud_loop_v0_1 import CloudLoopReviewRequired, SLOT_MS, slot_id
from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.cloud_seal_guarded_composition_v0_1 import (
    build_seal_guarded_composition,
)
from test_cloud_paper_composition_v0_1 import (
    FakeClient, FakeReservationLedger, MemoryStore, NOW, composition, make_budget_guard,
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


    def test_expired_guard_stops_before_extra_read_or_settlement(self):
        client, store = FakeClient(), MemoryStore()
        first = build_seal_guarded_composition(composition(client, store), enabled=True)
        result = first.run_slot(
            tick_ms=NOW, previous_slot=None, activation_enabled=True, run_id="fixture-1",
        )
        guard = make_budget_guard(now_ms=NOW + SLOT_MS)
        store.budget_guard = guard
        store.calls.clear()
        ledger = FakeReservationLedger()

        def stop_after_seal_read():
            if store.calls and store.calls[-1][0:2] == ("get", "live-run-result"):
                raise BudgetBlocked("FIXTURE_GUARD_EXPIRED")

        base = replace(
            composition(client, store, guard=guard, reservation_ledger=ledger),
            before_external=stop_after_seal_read,
        )
        runtime = build_seal_guarded_composition(base, enabled=True)
        before = copy.deepcopy(store.objects)
        with self.assertRaisesRegex(BudgetBlocked, "FIXTURE_GUARD_EXPIRED"):
            runtime.run_slot(
                tick_ms=NOW + SLOT_MS, previous_slot=result["slot_id"],
                activation_enabled=True, run_id="fixture-2",
            )
        self.assertEqual(store.calls[-1][0:2], ("get", "live-run-result"))
        self.assertEqual(store.objects, before)
        self.assertFalse(any(call[0].startswith("put") for call in store.calls))
        self.assertEqual(len(ledger.reservations), 1)
        self.assertEqual(ledger.settlements, [])

    def test_tampered_seal_prevents_recovery_receipt(self):
        class FailedSettlementLedger(FakeReservationLedger):
            def settle_slot(self, **kwargs):
                raise BudgetBlocked("FIXTURE_SETTLEMENT_FAILED")

        client, store, ledger = FakeClient(), MemoryStore(), FailedSettlementLedger()
        runtime = build_seal_guarded_composition(
            composition(client, store, reservation_ledger=ledger), enabled=True,
        )
        with self.assertRaisesRegex(BudgetBlocked, "FIXTURE_SETTLEMENT_FAILED"):
            runtime.run_slot(
                tick_ms=NOW, previous_slot=None, activation_enabled=True, run_id="fixture",
            )
        slot = slot_id(NOW)
        pointer = store.objects[("cloud-result", slot)]
        report = store.objects[("cloud-report", pointer["report_id"])]
        run_step = store.objects[("live-run-step", report["coordinator"]["step_id"])]
        store.objects[("live-run-result", run_step["request_id"])]["run_id"] = "wrong-run"
        before = copy.deepcopy(store.objects)
        store.calls.clear()
        with self.assertRaisesRegex(CloudLoopReviewRequired, "COORDINATOR_SEAL_INVALID"):
            runtime.recover_completed_slot(slot=slot, recovery_enabled=True)
        self.assertEqual(ledger.recovery_receipts, {})
        self.assertEqual(store.objects, before)
        self.assertFalse(any(call[0].startswith("put") for call in store.calls))


if __name__ == "__main__":
    unittest.main()
