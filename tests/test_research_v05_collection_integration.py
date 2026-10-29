"""Synthetic research source -> V0.5 shared admission -> R2 integration."""
import io
import json
import unittest
from unittest.mock import patch

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked, CloudBudgetGuard, R2UsageSnapshot
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import D1QueryResult
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import READ_SHARED_WRITER_SQL, SharedWriterReservation
from test_shared_signal_collection_v0_1 import SOURCES
from test_shared_signal_publish_v0_1 import MemoryS3
import test_prepaid_research_d1_v0_1 as research_fixture

try:
    from crypto_autopilot.research.shared_signal_collection_v0_2 import run_shared_signal_collection
except ModuleNotFoundError as exc:
    if exc.name != "crypto_autopilot.research.shared_signal_collection_v0_2":
        raise
    run_shared_signal_collection = None


class Response(io.BytesIO):
    status = 200
    headers = {"Content-Type": "application/json"}


class ResearchV05CollectionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(run_shared_signal_collection)
        self.f = research_fixture.DailyResearchD1Tests("test_daily_shared_read_debits_before_transport")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.db = self.f.f.sqlite()
        self.db.execute("INSERT INTO cloudflare_shared_writer_identities_v0_3 VALUES (?, 'ACTIVE', ?, ?)",
                        (research_fixture.WRITER, "a" * 64, self.f.f.now))
        self.sdk = MemoryS3()
        self.sources_called = []
        self.sql_called = []
        now = self.f.f.now
        self.snapshot = R2UsageSnapshot(
            account_wide=True, reservation_coverage_complete=True,
            observed_at_ms=now, measured_through_ms=now, storage_bytes=0,
            class_a_month=0, class_b_month=0, class_a_31_days=0, class_b_31_days=0,
            class_a_day=0, class_b_day=0, provider_requests_day=0, new_bytes_day=0,
        )
        envelope = self.f.meter.report()["ticket_envelope_charged_in_full"]
        self.reservation = SharedWriterReservation(
            writer_id=research_fixture.WRITER, slot_id=self.f.slot, idempotency_key=self.f.slot,
            slot_at_ms=now, reserved_at_ms=now, provider_requests=3,
            r2_class_a=3, r2_class_b=6, r2_new_bytes=270336,
            d1_queries=envelope["queries"], d1_rows_read=envelope["rows_read"],
            d1_rows_written=envelope["rows_written"], d1_storage_growth_bytes=envelope["storage_bytes"],
        )

    def sqlite_request(self, sql, params):
        self.sql_called.append(sql)
        cursor = self.db.execute(sql, params)
        columns = tuple(col[0] for col in cursor.description or ())
        rows = tuple(dict(zip(columns, row, strict=True)) for row in cursor.fetchall())
        self.db.commit()
        return D1QueryResult(rows, 1, 0 if sql == READ_SHARED_WRITER_SQL else 7), 1024

    def source(self, request, *, timeout):
        self.assertTrue(self.sql_called)
        self.sources_called.append(request.full_url)
        return Response(json.dumps({"title": "public synthetic"}).encode())

    def guard(self):
        return CloudBudgetGuard(snapshot=self.snapshot, clock_ms=lambda: self.f.f.now)

    def run_collection(self):
        return run_shared_signal_collection(
            sources=SOURCES, run_id="101", reservation=self.reservation,
            guard=self.guard(), execute=self.f.client.query, query_meter=self.f.meter,
            validate_binding=lambda: self.f.client.validate_runtime_binding(
                meter=self.f.meter, writer_id=research_fixture.WRITER, slot_id=self.f.slot,
            ),
            credentials={"account_id": "a" * 32, "bucket": "fixture",
                         "access_key_id": "fixture", "secret_access_key": "fixture"},
            transport=self.source, execution_enabled=True,
        )

    def test_disabled_returns_before_credentials_or_transport(self):
        result = run_shared_signal_collection(
            sources=[], run_id="", reservation=None, guard=None, execute=None,
            query_meter=None, validate_binding=None, credentials={}, execution_enabled=False,
        )
        self.assertEqual(result["status"], "SKIPPED_DISABLED")
        self.assertEqual(self.sql_called, [])
        self.assertEqual(self.sdk.events, [])

    def test_source_failure_retains_admission_and_no_r2_write(self):
        def fail_source(request, *, timeout):
            self.sources_called.append(request.full_url)
            raise OSError("synthetic source failure")
        with patch.dict("os.environ", {"CLOUDFLARE_ACCOUNT_ID": "a" * 32, "R2_BUCKET_NAME": "fixture"}), patch(
            "crypto_autopilot.paper.prepaid_d1_client_v0_1.PrepaidCloudflareD1QueryClient._request",
            side_effect=self.sqlite_request,
        ), patch.object(self, "source", side_effect=fail_source):
            result = self.run_collection()
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertTrue(result["central_reservation_retained"])
        self.assertEqual(len(self.sources_called), 1)
        self.assertEqual(self.sdk.events, [])
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3 WHERE writer_id=?",
            (research_fixture.WRITER,),
        ).fetchone()[0], 1)

    def test_v05_prepaid_collection_publishes_once_and_blocks_duplicate(self):
        def store_factory(**kwargs):
            return BudgetedR2Store(client=self.sdk, bucket=kwargs["bucket"],
                                   before_external=kwargs["before_external"])
        with patch.dict("os.environ", {"CLOUDFLARE_ACCOUNT_ID": "a" * 32, "R2_BUCKET_NAME": "fixture"}), patch(
            "crypto_autopilot.paper.prepaid_d1_client_v0_1.PrepaidCloudflareD1QueryClient._request",
            side_effect=self.sqlite_request,
        ), patch.object(BudgetedR2Store, "from_credentials", side_effect=store_factory):
            result = self.run_collection()
            before = list(self.sdk.events)
            with self.assertRaises(BudgetBlocked):
                self.run_collection()
        self.assertEqual(result["status"], "PUBLISHED")
        self.assertEqual(result["provider_requests_performed"], 3)
        self.assertEqual(len(self.sources_called), 3)
        self.assertEqual(self.sdk.events, before)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3 WHERE writer_id=?",
            (research_fixture.WRITER,),
        ).fetchone()[0], 1)
        self.assertEqual(self.f.meter.report()["query_attempts_charged"], 6)


if __name__ == "__main__":
    unittest.main()
