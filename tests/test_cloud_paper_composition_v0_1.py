from __future__ import annotations

import hashlib
import json
import unittest
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from unittest.mock import patch

from crypto_autopilot.features.market import OrderBookSnapshot
from crypto_autopilot.models import BookTicker, Candle, MarketTicker
from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import (
    D1LedgerUnavailable,
    D1SlotReservation,
    SlotUsage,
)
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
from crypto_autopilot.paper.cloud_loop_v0_1 import CloudLoopReviewRequired
from crypto_autopilot.paper.cloud_market_v0_1 import analyze_capture
from crypto_autopilot.paper.live_v0_1 import LivePaperPolicy
from crypto_autopilot.paper.run_store_v0_1 import PaperRunObjectAlreadyExistsError
from crypto_autopilot.risk import plan_position_size

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
        self.settlements = []
        self.slots = set()
        self.reservations_by_slot = {}
        self.recovery_receipts = {}

    def reserve_slot(self, *, slot_id, run_id, now_ms, snapshot):
        self.events.append("reservation")
        if self.reject or slot_id in self.slots:
            raise BudgetBlocked("BLOCKED_BUDGET_RESERVATION_REJECTED")
        self.slots.add(slot_id)
        self.reservations.append((slot_id, run_id, now_ms, snapshot))
        self.reservations_by_slot[slot_id] = D1SlotReservation(
            slot_id, run_id, now_ms, "RESERVED", SlotUsage(18, 128, 128, 2097152),
        )

    def settle_slot(self, *, slot_id, completed_at_ms, usage):
        self.events.append("settlement")
        if slot_id not in self.slots:
            raise BudgetBlocked("BLOCKED_BUDGET_SETTLEMENT_REVIEW_REQUIRED")
        self.settlements.append((slot_id, completed_at_ms, usage))
        current = self.reservations_by_slot[slot_id]
        self.reservations_by_slot[slot_id] = replace(current, state="SETTLED")

    def get_slot_reservation(self, *, slot_id):
        self.events.append("read-reservation")
        return self.reservations_by_slot.get(slot_id)

    def record_verified_result_recovery(
        self, *, slot_id, run_id, report_id, recovered_at_ms,
    ):
        self.events.append("recovery-receipt")
        value = (run_id, report_id, recovered_at_ms)
        existing = self.recovery_receipts.get(slot_id)
        if existing is not None and existing[:2] != value[:2]:
            raise BudgetBlocked("BLOCKED_BUDGET_RECOVERY_REVIEW_REQUIRED")
        if existing is None:
            self.recovery_receipts[slot_id] = value


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
        encoded = json.dumps(
            dict(payload), sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
        self._reserve("R2_CLASS_A", len(encoded))
        self.calls.append(("put", kind, object_id))
        key = (kind, object_id)
        if key in self.objects:
            if self.objects[key] != dict(payload):
                raise ValueError("immutable collision")
            return Receipt(True)
        self.objects[key] = dict(payload)
        return Receipt(False)

    def put_json_if_absent(self, kind, object_id, payload):
        encoded = json.dumps(
            dict(payload), sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
        self._reserve("R2_CLASS_A", len(encoded))
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

    class FakeD1UsageGuard:
        def validate_evidence(self):
            accesses.append("d1-evidence")

    usage_guard = (
        FakeD1UsageGuard()
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
        completion_clock_ms=lambda: NOW + 1,
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

        class RejectStaleEvidence:
            def validate_evidence(self):
                accesses.append("d1-evidence")
                raise BudgetBlocked("BLOCKED_D1_USAGE_EVIDENCE_STALE")

        reject_stale_evidence = RejectStaleEvidence()
        ledger = FakeReservationLedger(accesses)
        runtime = composition(
            client, store, accesses=accesses, reservation_ledger=ledger,
            d1_usage_guard=reject_stale_evidence,
        )
        with self.assertRaisesRegex(BudgetBlocked, "BLOCKED_D1_USAGE_EVIDENCE_STALE"):
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
        self.assertEqual(len(ledger.settlements), 1)
        settled_slot, completed_at, usage = ledger.settlements[0]
        self.assertEqual(settled_slot, slot)
        self.assertEqual(completed_at, NOW + 1)
        self.assertEqual(usage.provider_requests, 4)
        self.assertGreater(usage.class_a, 0)
        self.assertGreater(usage.class_b, 0)
        self.assertGreater(usage.new_bytes, 0)
        self.assertGreater(accesses.index("settlement"), accesses.index("reservation"))

    def test_restart_recovery_verifies_result_and_keeps_full_reservation(self):
        client, store, accesses = FakeClient(), MemoryStore(), []
        ledger = FakeReservationLedger(accesses)
        runtime = composition(
            client, store, accesses=accesses, reservation_ledger=ledger,
        )
        first = runtime.run_slot(
            tick_ms=NOW, previous_slot=None, activation_enabled=True,
            run_id="github-run-recovery",
        )
        self.assertEqual(first["state"], "NO_TRADE")
        slot = first["slot_id"]
        reserved = ledger.reservations_by_slot[slot]
        ledger.reservations_by_slot[slot] = replace(reserved, state="RESERVED")
        before_calls = list(store.calls)
        before_provider_calls = list(client.calls)

        recovery = runtime.recover_completed_slot(
            slot=slot, recovery_enabled=True,
        )

        self.assertEqual(recovery["state"], "RECOVERED_RESERVED_FULL")
        self.assertFalse(recovery["budget_released"])
        self.assertEqual(recovery["r2_writes_performed"], 0)
        self.assertEqual(ledger.reservations_by_slot[slot].state, "RESERVED")
        self.assertEqual(ledger.recovery_receipts[slot][0], "github-run-recovery")
        recovery_calls = store.calls[len(before_calls):]
        self.assertTrue(recovery_calls)
        self.assertTrue(all(call[0] == "get" for call in recovery_calls))
        self.assertEqual(client.calls, before_provider_calls)

    def test_recovery_defaults_disabled_and_missing_result_retains_reservation(self):
        client, store, accesses = FakeClient(), MemoryStore(), []
        ledger = FakeReservationLedger(accesses)
        runtime = composition(
            client, store, accesses=accesses, reservation_ledger=ledger,
        )
        disabled = runtime.recover_completed_slot(slot="0")
        self.assertEqual(disabled["state"], "DISABLED")
        self.assertEqual(store.calls, [])
        self.assertEqual(client.calls, [])

        slot = str((NOW - 7 * 60 * 1000) // (15 * 60 * 1000))
        ledger.slots.add(slot)
        ledger.reservations_by_slot[slot] = D1SlotReservation(
            slot, "reserved-run", NOW, "RESERVED", SlotUsage(18, 128, 128, 2097152),
        )
        with self.assertRaisesRegex(
            CloudPaperCompositionBlocked, "RECOVERY_RESULT_MISSING",
        ):
            runtime.recover_completed_slot(slot=slot, recovery_enabled=True)
        self.assertNotIn(slot, ledger.recovery_receipts)
        self.assertEqual(ledger.reservations_by_slot[slot].state, "RESERVED")

    def test_recovery_rejects_mismatched_immutable_result_pointer(self):
        client, store, accesses = FakeClient(), MemoryStore(), []
        ledger = FakeReservationLedger(accesses)
        runtime = composition(
            client, store, accesses=accesses, reservation_ledger=ledger,
        )
        first = runtime.run_slot(
            tick_ms=NOW, previous_slot=None, activation_enabled=True,
            run_id="github-run-pointer-mismatch",
        )
        slot = first["slot_id"]
        ledger.reservations_by_slot[slot] = replace(
            ledger.reservations_by_slot[slot], state="RESERVED",
        )
        pointer = dict(store.objects[("cloud-result", slot)])
        pointer["slot_id"] = "different-slot"
        store.objects[("cloud-result", slot)] = pointer

        with self.assertRaisesRegex(
            CloudLoopReviewRequired, "RESULT_POINTER_MISMATCH",
        ):
            runtime.recover_completed_slot(slot=slot, recovery_enabled=True)

        self.assertNotIn(slot, ledger.recovery_receipts)
        self.assertEqual(ledger.reservations_by_slot[slot].state, "RESERVED")

    def test_failed_settlement_keeps_reserved_slot_and_does_not_replay_io(self):
        class FailingSettlementLedger(FakeReservationLedger):
            def settle_slot(self, *, slot_id, completed_at_ms, usage):
                self.events.append("settlement")
                raise D1LedgerUnavailable("D1_LEDGER_REQUEST_FAILED")

        client, store, accesses = FakeClient(), MemoryStore(), []
        ledger = FailingSettlementLedger(accesses)
        runtime = composition(
            client, store, accesses=accesses, reservation_ledger=ledger,
        )
        with self.assertRaisesRegex(D1LedgerUnavailable, "D1_LEDGER_REQUEST_FAILED"):
            runtime.run_slot(
                tick_ms=NOW, previous_slot=None, activation_enabled=True,
                run_id="run-test",
            )
        self.assertEqual(len(ledger.reservations), 1)
        self.assertEqual(ledger.settlements, [])
        self.assertIn(ledger.reservations[0][0], ledger.slots)
        self.assertTrue(any(kind == "cloud-result" for kind, _ in store.objects))

    def test_duplicate_slot_rejected_before_provider_or_r2_replay(self):
        client, store, accesses = FakeClient(), MemoryStore(), []
        ledger = FakeReservationLedger(accesses)
        runtime = composition(
            client, store, accesses=accesses, reservation_ledger=ledger,
        )
        runtime.run_slot(
            tick_ms=NOW, previous_slot=None, activation_enabled=True,
            run_id="run-first",
        )
        provider_calls = len(client.calls)
        store_calls = len(store.calls)

        with self.assertRaisesRegex(BudgetBlocked, "RESERVATION_REJECTED"):
            runtime.run_slot(
                tick_ms=NOW, previous_slot=None, activation_enabled=True,
                run_id="run-replay",
            )

        self.assertEqual(len(ledger.reservations), 1)
        self.assertEqual(len(client.calls), provider_calls)
        self.assertEqual(len(store.calls), store_calls)

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

    def test_qualified_fixture_completes_entry_exit_and_no_trade_through_composition(self):
        symbol = "BTC_USDT_PERP"
        implementation_sha = "a" * 64
        family_validation = {
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
        }

        def canonical_sha(payload):
            encoded = json.dumps(
                payload, sort_keys=True, separators=(",", ":"),
                ensure_ascii=True, allow_nan=False,
            ).encode("utf-8")
            return hashlib.sha256(encoded).hexdigest()

        qualification = {
            "state": "PAPER_ELIGIBLE",
            "receipt_path": "research/receipts/test-only-candidate-qualification.json",
            "receipt_sha256": "b" * 64,
            "implementation_sha256": implementation_sha,
            "family_validation_report_sha256": canonical_sha(family_validation),
            "paper_execution_authorized": True,
            "holdout_accessed": False,
            "source_switch_authorized": False,
            "model_promotion_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        }
        registry = {
            "schema": "qookey-cloud-paper-strategy-registry-v0.1",
            "status": "QUALIFIED_PAPER_STRATEGIES_AVAILABLE",
            "provider": "PIONEX_PUBLIC",
            "strategies": [{
                "strategy_id": "test-only-trend",
                "strategy_family": "TREND_FOLLOWING",
                "provider": "PIONEX_PUBLIC",
                "symbols": [symbol],
                "regimes": ["ALT_EXPANSION"],
                "implementation_sha256": implementation_sha,
                "model_dependency": "NONE",
                "qualification": qualification,
            }],
            "model_quality": "REJECT",
            "production_fixture_admission": False,
            "automatic_promotion": False,
        }

        class MovingClient(FakeClient):
            def __init__(self):
                super().__init__()
                self.tick_ms = NOW

            def list_perpetual_book_tickers(self):
                self.calls.append("books")
                return [
                    BookTicker(
                        symbol=s, bid_price=340, bid_size=10,
                        ask_price=340.1, ask_size=10, timestamp_ms=self.tick_ms,
                    )
                    for s in (symbol, "UNKNOWNX_USDT_PERP")
                ]

            def get_order_book(self, requested_symbol, *, limit):
                self.calls.append(("depth", requested_symbol, limit))
                bid, ask = ((340.0, 340.1) if self.tick_ms == NOW
                            else (346.0, 346.1))
                return OrderBookSnapshot(
                    symbol=requested_symbol,
                    bids=((bid, 10.0),), asks=((ask, 10.0),),
                    update_time_ms=self.tick_ms,
                )

            def get_recent_trades(self, requested_symbol, *, limit):
                self.calls.append(("trades", requested_symbol, limit))
                return []

        client, store, accesses = MovingClient(), MemoryStore(), []
        base_analyze = analyze_capture
        emit_candidate = True

        def analyzed_fixture(capture, *, allowed_base_assets):
            nonlocal emit_candidate
            market = base_analyze(
                capture, allowed_base_assets=allowed_base_assets,
            )
            evidence = market["market_evidence"].get(symbol)
            if not isinstance(evidence, dict):
                raise AssertionError("synthetic cycle requires captured BTC evidence")
            route = {
                "symbol": symbol,
                "status": "ROUTE_MATCHED",
                "regime_state": "ALT_EXPANSION",
                "matches": [{
                    "family": "TREND_FOLLOWING",
                    "direction": "LONG",
                    "regime_state": "ALT_EXPANSION",
                    "reasons": ["synthetic CI route"],
                }],
            }
            market["context_status"] = "AVAILABLE"
            market["routes"] = [route]
            market["candidate_specs"] = []
            if emit_candidate:
                entry, stop = 340.0, 339.0
                market["candidate_specs"] = [{
                    "candidate": {
                        "strategy_id": "test-only-trend",
                        "symbol": symbol,
                        "strategy_family": "TREND_FOLLOWING",
                        "direction": "LONG",
                        "regime_state": "ALT_EXPANSION",
                        "provider": "PIONEX_PUBLIC",
                        "as_of_ms": evidence["last_bar_ms"],
                        "market_evidence_sha256": evidence["sha256"],
                        "strategy_route_sha256": canonical_sha(route),
                        "qualification_receipt_sha256": qualification["receipt_sha256"],
                        "strategy_implementation_sha256": implementation_sha,
                        "entry_price": entry,
                        "stop_price": stop,
                        "family_validation_report": family_validation,
                        "position_sizing_plan": asdict(plan_position_size(
                            direction="LONG", equity_usd=10_000.0,
                            entry_price=entry, stop_price=stop,
                        )),
                    },
                    "target_price": 345.0,
                }]
                emit_candidate = False
            return market

        runtime = composition(
            client, store, registry=registry, accesses=accesses,
        )
        with patch(
            "crypto_autopilot.paper.cloud_composition_v0_1.analyze_capture",
            side_effect=analyzed_fixture,
        ):
            first = runtime.run_slot(
                tick_ms=NOW, previous_slot=None, activation_enabled=True,
                run_id="synthetic-entry",
            )
            self.assertEqual(first["state"], "COMMITTED")
            self.assertEqual(first["candidate_count"], 1)
            self.assertEqual(first["market"]["execution_selection_status"], "READY")
            self.assertEqual(first["account"]["initial_equity_usd"], 10_000.0)
            self.assertEqual(first["account"]["open_position_count"], 1)

            client.tick_ms = NOW + 15 * 60 * 1000
            second = runtime.run_slot(
                tick_ms=client.tick_ms, previous_slot=first["slot_id"],
                activation_enabled=True, run_id="synthetic-exit",
            )
            self.assertEqual(second["state"], "COMMITTED")
            self.assertEqual(second["account"]["open_position_count"], 0)
            self.assertGreater(
                second["account"]["realized_closed_net_pnl_usd"], 0,
            )

            client.tick_ms = NOW + 30 * 60 * 1000
            third = runtime.run_slot(
                tick_ms=client.tick_ms, previous_slot=second["slot_id"],
                activation_enabled=True, run_id="synthetic-no-trade",
            )
        self.assertEqual(third["state"], "NO_TRADE")
        self.assertEqual(third["candidate_count"], 0)
        self.assertEqual(third["coordinator"]["sequence"], 3)
        self.assertEqual(third["account"]["open_position_count"], 0)
        self.assertTrue(any(kind == "cloud-report" for kind, _ in store.objects))
        self.assertTrue(any(kind == "cloud-result" for kind, _ in store.objects))
        self.assertEqual(
            len([event for event in accesses if event == "settlement"]), 3,
        )

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
