"""Synthetic prepaid D1 tests for the research writer's daily UTC slot."""
import unittest
from unittest.mock import patch

from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import (
    D1LedgerUnavailable, D1QueryResult, READ_SLOT_RESERVATION_SQL,
)
from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.prepaid_query_controller_v0_1 import (
    AllocationEvidence, claim_prepaid_query_meter,
)
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import (
    READ_SHARED_WRITER_SQL, RESERVE_SHARED_WRITER_SQL,
    SharedWriterReservation, reservation_params, reserve_shared_writer_envelope,
)
from test_prepaid_d1_runtime_v0_1 import DB_ID, NOW, PrepaidD1RuntimeTests
from test_prepaid_query_controller_v0_1 import FakeGitHub

try:
    from crypto_autopilot.research.prepaid_research_d1_v0_1 import ResearchPrepaidD1Client, WRITER
except ModuleNotFoundError as exc:
    if exc.name != "crypto_autopilot.research.prepaid_research_d1_v0_1":
        raise
    ResearchPrepaidD1Client = None
    WRITER = "crypto-autopilot:research-signal-layer-v0-2"


class DailyResearchD1Tests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(ResearchPrepaidD1Client)
        self.f = PrepaidD1RuntimeTests("test_meter_readonly_checks_never_debit_or_refresh")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.f.now = NOW + 600_000  # 02:17 UTC, not a Cloud Paper 15-minute slot.
        self.f.authority["writers"][0]["writer_id"] = WRITER
        self.f.github = FakeGitHub(self.f.authority)
        self.f._set_run(101)
        self.slot = f"slot:{self.f.now}"
        self.meter = claim_prepaid_query_meter(
            authority_document=self.f.authority, writer_id=WRITER,
            slot_id=self.slot, run_id=101, transport=self.f.github,
            evidence=AllocationEvidence(
                account_coverage_complete=True, zero_cost_verified=True,
                observed_at_ms=self.f.now, measured_through_ms=self.f.now,
                available={"queries": 1000, "rows_read": 1000000,
                           "rows_written": 10000, "storage_bytes": 10000000},
            ), clock_ms=lambda: self.f.now,
        )
        self.client = ResearchPrepaidD1Client(
            api_token="synthetic-token", account_id="a" * 32, database_id=DB_ID,
            usage_guard=self.f.make_guard(), query_meter=self.meter,
            writer_id=WRITER, slot_id=self.slot,
            database_evidence=self.f.database_evidence(),
        )

    def test_v05_admission_uses_prepaid_research_client_and_deduplicates(self):
        db = self.f.sqlite()
        db.execute("INSERT INTO cloudflare_shared_writer_identities_v0_3 VALUES (?, 'ACTIVE', ?, ?)",
                   (WRITER, "a" * 64, self.f.now))
        envelope = self.meter.report()["ticket_envelope_charged_in_full"]
        reservation = SharedWriterReservation(
            writer_id=WRITER, slot_id=self.slot, idempotency_key=self.slot,
            slot_at_ms=self.f.now, reserved_at_ms=self.f.now, provider_requests=3,
            r2_class_a=3, r2_class_b=6, r2_new_bytes=270336,
            d1_queries=envelope["queries"], d1_rows_read=envelope["rows_read"],
            d1_rows_written=envelope["rows_written"],
            d1_storage_growth_bytes=envelope["storage_bytes"],
        )
        def sqlite_request(sql, params):
            cursor = db.execute(sql, params)
            columns = tuple(column[0] for column in cursor.description or ())
            rows = tuple(dict(zip(columns, row, strict=True)) for row in cursor.fetchall())
            db.commit()
            writes = 0 if sql == READ_SHARED_WRITER_SQL else 7
            return D1QueryResult(rows, 1, writes), 1024
        with patch(
            "crypto_autopilot.paper.prepaid_d1_client_v0_1.PrepaidCloudflareD1QueryClient._request",
            side_effect=sqlite_request,
        ):
            result = reserve_shared_writer_envelope(
                execute=self.client.query, query_meter=self.meter, reservation=reservation,
                clock_ms=lambda: self.f.now, execution_enabled=True,
            )
            duplicate = reserve_shared_writer_envelope(
                execute=self.client.query, query_meter=self.meter, reservation=reservation,
                clock_ms=lambda: self.f.now, execution_enabled=True,
            )
        self.assertEqual(result, "RESERVED")
        self.assertEqual(duplicate, "EXISTING_RESERVATION")
        self.assertEqual(db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3 WHERE writer_id=?",
            (WRITER,),
        ).fetchone()[0], 1)
        self.assertEqual(self.meter.report()["query_attempts_charged"], 6)

    def test_daily_shared_read_debits_before_transport(self):
        def response(sql, params):
            self.assertEqual(self.meter.report()["query_attempts_charged"], 1)
            return D1QueryResult((), 1, 0), 1024
        with patch.object(self.client, "_request", side_effect=response) as send:
            self.client.query(READ_SHARED_WRITER_SQL, (WRITER, self.slot))
        send.assert_called_once()

    def test_fresh_ticket_cannot_fund_historical_or_future_slot(self):
        for value in (self.f.now - 86_400_000, self.f.now + 86_400_000):
            slot = f"slot:{value}"
            github = FakeGitHub(self.f.authority)
            stamp = "2026-10-03T02:17:00Z"
            github.runs[101]["run_started_at"] = stamp
            github.runs[101]["created_at"] = stamp
            meter = claim_prepaid_query_meter(
                authority_document=self.f.authority, writer_id=WRITER, slot_id=slot,
                run_id=101, transport=github, clock_ms=lambda: self.f.now,
                evidence=AllocationEvidence(
                    account_coverage_complete=True, zero_cost_verified=True,
                    observed_at_ms=self.f.now, measured_through_ms=self.f.now,
                    available={"queries": 1000, "rows_read": 1000000,
                               "rows_written": 10000, "storage_bytes": 10000000},
                ),
            )
            client = ResearchPrepaidD1Client(
                api_token="synthetic-token", account_id="a" * 32, database_id=DB_ID,
                usage_guard=self.f.make_guard(), query_meter=meter, writer_id=WRITER,
                slot_id=slot, database_evidence=self.f.database_evidence(),
            )
            with self.subTest(slot=slot), patch.object(client, "_request") as send:
                with self.assertRaises(BudgetBlocked):
                    client.query(READ_SHARED_WRITER_SQL, (WRITER, slot))
                send.assert_not_called()
            self.assertEqual(meter.report()["query_attempts_charged"], 0)

    def test_crossing_cutoff_after_debit_never_sends_d1_request(self):
        self.f.now += 599_999
        github = FakeGitHub(self.f.authority)
        stamp = "2026-10-03T02:26:59.999000Z"
        github.runs[101]["run_started_at"] = stamp
        github.runs[101]["created_at"] = stamp
        meter = claim_prepaid_query_meter(
            authority_document=self.f.authority, writer_id=WRITER, slot_id=self.slot,
            run_id=101, transport=github, clock_ms=lambda: self.f.now,
            evidence=AllocationEvidence(
                account_coverage_complete=True, zero_cost_verified=True,
                observed_at_ms=self.f.now, measured_through_ms=self.f.now,
                available={"queries": 1000, "rows_read": 1000000,
                           "rows_written": 10000, "storage_bytes": 10000000},
            ),
        )
        client = ResearchPrepaidD1Client(
            api_token="synthetic-token", account_id="a" * 32, database_id=DB_ID,
            usage_guard=self.f.make_guard(), query_meter=meter, writer_id=WRITER,
            slot_id=self.slot, database_evidence=self.f.database_evidence(),
        )
        charge = meter.charge_before_query
        def cross_cutoff(**kwargs):
            result = charge(**kwargs)
            self.f.now += 2
            return result
        with patch.object(meter, "charge_before_query", side_effect=cross_cutoff), patch(
            "crypto_autopilot.paper.prepaid_d1_client_v0_1.PrepaidCloudflareD1QueryClient._request"
        ) as send:
            with self.assertRaises(D1LedgerUnavailable):
                client.query(READ_SHARED_WRITER_SQL, (WRITER, self.slot))
            send.assert_not_called()
        self.assertEqual(meter.report()["query_attempts_charged"], 1)
        self.assertTrue(client.diagnostics()["review_required"])

    def test_valid_reservation_is_accepted_once_with_prepaid_debit(self):
        envelope = self.meter.report()["ticket_envelope_charged_in_full"]
        reservation = SharedWriterReservation(
            writer_id=WRITER, slot_id=self.slot, idempotency_key=self.slot,
            slot_at_ms=self.f.now, reserved_at_ms=self.f.now, provider_requests=3,
            r2_class_a=3, r2_class_b=6, r2_new_bytes=270336,
            d1_queries=envelope["queries"], d1_rows_read=envelope["rows_read"],
            d1_rows_written=envelope["rows_written"],
            d1_storage_growth_bytes=envelope["storage_bytes"],
        )
        def response(sql, params):
            self.assertEqual(self.meter.report()["query_attempts_charged"], 1)
            return D1QueryResult(({"writer_id": WRITER, "slot_id": self.slot},), 1, 7), 1024
        with patch.object(self.client, "_request", side_effect=response) as send:
            result = self.client.query(RESERVE_SHARED_WRITER_SQL, reservation_params(reservation))
        self.assertEqual(result.rows[0]["slot_id"], self.slot)
        send.assert_called_once()

    def test_daily_slot_rejects_future_or_wrong_grid_before_network(self):
        for value in (self.f.now - 86_400_000, self.f.now + 86_400_000, self.f.now + 60_000):
            other_slot = f"slot:{value}"
            with self.subTest(slot=other_slot), self.assertRaises(BudgetBlocked):
                ResearchPrepaidD1Client(
                    api_token="synthetic-token", account_id="a" * 32, database_id=DB_ID,
                    usage_guard=self.f.make_guard(), query_meter=self.meter,
                    writer_id=WRITER, slot_id=other_slot,
                    database_evidence=self.f.database_evidence(),
                )
        self.assertEqual(self.meter.report()["query_attempts_charged"], 0)

    def test_reservation_rejects_tampered_windows_and_envelope_before_debit(self):
        envelope = self.meter.report()["ticket_envelope_charged_in_full"]
        reservation = SharedWriterReservation(
            writer_id=WRITER, slot_id=self.slot, idempotency_key=self.slot,
            slot_at_ms=self.f.now, reserved_at_ms=self.f.now, provider_requests=3,
            r2_class_a=3, r2_class_b=6, r2_new_bytes=270336,
            d1_queries=envelope["queries"], d1_rows_read=envelope["rows_read"],
            d1_rows_written=envelope["rows_written"],
            d1_storage_growth_bytes=envelope["storage_bytes"],
        )
        good = reservation_params(reservation)
        for index in (0, 1, 2, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16):
            params = list(good)
            params[index] = "invalid" if isinstance(params[index], str) else params[index] + 1
            with self.subTest(index=index), self.assertRaises((BudgetBlocked, D1LedgerUnavailable)):
                self.client.query(RESERVE_SHARED_WRITER_SQL, tuple(params))
        self.assertEqual(self.meter.report()["query_attempts_charged"], 0)

    def test_stale_slot_blocks_before_debit(self):
        self.f.now += 600_001
        with self.assertRaises((BudgetBlocked, D1LedgerUnavailable)):
            self.client._validate_statement(READ_SHARED_WRITER_SQL, (WRITER, self.slot))
        self.assertEqual(self.meter.report()["query_attempts_charged"], 0)

    def test_other_slot_writer_or_legacy_sql_is_blocked_before_debit(self):
        invalid = (
            (READ_SHARED_WRITER_SQL, ("other", self.slot)),
            (READ_SHARED_WRITER_SQL, (WRITER, "slot:1")),
            (READ_SLOT_RESERVATION_SQL, ("1",)),
        )
        with patch.object(self.client, "_request") as send:
            for sql, params in invalid:
                with self.subTest(sql=sql, params=params):
                    with self.assertRaises((BudgetBlocked, D1LedgerUnavailable)):
                        self.client.query(sql, params)
        send.assert_not_called()
        self.assertEqual(self.meter.report()["query_attempts_charged"], 0)


if __name__ == "__main__":
    unittest.main()
