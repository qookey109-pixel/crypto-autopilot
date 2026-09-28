from __future__ import annotations

import sqlite3
import threading
from unittest.mock import patch
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import (
    D1CloudBudgetLedger,
    D1LedgerLimits,
    D1QueryResult,
    D1UsageGuard,
    CloudflareD1QueryClient,
    D1UsagePolicy,
    D1UsageSnapshot,
    SlotUsage,
)
from crypto_autopilot.paper.cloud_budget_v0_1 import (
    BudgetBlocked,
    CloudBudgetPolicy,
    R2UsageSnapshot,
)


SLOT_MS = 15 * 60 * 1000
SLOT_OFFSET_MS = 7 * 60 * 1000
NOW = 1_789_999_620_000


def paper_slot_id(now_ms: int) -> str:
    return str((now_ms - SLOT_OFFSET_MS) // SLOT_MS)
MIGRATION = (
    Path(__file__).parents[1]
    / "migrations"
    / "cloud_paper_budget_ledger_v0_1.sql"
).read_text(encoding="utf-8")


class SQLiteQueryClient:
    """Cloud CI-only SQLite analogue for D1's single-writer statement behavior."""

    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:", check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(MIGRATION)
        self.lock = threading.Lock()

    def query(self, sql: str, params: tuple[object, ...]) -> D1QueryResult:
        with self.lock:
            cursor = self.connection.execute(sql, params)
            rows = tuple(dict(row) for row in cursor.fetchall())
            written = max(cursor.rowcount, 0)
            return D1QueryResult(rows, rows_read=0, rows_written=written)


def snapshot(*, at_ms: int = NOW, **changes: object) -> R2UsageSnapshot:
    base = R2UsageSnapshot(
        account_wide=True,
        reservation_coverage_complete=True,
        observed_at_ms=at_ms,
        measured_through_ms=at_ms,
        storage_bytes=0,
        class_a_month=0,
        class_b_month=0,
        class_a_31_days=0,
        class_b_31_days=0,
        class_a_day=0,
        class_b_day=0,
        provider_requests_day=0,
        new_bytes_day=0,
    )
    from dataclasses import replace

    return replace(base, **changes)


def policy(**changes: object) -> CloudBudgetPolicy:
    base = CloudBudgetPolicy(
        provider_per_run=2,
        provider_per_day=8,
        r2_class_a_per_run=2,
        r2_class_b_per_run=2,
        r2_new_bytes_per_run=10,
        r2_class_a_per_day=4,
        r2_class_b_per_day=4,
        r2_new_bytes_per_day=40,
        r2_class_a_per_31_days=20,
        r2_class_b_per_31_days=20,
        project_class_a_per_month=20,
        project_class_b_per_month=20,
        free_class_a_per_month=30,
        free_class_b_per_month=30,
        r2_hard_stop_bytes=100,
        r2_object_max_bytes=10,
    )
    from dataclasses import replace

    return replace(base, **changes)


class D1CloudBudgetLedgerTests(unittest.TestCase):
    def make_ledger(self, client: SQLiteQueryClient, **policy_changes: object):
        return D1CloudBudgetLedger(
            client,
            policy=policy(**policy_changes),
            limits=D1LedgerLimits(max_rows_read_per_request=4_000),
        )

    def test_slot_reservation_is_atomic_and_daily_budget_is_shared(self):
        client = SQLiteQueryClient()
        ledger = self.make_ledger(client)
        first_ms = NOW
        second_ms = NOW + SLOT_MS
        third_ms = NOW + 2 * SLOT_MS
        ledger.reserve_slot(
            slot_id=paper_slot_id(first_ms), run_id="run-1",
            now_ms=first_ms, snapshot=snapshot(at_ms=first_ms),
        )
        ledger.reserve_slot(
            slot_id=paper_slot_id(second_ms), run_id="run-2",
            now_ms=second_ms, snapshot=snapshot(at_ms=second_ms),
        )
        with self.assertRaisesRegex(BudgetBlocked, "RESERVATION_REJECTED"):
            ledger.reserve_slot(
                slot_id=paper_slot_id(third_ms), run_id="run-3",
                now_ms=third_ms, snapshot=snapshot(at_ms=third_ms),
            )
        count = client.connection.execute(
            "SELECT reservation_count FROM cloud_paper_budget_meta WHERE singleton = 1"
        ).fetchone()[0]
        self.assertEqual(count, 2)

    def test_duplicate_slot_cannot_reserve_or_replay(self):
        client = SQLiteQueryClient()
        ledger = self.make_ledger(client)
        slot = paper_slot_id(NOW)
        ledger.reserve_slot(
            slot_id=slot, run_id="run-1", now_ms=NOW, snapshot=snapshot(),
        )
        with self.assertRaisesRegex(BudgetBlocked, "RESERVATION_REJECTED"):
            ledger.reserve_slot(
                slot_id=slot, run_id="run-2", now_ms=NOW, snapshot=snapshot(),
            )

    def test_noncanonical_slot_rejected_before_d1_query(self):
        client = SQLiteQueryClient()
        ledger = self.make_ledger(client)
        with self.assertRaisesRegex(BudgetBlocked, "SLOT_ID_INVALID"):
            ledger.reserve_slot(
                slot_id="custom-slot", run_id="run-custom",
                now_ms=NOW, snapshot=snapshot(),
            )
        with self.assertRaisesRegex(BudgetBlocked, "SLOT_ID_INVALID"):
            ledger.reserve_slot(
                slot_id=paper_slot_id(NOW), run_id="run-off-schedule",
                now_ms=NOW + 1, snapshot=snapshot(),
            )
        self.assertEqual(
            client.connection.execute(
                "SELECT reservation_count FROM cloud_paper_budget_meta WHERE singleton = 1"
            ).fetchone()[0],
            0,
        )

    def test_bounded_d1_read_envelope_fits_96_slot_two_query_ceiling(self):
        per_query = D1UsagePolicy().rows_read_per_query
        self.assertEqual(per_query, D1LedgerLimits().max_rows_read_per_request)
        daily_envelope = 96 * 2 * per_query
        self.assertEqual(daily_envelope, 768_000)
        self.assertLess(daily_envelope, D1UsagePolicy().rows_read_per_day)

    def test_settlement_releases_only_unused_envelope(self):
        client = SQLiteQueryClient()
        ledger = self.make_ledger(client)
        first_ms, second_ms, third_ms = NOW, NOW + SLOT_MS, NOW + 2 * SLOT_MS
        first_slot = paper_slot_id(first_ms)
        ledger.reserve_slot(
            slot_id=first_slot, run_id="run-1",
            now_ms=first_ms, snapshot=snapshot(at_ms=first_ms),
        )
        ledger.settle_slot(
            slot_id=first_slot,
            completed_at_ms=first_ms + 1,
            usage=SlotUsage(provider_requests=1, class_a=1, class_b=1, new_bytes=1),
        )
        ledger.reserve_slot(
            slot_id=paper_slot_id(second_ms), run_id="run-2",
            now_ms=second_ms, snapshot=snapshot(at_ms=second_ms),
        )
        with self.assertRaisesRegex(BudgetBlocked, "RESERVATION_REJECTED"):
            ledger.reserve_slot(
                slot_id=paper_slot_id(third_ms), run_id="run-3",
                now_ms=third_ms, snapshot=snapshot(at_ms=third_ms),
            )

    def test_unsettled_slot_keeps_the_full_reservation(self):
        client = SQLiteQueryClient()
        ledger = self.make_ledger(client)
        next_ms = NOW + SLOT_MS
        ledger.reserve_slot(
            slot_id=paper_slot_id(NOW), run_id="run-1",
            now_ms=NOW, snapshot=snapshot(),
        )
        with self.assertRaisesRegex(BudgetBlocked, "RESERVATION_REJECTED"):
            ledger.reserve_slot(
                slot_id=paper_slot_id(next_ms), run_id="run-2",
                now_ms=next_ms, snapshot=snapshot(at_ms=next_ms, class_a_day=2),
            )

    def test_monthly_headroom_includes_other_slot_reservations(self):
        client = SQLiteQueryClient()
        ledger = self.make_ledger(client)
        next_ms = NOW + SLOT_MS
        ledger.reserve_slot(
            slot_id=paper_slot_id(NOW), run_id="run-1",
            now_ms=NOW, snapshot=snapshot(),
        )
        with self.assertRaisesRegex(BudgetBlocked, "RESERVATION_REJECTED"):
            ledger.reserve_slot(
                slot_id=paper_slot_id(next_ms), run_id="run-2",
                now_ms=next_ms, snapshot=snapshot(at_ms=next_ms, class_a_month=18),
            )

    def test_storage_hard_stop_includes_other_slot_reservations(self):
        client = SQLiteQueryClient()
        ledger = self.make_ledger(client)
        next_ms = NOW + SLOT_MS
        ledger.reserve_slot(
            slot_id=paper_slot_id(NOW), run_id="run-1",
            now_ms=NOW, snapshot=snapshot(),
        )
        with self.assertRaisesRegex(BudgetBlocked, "RESERVATION_REJECTED"):
            ledger.reserve_slot(
                slot_id=paper_slot_id(next_ms), run_id="run-2",
                now_ms=next_ms,
                snapshot=snapshot(at_ms=next_ms, storage_bytes=81),
            )

    def test_missing_incomplete_or_stale_account_evidence_blocks_before_io(self):
        client = SQLiteQueryClient()
        ledger = self.make_ledger(client)
        cases = (
            snapshot(account_wide=False),
            snapshot(reservation_coverage_complete=False),
            snapshot(measured_through_ms=NOW - 51_000),
        )
        for index, evidence in enumerate(cases):
            with self.subTest(index=index):
                with self.assertRaises(BudgetBlocked):
                    ledger.reserve_slot(
                        slot_id=paper_slot_id(NOW),
                        run_id=f"run-{index}",
                        now_ms=NOW,
                        snapshot=evidence,
                    )
        count = client.connection.execute(
            "SELECT reservation_count FROM cloud_paper_budget_meta WHERE singleton = 1"
        ).fetchone()[0]
        self.assertEqual(count, 0)

    def test_exhausted_ledger_row_ceiling_fails_closed(self):
        client = SQLiteQueryClient()
        client.connection.execute(
            "UPDATE cloud_paper_budget_meta SET reservation_count = 100000 WHERE singleton = 1"
        )
        ledger = self.make_ledger(client)
        with self.assertRaisesRegex(BudgetBlocked, "RESERVATION_REJECTED"):
            ledger.reserve_slot(
                slot_id=paper_slot_id(NOW), run_id="run-1",
                now_ms=NOW, snapshot=snapshot(),
            )

    def test_concurrent_slots_cannot_overreserve(self):
        client = SQLiteQueryClient()
        ledger = self.make_ledger(client)

        def reserve(index: int) -> bool:
            now_ms = NOW + index * SLOT_MS
            try:
                ledger.reserve_slot(
                    slot_id=paper_slot_id(now_ms),
                    run_id=f"run-{index}",
                    now_ms=now_ms,
                    snapshot=snapshot(at_ms=now_ms),
                )
            except BudgetBlocked:
                return False
            return True

        with ThreadPoolExecutor(max_workers=8) as executor:
            accepted = list(executor.map(reserve, range(8)))
        self.assertEqual(sum(accepted), 2)
        count = client.connection.execute(
            "SELECT reservation_count FROM cloud_paper_budget_meta WHERE singleton = 1"
        ).fetchone()[0]
        self.assertEqual(count, 2)


class D1UsageGuardTests(unittest.TestCase):
    def make_guard(self, *, snapshot_changes=None, policy_changes=None, clock_ms=NOW):
        from dataclasses import replace

        evidence = D1UsageSnapshot(
            account_wide=True,
            reservation_coverage_complete=True,
            observed_at_ms=NOW,
            measured_through_ms=NOW,
            rows_read_day=0,
            rows_written_day=0,
            storage_bytes=0,
        )
        limits = D1UsagePolicy(
            rows_read_per_day=200,
            rows_written_per_day=20,
            storage_bytes_total=50_000,
            rows_read_per_query=100,
            rows_written_per_query=2,
            storage_growth_per_query_bytes=10,
        )
        if snapshot_changes:
            evidence = replace(evidence, **snapshot_changes)
        if policy_changes:
            limits = replace(limits, **policy_changes)
        return D1UsageGuard(
            snapshot=evidence,
            clock_ms=lambda: clock_ms,
            policy=limits,
        )

    def test_query_reservations_accumulate_within_guard(self):
        guard = self.make_guard()
        guard.reserve_query()
        guard.reserve_query()
        with self.assertRaisesRegex(BudgetBlocked, "BLOCKED_D1_ROWS_READ_DAILY_LIMIT"):
            guard.reserve_query()

    def test_missing_incomplete_stale_and_future_evidence_fail_closed(self):
        cases = (
            ({"account_wide": False}, NOW, "BLOCKED_D1_USAGE_EVIDENCE_INCOMPLETE"),
            (
                {"reservation_coverage_complete": False},
                NOW,
                "BLOCKED_D1_USAGE_EVIDENCE_INCOMPLETE",
            ),
            ({"measured_through_ms": NOW - 50_001}, NOW, "BLOCKED_D1_USAGE_EVIDENCE_STALE"),
            ({"observed_at_ms": NOW + 1}, NOW, "BLOCKED_D1_USAGE_EVIDENCE_FROM_FUTURE"),
            ({"rows_read_day": True}, NOW, "BLOCKED_D1_USAGE_EVIDENCE_UNKNOWN"),
        )
        for evidence, current, reason in cases:
            with self.subTest(reason=reason):
                guard = self.make_guard(snapshot_changes=evidence, clock_ms=current)
                with self.assertRaisesRegex(BudgetBlocked, reason):
                    guard.reserve_query()
                self.assertEqual(guard._reserved_reads_day, 0)

    def test_daily_write_and_storage_headroom_stop_before_reservation(self):
        guard = self.make_guard(snapshot_changes={"rows_written_day": 19})
        with self.assertRaisesRegex(
            BudgetBlocked, "BLOCKED_D1_ROWS_WRITTEN_DAILY_LIMIT"
        ):
            guard.reserve_query()
        self.assertEqual(guard._reserved_writes_day, 0)

        guard = self.make_guard(snapshot_changes={"storage_bytes": 49_991})
        with self.assertRaisesRegex(BudgetBlocked, "BLOCKED_D1_STORAGE_HARD_STOP"):
            guard.reserve_query()
        self.assertEqual(guard._reserved_storage_bytes, 0)


    def test_cloudflare_client_reserves_usage_before_http_request(self):
        class RejectingGuard:
            def reserve_query(self):
                raise BudgetBlocked("BLOCKED_D1_ROWS_READ_DAILY_LIMIT")

        client = CloudflareD1QueryClient(
            api_token="test-token",
            account_id="a" * 32,
            database_id="00000000-0000-0000-0000-000000000001",
            usage_guard=RejectingGuard(),
        )
        with patch("crypto_autopilot.paper.cloud_budget_ledger_v0_1.build_opener") as opener:
            with self.assertRaisesRegex(
                BudgetBlocked, "BLOCKED_D1_ROWS_READ_DAILY_LIMIT"
            ):
                client.query("SELECT 1", ())
        opener.assert_not_called()

    def test_invalid_policy_fails_closed(self):
        guard = self.make_guard(policy_changes={"request_timeout_reserve_ms": 60_000})
        with self.assertRaisesRegex(BudgetBlocked, "BLOCKED_D1_USAGE_POLICY_INVALID"):
            guard.reserve_query()


if __name__ == "__main__":
    unittest.main()
