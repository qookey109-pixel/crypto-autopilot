"""Synthetic regression for prepared Paper V0.5 prepaid D1 admission."""
from dataclasses import replace
import unittest
from unittest.mock import patch

from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import D1LedgerUnavailable, D1QueryResult
from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked, CloudBudgetPolicy
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import RESERVE_SHARED_WRITER_SQL as OLD_SQL
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import (
    READ_SHARED_WRITER_SQL, RESERVE_SHARED_WRITER_SQL, SharedWriterReservation, reservation_params,
)
import test_prepaid_d1_runtime_v0_1 as fixtures

try:
    from crypto_autopilot.paper.prepaid_paper_d1_v0_2 import PaperPrepaidD1Client
except ModuleNotFoundError as exc:
    if exc.name != "crypto_autopilot.paper.prepaid_paper_d1_v0_2":
        raise
    PaperPrepaidD1Client = None


class PaperV05PrepaidD1Tests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(PaperPrepaidD1Client)
        self.f = fixtures.PrepaidD1RuntimeTests("test_meter_readonly_checks_never_debit_or_refresh")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        p = CloudBudgetPolicy()
        ticket = self.f.meter.report()["ticket_envelope_charged_in_full"]
        self.reservation = SharedWriterReservation(
            writer_id=fixtures.WRITER, slot_id=f"slot:{self.f.now}", idempotency_key=f"slot:{self.f.now}",
            slot_at_ms=self.f.now, reserved_at_ms=self.f.now, provider_requests=p.provider_per_run,
            r2_class_a=p.r2_class_a_per_run, r2_class_b=p.r2_class_b_per_run,
            r2_new_bytes=p.r2_new_bytes_per_run, d1_queries=ticket["queries"],
            d1_rows_read=ticket["rows_read"], d1_rows_written=ticket["rows_written"],
            d1_storage_growth_bytes=ticket["storage_bytes"],
        )

    def client(self, enabled=False):
        return PaperPrepaidD1Client(
            api_token="synthetic-only", account_id="a" * 32, database_id=fixtures.DB_ID,
            usage_guard=self.f.guard, query_meter=self.f.meter, writer_id=fixtures.WRITER,
            slot_id=self.reservation.slot_id, database_evidence=self.f.evidence,
            execution_enabled=enabled,
        )

    def test_disabled_stops_before_debit_and_network(self):
        client = self.client()
        with patch("crypto_autopilot.paper.prepaid_d1_client_v0_1.build_opener") as network:
            with self.assertRaises(BudgetBlocked):
                client.query(READ_SHARED_WRITER_SQL, (fixtures.WRITER, self.reservation.slot_id))
        self.assertEqual(self.f.meter.report()["query_attempts_charged"], 0)
        network.assert_not_called()

    def test_v05_reservation_is_allowed_and_old_insert_is_not(self):
        client = self.client(True)
        params = reservation_params(self.reservation)
        with patch("crypto_autopilot.paper.prepaid_d1_client_v0_1.PrepaidCloudflareD1QueryClient._request",
                   return_value=(D1QueryResult(({"writer_id": fixtures.WRITER, "slot_id": self.reservation.slot_id},), 1, 7), 1024)) as request:
            result = client.query(RESERVE_SHARED_WRITER_SQL, params)
            self.assertEqual(len(result.rows), 1)
            with self.assertRaises(D1LedgerUnavailable):
                client.query(OLD_SQL, params)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(self.f.meter.report()["query_attempts_charged"], 1)

    def test_off_grid_slot_cannot_read_or_reserve(self):
        self.f.now += 1
        self.f._set_run(102)
        self.f.meter = self.f.claim(102)
        self.f.guard = self.f.make_guard()
        self.f.evidence = self.f.database_evidence()
        slot = f"slot:{self.f.now}"
        self.reservation = replace(self.reservation, slot_id=slot, idempotency_key=slot,
                                   slot_at_ms=self.f.now, reserved_at_ms=self.f.now)
        client = self.client(True)
        with patch("crypto_autopilot.paper.prepaid_d1_client_v0_1.build_opener") as network:
            for sql, params in (
                (READ_SHARED_WRITER_SQL, (fixtures.WRITER, slot)),
                (RESERVE_SHARED_WRITER_SQL, reservation_params(self.reservation)),
            ):
                with self.subTest(sql=sql), self.assertRaises(BudgetBlocked):
                    client.query(sql, params)
        network.assert_not_called()
        self.assertEqual(self.f.meter.report()["query_attempts_charged"], 0)

    def test_tampered_envelope_rejected_before_debit(self):
        client = self.client(True)
        for reservation in (replace(self.reservation, r2_new_bytes=1),
                            replace(self.reservation, provider_requests=0),
                            replace(self.reservation, d1_rows_read=1)):
            with self.subTest(reservation=reservation):
                with self.assertRaises((BudgetBlocked, D1LedgerUnavailable)):
                    client.query(RESERVE_SHARED_WRITER_SQL, reservation_params(reservation))
        self.assertEqual(self.f.meter.report()["query_attempts_charged"], 0)

    def test_response_after_usage_evidence_expires_needs_review(self):
        client = self.client(True)
        def late(*args):
            self.f.now += 50_001
            return D1QueryResult(({"writer_id": fixtures.WRITER, "slot_id": self.reservation.slot_id},), 1, 7), 1024
        with patch("crypto_autopilot.paper.prepaid_d1_client_v0_1.PrepaidCloudflareD1QueryClient._request",
                   side_effect=late) as request:
            with self.assertRaises(D1LedgerUnavailable):
                client.query(RESERVE_SHARED_WRITER_SQL, reservation_params(self.reservation))
        self.assertEqual(request.call_count, 1)
        self.assertTrue(client.diagnostics()["review_required"])
        self.assertEqual(self.f.meter.report()["query_attempts_charged"], 1)

    def test_late_committed_response_is_review_required_without_retry(self):
        client = self.client(True)
        def late(*args):
            self.f.now += 600_001
            return D1QueryResult(({"writer_id": fixtures.WRITER, "slot_id": self.reservation.slot_id},), 1, 7), 1024
        with patch("crypto_autopilot.paper.prepaid_d1_client_v0_1.PrepaidCloudflareD1QueryClient._request",
                   side_effect=late) as request:
            with self.assertRaises(D1LedgerUnavailable):
                client.query(RESERVE_SHARED_WRITER_SQL, reservation_params(self.reservation))
            with self.assertRaises(D1LedgerUnavailable):
                client.query(RESERVE_SHARED_WRITER_SQL, reservation_params(self.reservation))
        self.assertEqual(request.call_count, 1)
        self.assertTrue(client.diagnostics()["review_required"])
        self.assertEqual(self.f.meter.report()["query_attempts_charged"], 1)


if __name__ == "__main__":
    unittest.main()
