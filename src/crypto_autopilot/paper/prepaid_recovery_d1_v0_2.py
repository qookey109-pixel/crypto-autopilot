"""Prepared V0.5 prepaid D1 admission for bounded result-seal recovery.

This module is disabled by default, has no workflow, and does not establish
account coverage, trusted caller identity, calibrated cost or production authority.
"""
from __future__ import annotations

from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import D1LedgerUnavailable
from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.cloud_loop_v0_1 import SLOT_MS, SLOT_OFFSET_MS
from crypto_autopilot.paper.prepaid_d1_client_v0_1 import PrepaidCloudflareD1QueryClient
from crypto_autopilot.paper.shared_cloud_paper_recovery_v0_1 import WRITER as CLOUD_WRITER
from crypto_autopilot.paper.shared_run_recovery_v0_1 import WRITER as LIVE_WRITER
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import (
    READ_SHARED_WRITER_SQL, RESERVE_SHARED_WRITER_SQL, QueryOperation,
    SharedWriterReservation, reservation_params,
)

_DAY_MS = 86_400_000


class RecoveryPrepaidD1Client(PrepaidCloudflareD1QueryClient):
    """Whitelist only recovery V0.5 shared-admission statements."""

    def __init__(self, *, writer_id: str, slot_id: str, execution_enabled: bool = False, **kwargs):
        if type(execution_enabled) is not bool:
            raise BudgetBlocked("BLOCKED_RECOVERY_EXECUTION_FLAG")
        self._execution_enabled = execution_enabled
        if writer_id not in {LIVE_WRITER, CLOUD_WRITER} or not isinstance(slot_id, str):
            raise BudgetBlocked("BLOCKED_RECOVERY_SLOT_OR_WRITER")
        value = slot_id.removeprefix("slot:")
        if (
            slot_id != f"slot:{value}" or not value.isascii() or not value.isdigit()
            or str(int(value)) != value or int(value) <= 0
            or (int(value) - SLOT_OFFSET_MS) % SLOT_MS
        ):
            raise BudgetBlocked("BLOCKED_RECOVERY_SLOT_OR_WRITER")
        super().__init__(writer_id=writer_id, slot_id=slot_id, **kwargs)

    def query(self, sql: str, params: tuple[object, ...]):
        if not self._execution_enabled:
            raise BudgetBlocked("BLOCKED_RECOVERY_EXECUTION_DISABLED")
        return super().query(sql, params)

    def _validate_statement(self, sql: str, params: tuple[object, ...]) -> QueryOperation:
        if (
            sql not in (RESERVE_SHARED_WRITER_SQL, READ_SHARED_WRITER_SQL)
            or not isinstance(params, tuple) or len(params) != sql.count("?")
        ):
            raise D1LedgerUnavailable("D1_LEDGER_STATEMENT_NOT_APPROVED")
        slot_at_ms = int(self._slot.removeprefix("slot:"))
        now_ms = self._guard.clock_ms()
        if (
            type(now_ms) is not int or not 0 <= now_ms - slot_at_ms <= 600_000
            or now_ms // _DAY_MS != slot_at_ms // _DAY_MS
        ):
            raise BudgetBlocked("BLOCKED_RECOVERY_SLOT_STALE_OR_FUTURE")
        if sql == READ_SHARED_WRITER_SQL:
            if params != (self._writer, self._slot):
                raise BudgetBlocked("BLOCKED_PREPAID_SQL_IDENTITY_MISMATCH")
            return "REPLAY_READ"
        try:
            reservation = SharedWriterReservation(
                writer_id=params[3], slot_id=params[4], idempotency_key=params[5],
                slot_at_ms=params[6], reserved_at_ms=params[8],
                provider_requests=params[9], r2_class_a=params[10], r2_class_b=params[11],
                r2_new_bytes=params[12], d1_queries=params[13], d1_rows_read=params[14],
                d1_rows_written=params[15], d1_storage_growth_bytes=params[16],
            )
            envelope = self._meter.report()["ticket_envelope_charged_in_full"]
            bound = (
                params == reservation_params(reservation)
                and reservation.writer_id == self._writer and reservation.slot_id == self._slot
                and reservation.slot_at_ms == slot_at_ms
                and slot_at_ms <= reservation.reserved_at_ms <= now_ms
                and reservation.provider_requests == 0
                and reservation.r2_class_a == 8 and reservation.r2_class_b == 64
                and reservation.r2_new_bytes == 16384
                and reservation.d1_queries == envelope["queries"]
                and reservation.d1_rows_read == envelope["rows_read"]
                and reservation.d1_rows_written == envelope["rows_written"]
                and reservation.d1_storage_growth_bytes == envelope["storage_bytes"]
            )
        except (TypeError, ValueError, KeyError, IndexError, OverflowError, OSError):
            bound = False
        if not bound:
            raise BudgetBlocked("BLOCKED_PREPAID_SQL_IDENTITY_MISMATCH")
        return "RESERVATION"

    def _request(self, sql: str, params: tuple[object, ...]):
        self._validate_statement(sql, params)
        result = super()._request(sql, params)
        try:
            self._validate_statement(sql, params)
            self._guard.validate_evidence()
            self.validate_runtime_binding(meter=self._meter, writer_id=self._writer, slot_id=self._slot)
            self._database_evidence.validate(database_id=self._database_id, guard=self._guard)
        except Exception:
            raise D1LedgerUnavailable("D1_LEDGER_RESPONSE_UNVERIFIED") from None
        return result
