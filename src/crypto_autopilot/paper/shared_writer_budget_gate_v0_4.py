"""Prepared central account-wide budget gate for registered Cloudflare writers.

The gate uses only the V0.3 shared D1 reservation schema and a V0.4
NULL-by-default policy row. It creates no client and grants no execution
authority. Limits are read from D1, never supplied by the calling writer.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked

_RESERVATION_METRICS = (
    "provider_requests", "r2_class_a", "r2_class_b", "r2_new_bytes",
    "d1_queries", "d1_rows_read", "d1_rows_written",
    "d1_storage_growth_bytes",
)
_WRITER_ID_RE = re.compile(r"^[a-z0-9][a-z0-9:._/-]{0,127}$")
_SLOT_ID_RE = re.compile(r"^slot:(0|[1-9][0-9]{0,15})$")
_DAY_MS = 86_400_000
_ROLLING_DAYS = 31

RESERVE_SHARED_WRITER_SQL = """
WITH daily AS (
    SELECT COUNT(*) AS reservations,
           COALESCE(SUM(provider_requests), 0) AS provider_requests,
           COALESCE(SUM(r2_class_a), 0) AS r2_class_a,
           COALESCE(SUM(r2_class_b), 0) AS r2_class_b,
           COALESCE(SUM(r2_new_bytes), 0) AS r2_new_bytes,
           COALESCE(SUM(d1_queries), 0) AS d1_queries,
           COALESCE(SUM(d1_rows_read), 0) AS d1_rows_read,
           COALESCE(SUM(d1_rows_written), 0) AS d1_rows_written,
           COALESCE(SUM(d1_storage_growth_bytes), 0) AS d1_storage_growth_bytes
    FROM cloudflare_shared_writer_reservations_v0_3
    WHERE utc_day = CAST(? AS TEXT)
), rolling AS (
    SELECT COALESCE(SUM(r2_class_a), 0) AS r2_class_a,
           COALESCE(SUM(r2_class_b), 0) AS r2_class_b,
           COALESCE(SUM(r2_new_bytes), 0) AS r2_new_bytes
    FROM cloudflare_shared_writer_reservations_v0_3
    WHERE reserved_at_ms >= CAST(? AS INTEGER)
      AND reserved_at_ms <= CAST(? AS INTEGER)
), policy AS (
    SELECT * FROM cloudflare_shared_writer_budget_policy_v0_4
    WHERE policy_id = 1
), proposal (
    writer_id, slot_id, idempotency_key, slot_at_ms, utc_day, reserved_at_ms,
    provider_requests, r2_class_a, r2_class_b, r2_new_bytes,
    d1_queries, d1_rows_read, d1_rows_written, d1_storage_growth_bytes
) AS (
    VALUES (
        CAST(? AS TEXT), CAST(? AS TEXT), CAST(? AS TEXT), CAST(? AS INTEGER),
        CAST(? AS TEXT), CAST(? AS INTEGER), CAST(? AS INTEGER),
        CAST(? AS INTEGER), CAST(? AS INTEGER), CAST(? AS INTEGER),
        CAST(? AS INTEGER), CAST(? AS INTEGER), CAST(? AS INTEGER),
        CAST(? AS INTEGER)
    )
)
INSERT INTO cloudflare_shared_writer_reservations_v0_3 (
    writer_id, slot_id, idempotency_key, slot_at_ms, utc_day, reserved_at_ms,
    provider_requests, r2_class_a, r2_class_b, r2_new_bytes,
    d1_queries, d1_rows_read, d1_rows_written, d1_storage_growth_bytes
)
SELECT proposal.writer_id, proposal.slot_id, proposal.idempotency_key,
       proposal.slot_at_ms, proposal.utc_day, proposal.reserved_at_ms,
       proposal.provider_requests, proposal.r2_class_a, proposal.r2_class_b,
       proposal.r2_new_bytes, proposal.d1_queries, proposal.d1_rows_read,
       proposal.d1_rows_written, proposal.d1_storage_growth_bytes
