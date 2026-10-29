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
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import READ_SHARED_WRITER_SQL
from test_prepaid_d1_runtime_v0_1 import DB_ID, NOW, PrepaidD1RuntimeTests

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

    def test_daily_shared_read_debits_before_transport(self):
        def response(sql, params):
            self.assertEqual(self.meter.report()["query_attempts_charged"], 1)
            return D1QueryResult((), 1, 0), 1024
        with patch.object(self.client, "_request", side_effect=response) as send:
            self.client.query(READ_SHARED_WRITER_SQL, (WRITER, self.slot))
        send.assert_called_once()

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
