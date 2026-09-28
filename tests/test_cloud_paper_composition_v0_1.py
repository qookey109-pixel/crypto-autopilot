from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import UTC, datetime

from crypto_autopilot.models import BookTicker, Candle, MarketTicker
from crypto_autopilot.paper.cloud_budget_v0_1 import (
    BudgetBlocked,
    CloudBudgetGuard,
    CloudBudgetPolicy,
    R2UsageSnapshot,
)
from crypto_autopilot.paper.cloud_composition_v0_1 import (
    CloudPaperCompositionBlocked,
    CloudPaperNoTradeComposition,
)
from crypto_autopilot.paper.live_v0_1 import LivePaperPolicy
from crypto_autopilot.paper.run_store_v0_1 import PaperRunObjectAlreadyExistsError

NOW = int(datetime(2026, 9, 27, 8, 7, tzinfo=UTC).timestamp() * 1000)
HOUR_MS = 3_600_000


def bars():
    end = NOW // HOUR_MS * HOUR_MS
    return [
        Candle(
            time_ms=end - (240 - i) * HOUR_MS,
            open=100 + i, high=102 + i, low=99 + i,
            close=101 + i, volume=1000,
        )
        for i in range(240)
    ]


class FakeReservationLedger:
    def __init__(self, events=None, *, reject=False):
        self.events = events if events is not None else []
        self.reject = reject
        self.reservations = []
        self.slots = set()

    def reserve_slot(self, *, slot_id, run_id, now_ms, snapshot):
        self.events.append("reservation")
        if self.reject or slot_id in self.slots:
            raise BudgetBlocked("BLOCKED_BUDGET_RESERVATION_REJECTED")
        self.slots.add(slot_id)
        self.reservations.append((slot_id, run_id, now_ms, snapshot))


class FakeClient:
    def __init__(self):
        self.calls = []

    def list_perpetual_symbols(self):
        self.calls.append("symbols")
        return ["BTC_USDT_PERP", "UNKNOWNX_USDT_PERP"]

    def list_perpetual_tickers(self):
        self.calls.append("tickers")
        return [
            MarketTicker(symbol=s, close=340, base_volume=1000,
                         quote_amount=1_000_000, trade_count=100)
            for s in ("BTC_USDT_PERP", "UNKNOWNX_USDT_PERP")
        ]

    def list_perpetual_book_tickers(self):
        self.calls.append("books")
        return [
            BookTicker(symbol=s, bid_price=340, bid_size=10,
                       ask_price=340.1, ask_size=10, timestamp_ms=NOW)
            for s in ("BTC_USDT_PERP", "UNKNOWNX_USDT_PERP")
        ]

    def get_klines(self, symbol, interval, *, limit, end_time_ms):
        self.calls.append(("klines", symbol, interval, limit, end_time_ms))
        return bars()

    def get_order_book(self, symbol, *, limit):
        raise AssertionError("empty-registry no-trade path must not fetch a book")

    def get_recent_trades(self, symbol, *, limit):
        raise AssertionError("empty-registry no-trade path must not fetch trades")


@dataclass
class Receipt:
    replayed: bool


class MemoryStore:
    def __init__(self, budget_guard=None):
        self.objects = {}
        self.calls = []
        self.budget_guard = budget_guard

    def _reserve(self, operation, new_bytes=0):
        if self.budget_guard is not None:
            self.budget_guard.reserve(operation, new_bytes)

    def get_json(self, kind, object_id):
        self._reserve("R2_CLASS_B")
        self.calls.append(("get", kind, object_id))
        return self.objects.get((kind, object_id))

    def list_json_ids(self, kind):
        self._reserve("R2_CLASS_A")
        self.calls.append(("list", kind))
        return tuple(sorted(
            object_id for (stored_kind, object_id) in self.objects
            if stored_kind == kind
        ))

    def put_json(self, kind, object_id, payload):
        self._reserve("R2_CLASS_A")
        self.calls.append(("put", kind, object_id))
        key = (kind, object_id)
        if key in self.objects:
            if self.objects[key] != dict(payload):
                raise ValueError("immutable collision")
            return Receipt(True)
        self.objects[key] = dict(payload)
        return Receipt(False)

    def put_json_if_absent(self, kind, object_id, payload):
        self._reserve("R2_CLASS_A")
        self.calls.append(("put_if_absent", kind, object_id))
        key = (kind, object_id)
        if key in self.objects:
            raise PaperRunObjectAlreadyExistsError("already claimed")
        self.objects[key] = dict(payload)
        return Receipt(False)