FROM daily, rolling, policy, proposal
WHERE policy.max_reservations_per_utc_day IS NOT NULL
  AND policy.provider_requests_per_utc_day IS NOT NULL
  AND policy.r2_class_a_per_utc_day IS NOT NULL
  AND policy.r2_class_b_per_utc_day IS NOT NULL
  AND policy.r2_new_bytes_per_utc_day IS NOT NULL
  AND policy.d1_queries_per_utc_day IS NOT NULL
  AND policy.d1_rows_read_per_utc_day IS NOT NULL
  AND policy.d1_rows_written_per_utc_day IS NOT NULL
  AND policy.d1_storage_growth_bytes_per_utc_day IS NOT NULL
  AND policy.r2_class_a_per_rolling_31_days IS NOT NULL
  AND policy.r2_class_b_per_rolling_31_days IS NOT NULL
  AND policy.r2_new_bytes_per_rolling_31_days IS NOT NULL
  AND daily.reservations + 1 <= policy.max_reservations_per_utc_day
  AND daily.provider_requests + proposal.provider_requests <= policy.provider_requests_per_utc_day
  AND daily.r2_class_a + proposal.r2_class_a <= policy.r2_class_a_per_utc_day
  AND daily.r2_class_b + proposal.r2_class_b <= policy.r2_class_b_per_utc_day
  AND daily.r2_new_bytes + proposal.r2_new_bytes <= policy.r2_new_bytes_per_utc_day
  AND daily.d1_queries + proposal.d1_queries <= policy.d1_queries_per_utc_day
  AND daily.d1_rows_read + proposal.d1_rows_read <= policy.d1_rows_read_per_utc_day
  AND daily.d1_rows_written + proposal.d1_rows_written <= policy.d1_rows_written_per_utc_day
  AND daily.d1_storage_growth_bytes + proposal.d1_storage_growth_bytes
      <= policy.d1_storage_growth_bytes_per_utc_day
  AND rolling.r2_class_a + proposal.r2_class_a
      <= policy.r2_class_a_per_rolling_31_days
  AND rolling.r2_class_b + proposal.r2_class_b
      <= policy.r2_class_b_per_rolling_31_days
  AND rolling.r2_new_bytes + proposal.r2_new_bytes
      <= policy.r2_new_bytes_per_rolling_31_days
  AND EXISTS (
      SELECT 1 FROM cloudflare_shared_writer_identities_v0_3
      WHERE writer_id = proposal.writer_id AND lifecycle_state = 'ACTIVE'
  )
  AND NOT EXISTS (
      SELECT 1 FROM cloudflare_shared_writer_retirement_watermarks_v0_3
      WHERE writer_id = proposal.writer_id
        AND proposal.slot_at_ms <= retired_through_slot_at_ms
  )
ON CONFLICT(writer_id, slot_id) DO NOTHING
RETURNING writer_id, slot_id
"""

READ_SHARED_WRITER_SQL = """
SELECT writer_id, slot_id, idempotency_key, slot_at_ms, utc_day,
       reserved_at_ms, provider_requests, r2_class_a, r2_class_b,
       r2_new_bytes, d1_queries, d1_rows_read, d1_rows_written,
       d1_storage_growth_bytes
