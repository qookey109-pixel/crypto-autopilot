"""Synthetic V0.6 clock-guarded Live-Paper and Cloud-Paper recovery."""
import unittest
from unittest.mock import patch

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import RESERVE_SHARED_WRITER_SQL
from crypto_autopilot.paper.shared_writer_r2_budget_v0_3 import SharedWriterR2BudgetV06
from crypto_autopilot.paper.prepaid_shared_recovery_v0_3 import run_prepaid_shared_recovery_v0_3
from crypto_autopilot.paper.prepaid_cloud_paper_recovery_v0_3 import run_prepaid_cloud_paper_recovery_v0_3
import test_prepaid_shared_recovery_v0_2 as live_fixture
import test_prepaid_cloud_paper_recovery_v0_2 as cloud_fixture
import test_prepaid_d1_runtime_v0_1 as common


class LiveRecoveryClockGuardTests(unittest.TestCase):
    def setUp(self):
        for target in ("socket.getaddrinfo", "socket.socket.connect", "socket.socket.connect_ex"):
            blocker = patch(target, side_effect=AssertionError("unexpected network access"))
            blocker.start()
            self.addCleanup(blocker.stop)
        self.f = live_fixture.PrepaidSharedRecoveryTests("test_disabled_does_not_construct_clients")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def test_disabled_and_normal_repair_preserve_duplicate_gate(self):
        self.assertEqual(run_prepaid_shared_recovery_v0_3(
            **self.f.args(execution_enabled=False, credentials={})
        )["status"], "SKIPPED_DISABLED")
        with patch.object(live_fixture, "run_prepaid_shared_recovery_v0_2",
                          run_prepaid_shared_recovery_v0_3):
            self.f.test_actual_prepaid_admission_then_repair_and_duplicate_stop()

    def test_clock_rollback_after_commit_blocks_recovery_before_r2(self):
        db, statements, opener = self.f.transport()
        original_send = opener.open.side_effect
        original_admit = SharedWriterR2BudgetV06.admit
        slot, elapsed = self.f.f.now, [0]
        args = self.f.args(clock_ms=lambda: slot + elapsed[0])
        def after_insert(request, timeout):
            response = original_send(request, timeout)
            if statements[-1] == RESERVE_SHARED_WRITER_SQL:
                elapsed[0] = 50
            return response
        def guarded_admit(**kwargs):
            elapsed[0] = 100
            return original_admit(**kwargs)
        opener.open.side_effect = after_insert
        env = {"CLOUDFLARE_D1_API_TOKEN": "synthetic-token",
               "CLOUDFLARE_ACCOUNT_ID": "a" * 32,
               "CLOUDFLARE_D1_DATABASE_ID": common.DB_ID}
        with patch.dict("os.environ", env), patch(
            common.CLIENT_MODULE + ".build_opener", return_value=opener
        ), patch.object(SharedWriterR2BudgetV06, "admit", side_effect=guarded_admit):
            with self.assertRaises(BudgetBlocked):
                run_prepaid_shared_recovery_v0_3(**args)
        self.assertEqual(self.f.rec.backend.events, [])
        self.assertEqual(statements.count(RESERVE_SHARED_WRITER_SQL), 1)
        self.assertEqual(db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0], 1)
        self.assertGreater(self.f.f.meter.report()["query_attempts_charged"], 0)


class CloudRecoveryClockGuardTests(unittest.TestCase):
    def setUp(self):
        for target in ("socket.getaddrinfo", "socket.socket.connect", "socket.socket.connect_ex"):
            blocker = patch(target, side_effect=AssertionError("unexpected network access"))
            blocker.start()
            self.addCleanup(blocker.stop)
        self.f = cloud_fixture.CloudPaperRecoveryIntegrationTests(
            "test_cloud_loop_seal_repaired_only_in_cloud_namespace"
        )
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def test_normal_repair_is_namespace_scoped_and_duplicate_blocked(self):
        with patch.object(cloud_fixture, "run_prepaid_cloud_paper_recovery_v0_2",
                          run_prepaid_cloud_paper_recovery_v0_3):
            self.f.test_cloud_loop_seal_repaired_only_in_cloud_namespace()

    def test_rollback_after_commit_blocks_before_r2(self):
        db, _, statements, opener = self.f.transport()
        meter = self.f.recovery_meter()
        slot, elapsed = self.f.f.now, [0]
        snapshot = common.R2UsageSnapshot(
            account_wide=True, reservation_coverage_complete=True,
            observed_at_ms=slot, measured_through_ms=slot, storage_bytes=0,
            class_a_month=0, class_b_month=0, class_a_31_days=0, class_b_31_days=0,
            class_a_day=0, class_b_day=0, provider_requests_day=0, new_bytes_day=0,
        )
        original_send = opener.open.side_effect
        original_admit = SharedWriterR2BudgetV06.admit
        def after_insert(request, timeout):
            response = original_send(request, timeout)
            if statements[-1] == RESERVE_SHARED_WRITER_SQL:
                elapsed[0] = 50
            return response
        def guarded_admit(**kwargs):
            elapsed[0] = 100
            return original_admit(**kwargs)
        opener.open.side_effect = after_insert
        env = {"CLOUDFLARE_D1_API_TOKEN": "synthetic-token",
               "CLOUDFLARE_ACCOUNT_ID": "a" * 32,
               "CLOUDFLARE_D1_DATABASE_ID": common.DB_ID, "R2_BUCKET_NAME": "synthetic-only"}
        with patch.dict("os.environ", env), patch(
            common.CLIENT_MODULE + ".build_opener", return_value=opener
        ), patch.object(SharedWriterR2BudgetV06, "admit", side_effect=guarded_admit):
            with self.assertRaises(BudgetBlocked):
                run_prepaid_cloud_paper_recovery_v0_3(
                    run_id="fixture", r2_snapshot=snapshot, d1_snapshot=self.f.f.guard.snapshot,
                    query_meter=meter, clock_ms=lambda: slot + elapsed[0], slot_at_ms=slot,
                    database_evidence=self.f.f.evidence,
                    credentials={"account_id": "a" * 32, "bucket": "synthetic-only",
                                 "access_key_id": "fixture", "secret_access_key": "fixture"},
                    repair_missing_result_seals=True, execution_enabled=True,
                )
        self.assertEqual(self.f.f.sdk.calls, [])
        self.assertEqual(statements.count(RESERVE_SHARED_WRITER_SQL), 1)
        self.assertEqual(db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0], 1)
        self.assertGreater(meter.report()["query_attempts_charged"], 0)
