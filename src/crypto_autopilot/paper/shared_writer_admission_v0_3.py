"""Prepared deterministic helpers for shared D1 admission lifecycle V0.3.

This module contains no Cloudflare client and grants no production authority.
The SQL may be exercised with SQLite fixtures in GitHub CI only.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked


ROLLING_WINDOW_DAYS = 31
UTC_DAY_MS = 86_400_000
WRITER_ID_RE = re.compile(r"^[a-z0-9][a-z0-9:._/-]{0,127}$")
SLOT_ID_RE = re.compile(r"^slot:(0|[1-9][0-9]{0,15})$")

COMPACT_EXPIRED_RESERVATIONS_SQL = """
DELETE FROM cloudflare_shared_writer_reservations_v0_3
WHERE rowid IN (
    SELECT rowid
    FROM cloudflare_shared_writer_reservations_v0_3
         INDEXED BY cloudflare_shared_writer_time_v0_3_idx
    WHERE reserved_at_ms < CAST(? AS INTEGER)
    ORDER BY reserved_at_ms, writer_id, slot_id
    LIMIT CAST(? AS INTEGER)
)
RETURNING writer_id, slot_id, slot_at_ms, reserved_at_ms
"""

DAILY_SHARED_AGGREGATE_SQL = """
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
"""

ROLLING_SHARED_AGGREGATE_SQL = """
SELECT COUNT(*) AS reservations,
       COALESCE(SUM(r2_class_a), 0) AS r2_class_a,
       COALESCE(SUM(r2_class_b), 0) AS r2_class_b,
       COALESCE(SUM(r2_new_bytes), 0) AS r2_new_bytes
FROM cloudflare_shared_writer_reservations_v0_3
WHERE reserved_at_ms >= CAST(? AS INTEGER)
  AND reserved_at_ms <= CAST(? AS INTEGER)
"""

READ_SLOT_RESERVATION_SQL = """
SELECT writer_id, slot_id, idempotency_key, slot_at_ms, utc_day,
       reserved_at_ms, provider_requests, r2_class_a, r2_class_b,
       r2_new_bytes, d1_queries, d1_rows_read, d1_rows_written,
       d1_storage_growth_bytes
FROM cloudflare_shared_writer_reservations_v0_3
WHERE writer_id = CAST(? AS TEXT)
  AND slot_id = CAST(? AS TEXT)
