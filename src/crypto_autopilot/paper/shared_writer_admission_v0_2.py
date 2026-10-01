"""Prepared account-wide reservation statement for independent Cloudflare writers.

This is a deterministic D1/SQLite contract only. It does not construct a client,
provision a database, grant external access, or activate any production writer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked


RESERVE_SHARED_WRITER_SQL = """
WITH day_totals AS (
    SELECT COUNT(*) AS reservations,
           COALESCE(SUM(provider_requests), 0) AS provider_requests,
           COALESCE(SUM(r2_class_a), 0) AS r2_class_a,
           COALESCE(SUM(r2_class_b), 0) AS r2_class_b,
           COALESCE(SUM(r2_new_bytes), 0) AS r2_new_bytes,
           COALESCE(SUM(d1_queries), 0) AS d1_queries,
           COALESCE(SUM(d1_rows_written), 0) AS d1_rows_written,
           COALESCE(SUM(d1_storage_growth_bytes), 0) AS d1_storage_growth_bytes
    FROM cloudflare_shared_writer_reservations_v0_2
    WHERE utc_day = CAST(? AS TEXT)
), rolling_totals AS (
    SELECT COALESCE(SUM(r2_class_a), 0) AS r2_class_a,
           COALESCE(SUM(r2_class_b), 0) AS r2_class_b,
           COALESCE(SUM(r2_new_bytes), 0) AS r2_new_bytes
    FROM cloudflare_shared_writer_reservations_v0_2
    WHERE reserved_at_ms >= CAST(? AS INTEGER)
      AND reserved_at_ms <= CAST(? AS INTEGER)
), capacity AS (
    SELECT retained_reservations
    FROM cloudflare_shared_writer_admission_capacity_v0_2
    WHERE capacity_id = 1
)
INSERT INTO cloudflare_shared_writer_reservations_v0_2 (
    writer_id, idempotency_key, slot_id, utc_day, reserved_at_ms,
    provider_requests, r2_class_a, r2_class_b, r2_new_bytes,
    d1_queries, d1_rows_written, d1_storage_growth_bytes
)
SELECT
    CAST(? AS TEXT), CAST(? AS TEXT), CAST(? AS TEXT), CAST(? AS TEXT),
    CAST(? AS INTEGER), CAST(? AS INTEGER), CAST(? AS INTEGER),
    CAST(? AS INTEGER), CAST(? AS INTEGER), CAST(? AS INTEGER),
    CAST(? AS INTEGER), CAST(? AS INTEGER)
FROM day_totals, rolling_totals, capacity
WHERE day_totals.reservations < CAST(? AS INTEGER)
  AND capacity.retained_reservations < CAST(? AS INTEGER)
  AND day_totals.provider_requests + CAST(? AS INTEGER) <= CAST(? AS INTEGER)
  AND day_totals.r2_class_a + CAST(? AS INTEGER) <= CAST(? AS INTEGER)
  AND day_totals.r2_class_b + CAST(? AS INTEGER) <= CAST(? AS INTEGER)
  AND day_totals.r2_new_bytes + CAST(? AS INTEGER) <= CAST(? AS INTEGER)
  AND day_totals.d1_queries + CAST(? AS INTEGER) <= CAST(? AS INTEGER)
  AND day_totals.d1_rows_written + CAST(? AS INTEGER) <= CAST(? AS INTEGER)
  AND day_totals.d1_storage_growth_bytes + CAST(? AS INTEGER) <= CAST(? AS INTEGER)
  AND rolling_totals.r2_class_a + CAST(? AS INTEGER) <= CAST(? AS INTEGER)
  AND rolling_totals.r2_class_b + CAST(? AS INTEGER) <= CAST(? AS INTEGER)
  AND rolling_totals.r2_new_bytes + CAST(? AS INTEGER) <= CAST(? AS INTEGER)
ON CONFLICT(writer_id, idempotency_key) DO NOTHING
RETURNING writer_id, idempotency_key
"""

READ_SHARED_WRITER_RESERVATION_SQL = """
SELECT writer_id, idempotency_key, slot_id, utc_day, reserved_at_ms,
       provider_requests, r2_class_a, r2_class_b, r2_new_bytes,
       d1_queries, d1_rows_written, d1_storage_growth_bytes
FROM cloudflare_shared_writer_reservations_v0_2
WHERE writer_id = CAST(? AS TEXT)
  AND idempotency_key = CAST(? AS TEXT)
