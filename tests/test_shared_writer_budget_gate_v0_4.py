from __future__ import annotations

import sqlite3
import unittest
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import (
    QueryOperation,
    SharedWriterReservation,
    reserve_shared_writer_envelope,
)

ROOT = Path(__file__).parents[1]
BASE_MIGRATION = (ROOT / "migrations" / "cloudflare_shared_writer_admission_v0_3.sql").read_text()
POLICY_MIGRATION = (ROOT / "migrations" / "cloudflare_shared_writer_budget_policy_v0_4.sql").read_text()
NOW_MS = 1_791_234_567_000


@dataclass(frozen=True)
class Result:
    rows: tuple[dict[str, object], ...]


class SyntheticPrepaidMeter:
    """CI-only prepaid pool shared by all fixture callers; no cloud controller."""

    def __init__(self, max_queries: int = 100) -> None:
        self.max_queries = max_queries
        self.current_utc_day = "2026-10-01"
        self.charges: list[tuple[str, str, str, QueryOperation]] = []

    def charge_before_query(
        self, *, writer_id: str, slot_id: str, operation: QueryOperation,
    ) -> Literal["CHARGED"]:
        used = sum(day == self.current_utc_day for day, _, _, _ in self.charges)
        if used >= self.max_queries:
            raise BudgetBlocked("BLOCKED_PREPAID_QUERY_POOL_EXHAUSTED")
        self.charges.append((self.current_utc_day, writer_id, slot_id, operation))
        return "CHARGED"


