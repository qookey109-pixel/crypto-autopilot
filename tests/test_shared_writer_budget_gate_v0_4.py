from __future__ import annotations

import sqlite3
import unittest
from dataclasses import replace
from pathlib import Path

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import (
    SharedWriterReservation,
    reserve_shared_writer_envelope,
)

ROOT = Path(__file__).parents[1]
BASE_MIGRATION = (ROOT / "migrations" / "cloudflare_shared_writer_admission_v0_3.sql").read_text()
POLICY_MIGRATION = (ROOT / "migrations" / "cloudflare_shared_writer_budget_policy_v0_4.sql").read_text()
NOW_MS = 1_791_234_567_000


class SQLiteQuery:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def __call__(self, sql: str, params: tuple[object, ...]):
        cursor = self.db.execute(sql, params)
        columns = tuple(column[0] for column in cursor.description or ())
        rows = tuple(dict(zip(columns, row, strict=True)) for row in cursor.fetchall())
        return type("Result", (), {"rows": rows})()


class SharedWriterBudgetGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(BASE_MIGRATION)
        self.db.executescript(POLICY_MIGRATION)
        self.db.execute(
            """UPDATE cloudflare_shared_writer_lifecycle_policy_v0_3
               SET max_active_reservations=20, max_lifetime_writer_identities=10
               WHERE policy_id=1"""
        )
        self.db.execute(
            """UPDATE cloudflare_shared_writer_budget_policy_v0_4 SET
               max_reservations_per_utc_day=10,
               provider_requests_per_utc_day=10,
               r2_class_a_per_utc_day=10,
               r2_class_b_per_utc_day=10,
               r2_new_bytes_per_utc_day=10000,
               d1_queries_per_utc_day=100,
               d1_rows_read_per_utc_day=1000,
               d1_rows_written_per_utc_day=1000,
               d1_storage_growth_bytes_per_utc_day=100000,
               r2_class_a_per_rolling_31_days=100,
               r2_class_b_per_rolling_31_days=100,
               r2_new_bytes_per_rolling_31_days=100000
               WHERE policy_id=1"""
        )
        self.register("project-a:writer")
        self.register("project-b:writer")
        self.query = SQLiteQuery(self.db)

    def tearDown(self) -> None:
        self.db.close()

    def register(self, writer_id: str, state: str = "ACTIVE") -> None:
        self.db.execute(
            """INSERT INTO cloudflare_shared_writer_identities_v0_3
               (writer_id,lifecycle_state,owner_attestation_sha256,registered_at_ms)
               VALUES (?,?,?,?)""",
            (writer_id, state, "a" * 64, NOW_MS),
        )

    def reservation(self, writer_id: str, slot_at_ms: int, *, provider: int = 1, class_a: int = 1, bytes_new: int = 100) -> SharedWriterReservation:
        slot = f"slot:{slot_at_ms}"
        return SharedWriterReservation(
            writer_id=writer_id, slot_id=slot, idempotency_key=slot,
            slot_at_ms=slot_at_ms, reserved_at_ms=slot_at_ms,
            provider_requests=provider, r2_class_a=class_a, r2_class_b=0,
            r2_new_bytes=bytes_new, d1_queries=2, d1_rows_read=20,
            d1_rows_written=7, d1_storage_growth_bytes=128,
        )

    def test_null_policy_blocks_without_inserting(self) -> None:
        self.db.execute(
            "UPDATE cloudflare_shared_writer_budget_policy_v0_4 SET provider_requests_per_utc_day=NULL"
        )
        with self.assertRaisesRegex(BudgetBlocked, "POLICY_OR_WRITER_GATE"):
            reserve_shared_writer_envelope(
                execute=self.query, reservation=self.reservation("project-a:writer", NOW_MS),
            )
        count = self.db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0]
        self.assertEqual(count, 0)

    def test_daily_budget_is_shared_across_registered_writers(self) -> None:
        self.db.execute(
            "UPDATE cloudflare_shared_writer_budget_policy_v0_4 SET provider_requests_per_utc_day=1"
        )
        reserve_shared_writer_envelope(
            execute=self.query, reservation=self.reservation("project-a:writer", NOW_MS),
        )
        with self.assertRaisesRegex(BudgetBlocked, "POLICY_OR_WRITER_GATE"):
            reserve_shared_writer_envelope(
                execute=self.query, reservation=self.reservation("project-b:writer", NOW_MS + 1),
            )

    def test_rolling_cap_is_account_shared(self) -> None:
        self.db.execute(
            "UPDATE cloudflare_shared_writer_budget_policy_v0_4 SET r2_class_a_per_rolling_31_days=1"
        )
        reserve_shared_writer_envelope(
            execute=self.query, reservation=self.reservation("project-a:writer", NOW_MS),
        )
        with self.assertRaisesRegex(BudgetBlocked, "POLICY_OR_WRITER_GATE"):
            reserve_shared_writer_envelope(
                execute=self.query, reservation=self.reservation("project-b:writer", NOW_MS + 1),
            )

    def test_exact_replay_returns_existing_without_duplicate_reservation(self) -> None:
        reservation = self.reservation("project-a:writer", NOW_MS)
        self.assertEqual(
            reserve_shared_writer_envelope(execute=self.query, reservation=reservation),
            "RESERVED",
        )
        self.assertEqual(
            reserve_shared_writer_envelope(execute=self.query, reservation=reservation),
            "EXISTING_RESERVATION",
        )
        count = self.db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_changed_payload_for_same_writer_slot_blocks(self) -> None:
        reserve_shared_writer_envelope(
            execute=self.query, reservation=self.reservation("project-a:writer", NOW_MS),
        )
        with self.assertRaisesRegex(BudgetBlocked, "IDEMPOTENCY_CONFLICT"):
            reserve_shared_writer_envelope(
                execute=self.query,
                reservation=self.reservation("project-a:writer", NOW_MS, provider=2),
            )

    def test_retired_writer_cannot_reserve(self) -> None:
        self.register("project-c:retired", state="RETIRED")
        with self.assertRaisesRegex(BudgetBlocked, "POLICY_OR_WRITER_GATE"):
            reserve_shared_writer_envelope(
                execute=self.query, reservation=self.reservation("project-c:retired", NOW_MS),
            )

    def test_caller_cannot_pass_alternative_caps(self) -> None:
        with self.assertRaises(TypeError):
            reserve_shared_writer_envelope(
                execute=self.query,
                reservation=self.reservation("project-a:writer", NOW_MS),
                limits=object(),  # type: ignore[call-arg]
            )

    def test_reservation_must_cover_admission_and_ledger_write_floor(self) -> None:
        bad = replace(self.reservation("project-a:writer", NOW_MS), d1_rows_written=1)
        with self.assertRaisesRegex(ValueError, "LEDGER_COST_UNDERCOUNTED"):
            reserve_shared_writer_envelope(execute=self.query, reservation=bad)


if __name__ == "__main__":
    unittest.main()
