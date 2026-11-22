"""Synthetic clock-guarded Core100 comparison; no training or network."""
import unittest
from unittest.mock import patch

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import RESERVE_SHARED_WRITER_SQL
from crypto_autopilot.training import prepaid_core100_comparison_v0_2 as successor
import test_prepaid_core100_comparison_v0_1 as fixtures


class Core100ClockGuardTests(unittest.TestCase):
    def setUp(self):
        for target in ("socket.getaddrinfo", "socket.socket.connect", "socket.socket.connect_ex"):
            blocker = patch(target, side_effect=AssertionError("unexpected network access"))
            blocker.start()
            self.addCleanup(blocker.stop)
        self.f = fixtures.Core100SharedComparisonTests("test_disabled_has_no_d1_or_r2")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def test_disabled_precedes_all_access(self):
        result = successor.compare_prepaid_core100(**self.f.args(execution_enabled=False))
        self.assertEqual(result["status"], "SKIPPED_DISABLED")
        self.assertEqual(self.f.statements, [])
        self.assertEqual(self.f.f.sdk.calls, [])

    def test_normal_comparison_stays_read_only_and_prevents_duplicate(self):
        with patch.object(fixtures, "compare_prepaid_core100", successor.compare_prepaid_core100):
            self.f.test_comparator_uses_frozen_functions_after_shared_admission()

    def test_rollback_after_commit_blocks_before_r2(self):
        args = self.f.args()
        slot = self.f.f.now
        elapsed = [0]
        args["clock_ms"] = lambda: slot + elapsed[0]
        original_send = self.f.opener.open.side_effect
        original_admit = successor.SharedWriterR2BudgetV06.admit
        def after_insert(request, timeout):
            response = original_send(request, timeout)
            if self.f.statements[-1] == RESERVE_SHARED_WRITER_SQL:
                elapsed[0] = 50
            return response
        def admitted(**kwargs):
            elapsed[0] = 100
            return original_admit(**kwargs)
        self.f.opener.open.side_effect = after_insert
        with patch.object(successor.SharedWriterR2BudgetV06, "admit", side_effect=admitted), patch.object(
            successor.frozen.runner, "require_execution_window"
        ), patch.object(
            successor.frozen, "_validate_authority_and_implementation", return_value=({}, "b" * 40)
        ):
            with self.assertRaises(BudgetBlocked):
                successor.compare_prepaid_core100(**args)
        self.assertEqual(self.f.f.sdk.calls, [])
        self.assertEqual(self.f.statements.count(RESERVE_SHARED_WRITER_SQL), 1)
        self.assertEqual(self.f.db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0], 1)
        self.assertGreater(self.f.f.meter.report()["query_attempts_charged"], 0)