LIMIT 1
"""

WRITER_ID_RE = re.compile(r"^[a-z0-9][a-z0-9:._/-]{0,127}$")
UTC_DAY_MS = 86_400_000
ROLLING_WINDOW_DAYS = 31
_METRIC_FIELDS = (
    "provider_requests",
    "r2_class_a",
    "r2_class_b",
    "r2_new_bytes",
    "d1_queries",
    "d1_rows_written",
    "d1_storage_growth_bytes",
)


class SharedWriterQueryResult(Protocol):
    rows: tuple[dict[str, object], ...]


class SharedWriterQuery(Protocol):
    def __call__(
        self, sql: str, params: tuple[object, ...],
    ) -> SharedWriterQueryResult: ...


@dataclass(frozen=True, slots=True)
class SharedWriterReservation:
    writer_id: str
    idempotency_key: str
    slot_id: str
    reserved_at_ms: int
    provider_requests: int
    r2_class_a: int
    r2_class_b: int
    r2_new_bytes: int
    d1_queries: int
    d1_rows_written: int
    d1_storage_growth_bytes: int

    @property
    def utc_day(self) -> str:
        return datetime.fromtimestamp(
            self.reserved_at_ms / 1000, tz=UTC,
        ).date().isoformat()

    def validate(self) -> None:
        if not isinstance(self.writer_id, str) or not WRITER_ID_RE.fullmatch(
            self.writer_id
        ):
            raise ValueError("WRITER_ID_INVALID")
        if (
            not isinstance(self.idempotency_key, str)
            or not self.idempotency_key
            or len(self.idempotency_key) > 200
            or any(char in self.idempotency_key for char in "\r\n")
        ):
            raise ValueError("WRITER_IDEMPOTENCY_KEY_INVALID")
        if (
            not isinstance(self.slot_id, str)
            or not self.slot_id
            or len(self.slot_id) > 200
            or any(char in self.slot_id for char in "\r\n")
        ):
            raise ValueError("WRITER_SLOT_ID_INVALID")
        if type(self.reserved_at_ms) is not int or self.reserved_at_ms < 0:
            raise ValueError("WRITER_RESERVATION_TIME_INVALID")
        if any(
            type(getattr(self, field)) is not int or getattr(self, field) < 0
            for field in _METRIC_FIELDS
        ):
            raise ValueError("WRITER_RESERVATION_ENVELOPE_INVALID")
        if self.d1_rows_written < 2:
            raise ValueError("WRITER_LEDGER_ROWS_UNDERCOUNTED")

    def values(self) -> tuple[object, ...]:
        return (
            self.writer_id,
            self.idempotency_key,
            self.slot_id,
            self.utc_day,
            self.reserved_at_ms,
            *(getattr(self, field) for field in _METRIC_FIELDS),
        )


@dataclass(frozen=True, slots=True)
class SharedWriterAdmissionLimits:
    max_reservations_per_utc_day: int
    provider_requests_per_utc_day: int
    r2_class_a_per_utc_day: int
    r2_class_b_per_utc_day: int
    r2_new_bytes_per_utc_day: int
    d1_queries_per_utc_day: int
    d1_rows_written_per_utc_day: int
    d1_storage_growth_bytes_per_utc_day: int
    max_retained_reservations: int
    r2_class_a_per_rolling_31_days: int
    r2_class_b_per_rolling_31_days: int
    r2_new_bytes_per_rolling_31_days: int

    def validate(self) -> None:
        if any(
            type(getattr(self, field)) is not int or getattr(self, field) <= 0
            for field in self.__dataclass_fields__
        ):
            raise ValueError("SHARED_WRITER_LIMITS_INVALID")


def reservation_params(
    reservation: SharedWriterReservation,
    limits: SharedWriterAdmissionLimits,
) -> tuple[object, ...]:
    """Build fixed-order SQL parameters; unknown/zero limits are rejected."""
    reservation.validate()
    limits.validate()
    start_ms = reservation.reserved_at_ms - (
        ROLLING_WINDOW_DAYS * UTC_DAY_MS
    )
    return (
        reservation.utc_day,
        start_ms,
        reservation.reserved_at_ms,
        *reservation.values(),
        limits.max_reservations_per_utc_day,
        limits.max_retained_reservations,
        reservation.provider_requests,
        limits.provider_requests_per_utc_day,
        reservation.r2_class_a,
        limits.r2_class_a_per_utc_day,
        reservation.r2_class_b,
        limits.r2_class_b_per_utc_day,
        reservation.r2_new_bytes,
        limits.r2_new_bytes_per_utc_day,
        reservation.d1_queries,
        limits.d1_queries_per_utc_day,
        reservation.d1_rows_written,
        limits.d1_rows_written_per_utc_day,
        reservation.d1_storage_growth_bytes,
        limits.d1_storage_growth_bytes_per_utc_day,
        reservation.r2_class_a,
        limits.r2_class_a_per_rolling_31_days,
        reservation.r2_class_b,
        limits.r2_class_b_per_rolling_31_days,
        reservation.r2_new_bytes,
        limits.r2_new_bytes_per_rolling_31_days,
    )


def reserve_shared_writer_envelope(
    *,
    execute: SharedWriterQuery,
    reservation: SharedWriterReservation,
    limits: SharedWriterAdmissionLimits,
) -> Literal["RESERVED", "EXISTING_RESERVATION"]:
    """Atomically reserve an envelope or fail closed.

    An exact replay returns EXISTING_RESERVATION so callers must not repeat the
    external operation. A changed payload under the same key is a hard conflict.
    Reservations are conservative and never released by this prepared contract.
    """
    params = reservation_params(reservation, limits)
    inserted = execute(RESERVE_SHARED_WRITER_SQL, params)
    if inserted.rows:
        if len(inserted.rows) != 1 or inserted.rows[0] != {
            "writer_id": reservation.writer_id,
            "idempotency_key": reservation.idempotency_key,
        }:
            raise BudgetBlocked("SHARED_WRITER_RESERVATION_RESULT_INVALID")
        return "RESERVED"

    existing = execute(
        READ_SHARED_WRITER_RESERVATION_SQL,
        (reservation.writer_id, reservation.idempotency_key),
    )
    if not existing.rows:
        raise BudgetBlocked("SHARED_ACCOUNT_BUDGET_EXCEEDED")
    if len(existing.rows) != 1 or existing.rows[0] != dict(
        zip(
            (
                "writer_id",
                "idempotency_key",
                "slot_id",
                "utc_day",
                "reserved_at_ms",
                *_METRIC_FIELDS,
            ),
            reservation.values(),
            strict=True,
        )
    ):
        raise BudgetBlocked("SHARED_WRITER_IDEMPOTENCY_CONFLICT")
    return "EXISTING_RESERVATION"
