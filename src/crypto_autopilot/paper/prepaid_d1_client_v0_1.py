"""Prepaid, single-attempt D1 transport for the existing Cloud Paper SQL.

No D1 request funds another request. Every statement burns a claimed ticket
before transport. Unknown actual usage poisons the client until human review.
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.request import Request, build_opener

from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import (
    ACCOUNT_ID_RE,
    DATABASE_ID_RE,
    READ_SLOT_RESERVATION_SQL,
    RECORD_RECOVERY_RECEIPT_SQL,
    RESERVE_SLOT_SQL,
    SETTLE_SLOT_SQL,
    D1LedgerUnavailable,
    D1QueryResult,
    D1UsageGuard,
    _NoRedirect,
)
from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.cloud_loop_v0_1 import SLOT_MS, SLOT_OFFSET_MS
from crypto_autopilot.paper.prepaid_query_controller_v0_1 import PrepaidQueryMeter
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import (
    READ_SHARED_WRITER_SQL,
    RESERVE_SHARED_WRITER_SQL,
    QueryOperation,
)

_OPERATIONS: dict[str, QueryOperation] = {
    RESERVE_SLOT_SQL: "RESERVATION",
    SETTLE_SLOT_SQL: "RESERVATION",
    RECORD_RECOVERY_RECEIPT_SQL: "RESERVATION",
    READ_SLOT_RESERVATION_SQL: "REPLAY_READ",
    RESERVE_SHARED_WRITER_SQL: "RESERVATION",
    READ_SHARED_WRITER_SQL: "REPLAY_READ",
}


@dataclass(frozen=True, slots=True)
class DatabaseSizeEvidence:
    """Independently measured database bytes; not fetched by this adapter."""

    database_id: str
    coverage_complete: bool
    observed_at_ms: int
    measured_through_ms: int
    size_bytes: int

    def validate(self, *, database_id: str, guard: D1UsageGuard) -> None:
        now = guard.clock_ms()
        usable_age = guard.policy.max_evidence_age_ms - guard.policy.request_timeout_reserve_ms
        if (
            self.database_id != database_id or self.coverage_complete is not True
            or type(self.size_bytes) is not int or self.size_bytes < 0
            or self.size_bytes > guard.snapshot.storage_bytes
        ):
            raise BudgetBlocked("BLOCKED_PREPAID_DATABASE_EVIDENCE_INVALID")
        for stamp in (self.observed_at_ms, self.measured_through_ms):
            if (
                type(stamp) is not int or not 0 <= now - stamp <= usable_age
                or datetime.fromtimestamp(stamp / 1000, UTC).date()
                != datetime.fromtimestamp(now / 1000, UTC).date()
            ):
                raise BudgetBlocked("BLOCKED_PREPAID_DATABASE_EVIDENCE_STALE")


class PrepaidCloudflareD1QueryClient:
    """Exactly one prepaid attempt per whitelisted, identity-bound SQL."""

    def __init__(
        self, *, api_token: str, account_id: str, database_id: str,
        usage_guard: D1UsageGuard, query_meter: PrepaidQueryMeter,
        writer_id: str, slot_id: str, database_evidence: DatabaseSizeEvidence,
        timeout_seconds: float = 10.0,
    ) -> None:
        # Gate checks precede credential validation and HTTP construction.
        self.validate_inputs(
            usage_guard=usage_guard, query_meter=query_meter,
            writer_id=writer_id, slot_id=slot_id,
        )
        if (
            not isinstance(api_token, str) or not api_token
            or any(ch in api_token for ch in "\r\n")
        ):
            raise D1LedgerUnavailable("D1_LEDGER_CREDENTIAL_MISSING")
        if not isinstance(account_id, str) or not ACCOUNT_ID_RE.fullmatch(account_id):
            raise D1LedgerUnavailable("D1_LEDGER_ACCOUNT_ID_INVALID")
        if not isinstance(database_id, str) or not DATABASE_ID_RE.fullmatch(database_id):
            raise D1LedgerUnavailable("D1_LEDGER_DATABASE_ID_INVALID")
        if isinstance(timeout_seconds, bool) or not 0 < timeout_seconds <= 10:
            raise D1LedgerUnavailable("D1_LEDGER_TIMEOUT_INVALID")
        if not isinstance(database_evidence, DatabaseSizeEvidence):
            raise BudgetBlocked("BLOCKED_PREPAID_DATABASE_EVIDENCE_REQUIRED")
        database_evidence.validate(database_id=database_id, guard=usage_guard)
        self._api_token = api_token
        self._account_id = account_id
        self._database_id = database_id
        self._guard = usage_guard
        self._meter = query_meter
        self._writer = writer_id
        self._slot = slot_id
        self._database_evidence = database_evidence
        self._last_size = database_evidence.size_bytes
        self._timeout = timeout_seconds
        self._poisoned = False
        self._lock = threading.Lock()

    @staticmethod
    def validate_inputs(
        *, usage_guard: D1UsageGuard, query_meter: PrepaidQueryMeter,
        writer_id: str, slot_id: str,
    ) -> None:
        if not isinstance(query_meter, PrepaidQueryMeter):
            raise BudgetBlocked("BLOCKED_PREPAID_QUERY_METER_REQUIRED")
        if not isinstance(usage_guard, D1UsageGuard):
            raise BudgetBlocked("BLOCKED_PREPAID_USAGE_GUARD_REQUIRED")
        usage_guard.validate_evidence()
        query_meter.validate_binding(writer_id=writer_id, slot_id=slot_id)
        for operation in ("RESERVATION", "REPLAY_READ"):
            cost = query_meter.statement_cost(operation)
            p = usage_guard.policy
            if (
                cost.rows_read > p.rows_read_per_query
                or cost.rows_written > p.rows_written_per_query
                or cost.storage_bytes > p.storage_growth_per_query_bytes
            ):
                raise BudgetBlocked("BLOCKED_PREPAID_LOCAL_ENVELOPE_UNDERCOUNTED")

    @classmethod
    def from_environment(
        cls, *, usage_guard: D1UsageGuard, query_meter: PrepaidQueryMeter,
        writer_id: str, slot_id: str, database_evidence: DatabaseSizeEvidence,
    ) -> PrepaidCloudflareD1QueryClient:
        cls.validate_inputs(
            usage_guard=usage_guard, query_meter=query_meter,
            writer_id=writer_id, slot_id=slot_id,
        )
        return cls(
            api_token=os.environ.get("CLOUDFLARE_D1_API_TOKEN", ""),
            account_id=os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""),
            database_id=os.environ.get("CLOUDFLARE_D1_DATABASE_ID", ""),
            usage_guard=usage_guard, query_meter=query_meter,
            writer_id=writer_id, slot_id=slot_id, database_evidence=database_evidence,
        )

    def validate_runtime_binding(
        self, *, meter: PrepaidQueryMeter, writer_id: str, slot_id: str,
    ) -> None:
        if self._meter is not meter or self._writer != writer_id or self._slot != slot_id:
            raise BudgetBlocked("BLOCKED_PREPAID_RUNTIME_BINDING_MISMATCH")
        meter.validate_binding(writer_id=writer_id, slot_id=slot_id)

    def __repr__(self) -> str:
        return "PrepaidCloudflareD1QueryClient(credentials=REDACTED)"

    def _validate_statement(self, sql: str, params: tuple[object, ...]) -> QueryOperation:
        if (
            not isinstance(sql, str) or sql not in _OPERATIONS
            or not isinstance(params, tuple) or len(params) != sql.count("?")
        ):
            raise D1LedgerUnavailable("D1_LEDGER_STATEMENT_NOT_APPROVED")
        legacy_slot = self._slot.removeprefix("slot:")
        if not legacy_slot.isdigit():
            raise BudgetBlocked("BLOCKED_PREPAID_SLOT_INVALID")
        slot_at_ms = int(legacy_slot)
        if (slot_at_ms - SLOT_OFFSET_MS) % SLOT_MS:
            raise BudgetBlocked("BLOCKED_PREPAID_SLOT_INVALID")
        ordinal = str((slot_at_ms - SLOT_OFFSET_MS) // SLOT_MS)
        if sql == RESERVE_SLOT_SQL:
            bound = params[10] == ordinal
        elif sql == SETTLE_SLOT_SQL:
            bound = params[4] == ordinal
        elif sql == READ_SLOT_RESERVATION_SQL:
            bound = params[0] == ordinal
        elif sql == RECORD_RECOVERY_RECEIPT_SQL:
            bound = params[0] == ordinal and params[4] == ordinal
        elif sql == RESERVE_SHARED_WRITER_SQL:
            bound = (
                params[3] == self._writer and params[4] == self._slot
                and params[5] == self._slot
                and type(params[6]) is int and params[6] == slot_at_ms
            )
        else:
            bound = params == (self._writer, self._slot)
        if not bound:
            raise BudgetBlocked("BLOCKED_PREPAID_SQL_IDENTITY_MISMATCH")
        return _OPERATIONS[sql]

    def query(self, sql: str, params: tuple[object, ...]) -> D1QueryResult:
        with self._lock:
            if self._poisoned:
                raise D1LedgerUnavailable("D1_LEDGER_REVIEW_REQUIRED")
            operation = self._validate_statement(sql, params)
            self._database_evidence.validate(database_id=self._database_id, guard=self._guard)
            self._guard.reserve_query()
            self._meter.charge_before_query(
                writer_id=self._writer, slot_id=self._slot, operation=operation,
            )
            # From here an ambiguous response keeps the debit and poisons this
            # client. A new process cannot resume the same remote ticket.
            try:
                self._guard.validate_evidence()
                self._meter.validate_binding(writer_id=self._writer, slot_id=self._slot)
                cost = self._meter.statement_cost(operation)
                result, size = self._request(sql, params)
                if (
                    result.rows_read > cost.rows_read
                    or result.rows_written > cost.rows_written
                    or size > self._last_size + cost.storage_bytes
                ):
                    raise D1LedgerUnavailable("D1_LEDGER_QUERY_HARD_STOP")
                self._last_size = max(self._last_size, size)
                return result
            except Exception:
                self._poisoned = True
                raise D1LedgerUnavailable("D1_LEDGER_REVIEW_REQUIRED") from None

    def _request(self, sql: str, params: tuple[object, ...]) -> tuple[D1QueryResult, int]:
        request = Request(
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{self._account_id}/d1/database/{self._database_id}/query",
            data=json.dumps({"sql": sql, "params": [str(p) for p in params]}).encode(),
            method="POST",
            headers={
                "Authorization": "Bearer " + self._api_token,
                "Content-Type": "application/json", "Accept": "application/json",
                "User-Agent": "crypto-autopilot-prepaid-d1-v0.1",
            },
        )
        try:
            with build_opener(_NoRedirect).open(request, timeout=self._timeout) as response:
                raw = response.read(256_001)
            if len(raw) > 256_000:
                raise ValueError
            decoded = json.loads(raw)
            statements = decoded.get("result") if isinstance(decoded, dict) else None
            if (
                not isinstance(decoded, dict) or decoded.get("success") is not True
                or not isinstance(statements, list) or len(statements) != 1
            ):
                raise ValueError
            statement = statements[0]
            if not isinstance(statement, dict) or statement.get("success") is not True:
                raise ValueError
            meta, rows = statement.get("meta"), statement.get("results")
            if not isinstance(meta, dict) or not isinstance(rows, list) or any(
                not isinstance(row, dict) for row in rows
            ):
                raise ValueError
            values = tuple(meta.get(name) for name in ("rows_read", "rows_written", "size_after"))
            if any(type(value) is not int or value < 0 for value in values):
                raise ValueError
            return D1QueryResult(tuple(rows), values[0], values[1]), values[2]
        except Exception:
            raise D1LedgerUnavailable("D1_LEDGER_RESPONSE_UNVERIFIED") from None
