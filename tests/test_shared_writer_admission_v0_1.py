from __future__ import annotations

import sqlite3
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.shared_writer_admission_v0_1 import (
    SharedWriterAdmissionLimits,
    SharedWriterReservation,
    reserve_shared_writer_envelope,
)


MIGRATION = (
    Path(__file__).parents[1]
    / "migrations"
    / "cloudflare_shared_writer_admission_v0_1.sql"
).read_text(encoding="utf-8")
NOW_MS = 1_791_234_567_000


class SQLiteAdmissionClient:
    """Cloud-CI synthetic analogue; this never connects to Cloudflare."""

    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:", check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(MIGRATION)
        self.lock = threading.Lock()
        self.query_count = 0

    def __call__(self, sql: str, params: tuple[object, ...]):
        with self.lock:
            self.query_count += 1
            cursor = self.connection.execute(sql, params)
            return type(
                "Result",
                (),
                {"rows": tuple(dict(row) for row in cursor.fetchall())},
            )()


def limits(**changes: int) -> SharedWriterAdmissionLimits:
    values = {
        "max_reservations_per_utc_day": 20,
        "provider_requests_per_utc_day": 20,
        "r2_class_a_per_utc_day": 20,
        "r2_class_b_per_utc_day": 20,
        "r2_new_bytes_per_utc_day": 2000,
        "d1_queries_per_utc_day": 40,
        "d1_storage_growth_bytes_per_utc_day": 20000,
        "r2_class_a_per_rolling_31_days": 50,
        "r2_class_b_per_rolling_31_days": 50,
        "r2_new_bytes_per_rolling_31_days": 5000,
    }
    values.update(changes)
    return SharedWriterAdmissionLimits(**values)


def reservation(
    writer_id: str = "project-a:writer",
    key: str = "slot:2026-10-02T00:00:00Z",
    *,
    slot: str = "2026-10-02T00:00:00Z",
    at_ms: int = NOW_MS,
    **changes: int,
) -> SharedWriterReservation:
    values = {
        "provider_requests": 1,
        "r2_class_a": 1,
        "r2_class_b": 0,
        "r2_new_bytes": 100,
        "d1_queries": 2,
        "d1_storage_growth_bytes": 256,
    }
    values.update(changes)
    return SharedWriterReservation(
        writer_id=writer_id,
        idempotency_key=key,
        slot_id=slot,
        reserved_at_ms=at_ms,
        **values,
    )


