"""Offline integration for disabled shared-admitted Live-Paper coordinator."""
import json
import unittest
from dataclasses import replace
from unittest.mock import Mock, patch

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked, R2UsageSnapshot
from crypto_autopilot.paper.cloud_loop_v0_1 import SLOT_MS
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import RESERVE_SHARED_WRITER_SQL
from crypto_autopilot.paper.prepaid_live_coordinator_v0_1 import run_prepaid_live_coordinator
from test_live_paper_run_recovery_v0_1 import _bootstrap_state
import test_prepaid_d1_runtime_v0_1 as fixtures

WRITER = "crypto-autopilot:live-paper-run-coordinator-v0-1"


class SharedLiveCoordinatorTests(unittest.TestCase):
    def setUp(self):
        original = fixtures.authority_fixture
        def authority():
            data = original()
            data["writers"][0]["writer_id"] = WRITER
            return data
        for active in (patch.object(fixtures, "WRITER", WRITER),
                       patch.object(fixtures, "authority_fixture", side_effect=authority)):
            active.start()
            self.addCleanup(active.stop)
        self.f = fixtures.PrepaidD1RuntimeTests("test_meter_readonly_checks_never_debit_or_refresh")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.initial, _ = _bootstrap_state()
        self.db = self.f.sqlite()
        self.statements = []
        def send(request, timeout):
            body = json.loads(request.data)
            self.statements.append(body["sql"])
            cursor = self.db.execute(body["sql"], tuple(body["params"]))
            names = tuple(x[0] for x in cursor.description or ())
            rows = [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]
            self.db.commit()
            return fixtures.Response(fixtures.body(rows=rows, reads=1,
                                     writes=7 if "INSERT INTO" in body["sql"] else 0,
                                     size=1024))
        self.opener = Mock()
        self.opener.open.side_effect = send
        def store_factory(**kwargs):
            return BudgetedR2Store(client=self.f.sdk, bucket=kwargs["bucket"],
                                   before_external=kwargs["before_external"])
        env = {"CLOUDFLARE_D1_API_TOKEN": "fixture", "CLOUDFLARE_ACCOUNT_ID": "a" * 32,
               "CLOUDFLARE_D1_DATABASE_ID": fixtures.DB_ID, "R2_BUCKET_NAME": "fixture"}
        for active in (patch.dict("os.environ", env),
                       patch(fixtures.CLIENT_MODULE + ".build_opener", return_value=self.opener),
                       patch.object(BudgetedR2Store, "from_credentials", side_effect=store_factory)):
            active.start()
            self.addCleanup(active.stop)

    def args(self, **changes):
        now = self.f.now
        snapshot = R2UsageSnapshot(
            account_wide=True, reservation_coverage_complete=True,
            observed_at_ms=now, measured_through_ms=now, storage_bytes=0,
            class_a_month=0, class_b_month=0, class_a_31_days=0, class_b_31_days=0,
            class_a_day=0, class_b_day=0, provider_requests_day=0, new_bytes_day=0,
        )
        args = dict(run_name="fixture", tick_time_ms=now, candidate_specs=(),
                    initial_state=self.initial, previous_step_id=None, r2_snapshot=snapshot,
                    d1_snapshot=self.f.make_guard().snapshot, query_meter=self.f.meter,
                    clock_ms=lambda: self.f.now, slot_at_ms=now,
                    database_evidence=self.f.database_evidence(),
                    credentials={"account_id": "a" * 32, "bucket": "fixture",
                                 "access_key_id": "fixture", "secret_access_key": "fixture"},
                    execution_enabled=True)
        args.update(changes)
        return args

    def test_disabled_does_not_consume_or_access(self):
        result = run_prepaid_live_coordinator(**self.args(execution_enabled=False))
        self.assertEqual(result["status"], "SKIPPED_DISABLED")
        self.assertEqual(self.f.sdk.calls, [])
        self.assertEqual(self.statements, [])
        self.assertEqual(self.f.meter.report()["query_attempts_charged"], 0)

    def test_admission_no_trade_continuation_and_duplicate(self):
        first = run_prepaid_live_coordinator(**self.args())
        self.assertEqual(first["status"], "COMMITTED")
        self.assertEqual(first["provider_requests_performed"], 0)
        self.assertEqual(self.statements, [RESERVE_SHARED_WRITER_SQL])
        before = list(self.f.sdk.calls)
        with self.assertRaises(BudgetBlocked):
            run_prepaid_live_coordinator(**self.args())
        self.assertEqual(self.f.sdk.calls, before)
        self.f.now += SLOT_MS
        self.f._set_run(102)
        self.f.meter = self.f.claim(102)
        second = run_prepaid_live_coordinator(**self.args(
            initial_state=None, previous_step_id=first["step_id"],
        ))
        self.assertEqual(second["status"], "COMMITTED")
        self.assertEqual(second["run_id"], first["run_id"])
        self.assertEqual(second["provider_requests_performed"], 0)
        self.assertEqual(self.statements.count(RESERVE_SHARED_WRITER_SQL), 3)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0], 2)

    def test_missing_seal_blocks_continuation_without_new_writes(self):
        first = run_prepaid_live_coordinator(**self.args())
        self.assertEqual(first["status"], "COMMITTED")
        key = next(k for k in self.f.sdk.objects if "/live-run-result/" in k)
        del self.f.sdk.objects[key]
        self.f.now += SLOT_MS
        self.f._set_run(102)
        self.f.meter = self.f.claim(102)
        before = sum(call["operation"] == "PUT" for call in self.f.sdk.calls)
        result = run_prepaid_live_coordinator(**self.args(
            initial_state=None, previous_step_id=first["step_id"],
        ))
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertTrue(result["central_reservation_retained"])
        self.assertEqual(sum(call["operation"] == "PUT" for call in self.f.sdk.calls), before)
        self.assertEqual(result["provider_requests_performed"], 0)

    def test_incomplete_usage_blocks_before_d1_or_r2(self):
        args = self.args()
        args["r2_snapshot"] = replace(args["r2_snapshot"], reservation_coverage_complete=False)
        with self.assertRaises(BudgetBlocked):
            run_prepaid_live_coordinator(**args)
        self.assertEqual(self.statements, [])
        self.assertEqual(self.f.sdk.calls, [])


if __name__ == "__main__":
    unittest.main()
