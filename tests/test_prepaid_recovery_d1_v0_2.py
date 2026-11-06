"""Synthetic V0.5 prepaid recovery admission; no production execution."""
from dataclasses import replace
import unittest
from unittest.mock import patch

from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import D1LedgerUnavailable, D1QueryResult
from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import RESERVE_SHARED_WRITER_SQL as OLD_SQL
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import (
    READ_SHARED_WRITER_SQL, RESERVE_SHARED_WRITER_SQL, SharedWriterReservation,
    reservation_params, reserve_shared_writer_envelope,
)
import test_prepaid_d1_runtime_v0_1 as fixtures

try:
    from crypto_autopilot.paper.prepaid_recovery_d1_v0_2 import RecoveryPrepaidD1Client
except ModuleNotFoundError as exc:
    if exc.name != "crypto_autopilot.paper.prepaid_recovery_d1_v0_2":
        raise
    RecoveryPrepaidD1Client = None

WRITER = "crypto-autopilot:live-paper-run-recovery-v0-1"
CLIENT = "crypto_autopilot.paper.prepaid_d1_client_v0_1"


class RecoveryV05PrepaidD1Tests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(RecoveryPrepaidD1Client)
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
        t = self.f.meter.report()["ticket_envelope_charged_in_full"]
        self.reservation = SharedWriterReservation(
            writer_id=WRITER, slot_id=f"slot:{self.f.now}", idempotency_key=f"slot:{self.f.now}",
            slot_at_ms=self.f.now, reserved_at_ms=self.f.now, provider_requests=0,
            r2_class_a=8, r2_class_b=64, r2_new_bytes=16384,
            d1_queries=t["queries"], d1_rows_read=t["rows_read"],
            d1_rows_written=t["rows_written"], d1_storage_growth_bytes=t["storage_bytes"],
        )

    def client(self, enabled=False):
        return RecoveryPrepaidD1Client(
            api_token="synthetic-only", account_id="a" * 32, database_id=fixtures.DB_ID,
            usage_guard=self.f.guard, query_meter=self.f.meter, writer_id=WRITER,
            slot_id=self.reservation.slot_id, database_evidence=self.f.evidence,
            execution_enabled=enabled,
        )

    def test_disabled_rejects_before_debit_and_network(self):
        client = self.client()
        with patch(CLIENT + ".build_opener") as network, self.assertRaises(BudgetBlocked):
            client.query(READ_SHARED_WRITER_SQL, (WRITER, self.reservation.slot_id))
        self.assertEqual(self.f.meter.report()["query_attempts_charged"], 0)
        network.assert_not_called()

    def test_v05_reserves_once_and_replay_retains_full_debits(self):
        db = self.f.sqlite()
        client = self.client(True)

        def sqlite_request(sql, params):
            cursor = db.execute(sql, params)
            names = tuple(col[0] for col in cursor.description or ())
            rows = tuple(dict(zip(names, row, strict=True)) for row in cursor.fetchall())
            db.commit()
            return D1QueryResult(rows, 1, 0 if sql == READ_SHARED_WRITER_SQL else 7), 1024

        with patch(CLIENT + ".PrepaidCloudflareD1QueryClient._request", side_effect=sqlite_request):
            for expected in ("RESERVED", "EXISTING_RESERVATION"):
                self.assertEqual(reserve_shared_writer_envelope(
                    execute=client.query, reservation=self.reservation, query_meter=self.f.meter,
                    clock_ms=lambda: self.f.now, execution_enabled=True,
                ), expected)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3").fetchone()[0], 1)
        self.assertEqual(self.f.meter.report()["query_attempts_charged"], 6)

    def test_rejects_old_sql_and_tampered_envelopes_without_debit(self):
        client = self.client(True)
        with self.assertRaises(D1LedgerUnavailable):
            client.query(OLD_SQL, reservation_params(self.reservation))
        for altered in (replace(self.reservation, r2_class_a=7),
                        replace(self.reservation, provider_requests=1),
                        replace(self.reservation, d1_rows_read=1)):
            with self.subTest(altered=altered), self.assertRaises(BudgetBlocked):
                client.query(RESERVE_SHARED_WRITER_SQL, reservation_params(altered))
        self.assertEqual(self.f.meter.report()["query_attempts_charged"], 0)

    def test_late_response_poisoned_and_never_retried(self):
        client = self.client(True)
        def late(*args):
            self.f.now += 600001
            return D1QueryResult(({"writer_id": WRITER, "slot_id": self.reservation.slot_id},), 1, 7), 1024
        with patch(CLIENT + ".PrepaidCloudflareD1QueryClient._request", side_effect=late) as request:
            for _ in range(2):
                with self.assertRaises(D1LedgerUnavailable):
                    client.query(RESERVE_SHARED_WRITER_SQL, reservation_params(self.reservation))
        self.assertEqual(request.call_count, 1)
        self.assertTrue(client.diagnostics()["review_required"])
        self.assertEqual(self.f.meter.report()["query_attempts_charged"], 1)