class SQLiteQuery:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db
        self.calls = 0

    def __call__(self, sql: str, params: tuple[object, ...]) -> Result:
        self.calls += 1
        cursor = self.db.execute(sql, params)
        columns = tuple(column[0] for column in cursor.description or ())
        rows = tuple(dict(zip(columns, row, strict=True)) for row in cursor.fetchall())
        return Result(rows)


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
        self.meter = SyntheticPrepaidMeter()

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
            provider_requests=provider, r2_class_a=class_a, r2_class_b=1,
            r2_new_bytes=bytes_new, d1_queries=2, d1_rows_read=20,
            d1_rows_written=7, d1_storage_growth_bytes=128,
        )

    def test_null_policy_blocks_without_inserting(self) -> None:
        self.db.execute(
            "UPDATE cloudflare_shared_writer_budget_policy_v0_4 SET provider_requests_per_utc_day=NULL"
        )
        with self.assertRaisesRegex(BudgetBlocked, "POLICY_OR_WRITER_GATE"):
            reserve_shared_writer_envelope(
                execute=self.query, query_meter=self.meter, reservation=self.reservation("project-a:writer", NOW_MS),
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
            execute=self.query, query_meter=self.meter, reservation=self.reservation("project-a:writer", NOW_MS),
        )
        with self.assertRaisesRegex(BudgetBlocked, "POLICY_OR_WRITER_GATE"):
            reserve_shared_writer_envelope(
                execute=self.query, query_meter=self.meter, reservation=self.reservation("project-b:writer", NOW_MS + 1),
            )

    def test_rolling_cap_is_account_shared(self) -> None:
        self.db.execute(
            "UPDATE cloudflare_shared_writer_budget_policy_v0_4 SET r2_class_a_per_rolling_31_days=1"
        )
        reserve_shared_writer_envelope(
            execute=self.query, query_meter=self.meter, reservation=self.reservation("project-a:writer", NOW_MS),
        )
        with self.assertRaisesRegex(BudgetBlocked, "POLICY_OR_WRITER_GATE"):
            reserve_shared_writer_envelope(
                execute=self.query, query_meter=self.meter, reservation=self.reservation("project-b:writer", NOW_MS + 1),
            )

    def test_exact_replay_returns_existing_without_duplicate_reservation(self) -> None:
        reservation = self.reservation("project-a:writer", NOW_MS)
        self.assertEqual(
            reserve_shared_writer_envelope(execute=self.query, query_meter=self.meter, reservation=reservation),
            "RESERVED",
        )
        self.assertEqual(
            reserve_shared_writer_envelope(execute=self.query, query_meter=self.meter, reservation=reservation),
            "EXISTING_RESERVATION",
        )
        count = self.db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_changed_payload_for_same_writer_slot_blocks(self) -> None:
        reserve_shared_writer_envelope(
            execute=self.query, query_meter=self.meter, reservation=self.reservation("project-a:writer", NOW_MS),
        )
        with self.assertRaisesRegex(BudgetBlocked, "IDEMPOTENCY_CONFLICT"):
            reserve_shared_writer_envelope(
                execute=self.query, query_meter=self.meter,
                reservation=self.reservation("project-a:writer", NOW_MS, provider=2),
            )

    def test_retired_writer_cannot_reserve(self) -> None:
        self.register("project-c:retired", state="RETIRED")
        with self.assertRaisesRegex(BudgetBlocked, "POLICY_OR_WRITER_GATE"):
            reserve_shared_writer_envelope(
                execute=self.query, query_meter=self.meter, reservation=self.reservation("project-c:retired", NOW_MS),
            )

    def test_caller_cannot_pass_alternative_caps(self) -> None:
        with self.assertRaises(TypeError):
            reserve_shared_writer_envelope(
                execute=self.query, query_meter=self.meter,
                reservation=self.reservation("project-a:writer", NOW_MS),
                limits=object(),  # type: ignore[call-arg]
            )

    def test_reservation_must_cover_admission_and_ledger_write_floor(self) -> None:
        bad = replace(self.reservation("project-a:writer", NOW_MS), d1_rows_written=1)
        with self.assertRaisesRegex(ValueError, "LEDGER_COST_UNDERCOUNTED"):
            reserve_shared_writer_envelope(execute=self.query, query_meter=self.meter, reservation=bad)


    def test_missing_meter_blocks_before_any_sql(self) -> None:
        with self.assertRaisesRegex(BudgetBlocked, "QUERY_METER_REQUIRED"):
            reserve_shared_writer_envelope(
                execute=self.query, reservation=self.reservation("project-a:writer", NOW_MS),
            )
        self.assertEqual(self.query.calls, 0)

    def test_repeated_replay_exhausts_pool_before_next_sql(self) -> None:
        self.meter.max_queries = 3
        reservation = self.reservation("project-a:writer", NOW_MS)
        self.assertEqual(
            reserve_shared_writer_envelope(
                execute=self.query, query_meter=self.meter, reservation=reservation,
            ), "RESERVED",
        )
        self.assertEqual(
            reserve_shared_writer_envelope(
                execute=self.query, query_meter=self.meter, reservation=reservation,
            ), "EXISTING_RESERVATION",
        )
        with self.assertRaisesRegex(BudgetBlocked, "PREPAID_QUERY_POOL_EXHAUSTED"):
            reserve_shared_writer_envelope(
                execute=self.query, query_meter=self.meter, reservation=reservation,
            )
        self.assertEqual(self.query.calls, 3)
        self.assertEqual(len(self.meter.charges), 3)

    def test_blocked_readback_keeps_first_attempt_charged(self) -> None:
        self.meter.max_queries = 2
        reservation = self.reservation("project-a:writer", NOW_MS)
        reserve_shared_writer_envelope(
            execute=self.query, query_meter=self.meter, reservation=reservation,
        )
        with self.assertRaisesRegex(BudgetBlocked, "PREPAID_QUERY_POOL_EXHAUSTED"):
            reserve_shared_writer_envelope(
                execute=self.query, query_meter=self.meter, reservation=reservation,
            )
        self.assertEqual(self.query.calls, 2)
        self.assertEqual(len(self.meter.charges), 2)
        self.assertEqual(self.meter.charges[-1][-1], "RESERVATION")

    def test_rejected_reservations_consume_attempt_pool_without_ledger_rows(self) -> None:
        self.meter.max_queries = 2
        self.db.execute(
            "UPDATE cloudflare_shared_writer_budget_policy_v0_4 SET provider_requests_per_utc_day=NULL"
        )
        reservation = self.reservation("project-a:writer", NOW_MS)
        with self.assertRaisesRegex(BudgetBlocked, "POLICY_OR_WRITER_GATE"):
            reserve_shared_writer_envelope(
                execute=self.query, query_meter=self.meter, reservation=reservation,
            )
        with self.assertRaisesRegex(BudgetBlocked, "PREPAID_QUERY_POOL_EXHAUSTED"):
            reserve_shared_writer_envelope(
                execute=self.query, query_meter=self.meter, reservation=reservation,
            )
        self.assertEqual(self.query.calls, 2)
        self.assertEqual(len(self.meter.charges), 2)
        count = self.db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0]
        self.assertEqual(count, 0)

    def test_failed_query_does_not_refund_or_retry(self) -> None:
        calls = []

        def failing_query(sql: str, params: tuple[object, ...]) -> Result:
            calls.append((sql, params))
            raise OSError("synthetic transport failure")

        self.meter.max_queries = 1
        reservation = self.reservation("project-a:writer", NOW_MS)
        with self.assertRaisesRegex(BudgetBlocked, "RESERVATION_UNVERIFIED"):
            reserve_shared_writer_envelope(
                execute=failing_query, query_meter=self.meter, reservation=reservation,
            )
        with self.assertRaisesRegex(BudgetBlocked, "PREPAID_QUERY_POOL_EXHAUSTED"):
            reserve_shared_writer_envelope(
                execute=failing_query, query_meter=self.meter, reservation=reservation,
            )
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(self.meter.charges), 1)

    def test_attempt_pool_is_shared_across_writers(self) -> None:
        self.meter.max_queries = 1
        reserve_shared_writer_envelope(
            execute=self.query, query_meter=self.meter,
            reservation=self.reservation("project-a:writer", NOW_MS),
        )
        with self.assertRaisesRegex(BudgetBlocked, "PREPAID_QUERY_POOL_EXHAUSTED"):
            reserve_shared_writer_envelope(
                execute=self.query, query_meter=self.meter,
                reservation=self.reservation("project-b:writer", NOW_MS + 1),
            )
        self.assertEqual(self.query.calls, 1)

    def test_replay_charge_uses_meter_current_day_not_original_slot_day(self) -> None:
        reservation = self.reservation("project-a:writer", NOW_MS)
        reserve_shared_writer_envelope(
            execute=self.query, query_meter=self.meter, reservation=reservation,
        )
        self.meter.current_utc_day = "2026-10-02"
        reserve_shared_writer_envelope(
            execute=self.query, query_meter=self.meter, reservation=reservation,
        )
        self.assertEqual([charge[0] for charge in self.meter.charges],
                         ["2026-10-01", "2026-10-02", "2026-10-02"])

    def test_invalid_or_failed_meter_never_queries(self) -> None:
        class InvalidMeter:
            def charge_before_query(self, **kwargs: object) -> str:
                return "NOT_CHARGED"

        class FailedMeter:
            def charge_before_query(self, **kwargs: object) -> Literal["CHARGED"]:
                raise OSError("synthetic meter unavailable")

        for meter in (InvalidMeter(), FailedMeter()):
            with self.subTest(meter=type(meter).__name__):
                with self.assertRaisesRegex(BudgetBlocked, "QUERY_METER"):
                    reserve_shared_writer_envelope(
                        execute=self.query, query_meter=meter,
                        reservation=self.reservation("project-a:writer", NOW_MS),
                    )
        self.assertEqual(self.query.calls, 0)

    def test_existing_reservation_cannot_replay_after_writer_retirement(self) -> None:
        reservation = self.reservation("project-a:writer", NOW_MS)
        reserve_shared_writer_envelope(
            execute=self.query, query_meter=self.meter, reservation=reservation,
        )
        self.db.execute(
            "UPDATE cloudflare_shared_writer_identities_v0_3 SET lifecycle_state='RETIRED' "
            "WHERE writer_id='project-a:writer'"
        )
        with self.assertRaisesRegex(BudgetBlocked, "POLICY_OR_WRITER_GATE"):
            reserve_shared_writer_envelope(
                execute=self.query, query_meter=self.meter, reservation=reservation,
            )

    def test_each_daily_workload_dimension_blocks_second_writer(self) -> None:
        reservation = self.reservation("project-a:writer", NOW_MS)
        dimensions = {
            "provider_requests": "provider_requests_per_utc_day",
            "r2_class_a": "r2_class_a_per_utc_day",
            "r2_class_b": "r2_class_b_per_utc_day",
            "r2_new_bytes": "r2_new_bytes_per_utc_day",
            "d1_queries": "d1_queries_per_utc_day",
            "d1_rows_read": "d1_rows_read_per_utc_day",
            "d1_rows_written": "d1_rows_written_per_utc_day",
            "d1_storage_growth_bytes": "d1_storage_growth_bytes_per_utc_day",
        }
        for metric, column in dimensions.items():
            with self.subTest(metric=metric):
                self.db.execute("SAVEPOINT cap_case")
                self.db.execute(
                    f"UPDATE cloudflare_shared_writer_budget_policy_v0_4 SET {column}=?",
                    (getattr(reservation, metric),),
                )
                reserve_shared_writer_envelope(
                    execute=self.query, query_meter=self.meter, reservation=reservation,
                )
                with self.assertRaisesRegex(BudgetBlocked, "POLICY_OR_WRITER_GATE"):
                    reserve_shared_writer_envelope(
                        execute=self.query, query_meter=self.meter,
                        reservation=self.reservation("project-b:writer", NOW_MS + 1),
                    )
                self.db.execute("ROLLBACK TO cap_case")
                self.db.execute("RELEASE cap_case")

    def test_malformed_query_response_keeps_debit_and_blocks(self) -> None:
        def malformed_query(sql: str, params: tuple[object, ...]) -> Result:
            return Result(({}, {}))

        with self.assertRaisesRegex(BudgetBlocked, "QUERY_RESULT_INVALID"):
            reserve_shared_writer_envelope(
                execute=malformed_query, query_meter=self.meter,
                reservation=self.reservation("project-a:writer", NOW_MS),
            )
        self.assertEqual(len(self.meter.charges), 1)

    def test_daily_workload_cap_resets_on_next_utc_day(self) -> None:
        self.db.execute(
            "UPDATE cloudflare_shared_writer_budget_policy_v0_4 SET provider_requests_per_utc_day=1"
        )
        reserve_shared_writer_envelope(
            execute=self.query, query_meter=self.meter,
            reservation=self.reservation("project-a:writer", NOW_MS),
        )
        reserve_shared_writer_envelope(
            execute=self.query, query_meter=self.meter,
            reservation=self.reservation("project-b:writer", NOW_MS + 86_400_000),
        )
        count = self.db.execute(
            "SELECT COUNT(DISTINCT utc_day) FROM cloudflare_shared_writer_reservations_v0_3"
        ).fetchone()[0]
        self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()