LIMIT 1
"""

RESERVATION_ENVELOPE_FIELDS = (
    "writer_id", "slot_id", "idempotency_key", "slot_at_ms", "utc_day",
    "reserved_at_ms", "provider_requests", "r2_class_a", "r2_class_b",
    "r2_new_bytes", "d1_queries", "d1_rows_read", "d1_rows_written",
    "d1_storage_growth_bytes",
)


READ_WRITER_WATERMARK_SQL = """
SELECT retired_through_slot_at_ms, retired_reservation_count
FROM cloudflare_shared_writer_retirement_watermarks_v0_3
WHERE writer_id = CAST(? AS TEXT)
LIMIT 1
"""


@dataclass(frozen=True, slots=True)
class WriterSlotIdentity:
    writer_id: str
    slot_id: str
    idempotency_key: str
    slot_at_ms: int

    def validate(self) -> None:
        if not isinstance(self.writer_id, str) or not WRITER_ID_RE.fullmatch(
            self.writer_id
        ):
            raise ValueError("WRITER_ID_INVALID")
        if type(self.slot_at_ms) is not int or self.slot_at_ms <= 0:
            raise ValueError("WRITER_SLOT_TIME_INVALID")
        expected = f"slot:{self.slot_at_ms}"
        if (
            not isinstance(self.slot_id, str)
            or not SLOT_ID_RE.fullmatch(self.slot_id)
            or self.slot_id != expected
        ):
            raise ValueError("WRITER_SLOT_ID_NOT_CANONICAL")
        if self.idempotency_key != self.slot_id:
            raise ValueError("WRITER_IDEMPOTENCY_KEY_MUST_EQUAL_SLOT")


def validate_fresh_slot(
    identity: WriterSlotIdentity,
    *,
    now_ms: int,
    max_slot_age_ms: int,
    max_future_skew_ms: int,
    retired_through_slot_at_ms: int | None,
) -> None:
    """Reject a stale or retired slot before any provider or storage operation."""
    identity.validate()
    if type(now_ms) is not int or now_ms < 0:
        raise ValueError("WRITER_CLOCK_INVALID")
    if type(max_slot_age_ms) is not int or max_slot_age_ms <= 0:
        raise ValueError("WRITER_SLOT_AGE_POLICY_INVALID")
    if type(max_future_skew_ms) is not int or max_future_skew_ms < 0:
        raise ValueError("WRITER_SLOT_SKEW_POLICY_INVALID")
    if retired_through_slot_at_ms is not None and (
        type(retired_through_slot_at_ms) is not int
        or retired_through_slot_at_ms < 0
    ):
        raise ValueError("WRITER_RETIREMENT_WATERMARK_INVALID")
    if (
        retired_through_slot_at_ms is not None
        and identity.slot_at_ms <= retired_through_slot_at_ms
    ):
        raise BudgetBlocked("BLOCKED_STALE_WRITER_SLOT")
    if identity.slot_at_ms < now_ms - max_slot_age_ms:
        raise BudgetBlocked("BLOCKED_STALE_WRITER_SLOT")
    if identity.slot_at_ms > now_ms + max_future_skew_ms:
        raise BudgetBlocked("BLOCKED_FUTURE_WRITER_SLOT")



def classify_reservation_replay(
    identity: WriterSlotIdentity,
    proposed_envelope: Mapping[str, object],
    existing_envelope: Mapping[str, object] | None,
    *,
    now_ms: int,
    max_slot_age_ms: int,
    max_future_skew_ms: int,
    retired_through_slot_at_ms: int | None,
) -> str:
    """Return an exact retained replay without repeating external access."""
    identity.validate()
    if set(proposed_envelope) != set(RESERVATION_ENVELOPE_FIELDS):
        raise ValueError("WRITER_RESERVATION_ENVELOPE_FIELDS_INVALID")
    if (
        proposed_envelope["writer_id"] != identity.writer_id
        or proposed_envelope["slot_id"] != identity.slot_id
        or proposed_envelope["idempotency_key"] != identity.idempotency_key
        or proposed_envelope["slot_at_ms"] != identity.slot_at_ms
    ):
        raise ValueError("WRITER_RESERVATION_ENVELOPE_IDENTITY_MISMATCH")
    if existing_envelope is not None:
        if set(existing_envelope) != set(RESERVATION_ENVELOPE_FIELDS):
            raise BudgetBlocked("BLOCKED_IDEMPOTENCY_CONFLICT")
        if all(
            existing_envelope[field] == proposed_envelope[field]
            for field in RESERVATION_ENVELOPE_FIELDS
        ):
            return "RETURN_EXISTING"
        raise BudgetBlocked("BLOCKED_IDEMPOTENCY_CONFLICT")
    validate_fresh_slot(
        identity,
        now_ms=now_ms,
        max_slot_age_ms=max_slot_age_ms,
        max_future_skew_ms=max_future_skew_ms,
        retired_through_slot_at_ms=retired_through_slot_at_ms,
    )
    return "NEW"



def minimum_reservation_rows_written() -> int:
    """Schema-derived floor: reservation table/indexes plus policy table/index."""
    return 7


def minimum_compaction_rows_written(max_deleted_rows: int) -> int:
    """Floor includes the compaction admission row and delete-trigger writes.

    Per deleted reservation the schema writes the reservation table and three
    indexes (4), the policy counter and its primary-key index (2), and the
    per-writer watermark and its primary-key index (2). Cloudflare metadata
    calibration must establish the actual conservative upper bound.
    """
    if type(max_deleted_rows) is not int or max_deleted_rows <= 0:
        raise ValueError("COMPACTION_BATCH_LIMIT_INVALID")
    return minimum_reservation_rows_written() + 8 * max_deleted_rows


def compaction_statement_params(
    *,
    now_ms: int,
    max_deleted_rows: int | None,
    compaction_authorized: bool,
    reserved_rows_written: int | None,
) -> tuple[int, int]:
    """Build a bounded compaction statement only under a separate authority."""
    if compaction_authorized is not True:
        raise BudgetBlocked("BLOCKED_COMPACTION_AUTHORITY_REQUIRED")
    if type(now_ms) is not int or now_ms < ROLLING_WINDOW_DAYS * UTC_DAY_MS:
        raise ValueError("COMPACTION_CLOCK_INVALID")
    if type(max_deleted_rows) is not int or max_deleted_rows <= 0:
        raise BudgetBlocked("BLOCKED_COMPACTION_BATCH_CAP_REQUIRED")
    if (
        type(reserved_rows_written) is not int
        or reserved_rows_written < minimum_compaction_rows_written(
            max_deleted_rows
        )
    ):
        raise BudgetBlocked("BLOCKED_COMPACTION_WRITE_ENVELOPE")
    cutoff_ms = now_ms - ROLLING_WINDOW_DAYS * UTC_DAY_MS
    return cutoff_ms, max_deleted_rows
