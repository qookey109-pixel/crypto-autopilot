"""Synthetic V0.6 admission in the disabled Live-Paper coordinator."""
import unittest
from unittest.mock import patch

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.prepaid_live_coordinator_v0_2 import run_prepaid_live_coordinator
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import RESERVE_SHARED_WRITER_SQL
import test_prepaid_live_coordinator_v0_1 as fixtures


class LivePaperClockGuardTests(unittest.TestCase):
    def setUp(self):
        for target in ("socket.getaddrinfo", "socket.socket.connect", "socket.socket.connect_ex"):
            blocker = patch(target, side_effect=AssertionError("unexpected network access"))
            blocker.start()
            self.addCleanup(blocker.stop)
        self.f = fixtures.SharedLiveCoordinatorTests("test_disabled_does_not_consume_or_access")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def test_disabled_before_external_work(self):
        result = run_prepaid_live_coordinator(**self.f.args(execution_enabled=False))
        self.assertEqual(result["status"], "SKIPPED_DISABLED")
        self.assertEqual(self.f.statements, [])
        self.assertEqual(self.f.f.sdk.calls, [])

    def test_no_trade_continuation_and_duplicate_slot(self):
        with patch.object(fixtures, "run_prepaid_live_coordinator", run_prepaid_live_coordinator):
            self.f.test_admission_no_trade_continuation_and_duplicate()

    def test_post_commit_clock_rollback_stops_before_r2_and_provider(self):
        args = self.f.args()
        slot = self.f.f.now
        elapsed = [100]
        reads = [0]
        def clock():
            reads[0] += 1
            return slot if reads[0] == 1 else slot + elapsed[0]
        args["clock_ms"] = clock
        original = self.f.opener.open.side_effect
        def rollback_after_insert(request, timeout):
            response = original(request, timeout)
            if self.f.statements[-1] == RESERVE_SHARED_WRITER_SQL:
                elapsed[0] = 50
            return response
        self.f.opener.open.side_effect = rollback_after_insert
        with patch("crypto_autopilot.paper.cloud_pionex_client_v0_1.build_opener") as provider:
            with self.assertRaises(BudgetBlocked):
                run_prepaid_live_coordinator(**args)
        provider.assert_not_called()
        self.assertEqual(self.f.f.sdk.calls, [])
        self.assertEqual(self.f.statements.count(RESERVE_SHARED_WRITER_SQL), 1)
        self.assertEqual(self.f.db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0], 1)
        self.assertGreater(self.f.f.meter.report()["query_attempts_charged"], 0)
