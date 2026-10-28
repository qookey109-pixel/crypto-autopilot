from __future__ import annotations

import json
import unittest
from dataclasses import replace
from unittest.mock import Mock, patch

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.prepaid_shared_recovery_v0_1 import run_prepaid_shared_recovery
import test_prepaid_d1_runtime_v0_1 as fixtures
from test_shared_run_recovery_v0_1 import SharedRunRecoveryTests

WRITER = "crypto-autopilot:live-paper-run-recovery-v0-1"
MODULE = "crypto_autopilot.paper.prepaid_shared_recovery_v0_1"


class PrepaidSharedRecoveryTests(unittest.TestCase):
    def setUp(self):
        original = fixtures.authority_fixture

        def authority():
            data = original()
            data["writers"][0]["writer_id"] = WRITER
            return data

        self.patches = [
            patch.object(fixtures, "WRITER", WRITER),
            patch.object(fixtures, "authority_fixture", side_effect=authority),
        ]
        for active in self.patches:
            active.start()
            self.addCleanup(active.stop)
        self.f = fixtures.PrepaidD1RuntimeTests("test_meter_readonly_checks_never_debit_or_refresh")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.rec = SharedRunRecoveryTests("test_consistent_audit_does_not_write")
        self.rec.setUp()
        self.addCleanup(self.rec.doCleanups)
        self.r2 = replace(self.rec.snapshot, observed_at_ms=self.f.now, measured_through_ms=self.f.now)

    def args(self, **overrides):
        values = dict(
            run_id=self.rec.committed["run_id"], r2_snapshot=self.r2,
            d1_snapshot=self.f.guard.snapshot, query_meter=self.f.meter,
            clock_ms=lambda: self.f.now, slot_at_ms=self.f.now,
            database_evidence=self.f.evidence,
            credentials={"account_id": "a" * 32, "bucket": "fixture",
                         "access_key_id": "fixture", "secret_access_key": "fixture"},
            repair_missing_result_seals=True, execution_enabled=True,
        )
        values.update(overrides)
        return values

    def transport(self):
        db = self.f.sqlite()
        statements = []
        def send(request, timeout):
            payload = json.loads(request.data)
            statements.append(payload["sql"])
            cursor = db.execute(payload["sql"], tuple(payload["params"]))
            names = tuple(row[0] for row in cursor.description or ())
            rows = [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]
            db.commit()
            self.rec.claimed = True
            return fixtures.Response(fixtures.body(rows=rows, reads=1, writes=7, size=1088))
        opener = Mock()
        opener.open.side_effect = send
        return db, statements, opener

    def test_disabled_does_not_construct_clients(self):
        with patch(MODULE + ".PrepaidCloudflareD1QueryClient.from_environment") as client:
            result = run_prepaid_shared_recovery(**self.args(execution_enabled=False, credentials={}))
        self.assertEqual(result["status"], "SKIPPED_DISABLED")
        client.assert_not_called()
        self.assertEqual(self.rec.backend.events, [])

    def test_invalid_meter_or_slot_stops_before_credentials_or_network(self):
        with patch(MODULE + ".PrepaidCloudflareD1QueryClient.from_environment") as client:
            for changes in ({"query_meter": object()}, {"slot_at_ms": self.f.now + 1}):
                with self.subTest(changes=changes), self.assertRaises(BudgetBlocked):
                    run_prepaid_shared_recovery(**self.args(**changes))
        client.assert_not_called()
        self.assertEqual(self.rec.backend.events, [])

    def test_actual_prepaid_admission_then_repair_and_duplicate_stop(self):
        db, statements, opener = self.transport()
        key = self.rec.remove_seal()
        env = {"CLOUDFLARE_D1_API_TOKEN": "synthetic-token",
               "CLOUDFLARE_ACCOUNT_ID": "a" * 32,
               "CLOUDFLARE_D1_DATABASE_ID": fixtures.DB_ID}
        with patch.dict("os.environ", env), patch(fixtures.CLIENT_MODULE + ".build_opener", return_value=opener):
            result = run_prepaid_shared_recovery(**self.args())
            self.assertEqual(result["state"], "MISSING_RESULT_SEALS_REPAIRED")
            self.assertEqual(result["result_seal_writes_performed"], 1)
            self.assertEqual(len(statements), 1)
            self.assertEqual(self.f.meter.report()["query_attempts_charged"], 2)
            self.assertIn(key, self.rec.backend.objects)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3").fetchone()[0], 1)
            before = list(self.rec.backend.events)
            with self.assertRaises(BudgetBlocked):
                run_prepaid_shared_recovery(**self.args())
        self.assertEqual(self.rec.backend.events, before)
        self.assertEqual(len(statements), 3)

    def test_wrong_writer_ticket_fails_before_client(self):
        with patch(MODULE + ".PrepaidCloudflareD1QueryClient.from_environment") as client:
            self.f.meter._slot_id = "slot:1"
            with self.assertRaises(BudgetBlocked):
                run_prepaid_shared_recovery(**self.args())
        client.assert_not_called()
        self.assertEqual(self.rec.backend.events, [])


if __name__ == "__main__":
    unittest.main()
