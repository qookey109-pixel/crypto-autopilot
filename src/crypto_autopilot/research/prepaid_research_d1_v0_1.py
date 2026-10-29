"""Prepared research-only D1 transport for the 02:17 UTC daily slot.

No workflow or production execution is enabled by this module.
"""
from __future__ import annotations

from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import D1LedgerUnavailable
from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.prepaid_d1_client_v0_1 import PrepaidCloudflareD1QueryClient
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import (
    READ_SHARED_WRITER_SQL, RESERVE_SHARED_WRITER_SQL, QueryOperation,
    SharedWriterReservation, reservation_params,
)

WRITER = "crypto-autopilot:research-signal-layer-v0-2"
_DAY_MS = 86_400_000
_SLOT_OFFSET_MS = (2 * 60 + 17) * 60_000


class ResearchPrepaidD1Client(PrepaidCloudflareD1QueryClient):
    """Share only admission statements; never expose Paper ledger statements."""

    def __init__(self, *, writer_id: str, slot_id: str, **kwargs):
        if writer_id != WRITER or not isinstance(slot_id, str) or not slot_id.startswith("slot:"):
            raise BudgetBlocked("BLOCKED_RESEARCH_SLOT_OR_WRITER")
        value = slot_id.removeprefix("slot:")
        if (
            not value.isascii() or not value.isdigit() or str(int(value)) != value
            or int(value) <= 0 or int(value) % _DAY_MS != _SLOT_OFFSET_MS
        ):
            raise BudgetBlocked("BLOCKED_RESEARCH_SLOT_OR_WRITER")
        super().__init__(writer_id=writer_id, slot_id=slot_id, **kwargs)

    def _validate_statement(self, sql: str, params: tuple[object, ...]) -> QueryOperation:
        if (
            sql not in (RESERVE_SHARED_WRITER_SQL, READ_SHARED_WRITER_SQL)
            or not isinstance(params, tuple) or len(params) != sql.count("?")
        ):
            raise D1LedgerUnavailable("D1_LEDGER_STATEMENT_NOT_APPROVED")
        slot_at_ms = int(self._slot.removeprefix("slot:"))
        now_ms = self._guard.clock_ms()
        if type(now_ms) is not int or not 0 <= now_ms - slot_at_ms <= 600_000:
            raise BudgetBlocked("BLOCKED_RESEARCH_SLOT_STALE_OR_FUTURE")
        if sql == RESERVE_SHARED_WRITER_SQL:
            try:
                reservation = SharedWriterReservation(
                    writer_id=params[3], slot_id=params[4], idempotency_key=params[5],
                    slot_at_ms=params[6], reserved_at_ms=params[8],
                    provider_requests=params[9], r2_class_a=params[10],
                    r2_class_b=params[11], r2_new_bytes=params[12],
                    d1_queries=params[13], d1_rows_read=params[14],
                    d1_rows_written=params[15], d1_storage_growth_bytes=params[16],
                )
                envelope = self._meter.report()["ticket_envelope_charged_in_full"]
                bound = (
                    params == reservation_params(reservation)
                    and reservation.writer_id == WRITER and reservation.slot_id == self._slot
                    and reservation.slot_at_ms == slot_at_ms
                    and slot_at_ms <= reservation.reserved_at_ms <= now_ms
                    and 0 <= reservation.provider_requests <= 3
                    and reservation.r2_class_a == 3 and reservation.r2_class_b == 6
                    and reservation.r2_new_bytes == 270_336
                    and reservation.d1_queries == envelope["queries"]
                    and reservation.d1_rows_read == envelope["rows_read"]
                    and reservation.d1_rows_written == envelope["rows_written"]
                    and reservation.d1_storage_growth_bytes == envelope["storage_bytes"]
                )
            except (TypeError, ValueError, KeyError, OverflowError, OSError):
                bound = False
            operation: QueryOperation = "RESERVATION"
        else:
            bound = params == (WRITER, self._slot)
            operation = "REPLAY_READ"
        if not bound:
            raise BudgetBlocked("BLOCKED_PREPAID_SQL_IDENTITY_MISMATCH")
        return operation
