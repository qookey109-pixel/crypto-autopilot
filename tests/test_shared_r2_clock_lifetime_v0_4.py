"""Regression: clock rollback after admission must not release an R2 call."""
import unittest

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.shared_writer_r2_budget_v0_3 import SharedWriterR2BudgetV06
from test_shared_writer_r2_budget_v0_1 import Backend, NOW, SharedR2BudgetTests


class R2AdmissionClockLifetimeTests(unittest.TestCase):
    def test_clock_rollback_before_r2_is_blocked_without_refund(self):
        fixture = SharedR2BudgetTests().fixture()
        guard, reservation, meter, calls, execute, clock = fixture
        clock[0] = NOW + 100
        budget = SharedWriterR2BudgetV06.admit(
            reservation=reservation, guard=guard, execute=execute,
            query_meter=meter, validate_binding=lambda: None, execution_enabled=True,
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(meter.charges), 1)
        clock[0] = NOW + 50
        backend = Backend()
        store = BudgetedR2Store(client=backend, bucket="fixture", before_external=budget.reserve)
        with self.assertRaises(BudgetBlocked):
            store.put_bytes("key", b"1")
        self.assertEqual(backend.calls, 0)
        self.assertEqual(len(meter.charges), 1)
