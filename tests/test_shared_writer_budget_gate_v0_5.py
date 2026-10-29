"""Synthetic regression for shared budget V0.5 timestamp ordering."""
import unittest

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
        )
        with self.assertRaisesRegex(BudgetBlocked, "POLICY_OR_WRITER_GATE"):
            reserve_shared_writer_envelope(
                execute=self.f.query, query_meter=self.f.meter, reservation=earlier,
            )
        self.assertEqual(self.f.db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0], 1)

    def test_cross_day_out_of_order_still_counts_newer_commit(self):
        self.f.db.execute(
            "UPDATE cloudflare_shared_writer_budget_policy_v0_4 "
            "SET r2_class_a_per_rolling_31_days=1, r2_class_a_per_utc_day=10"
        )
        boundary = (NOW_MS // 86_400_000 + 1) * 86_400_000
        later = self.f.reservation("project-b:writer", boundary + 1000)
        earlier = self.f.reservation("project-a:writer", boundary - 1000)
        reserve_shared_writer_envelope(
            execute=self.f.query, query_meter=self.f.meter, reservation=later,
        )
        with self.assertRaisesRegex(BudgetBlocked, "POLICY_OR_WRITER_GATE"):
            reserve_shared_writer_envelope(
                execute=self.f.query, query_meter=self.f.meter, reservation=earlier,
            )

    def test_exact_replay_does_not_create_second_reservation(self):
        reservation = self.f.reservation("project-a:writer", NOW_MS)
        self.assertEqual(reserve_shared_writer_envelope(
            execute=self.f.query, query_meter=self.f.meter, reservation=reservation,
        ), "RESERVED")
        self.assertEqual(reserve_shared_writer_envelope(
            execute=self.f.query, query_meter=self.f.meter, reservation=reservation,
        ), "EXISTING_RESERVATION")


if __name__ == "__main__":
    unittest.main()