REGISTRY = {
    "schema": "qookey-cloud-paper-strategy-registry-v0.1",
    "status": "EMPTY_NO_ELIGIBLE_STRATEGIES",
    "provider": "PIONEX_PUBLIC",
    "strategies": [],
    "model_quality": "REJECT",
    "production_fixture_admission": False,
    "automatic_promotion": False,
}


def make_budget_guard(policy=CloudBudgetPolicy()):
    now_ms = NOW
    return CloudBudgetGuard(
        snapshot=R2UsageSnapshot(
            account_wide=True,
            reservation_coverage_complete=True,
            observed_at_ms=now_ms,
            measured_through_ms=now_ms,
            storage_bytes=0,
            class_a_month=0,
            class_b_month=0,
            class_a_31_days=0,
            class_b_31_days=0,
            class_a_day=0,
            class_b_day=0,
            provider_requests_day=0,
            new_bytes_day=0,
        ),
        clock_ms=lambda: now_ms,
        policy=policy,
    )


def composition(
    client, store, registry=REGISTRY, guard=None, accesses=None,
    reservation_ledger="default", d1_usage_guard="default",
):
    guard = guard or make_budget_guard()
    if getattr(store, "budget_guard", None) is None:
        store.budget_guard = guard
    accesses = accesses if accesses is not None else []
    ledger = (
        FakeReservationLedger(accesses)
        if reservation_ledger == "default" else reservation_ledger
    )

    def default_d1_usage_guard(tick_ms):
        accesses.append("d1-evidence")

    usage_guard = (
        default_d1_usage_guard
        if d1_usage_guard == "default" else d1_usage_guard
    )
    return CloudPaperNoTradeComposition(
        client=client,
        store=store,
        strategy_registry=registry,
        allowed_base_assets=frozenset({"BTC"}),
        paper_policy=LivePaperPolicy(),
        budget_guard=guard,
        before_external=lambda: accesses.append("guard"),
        reservation_ledger=ledger,
        d1_usage_guard=usage_guard,
    )


