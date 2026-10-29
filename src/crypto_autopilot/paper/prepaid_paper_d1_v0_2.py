"""Prepared V0.5 prepaid D1 client for Paper slots; no execution authority."""
from __future__ import annotations

from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import D1LedgerUnavailable
from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked, CloudBudgetPolicy
from crypto_autopilot.paper.prepaid_d1_client_v0_1 import PrepaidCloudflareD1QueryClient
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import (
    RESERVE_SHARED_WRITER_SQL as OLD_RESERVE_SQL,
)
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import (
    READ_SHARED_WRITER_SQL, RESERVE_SHARED_WRITER_SQL, QueryOperation,
    SharedWriterReservation, reservation_params,
)

_DAY_MS = 86_400_000


class PaperPrepaidD1Client(PrepaidCloudflareD1QueryClient):
    """Bound Paper SQL with V0.5 admission; disabled by default."""

    def __init__(self, *, execution_enabled: bool = False, **kwargs):
        if type(execution_enabled) is not bool:
            raise BudgetBlocked("BLOCKED_PAPER_EXECUTION_FLAG")
        self._execution_enabled = execution_enabled
        super().__init__(**kwargs)

    def query(self, sql: str, params: tuple[object, ...]):
        if not self._execution_enabled:
            raise BudgetBlocked("BLOCKED_PAPER_EXECUTION_DISABLED")
        return super().query(sql, params)

    def _validate_statement(self, sql: str, params: tuple[object, ...]) -> QueryOperation:
        if not isinstance(sql, str) or not isinstance(params, tuple) or len(params) != sql.count("?"):
            raise D1LedgerUnavailable("D1_LEDGER_STATEMENT_NOT_APPROVED")
        slot_value = self._slot.removeprefix("slot:")
        if not slot_value.isascii() or not slot_value.isdigit() or str(int(slot_value)) != slot_value:
            raise BudgetBlocked("BLOCKED_PREPAID_SLOT_INVALID")
        slot_at_ms = int(slot_value)
        now_ms = self._guard.clock_ms()
        if (
            type(now_ms) is not int or not 0 <= now_ms - slot_at_ms <= 600_000
            or now_ms // _DAY_MS != slot_at_ms // _DAY_MS
        ):
            raise BudgetBlocked("BLOCKED_PAPER_SLOT_STALE_OR_FUTURE")
        if sql == OLD_RESERVE_SQL:
            raise D1LedgerUnavailable("D1_LEDGER_STATEMENT_NOT_APPROVED")
        if sql == READ_SHARED_WRITER_SQL:
            if params != (self._writer, self._slot):
                raise BudgetBlocked("BLOCKED_PREPAID_SQL_IDENTITY_MISMATCH")
            return "REPLAY_READ"
        if sql != RESERVE_SHARED_WRITER_SQL:
            return super()._validate_statement(sql, params)
        try:
            reservation = SharedWriterReservation(
                writer_id=params[3], slot_id=params[4], idempotency_key=params[5],
                slot_at_ms=params[6], reserved_at_ms=params[8],
                provider_requests=params[9], r2_class_a=params[10], r2_class_b=params[11],
                r2_new_bytes=params[12], d1_queries=params[13], d1_rows_read=params[14],
                d1_rows_written=params[15], d1_storage_growth_bytes=params[16],
            )
            p = CloudBudgetPolicy()
            envelope = self._meter.report()["ticket_envelope_charged_in_full"]
            bound = (
                params == reservation_params(reservation)
                and reservation.writer_id == self._writer and reservation.slot_id == self._slot
                and reservation.slot_at_ms == slot_at_ms
                and slot_at_ms <= reservation.reserved_at_ms <= now_ms
                and reservation.provider_requests == p.provider_per_run
                and reservation.r2_class_a == p.r2_class_a_per_run
                and reservation.r2_class_b == p.r2_class_b_per_run
                and reservation.r2_new_bytes == p.r2_new_bytes_per_run
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
        # On ambiguous or late results, the inherited client poisons itself and
        # retains the prepaid debit; no caller may retry automatically.
        self._validate_statement(sql, params)
        result = super()._request(sql, params)
        self._validate_statement(sql, params)
        self._guard.validate_evidence()
        self.validate_runtime_binding(meter=self._meter, writer_id=self._writer, slot_id=self._slot)
        self._database_evidence.validate(database_id=self._database_id, guard=self._guard)
        return result
