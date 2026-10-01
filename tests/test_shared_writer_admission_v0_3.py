from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.shared_writer_admission_v0_3 import (
    COMPACT_EXPIRED_RESERVATIONS_SQL,
    DAILY_SHARED_AGGREGATE_SQL,
    READ_SLOT_RESERVATION_SQL,
    ROLLING_SHARED_AGGREGATE_SQL,
    WriterSlotIdentity,
    classify_reservation_replay,
    compaction_statement_params,
    minimum_compaction_rows_written,
    minimum_reservation_rows_written,
    validate_fresh_slot,
)


MIGRATION = (
    Path(__file__).parents[1]
    / "migrations"
    / "cloudflare_shared_writer_admission_v0_3.sql"
).read_text(encoding="utf-8")
NOW_MS = 1_791_234_567_000
DAY_MS = 86_400_000


class SharedWriterLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(MIGRATION)

    def tearDown(self) -> None:
        self.db.close()

    def configure(self, *, reservations: int = 8, writers: int = 3) -> None:
        self.db.execute(
            """
            UPDATE cloudflare_shared_writer_lifecycle_policy_v0_3
            SET max_active_reservations = ?,
                max_lifetime_writer_identities = ?
            WHERE policy_id = 1
            """,
            (reservations, writers),
        )

    def register(self, writer_id: str) -> None:
        self.db.execute(
            """
            INSERT INTO cloudflare_shared_writer_identities_v0_3
                (writer_id, lifecycle_state, owner_attestation_sha256, registered_at_ms)
            VALUES (?, 'ACTIVE', ?, ?)
            """,
            (writer_id, "a" * 64, NOW_MS),
        )

    def reserve(self, writer_id: str, slot_at_ms: int, *, reserved_at_ms: int | None = None) -> None:
        self.db.execute(
            """
            INSERT INTO cloudflare_shared_writer_reservations_v0_3 (
                writer_id, slot_id, idempotency_key, slot_at_ms, utc_day,
                reserved_at_ms, provider_requests, r2_class_a, r2_class_b,
                r2_new_bytes, d1_queries, d1_rows_read, d1_rows_written,
                d1_storage_growth_bytes
            ) VALUES (?, ?, ?, ?, '2026-10-02', ?, 1, 1, 0, 100, 2, 20, 7, 256)
            """,
            (
                writer_id,
                f"slot:{slot_at_ms}",
                f"slot:{slot_at_ms}",
                slot_at_ms,
                slot_at_ms if reserved_at_ms is None else reserved_at_ms,
            ),
        )

    def retained_count(self) -> int:
        return int(
            self.db.execute(
                """
                SELECT retained_reservations
                FROM cloudflare_shared_writer_lifecycle_policy_v0_3
                WHERE policy_id = 1
                """
            ).fetchone()[0]
        )

    def test_unconfigured_capacity_blocks_writer_and_reservation_creation(self) -> None:
        with self.assertRaisesRegex(sqlite3.IntegrityError, "BLOCKED_WRITER_IDENTITY_CAP"):
            self.register("project-a:writer")
        self.configure()
        self.register("project-a:writer")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "BLOCKED_RESERVATION_CAPACITY"):
            self.reserve("project-a:writer", NOW_MS)

    def test_writer_scoped_identity_allows_shared_slot_and_exact_slot_is_unique(self) -> None:
        self.configure()
        self.register("project-a:writer")
        self.register("project-b:writer")
        self.reserve("project-a:writer", NOW_MS)
        self.reserve("project-b:writer", NOW_MS)
        self.assertEqual(self.retained_count(), 2)
        with self.assertRaises(sqlite3.IntegrityError):
            self.reserve("project-a:writer", NOW_MS)

    def test_budget_aggregates_include_all_registered_writers(self) -> None:
        self.configure()
        self.register("project-a:writer")
        self.register("project-b:writer")
        self.reserve("project-a:writer", NOW_MS)
        self.reserve("project-b:writer", NOW_MS + 1)
        daily = self.db.execute(DAILY_SHARED_AGGREGATE_SQL, ("2026-10-02",)).fetchone()
        rolling = self.db.execute(
            ROLLING_SHARED_AGGREGATE_SQL,
            (NOW_MS - 31 * DAY_MS, NOW_MS + 1),
        ).fetchone()
        self.assertEqual((daily["reservations"], daily["provider_requests"]), (2, 2))
        self.assertEqual((daily["r2_class_a"], daily["d1_rows_written"]), (2, 14))
        self.assertEqual((rolling["reservations"], rolling["r2_class_a"]), (2, 2))

    def test_capacity_is_released_only_by_triggered_retention_delete(self) -> None:
        self.configure(reservations=2)
        self.register("project-a:writer")
        expired_slot = NOW_MS - 32 * DAY_MS
        self.reserve("project-a:writer", expired_slot)
        self.reserve("project-a:writer", expired_slot + 1)
        with self.assertRaisesRegex(sqlite3.IntegrityError, "BLOCKED_RESERVATION_CAPACITY"):
            self.reserve("project-a:writer", NOW_MS)
        result = self.db.execute(
            """
            DELETE FROM cloudflare_shared_writer_reservations_v0_3
            WHERE rowid = (
                SELECT rowid
                FROM cloudflare_shared_writer_reservations_v0_3
                WHERE reserved_at_ms < ?
                ORDER BY reserved_at_ms
                LIMIT 1
            )
            RETURNING slot_id
            """,
            (NOW_MS - 31 * DAY_MS,),
        ).fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(self.retained_count(), 1)
        self.reserve("project-a:writer", NOW_MS)
        self.assertEqual(self.retained_count(), 2)

    def test_compaction_is_bounded_and_keeps_the_inclusive_31_day_boundary(self) -> None:
        self.configure(reservations=10)
        self.register("project-a:writer")
        expired_a = NOW_MS - 33 * DAY_MS
        expired_b = NOW_MS - 32 * DAY_MS
        boundary = NOW_MS - 31 * DAY_MS
        self.reserve("project-a:writer", expired_a)
        self.reserve("project-a:writer", expired_b)
        self.reserve("project-a:writer", boundary)
        params = compaction_statement_params(
            now_ms=NOW_MS,
            max_deleted_rows=1,
            compaction_authorized=True,
            reserved_rows_written=minimum_compaction_rows_written(1),
        )
        deleted = self.db.execute(
            COMPACT_EXPIRED_RESERVATIONS_SQL, params
        ).fetchall()
        self.assertEqual(len(deleted), 1)
        self.assertEqual(self.retained_count(), 2)
        remaining = self.db.execute(
            "SELECT slot_at_ms FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchall()
        self.assertEqual({int(row[0]) for row in remaining}, {expired_b, boundary})
        watermark = self.db.execute(
            """
            SELECT retired_through_slot_at_ms, retired_reservation_count
            FROM cloudflare_shared_writer_retirement_watermarks_v0_3
            WHERE writer_id = 'project-a:writer'
            """
        ).fetchone()
        self.assertEqual(tuple(watermark), (expired_a, 1))

    def test_purged_slot_cannot_be_reintroduced_as_a_stale_replay(self) -> None:
        self.configure()
        self.register("project-a:writer")
        old_slot = NOW_MS - 32 * DAY_MS
        self.reserve("project-a:writer", old_slot)
        self.db.execute(
            """
            DELETE FROM cloudflare_shared_writer_reservations_v0_3
            WHERE reserved_at_ms < ?
            """,
            (NOW_MS - 31 * DAY_MS,),
        )
        with self.assertRaisesRegex(sqlite3.IntegrityError, "BLOCKED_STALE_WRITER_SLOT"):
            self.reserve("project-a:writer", old_slot)

    def test_compaction_requires_explicit_authority_finite_cap_and_budget(self) -> None:
        with self.assertRaisesRegex(BudgetBlocked, "BLOCKED_COMPACTION_AUTHORITY_REQUIRED"):
            compaction_statement_params(
                now_ms=NOW_MS,
                max_deleted_rows=1,
                compaction_authorized=False,
                reserved_rows_written=100,
            )
        with self.assertRaisesRegex(BudgetBlocked, "BLOCKED_COMPACTION_BATCH_CAP_REQUIRED"):
            compaction_statement_params(
                now_ms=NOW_MS,
                max_deleted_rows=None,
                compaction_authorized=True,
                reserved_rows_written=100,
            )
        with self.assertRaisesRegex(BudgetBlocked, "BLOCKED_COMPACTION_WRITE_ENVELOPE"):
            compaction_statement_params(
                now_ms=NOW_MS,
                max_deleted_rows=2,
                compaction_authorized=True,
                reserved_rows_written=minimum_compaction_rows_written(2) - 1,
            )

    def test_slot_identity_and_retirement_watermark_are_fail_closed(self) -> None:
        identity = WriterSlotIdentity(
            writer_id="project-a:writer",
            slot_id=f"slot:{NOW_MS}",
            idempotency_key=f"slot:{NOW_MS}",
            slot_at_ms=NOW_MS,
        )
        validate_fresh_slot(
            identity,
            now_ms=NOW_MS + 1_000,
            max_slot_age_ms=60_000,
            max_future_skew_ms=0,
            retired_through_slot_at_ms=NOW_MS - 1,
        )
        with self.assertRaisesRegex(BudgetBlocked, "BLOCKED_STALE_WRITER_SLOT"):
            validate_fresh_slot(
                identity,
                now_ms=NOW_MS + 1_000,
                max_slot_age_ms=60_000,
                max_future_skew_ms=0,
                retired_through_slot_at_ms=NOW_MS,
            )
        with self.assertRaisesRegex(ValueError, "WRITER_IDEMPOTENCY_KEY_MUST_EQUAL_SLOT"):
            validate_fresh_slot(
                WriterSlotIdentity(
                    writer_id="project-a:writer",
                    slot_id=f"slot:{NOW_MS}",
                    idempotency_key="different-key",
                    slot_at_ms=NOW_MS,
                ),
                now_ms=NOW_MS,
                max_slot_age_ms=60_000,
                max_future_skew_ms=0,
                retired_through_slot_at_ms=None,
            )

    def test_exact_retained_replay_returns_existing_without_freshness_rejection(self) -> None:
        self.configure()
        self.register("project-a:writer")
        old_slot = NOW_MS - 32 * DAY_MS
        self.reserve("project-a:writer", old_slot)
        identity = WriterSlotIdentity(
            writer_id="project-a:writer",
            slot_id=f"slot:{old_slot}",
            idempotency_key=f"slot:{old_slot}",
            slot_at_ms=old_slot,
        )
        row = self.db.execute(
            READ_SLOT_RESERVATION_SQL, (identity.writer_id, identity.slot_id)
        ).fetchone()
        proposed = dict(row)
        self.assertEqual(
            classify_reservation_replay(
                identity, proposed, dict(row), now_ms=NOW_MS,
                max_slot_age_ms=31 * DAY_MS, max_future_skew_ms=0,
                retired_through_slot_at_ms=None,
            ),
            "RETURN_EXISTING",
        )
        changed = dict(proposed)
        changed["d1_rows_written"] = int(changed["d1_rows_written"]) + 1
        with self.assertRaisesRegex(BudgetBlocked, "BLOCKED_IDEMPOTENCY_CONFLICT"):
            classify_reservation_replay(
                identity, changed, dict(row), now_ms=NOW_MS,
                max_slot_age_ms=31 * DAY_MS, max_future_skew_ms=0,
                retired_through_slot_at_ms=None,
            )

    def test_missing_old_replay_is_rejected_after_compaction(self) -> None:
        identity = WriterSlotIdentity(
            writer_id="project-a:writer",
            slot_id="slot:1000",
            idempotency_key="slot:1000",
            slot_at_ms=1000,
        )
        with self.assertRaisesRegex(BudgetBlocked, "BLOCKED_STALE_WRITER_SLOT"):
            classify_reservation_replay(
                identity, {
                    "writer_id": identity.writer_id,
                    "slot_id": identity.slot_id,
                    "idempotency_key": identity.idempotency_key,
                    "slot_at_ms": identity.slot_at_ms,
                    "utc_day": "1970-01-01",
                    "reserved_at_ms": 1000,
                    "provider_requests": 0,
                    "r2_class_a": 0,
                    "r2_class_b": 0,
                    "r2_new_bytes": 0,
                    "d1_queries": 0,
                    "d1_rows_read": 0,
                    "d1_rows_written": 0,
                    "d1_storage_growth_bytes": 0,
                }, None, now_ms=NOW_MS, max_slot_age_ms=31 * DAY_MS,
                max_future_skew_ms=0, retired_through_slot_at_ms=None,
            )

    def test_cost_floors_include_admission_compaction_trigger_and_index_rows(self) -> None:
        self.assertEqual(minimum_reservation_rows_written(), 7)
        self.assertEqual(minimum_compaction_rows_written(3), 31)


if __name__ == "__main__":
    unittest.main()