FROM cloudflare_shared_writer_reservations_v0_3
WHERE writer_id = CAST(? AS TEXT) AND slot_id = CAST(? AS TEXT)
LIMIT 1
"""

_FIELDS = (
    "writer_id", "slot_id", "idempotency_key", "slot_at_ms", "utc_day",
    "reserved_at_ms", *_RESERVATION_METRICS,
)


class QueryResult(Protocol):
    rows: tuple[dict[str, object], ...]


class Query(Protocol):
    def __call__(self, sql: str, params: tuple[object, ...]) -> QueryResult: ...


@dataclass(frozen=True, slots=True)
class SharedWriterReservation:
    writer_id: str
    slot_id: str
    idempotency_key: str
    slot_at_ms: int
    reserved_at_ms: int
    provider_requests: int
    r2_class_a: int
    r2_class_b: int
    r2_new_bytes: int
    d1_queries: int
    d1_rows_read: int
    d1_rows_written: int
    d1_storage_growth_bytes: int

    @property
    def utc_day(self) -> str:
        return datetime.fromtimestamp(self.reserved_at_ms / 1000, tz=UTC).date().isoformat()

    def validate(self) -> None:
        if not isinstance(self.writer_id, str) or not _WRITER_ID_RE.fullmatch(self.writer_id):
            raise ValueError("WRITER_ID_INVALID")
        if (
            type(self.slot_at_ms) is not int or self.slot_at_ms <= 0
            or self.slot_id != f"slot:{self.slot_at_ms}"
            or not isinstance(self.slot_id, str) or not _SLOT_ID_RE.fullmatch(self.slot_id)
            or self.idempotency_key != self.slot_id
        ):
            raise ValueError("WRITER_SLOT_IDENTITY_INVALID")
        if type(self.reserved_at_ms) is not int or self.reserved_at_ms < self.slot_at_ms:
            raise ValueError("WRITER_RESERVATION_TIME_INVALID")
        if any(
            type(getattr(self, name)) is not int or getattr(self, name) < 0
            for name in _RESERVATION_METRICS
        ):
            raise ValueError("WRITER_RESERVATION_ENVELOPE_INVALID")
        if self.d1_queries < 2 or self.d1_rows_read < 1 or self.d1_rows_written < 7:
            raise ValueError("WRITER_LEDGER_COST_UNDERCOUNTED")

    def values(self) -> tuple[object, ...]:
        return tuple(getattr(self, name) for name in _FIELDS)


def reservation_params(reservation: SharedWriterReservation) -> tuple[object, ...]:
    """Limits are intentionally absent: SQL reads the single shared policy row."""
    reservation.validate()
    return (
        reservation.utc_day,
        reservation.reserved_at_ms - _ROLLING_DAYS * _DAY_MS,
        reservation.reserved_at_ms,
        *reservation.values(),
    )


def _row_values(row: Mapping[str, object]) -> dict[str, object]:
    return {name: row.get(name) for name in _FIELDS}


def reserve_shared_writer_envelope(
    *, execute: Query, reservation: SharedWriterReservation,
) -> Literal["RESERVED", "EXISTING_RESERVATION"]:
    """Reserve centrally capped account usage; ambiguous outcomes always block."""
    params = reservation_params(reservation)
    try:
        inserted = execute(RESERVE_SHARED_WRITER_SQL, params)
    except Exception:
        raise BudgetBlocked("BLOCKED_SHARED_WRITER_RESERVATION_UNVERIFIED") from None
    if inserted.rows:
        if len(inserted.rows) != 1 or inserted.rows[0] != {
            "writer_id": reservation.writer_id, "slot_id": reservation.slot_id,
        }:
            raise BudgetBlocked("BLOCKED_SHARED_WRITER_RESERVATION_RESULT_INVALID")
        return "RESERVED"

    try:
        existing = execute(
            READ_SHARED_WRITER_SQL, (reservation.writer_id, reservation.slot_id),
        )
    except Exception:
        raise BudgetBlocked("BLOCKED_SHARED_WRITER_REPLAY_UNVERIFIED") from None
    if not existing.rows:
        raise BudgetBlocked("BLOCKED_SHARED_WRITER_POLICY_OR_WRITER_GATE")
    if len(existing.rows) != 1 or _row_values(existing.rows[0]) != dict(
        zip(_FIELDS, reservation.values(), strict=True)
    ):
        raise BudgetBlocked("BLOCKED_SHARED_WRITER_IDEMPOTENCY_CONFLICT")
    return "EXISTING_RESERVATION"