class SharedWriterAdmissionTests(unittest.TestCase):
    def test_different_writers_can_reserve_the_same_slot(self):
        client = SQLiteAdmissionClient()
        first = reserve_shared_writer_envelope(
            execute=client, reservation=reservation("project-a:writer"),
            limits=limits(),
        )
        second = reserve_shared_writer_envelope(
            execute=client,
            reservation=reservation("project-b:writer"),
            limits=limits(),
        )
        self.assertEqual((first, second), ("RESERVED", "RESERVED"))
        count = client.connection.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_1"
        ).fetchone()[0]
        self.assertEqual(count, 2)

    def test_exact_replay_returns_existing_without_adding_usage(self):
        client = SQLiteAdmissionClient()
        entry = reservation()
        self.assertEqual(
            reserve_shared_writer_envelope(
                execute=client, reservation=entry, limits=limits(),
            ),
            "RESERVED",
        )
        before = client.connection.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_1"
        ).fetchone()[0]
        self.assertEqual(
            reserve_shared_writer_envelope(
                execute=client, reservation=entry, limits=limits(),
            ),
            "EXISTING_RESERVATION",
        )
        after = client.connection.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_1"
        ).fetchone()[0]
        self.assertEqual((before, after), (1, 1))

    def test_reusing_idempotency_key_with_changed_envelope_blocks(self):
        client = SQLiteAdmissionClient()
        reserve_shared_writer_envelope(
            execute=client, reservation=reservation(), limits=limits(),
        )
        with self.assertRaisesRegex(
            BudgetBlocked, "SHARED_WRITER_IDEMPOTENCY_CONFLICT",
        ):
            reserve_shared_writer_envelope(
                execute=client,
                reservation=reservation(provider_requests=2),
                limits=limits(),
            )

    def test_daily_budget_is_aggregated_across_writers(self):
        client = SQLiteAdmissionClient()
        cap = limits(provider_requests_per_utc_day=3)
        for writer in ("project-a:writer", "project-b:writer", "project-c:writer"):
            reserve_shared_writer_envelope(
                execute=client, reservation=reservation(writer), limits=cap,
            )
        with self.assertRaisesRegex(
            BudgetBlocked, "SHARED_ACCOUNT_BUDGET_EXCEEDED",
        ):
            reserve_shared_writer_envelope(
                execute=client,
                reservation=reservation("project-d:writer"),
                limits=cap,
            )

    def test_rolling_31_day_budget_aggregates_across_utc_days(self):
        client = SQLiteAdmissionClient()
        cap = limits(r2_class_a_per_rolling_31_days=2)
        reserve_shared_writer_envelope(
            execute=client, reservation=reservation(), limits=cap,
        )
        next_day = reservation(
            writer_id="project-b:writer",
            key="slot:next-day",
            slot="slot:next-day",
            at_ms=NOW_MS + 86_400_000,
        )
        self.assertEqual(
            reserve_shared_writer_envelope(
                execute=client, reservation=next_day, limits=cap,
            ),
            "RESERVED",
        )
        third = reservation(
            writer_id="project-c:writer",
            key="slot:third-day",
            slot="slot:third-day",
            at_ms=NOW_MS + 2 * 86_400_000,
        )
        with self.assertRaisesRegex(
            BudgetBlocked, "SHARED_ACCOUNT_BUDGET_EXCEEDED",
        ):
            reserve_shared_writer_envelope(
                execute=client, reservation=third, limits=cap,
            )

    def test_daily_d1_envelope_is_included_in_shared_gate(self):
        client = SQLiteAdmissionClient()
        cap = limits(d1_queries_per_utc_day=3)
        reserve_shared_writer_envelope(
            execute=client, reservation=reservation(), limits=cap,
        )
        with self.assertRaisesRegex(
            BudgetBlocked, "SHARED_ACCOUNT_BUDGET_EXCEEDED",
        ):
            reserve_shared_writer_envelope(
                execute=client,
                reservation=reservation(
                    writer_id="project-b:writer", d1_queries=2,
                ),
                limits=cap,
            )

    def test_concurrent_reservations_cannot_exceed_account_cap(self):
        client = SQLiteAdmissionClient()
        cap = limits(provider_requests_per_utc_day=4)

        def attempt(index: int) -> str:
            try:
                return reserve_shared_writer_envelope(
                    execute=client,
                    reservation=reservation(
                        writer_id=f"project-{index}:writer",
                        key=f"slot:{index}",
                    ),
                    limits=cap,
                )
            except BudgetBlocked as error:
                self.assertIn("SHARED_ACCOUNT_BUDGET_EXCEEDED", str(error))
                return "BLOCKED"

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(attempt, range(10)))
        self.assertEqual(results.count("RESERVED"), 4)
        self.assertEqual(results.count("BLOCKED"), 6)
        count = client.connection.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_1"
        ).fetchone()[0]
        self.assertEqual(count, 4)

    def test_invalid_writer_or_negative_envelope_fails_before_query(self):
        client = SQLiteAdmissionClient()
        with self.assertRaisesRegex(ValueError, "WRITER_ID_INVALID"):
            reserve_shared_writer_envelope(
                execute=client,
                reservation=reservation(writer_id="Project A"),
                limits=limits(),
            )
        with self.assertRaisesRegex(ValueError, "WRITER_RESERVATION_ENVELOPE_INVALID"):
            reserve_shared_writer_envelope(
                execute=client,
                reservation=reservation(provider_requests=-1),
                limits=limits(),
            )
        self.assertEqual(client.query_count, 0)

    def test_missing_or_zero_policy_limits_fail_before_query(self):
        client = SQLiteAdmissionClient()
        with self.assertRaisesRegex(ValueError, "SHARED_WRITER_LIMITS_INVALID"):
            reserve_shared_writer_envelope(
                execute=client,
                reservation=reservation(),
                limits=limits(provider_requests_per_utc_day=0),
            )
        self.assertEqual(client.query_count, 0)


if __name__ == "__main__":
    unittest.main()
