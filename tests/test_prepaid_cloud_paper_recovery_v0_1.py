from __future__ import annotations

import json
import unittest
from dataclasses import replace
from unittest.mock import Mock, patch

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.cloud_loop_v0_1 import SLOT_MS, committed_report
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.cloud_runtime_v0_1 import CLOUD_PAPER_PREFIX
from crypto_autopilot.paper.cloud_runtime_v0_3 import build_runtime_composition
from crypto_autopilot.paper.run_store_v0_1 import R2PaperRunStore
from crypto_autopilot.paper.prepaid_cloud_paper_recovery_v0_1 import run_prepaid_cloud_paper_recovery
from crypto_autopilot.paper.prepaid_query_controller_v0_1 import AllocationEvidence, claim_prepaid_query_meter
import test_prepaid_d1_runtime_v0_1 as fixtures

WRITER = "crypto-autopilot:cloud-paper-run-recovery-v0-1"


class CloudPaperRecoveryIntegrationTests(unittest.TestCase):
    def setUp(self):
        original = fixtures.authority_fixture
        def authority():
            data = original()
            data["writers"][1]["writer_id"] = WRITER
            return data
        self.authority_patch = patch.object(fixtures, "authority_fixture", side_effect=authority)
        self.authority_patch.start()
        self.addCleanup(self.authority_patch.stop)
        self.f = fixtures.PrepaidD1RuntimeTests("test_meter_readonly_checks_never_debit_or_refresh")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def transport(self):
        db = self.f.sqlite()
        db.execute("INSERT INTO cloudflare_shared_writer_identities_v0_3 VALUES (?, 'ACTIVE', ?, ?)",
                   (WRITER, "b" * 64, self.f.now))
        size, statements = [1024], []
        def send(request, timeout):
            payload = json.loads(request.data)
            statements.append(payload["sql"])
            cursor = db.execute(payload["sql"], tuple(payload["params"]))
            names = tuple(row[0] for row in cursor.description or ())
            rows = [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]
            db.commit()
            size[0] += 64
            return fixtures.Response(fixtures.body(rows=rows, reads=1, writes=7, size=size[0]))
        opener = Mock()
        opener.open.side_effect = send
        return db, size, statements, opener

    def recovery_meter(self):
        self.f._set_run(201)
        return claim_prepaid_query_meter(
            authority_document=self.f.authority, writer_id=WRITER,
            slot_id=f"slot:{self.f.now}", run_id=201, transport=self.f.github,
            evidence=AllocationEvidence(
                account_coverage_complete=True, zero_cost_verified=True,
                observed_at_ms=self.f.now, measured_through_ms=self.f.now,
                available={"queries": 1000, "rows_read": 1_000_000,
                           "rows_written": 10_000, "storage_bytes": 10_000_000},
            ), clock_ms=lambda: self.f.now,
        )

    def test_cloud_loop_seal_repaired_only_in_cloud_namespace(self):
        db, size, statements, opener = self.transport()
        with patch(fixtures.CLIENT_MODULE + ".build_opener", return_value=opener):
            with patch.object(fixtures, "build_runtime_composition", build_runtime_composition):
                runtime = self.f.runtime()
            report = runtime.run_slot(
                tick_ms=self.f.now, previous_slot=None, activation_enabled=True, run_id="fixture-101",
            )
            self.assertEqual(report["state"], "NO_TRADE")
            key = next(k for k in self.f.sdk.objects if k.startswith(CLOUD_PAPER_PREFIX + "/live-run-result/"))
            run_id = report["coordinator"]["run_id"]
            del self.f.sdk.objects[key]
            sentinel = "paper-run-store/v0.1/live-run-result/sentinel.json"
            self.f.sdk.objects[sentinel] = (b"old-namespace-untouched", {})
            self.f.now += SLOT_MS
            meter = self.recovery_meter()
            snapshot = replace(runtime.budget_guard.snapshot, observed_at_ms=self.f.now,
                               measured_through_ms=self.f.now)
            env = {"CLOUDFLARE_D1_API_TOKEN": "synthetic-token",
                   "CLOUDFLARE_ACCOUNT_ID": "a" * 32,
                   "CLOUDFLARE_D1_DATABASE_ID": fixtures.DB_ID,
                   "R2_BUCKET_NAME": "synthetic-only"}
            def store_factory(**kwargs):
                return BudgetedR2Store(client=self.f.sdk, bucket=kwargs["bucket"],
                                       before_external=kwargs["before_external"], policy=kwargs["policy"])
            with patch.dict("os.environ", env), patch.object(BudgetedR2Store, "from_credentials", side_effect=store_factory):
                args = dict(
                    run_id=run_id, r2_snapshot=snapshot,
                    d1_snapshot=self.f.make_guard(size[0]).snapshot, query_meter=meter,
                    clock_ms=lambda: self.f.now, slot_at_ms=self.f.now,
                    database_evidence=self.f.database_evidence(size[0]),
                    credentials={"account_id": "a" * 32, "bucket": "synthetic-only",
                                 "access_key_id": "fixture", "secret_access_key": "fixture"},
                    repair_missing_result_seals=True, execution_enabled=True,
                )
                result = run_prepaid_cloud_paper_recovery(**args)
                before_duplicate = list(self.f.sdk.calls)
                with self.assertRaises(BudgetBlocked):
                    run_prepaid_cloud_paper_recovery(**args)
                self.assertEqual(self.f.sdk.calls, before_duplicate)
            self.assertEqual(result["state"], "MISSING_RESULT_SEALS_REPAIRED")
            self.assertEqual(result["result_seal_writes_performed"], 1)
            self.assertIn(key, self.f.sdk.objects)
            self.assertEqual(self.f.sdk.objects[sentinel], (b"old-namespace-untouched", {}))
            readback = R2PaperRunStore(
                BudgetedR2Store(client=self.f.sdk, bucket="fixture", before_external=lambda *_: None),
                prefix=CLOUD_PAPER_PREFIX,
            )
            self.assertIsNotNone(committed_report(readback, report["slot_id"]))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3").fetchone()[0], 2)
            self.assertEqual(len(statements), 6)
            self.assertEqual(meter.report()["query_attempts_charged"], 6)

    def test_wrong_writer_or_bucket_blocks_before_client_and_r2(self):
        meter = self.recovery_meter()
        snapshot = fixtures.R2UsageSnapshot(
            account_wide=True, reservation_coverage_complete=True,
            observed_at_ms=self.f.now, measured_through_ms=self.f.now, storage_bytes=0,
            class_a_month=0, class_b_month=0, class_a_31_days=0, class_b_31_days=0,
            class_a_day=0, class_b_day=0, provider_requests_day=0, new_bytes_day=0,
        )
        args = dict(
            run_id="test", r2_snapshot=snapshot, d1_snapshot=self.f.guard.snapshot,
            query_meter=meter, clock_ms=lambda: self.f.now, slot_at_ms=self.f.now,
            database_evidence=self.f.evidence,
            credentials={"account_id": "a" * 32, "bucket": "wrong-bucket",
                         "access_key_id": "fixture", "secret_access_key": "fixture"},
            repair_missing_result_seals=True, execution_enabled=True,
        )
        env = {"CLOUDFLARE_ACCOUNT_ID": "a" * 32, "R2_BUCKET_NAME": "synthetic-only"}
        with patch.dict("os.environ", env), patch(
            "crypto_autopilot.paper.prepaid_cloud_paper_recovery_v0_1.PrepaidCloudflareD1QueryClient.from_environment"
        ) as client:
            with self.assertRaisesRegex(BudgetBlocked, "BUCKET_MISMATCH"):
                run_prepaid_cloud_paper_recovery(**args)
            args["query_meter"] = self.f.meter
            with self.assertRaises(BudgetBlocked):
                run_prepaid_cloud_paper_recovery(**args)
        client.assert_not_called()
        self.assertEqual(self.f.sdk.calls, [])

    def test_truncated_cloud_inventory_stops_without_repair(self):
        db, size, statements, opener = self.transport()
        with patch(fixtures.CLIENT_MODULE + ".build_opener", return_value=opener):
            with patch.object(fixtures, "build_runtime_composition", build_runtime_composition):
                runtime = self.f.runtime()
            report = runtime.run_slot(
                tick_ms=self.f.now, previous_slot=None, activation_enabled=True, run_id="fixture-101",
            )
            key = next(k for k in self.f.sdk.objects if k.startswith(CLOUD_PAPER_PREFIX + "/live-run-result/"))
            del self.f.sdk.objects[key]
            self.f.now += SLOT_MS
            meter = self.recovery_meter()
            snapshot = replace(runtime.budget_guard.snapshot, observed_at_ms=self.f.now,
                               measured_through_ms=self.f.now)
            original_list = self.f.sdk.list_objects_v2
            def truncated(**kwargs):
                page = original_list(**kwargs)
                page["IsTruncated"] = True
                return page
            def store_factory(**kwargs):
                return BudgetedR2Store(client=self.f.sdk, bucket=kwargs["bucket"],
                                       before_external=kwargs["before_external"], policy=kwargs["policy"])
            env = {"CLOUDFLARE_D1_API_TOKEN": "synthetic-token",
                   "CLOUDFLARE_ACCOUNT_ID": "a" * 32,
                   "CLOUDFLARE_D1_DATABASE_ID": fixtures.DB_ID,
                   "R2_BUCKET_NAME": "synthetic-only"}
            self.f.sdk.calls.clear()
            with patch.dict("os.environ", env), patch.object(
                BudgetedR2Store, "from_credentials", side_effect=store_factory,
            ), patch.object(self.f.sdk, "list_objects_v2", side_effect=truncated):
                result = run_prepaid_cloud_paper_recovery(
                    run_id=report["coordinator"]["run_id"], r2_snapshot=snapshot,
                    d1_snapshot=self.f.make_guard(size[0]).snapshot, query_meter=meter,
                    clock_ms=lambda: self.f.now, slot_at_ms=self.f.now,
                    database_evidence=self.f.database_evidence(size[0]),
                    credentials={"account_id": "a" * 32, "bucket": "synthetic-only",
                                 "access_key_id": "fixture", "secret_access_key": "fixture"},
                    repair_missing_result_seals=True, execution_enabled=True,
                )
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertTrue(result["central_reservation_retained"])
        self.assertIsNone(result["result_seal_writes_performed"])
        self.assertNotIn(key, self.f.sdk.objects)
        self.assertFalse(any(call["operation"] == "PUT" for call in self.f.sdk.calls))
        self.assertEqual(len(statements), 4)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3").fetchone()[0], 2)

    def test_disabled_does_not_touch_cloud(self):
        result = run_prepaid_cloud_paper_recovery(
            run_id="", r2_snapshot=None, d1_snapshot=None, query_meter=None,
            clock_ms=lambda: self.f.now, slot_at_ms=self.f.now, database_evidence=None,
            credentials={}, execution_enabled=False,
        )
        self.assertEqual(result["status"], "SKIPPED_DISABLED")
        self.assertEqual(self.f.sdk.calls, [])


if __name__ == "__main__":
    unittest.main()
