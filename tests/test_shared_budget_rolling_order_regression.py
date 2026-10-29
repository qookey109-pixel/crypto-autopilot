"""Regression: out-of-order shared reservations must not bypass rolling caps."""
import unittest

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import reserve_shared_writer_envelope
from test_shared_writer_budget_gate_v0_4 import NOW_MS, SharedWriterBudgetGateTests


class RollingOrderRegressionTests(unittest.TestCase):
    def test_later_timestamp_committed_first_is_not_omitted(self):
        fixture = SharedWriterBudgetGateTests("test_rolling_cap_is_account_shared")
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        fixture.db.execute(
            "UPDATE cloudflare_shared_writer_budget_policy_v0_4 "
            "SET r2_class_a_per_rolling_31_days=1, r2_class_a_per_utc_day=10"
        )
        later = fixture.reservation("project-b:writer", NOW_MS + 1000)
        earlier = fixture.reservation("project-a:writer", NOW_MS)
        reserve_shared_writer_envelope(
            execute=fixture.query, query_meter=fixture.meter, reservation=later,
        )
        with self.assertRaisesRegex(BudgetBlocked, "POLICY_OR_WRITER_GATE"):
            reserve_shared_writer_envelope(
                execute=fixture.query, query_meter=fixture.meter, reservation=earlier,
            )
        self.assertEqual(fixture.db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
