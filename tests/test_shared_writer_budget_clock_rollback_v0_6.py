"""Synthetic regression: a backward clock step after commit must not release work."""
import unittest

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.shared_writer_budget_gate_v0_6 import reserve_shared_writer_envelope
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

    def test_clock_rollback_after_debit_blocks_before_sql(self):
        fixture = SharedWriterBudgetGateTests("test_rolling_cap_is_account_shared")
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        reservation = fixture.reservation("project-a:writer", NOW_MS)
        current = [NOW_MS + 100]
        charge = fixture.meter.charge_before_query
        def clock_back_on_charge(**kwargs):
            result = charge(**kwargs)
            current[0] = NOW_MS + 50
            return result
        fixture.meter.charge_before_query = clock_back_on_charge
        with self.assertRaises(BudgetBlocked):
            reserve_shared_writer_envelope(
                execute=fixture.query, query_meter=fixture.meter,
                reservation=reservation, clock_ms=lambda: current[0],
                execution_enabled=True,
            )
        self.assertEqual(fixture.query.calls, 0)
        self.assertEqual(len(fixture.meter.charges), 1)

    def test_nondecreasing_clock_keeps_reservation_and_replay(self):
        fixture = SharedWriterBudgetGateTests("test_rolling_cap_is_account_shared")
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        reservation = fixture.reservation("project-a:writer", NOW_MS)
        kwargs = dict(execute=fixture.query, query_meter=fixture.meter,
                      reservation=reservation, clock_ms=lambda: NOW_MS,
                      execution_enabled=True)
        self.assertEqual(reserve_shared_writer_envelope(**kwargs), "RESERVED")
        self.assertEqual(reserve_shared_writer_envelope(**kwargs), "EXISTING_RESERVATION")

    def test_default_disabled_before_clock_or_query(self):
        fixture = SharedWriterBudgetGateTests("test_rolling_cap_is_account_shared")
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        reservation = fixture.reservation("project-a:writer", NOW_MS)
        def forbidden_clock():
            raise AssertionError("clock must not be called")
        with self.assertRaisesRegex(BudgetBlocked, "EXECUTION_DISABLED"):
            reserve_shared_writer_envelope(
                execute=fixture.query, query_meter=fixture.meter,
                reservation=reservation, clock_ms=forbidden_clock,
            )
        self.assertEqual(fixture.query.calls, 0)
        self.assertEqual(fixture.meter.charges, [])
