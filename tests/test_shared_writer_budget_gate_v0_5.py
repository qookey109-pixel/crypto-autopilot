"""Synthetic regression for shared budget V0.5 timestamp ordering."""
import unittest
from dataclasses import replace

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from test_shared_writer_budget_gate_v0_4 import NOW_MS, SharedWriterBudgetGateTests

try:
    from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import reserve_shared_writer_envelope
except ModuleNotFoundError as exc:
    if exc.name != "crypto_autopilot.paper.shared_writer_budget_gate_v0_5":
        raise
    reserve_shared_writer_envelope = None


class RollingOrderTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(reserve_shared_writer_envelope)
        self.f = SharedWriterBudgetGateTests("test_rolling_cap_is_account_shared")
        self.f.setUp()
        self.addCleanup(self.f.tearDown)

    def test_later_timestamp_committed_first_counts_towards_cap(self):
        self.f.db.execute(
            "UPDATE cloudflare_shared_writer_budget_policy_v0_4 "
            "SET r2_class_a_per_rolling_31_days=1, r2_class_a_per_utc_day=10"
        )
        later = self.f.reservation("project-b:writer", NOW_MS + 1000)
        earlier = self.f.reservation("project-a:writer", NOW_MS)
        reserve_shared_writer_envelope(
            execute=self.f.query, query_meter=self.f.meter, reservation=later,
            clock_ms=lambda: later.reserved_at_ms,
        )
        with self.assertRaisesRegex(BudgetBlocked, "POLICY_OR_WRITER_GATE"):
            reserve_shared_writer_envelope(
                execute=self.f.query, query_meter=self.f.meter, reservation=earlier,
                clock_ms=lambda: later.reserved_at_ms,
            )
        self.assertEqual(self.f.db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0], 1)

    def test_previous_day_delayed_reservation_is_blocked(self):
        self.f.db.execute(
            "UPDATE cloudflare_shared_writer_budget_policy_v0_4 "
            "SET r2_class_a_per_rolling_31_days=1, r2_class_a_per_utc_day=10"
        )
        boundary = (NOW_MS // 86_400_000 + 1) * 86_400_000
        later = self.f.reservation("project-b:writer", boundary + 1000)
        earlier = self.f.reservation("project-a:writer", boundary - 1000)
        reserve_shared_writer_envelope(
            execute=self.f.query, query_meter=self.f.meter, reservation=later,
            clock_ms=lambda: later.reserved_at_ms,
        )
        with self.assertRaisesRegex(BudgetBlocked, "TIME_INVALID"):
            reserve_shared_writer_envelope(
                execute=self.f.query, query_meter=self.f.meter, reservation=earlier,
                clock_ms=lambda: later.reserved_at_ms,
            )

    def test_prior_day_slot_with_current_day_reservation_is_blocked(self):
        boundary = (NOW_MS // 86_400_000 + 1) * 86_400_000
        reservation = self.f.reservation("project-a:writer", boundary - 1000)
        reservation = replace(reservation, reserved_at_ms=boundary + 1000)
        with self.assertRaisesRegex(BudgetBlocked, "TIME_INVALID"):
            reserve_shared_writer_envelope(
                execute=self.f.query, query_meter=self.f.meter, reservation=reservation,
                clock_ms=lambda: boundary + 1000,
            )
        self.assertEqual(self.f.query.calls, 0)
        self.assertEqual(self.f.meter.charges, [])

    def test_future_and_stale_timestamps_reject_before_query(self):
        for value in (NOW_MS + 32 * 86_400_000, NOW_MS - 600_001):
            reservation = self.f.reservation("project-a:writer", value)
            with self.subTest(value=value), self.assertRaisesRegex(BudgetBlocked, "TIME_INVALID"):
                reserve_shared_writer_envelope(
                    execute=self.f.query, query_meter=self.f.meter, reservation=reservation,
                    clock_ms=lambda: NOW_MS,
                )
        self.assertEqual(self.f.query.calls, 0)
        self.assertEqual(self.f.meter.charges, [])

    def test_crossing_midnight_after_debit_blocks_before_sql(self):
        boundary = (NOW_MS // 86_400_000 + 1) * 86_400_000
        current = [boundary - 1]
        reservation = self.f.reservation("project-a:writer", current[0])
        charge = self.f.meter.charge_before_query
        def crossing_meter(**kwargs):
            result = charge(**kwargs)
            current[0] += 2
            return result
        self.f.meter.charge_before_query = crossing_meter
        with self.assertRaisesRegex(BudgetBlocked, "RESERVATION_UNVERIFIED"):
            reserve_shared_writer_envelope(
                execute=self.f.query, query_meter=self.f.meter, reservation=reservation,
                clock_ms=lambda: current[0],
            )
        self.assertEqual(self.f.query.calls, 0)
        self.assertEqual(len(self.f.meter.charges), 1)

    def test_late_sql_result_keeps_insert_and_does_not_authorize_work(self):
        current = [NOW_MS]
        reservation = self.f.reservation("project-a:writer", NOW_MS)
        def late_result(sql, params):
            result = self.f.query(sql, params)
            current[0] += 600_001
            return result
        with self.assertRaisesRegex(BudgetBlocked, "RESERVATION_UNVERIFIED"):
            reserve_shared_writer_envelope(
                execute=late_result, query_meter=self.f.meter, reservation=reservation,
                clock_ms=lambda: current[0],
            )
        self.assertEqual(self.f.query.calls, 1)
        self.assertEqual(len(self.f.meter.charges), 1)
        self.assertEqual(self.f.db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0], 1)

    def test_replay_cutoff_after_debit_blocks_second_query_and_keeps_row(self):
        current = [NOW_MS]
        reservation = self.f.reservation("project-a:writer", NOW_MS)
        self.assertEqual(reserve_shared_writer_envelope(
            execute=self.f.query, query_meter=self.f.meter, reservation=reservation,
            clock_ms=lambda: current[0],
        ), "RESERVED")
        charge = self.f.meter.charge_before_query
        def crossing_meter(**kwargs):
            result = charge(**kwargs)
            if kwargs["operation"] == "REPLAY_READ":
                current[0] += 600_001
            return result
        self.f.meter.charge_before_query = crossing_meter
        with self.assertRaisesRegex(BudgetBlocked, "REPLAY_UNVERIFIED"):
            reserve_shared_writer_envelope(
                execute=self.f.query, query_meter=self.f.meter, reservation=reservation,
                clock_ms=lambda: current[0],
            )
        self.assertEqual(self.f.query.calls, 2)
        self.assertEqual(len(self.f.meter.charges), 3)
        self.assertEqual(self.f.db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0], 1)

    def test_exact_replay_does_not_create_second_reservation(self):
        reservation = self.f.reservation("project-a:writer", NOW_MS)
        self.assertEqual(reserve_shared_writer_envelope(
            execute=self.f.query, query_meter=self.f.meter, reservation=reservation,
            clock_ms=lambda: reservation.reserved_at_ms,
        ), "RESERVED")
        self.assertEqual(reserve_shared_writer_envelope(
            execute=self.f.query, query_meter=self.f.meter, reservation=reservation,
            clock_ms=lambda: reservation.reserved_at_ms,
        ), "EXISTING_RESERVATION")


if __name__ == "__main__":
    unittest.main()
