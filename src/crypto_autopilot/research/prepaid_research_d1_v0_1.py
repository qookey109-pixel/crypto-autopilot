"""Prepared research-only D1 transport for the 02:17 UTC daily slot.

No workflow or production execution is enabled by this module.
"""
from __future__ import annotations

from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import D1LedgerUnavailable
from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.prepaid_d1_client_v0_1 import PrepaidCloudflareD1QueryClient
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import (
    READ_SHARED_WRITER_SQL, RESERVE_SHARED_WRITER_SQL, QueryOperation,
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
        if sql == RESERVE_SHARED_WRITER_SQL:
            bound = (
                params[3] == WRITER and params[4] == self._slot
                and params[5] == self._slot and type(params[6]) is int
                and params[6] == int(self._slot.removeprefix("slot:"))
            )
            operation: QueryOperation = "RESERVATION"
        else:
            bound = params == (WRITER, self._slot)
            operation = "REPLAY_READ"
        if not bound:
            raise BudgetBlocked("BLOCKED_PREPAID_SQL_IDENTITY_MISMATCH")
        return operation