class CloudPaperCompositionTests(unittest.TestCase):
    def test_disabled_is_side_effect_free(self):
        client, store, accesses = FakeClient(), MemoryStore(), []
        result = composition(client, store, accesses=accesses).run_slot(
            tick_ms=NOW, previous_slot=None,
        )
        self.assertEqual(result["state"], "DISABLED")
        self.assertEqual(result["reason"], "ACTIVATION_DISABLED")
        self.assertEqual(client.calls, [])
        self.assertEqual(store.calls, [])
        self.assertEqual(accesses, [])

    def test_nonempty_registry_fails_before_external_access(self):
        client, store, accesses = FakeClient(), MemoryStore(), []
        registry = {**REGISTRY, "status": "READY", "strategies": [{"strategy_id": "x"}]}
        runtime = composition(client, store, registry, accesses=accesses)
        with self.assertRaisesRegex(
            CloudPaperCompositionBlocked, "PRODUCTION_STRATEGY_AUTHORITY_UNAVAILABLE",
        ):
            runtime.run_slot(
                tick_ms=NOW, previous_slot=None, activation_enabled=True,
                run_id="run-test",
            )
        self.assertEqual(client.calls, [])
        self.assertEqual(store.calls, [])
        self.assertEqual(accesses, [])

    def test_mismatched_r2_guard_fails_before_any_external_access(self):
        client = FakeClient()
        store = MemoryStore(budget_guard=make_budget_guard())
        with self.assertRaisesRegex(
            CloudPaperCompositionBlocked, "R2_BUDGET_GUARD_NOT_BOUND",
        ):
            composition(client, store, guard=make_budget_guard())
        self.assertEqual(client.calls, [])
        self.assertEqual(store.calls, [])

    def test_missing_d1_budget_evidence_or_ledger_blocks_before_any_access(self):
        client, store, accesses = FakeClient(), MemoryStore(), []
        runtime = composition(
            client, store, accesses=accesses, reservation_ledger=None,
        )
        with self.assertRaisesRegex(
            CloudPaperCompositionBlocked, "D1_BUDGET_EVIDENCE_OR_LEDGER_MISSING",
        ):
            runtime.run_slot(
                tick_ms=NOW, previous_slot=None, activation_enabled=True,
                run_id="run-test",
            )
        self.assertEqual(client.calls, [])
        self.assertEqual(store.calls, [])
        self.assertEqual(accesses, [])

    def test_d1_usage_evidence_gate_runs_before_atomic_slot_reservation(self):
        client, store, accesses = FakeClient(), MemoryStore(), []

        def reject_stale_evidence(tick_ms):
            accesses.append("d1-evidence")
            raise BudgetBlocked("D1_USAGE_EVIDENCE_STALE")
        ledger = FakeReservationLedger(accesses)
        runtime = composition(
            client, store, accesses=accesses, reservation_ledger=ledger,
            d1_usage_guard=reject_stale_evidence,
        )
        with self.assertRaisesRegex(BudgetBlocked, "D1_USAGE_EVIDENCE_STALE"):
            runtime.run_slot(
                tick_ms=NOW, previous_slot=None, activation_enabled=True,
                run_id="run-test",
            )
        self.assertEqual(accesses, ["guard", "d1-evidence"])
        self.assertEqual(ledger.reservations, [])
        self.assertEqual(client.calls, [])
        self.assertEqual(store.calls, [])

    def test_atomic_slot_reservation_precedes_provider_and_r2(self):
        client, store, accesses = FakeClient(), MemoryStore(), []
        ledger = FakeReservationLedger(accesses)
        runtime = composition(
            client, store, accesses=accesses, reservation_ledger=ledger,
        )
        runtime.run_slot(
            tick_ms=NOW, previous_slot=None, activation_enabled=True,
            run_id="run-test",
        )
        self.assertEqual(accesses[:3], ["guard", "d1-evidence", "reservation"])
        self.assertEqual(len(ledger.reservations), 1)
        slot, run_id, now_ms, snapshot = ledger.reservations[0]
        self.assertEqual(run_id, "run-test")
        self.assertEqual(now_ms, NOW)
        self.assertIs(snapshot, runtime.budget_guard.snapshot)
        self.assertTrue(slot.isdigit())
        self.assertLess(accesses.index("reservation"), accesses.index("guard", 1))

    def test_rejected_atomic_reservation_prevents_provider_and_r2(self):
        client, store, accesses = FakeClient(), MemoryStore(), []
        ledger = FakeReservationLedger(accesses, reject=True)
        runtime = composition(
            client, store, accesses=accesses, reservation_ledger=ledger,
        )
        with self.assertRaisesRegex(BudgetBlocked, "RESERVATION_REJECTED"):
            runtime.run_slot(
                tick_ms=NOW, previous_slot=None, activation_enabled=True,
                run_id="run-test",
            )
        self.assertEqual(accesses, ["guard", "d1-evidence", "reservation"])
        self.assertEqual(client.calls, [])
        self.assertEqual(store.calls, [])

    def test_provider_limit_blocks_before_the_excess_market_request(self):
        client, accesses = FakeClient(), []
        guard = make_budget_guard(CloudBudgetPolicy(provider_per_run=3))
        runtime = composition(client, MemoryStore(), guard=guard, accesses=accesses)
        with self.assertRaisesRegex(BudgetBlocked, "PROVIDER_RUN_LIMIT"):
            runtime.run_slot(
                tick_ms=NOW, previous_slot=None, activation_enabled=True,
                run_id="run-test",
            )
        self.assertEqual(len(client.calls), 3)

    def test_enabled_empty_registry_composes_to_audited_no_trade(self):
        client, store, accesses = FakeClient(), MemoryStore(), []
        result = composition(client, store, accesses=accesses).run_slot(
            tick_ms=NOW, previous_slot=None, activation_enabled=True,
            run_id="run-test",
        )
        self.assertEqual(result["state"], "NO_TRADE")
        self.assertEqual(result["reason_codes"], [
            "REGIME_UNAVAILABLE", "NO_ELIGIBLE_STRATEGY",
        ])
        self.assertEqual(result["market"]["provider"], "PIONEX_PUBLIC")
        self.assertEqual(result["market"]["candidate_specs"], [])
        self.assertEqual(result["operation_counts"]["provider_requests"], 4)
        self.assertEqual(len(client.calls), 4)
        self.assertTrue(store.calls)
        self.assertTrue(accesses)
        self.assertTrue(any(kind == "cloud-report" for kind, _ in store.objects))
        self.assertTrue(any(kind == "cloud-result" for kind, _ in store.objects))


if __name__ == "__main__":
    unittest.main()
