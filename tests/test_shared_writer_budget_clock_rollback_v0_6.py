"""Synthetic regression: a backward clock step after commit must not release work."""
import unittest

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import reserve_shared_writer_envelope
from test_shared_writer_budget_gate_v0_4 import NOW_MS, SharedWriterBudgetGateTests


class ClockRollbackTests(unittest.TestCase):
    def test_backward_clock_after_commit_blocks_and_preserves_charge_and_row(self):
        fixture = SharedWriterBudgetGateTests("test_rolling_cap_is_account_shared")
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        reservation = fixture.reservation("project-a:writer", NOW_MS)
        current = [NOW_MS + 100]
        def query_then_clock_back(sql, params):
            result = fixture.query(sql, params)
            current[0] = NOW_MS + 50
            return result
        with self.assertRaises(BudgetBlocked):
            reserve_shared_writer_envelope(
                execute=query_then_clock_back, query_meter=fixture.meter,
                reservation=reservation, clock_ms=lambda: current[0],
                execution_enabled=True,
            )
        self.assertEqual(fixture.query.calls, 1)
        self.assertEqual(len(fixture.meter.charges), 1)
        self.assertEqual(fixture.db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0], 1)
