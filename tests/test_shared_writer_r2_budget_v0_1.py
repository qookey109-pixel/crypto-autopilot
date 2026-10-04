from __future__ import annotations

import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace

from crypto_autopilot.paper.cloud_budget_v0_1 import (
    BudgetBlocked, CloudBudgetGuard, R2UsageSnapshot,
)
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import SharedWriterReservation
from crypto_autopilot.paper.shared_writer_r2_budget_v0_1 import SharedWriterR2Budget

NOW = 1_800_000_000_000


@dataclass
class Result:
    rows: tuple[dict[str, object], ...]


class Meter:
    def __init__(self):
        self.charges = []

    def charge_before_query(self, *, writer_id, slot_id, operation):
        self.charges.append((writer_id, slot_id, operation))
        return "CHARGED"


class Backend:
    def __init__(self):
        self.calls = 0

    def put_object(self, **kwargs):
        self.calls += 1
        raise RuntimeError("transport failed")


class SharedR2BudgetTests(unittest.TestCase):
    def fixture(self):
        snapshot = R2UsageSnapshot(
            account_wide=True, reservation_coverage_complete=True,
            observed_at_ms=NOW, measured_through_ms=NOW, storage_bytes=0,
            class_a_month=0, class_b_month=0, class_a_31_days=0, class_b_31_days=0,
            class_a_day=0, class_b_day=0, provider_requests_day=0, new_bytes_day=0,
        )
        clock = [NOW]
        guard = CloudBudgetGuard(snapshot=snapshot, clock_ms=lambda: clock[0])
        reservation = SharedWriterReservation(
            writer_id="repo:writer", slot_id=f"slot:{NOW}", idempotency_key=f"slot:{NOW}",
            slot_at_ms=NOW, reserved_at_ms=NOW, provider_requests=0,
            r2_class_a=1, r2_class_b=1, r2_new_bytes=4,
            d1_queries=4, d1_rows_read=100, d1_rows_written=10,
            d1_storage_growth_bytes=100,
        )
        meter = Meter()
        calls = []
        def execute(sql, params):
            calls.append(sql)
            return Result(({"writer_id": reservation.writer_id,
                            "slot_id": reservation.slot_id},))
        return guard, reservation, meter, calls, execute, clock

    def admit(self, fixture):
        guard, reservation, meter, calls, execute, clock = fixture
        return SharedWriterR2Budget.admit(
            reservation=reservation, guard=guard, execute=execute,
            query_meter=meter, validate_binding=lambda: None,
        )

    def test_admission_then_attempt_caps(self):
        fixture = self.fixture()
        budget = self.admit(fixture)
        self.assertEqual(len(fixture[3]), 1)
        self.assertEqual(len(fixture[2].charges), 1)
        budget.reserve("R2_CLASS_A", 4)
        budget.reserve("R2_CLASS_B")
        with self.assertRaisesRegex(BudgetBlocked, "EXHAUSTED"):
            budget.reserve("R2_CLASS_A")
        self.assertEqual(budget.attempted_usage(),
                         {"r2_class_a": 1, "r2_class_b": 1, "r2_new_bytes": 4})

    def test_existing_reservation_never_reopens_r2(self):
        guard, reservation, meter, calls, _, clock = self.fixture()
        row = asdict(reservation)
        row["utc_day"] = reservation.utc_day
        def execute(sql, params):
            calls.append(sql)
            return Result(()) if len(calls) == 1 else Result((row,))
        with self.assertRaisesRegex(BudgetBlocked, "EXISTING_RESERVATION"):
            SharedWriterR2Budget.admit(
                reservation=reservation, guard=guard, execute=execute,
                query_meter=meter, validate_binding=lambda: None,
            )
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(meter.charges), 2)

    def test_stale_snapshot_and_bad_binding_precede_query(self):
        guard, reservation, meter, calls, execute, clock = self.fixture()
        clock[0] += 60_001
        with self.assertRaisesRegex(BudgetBlocked, "STALE"):
            SharedWriterR2Budget.admit(
                reservation=reservation, guard=guard, execute=execute,
                query_meter=meter, validate_binding=lambda: None,
            )
        self.assertEqual(calls, [])
        clock[0] = NOW
        def invalid():
            raise BudgetBlocked("binding changed")
        with self.assertRaisesRegex(BudgetBlocked, "binding"):
            SharedWriterR2Budget.admit(
                reservation=reservation, guard=guard, execute=execute,
                query_meter=meter, validate_binding=invalid,
            )
        self.assertEqual(calls, [])

    def test_failed_store_attempt_is_not_refunded_or_retried(self):
        budget = self.admit(self.fixture())
        backend = Backend()
        store = BudgetedR2Store(client=backend, bucket="fixture",
                                before_external=budget.reserve)
        with self.assertRaisesRegex(RuntimeError, "transport"):
            store.put_bytes("key", b"1234")
        with self.assertRaisesRegex(BudgetBlocked, "EXHAUSTED"):
            store.put_bytes("key", b"1234")
        self.assertEqual(backend.calls, 1)
        self.assertEqual(budget.attempted_usage()["r2_new_bytes"], 4)

    def test_parallel_callbacks_cannot_overspend(self):
        budget = self.admit(self.fixture())
        def attempt(_):
            try:
                budget.reserve("R2_CLASS_A", 1)
                return True
            except BudgetBlocked:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(attempt, range(8))), 1)

    def test_invalid_operations_bytes_and_expiry(self):
        fixture = self.fixture()
        budget = self.admit(fixture)
        for op, size in (("DELETE", 0), ("R2_CLASS_B", 1),
                         ("R2_CLASS_A", True), ("R2_CLASS_A", -1)):
            with self.subTest(op=op, size=size), self.assertRaises(BudgetBlocked):
                budget.reserve(op, size)
        self.assertEqual(budget.attempted_usage()["r2_class_a"], 0)
        fixture[-1][0] += 60_001
        with self.assertRaisesRegex(BudgetBlocked, "STALE"):
            budget.reserve("R2_CLASS_A")
        self.assertEqual(budget.attempted_usage()["r2_class_a"], 0)

    def test_post_admission_failure_retains_charge(self):
        guard, reservation, meter, calls, execute, clock = self.fixture()
        count = [0]
        def binding():
            count[0] += 1
            if count[0] == 2:
                raise BudgetBlocked("binding changed")
        with self.assertRaisesRegex(BudgetBlocked, "binding"):
            SharedWriterR2Budget.admit(
                reservation=reservation, guard=guard, execute=execute,
                query_meter=meter, validate_binding=binding,
            )
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(meter.charges), 1)

    def test_ledger_failure_keeps_prepaid_debit(self):
        guard, reservation, meter, calls, execute, clock = self.fixture()
        def fail(sql, params):
            calls.append(sql)
            raise RuntimeError("network")
        with self.assertRaisesRegex(BudgetBlocked, "UNVERIFIED"):
            SharedWriterR2Budget.admit(
                reservation=reservation, guard=guard, execute=fail,
                query_meter=meter, validate_binding=lambda: None,
            )
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(meter.charges), 1)

    def test_unknown_coverage_precedes_query(self):
        guard, reservation, meter, calls, execute, clock = self.fixture()
        guard.snapshot = replace(guard.snapshot, reservation_coverage_complete=False)
        with self.assertRaisesRegex(BudgetBlocked, "INCOMPLETE"):
            SharedWriterR2Budget.admit(
                reservation=reservation, guard=guard, execute=execute,
                query_meter=meter, validate_binding=lambda: None,
            )
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
