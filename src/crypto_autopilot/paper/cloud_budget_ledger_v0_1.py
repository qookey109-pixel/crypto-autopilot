"""Cloudflare D1-backed, fail-closed Cloud Paper slot reservations.

The ledger is additive infrastructure support only. It does not provision D1,
fetch R2 usage, call a provider, write R2, activate Cloud Paper, or schedule work.
"""
from __future__ import annotations

import json
import os
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from crypto_autopilot.paper.cloud_budget_v0_1 import (
    BudgetBlocked,
    CloudBudgetPolicy,
    R2UsageSnapshot,
)


RESERVE_SLOT_SQL = """
WITH recent AS (
    SELECT
        reserved_at_ms,
        run_id,
        COALESCE(actual_provider_requests, reserved_provider_requests) AS provider_requests,
        COALESCE(actual_class_a, reserved_class_a) AS class_a,
        COALESCE(actual_class_b, reserved_class_b) AS class_b,
        COALESCE(actual_new_bytes, reserved_new_bytes) AS new_bytes
    FROM cloud_paper_budget_reservations
    WHERE reserved_at_ms >= CAST(? AS INTEGER)
      AND reserved_at_ms >= CAST(? AS INTEGER)
      AND reserved_at_ms <= CAST(? AS INTEGER)
), totals AS (
    SELECT
        COALESCE(SUM(CASE WHEN reserved_at_ms >= CAST(? AS INTEGER) THEN class_a ELSE 0 END), 0) AS month_a,
        COALESCE(SUM(CASE WHEN reserved_at_ms >= CAST(? AS INTEGER) THEN class_a ELSE 0 END), 0) AS day_a,
        COALESCE(SUM(class_a), 0) AS rolling_a,
        COALESCE(SUM(CASE WHEN reserved_at_ms >= CAST(? AS INTEGER) THEN class_b ELSE 0 END), 0) AS month_b,
        COALESCE(SUM(CASE WHEN reserved_at_ms >= CAST(? AS INTEGER) THEN class_b ELSE 0 END), 0) AS day_b,
        COALESCE(SUM(class_b), 0) AS rolling_b,
        COALESCE(SUM(CASE WHEN reserved_at_ms >= CAST(? AS INTEGER) THEN provider_requests ELSE 0 END), 0) AS day_provider,
        COALESCE(SUM(CASE WHEN run_id = ? THEN provider_requests ELSE 0 END), 0) AS run_provider,
        COALESCE(SUM(CASE WHEN reserved_at_ms >= CAST(? AS INTEGER) THEN new_bytes ELSE 0 END), 0) AS day_bytes,
        COALESCE(SUM(new_bytes), 0) AS rolling_bytes
    FROM recent
)
INSERT INTO cloud_paper_budget_reservations (
    slot_id, run_id, reserved_at_ms, measured_through_ms, state,
    reserved_provider_requests, reserved_class_a, reserved_class_b, reserved_new_bytes,
    actual_provider_requests, actual_class_a, actual_class_b, actual_new_bytes
)
SELECT
    CAST(? AS TEXT), CAST(? AS TEXT), CAST(? AS INTEGER), CAST(? AS INTEGER), 'RESERVED',
    CAST(? AS INTEGER), CAST(? AS INTEGER), CAST(? AS INTEGER), CAST(? AS INTEGER),
    NULL, NULL, NULL, NULL
FROM totals
WHERE (SELECT reservation_count FROM cloud_paper_budget_meta WHERE singleton = 1) < CAST(? AS INTEGER)
  AND NOT EXISTS (
      SELECT 1 FROM cloud_paper_budget_reservations
      WHERE slot_id = CAST(? AS TEXT)
  )
  AND CAST(? AS INTEGER) + month_a + CAST(? AS INTEGER) <= CAST(? AS INTEGER)
  AND CAST(? AS INTEGER) + day_a + CAST(? AS INTEGER) <= CAST(? AS INTEGER)
  AND CAST(? AS INTEGER) + rolling_a + CAST(? AS INTEGER) <= CAST(? AS INTEGER)
  AND CAST(? AS INTEGER) + month_b + CAST(? AS INTEGER) <= CAST(? AS INTEGER)
  AND CAST(? AS INTEGER) + day_b + CAST(? AS INTEGER) <= CAST(? AS INTEGER)
  AND CAST(? AS INTEGER) + rolling_b + CAST(? AS INTEGER) <= CAST(? AS INTEGER)
  AND CAST(? AS INTEGER) + day_provider + CAST(? AS INTEGER) <= CAST(? AS INTEGER)
  AND run_provider + CAST(? AS INTEGER) <= CAST(? AS INTEGER)
  AND CAST(? AS INTEGER) + day_bytes + CAST(? AS INTEGER) <= CAST(? AS INTEGER)
  AND CAST(? AS INTEGER) + rolling_bytes + CAST(? AS INTEGER) <= CAST(? AS INTEGER)
RETURNING slot_id
"""

SETTLE_SLOT_SQL = """
UPDATE cloud_paper_budget_reservations
SET state = 'SETTLED',
    actual_provider_requests = CAST(? AS INTEGER),
    actual_class_a = CAST(? AS INTEGER),
    actual_class_b = CAST(? AS INTEGER),
    actual_new_bytes = CAST(? AS INTEGER)
WHERE slot_id = CAST(? AS TEXT)
  AND state = 'RESERVED'
  AND CAST(? AS INTEGER) >= reserved_at_ms
  AND CAST(? AS INTEGER) <= reserved_provider_requests
  AND CAST(? AS INTEGER) <= reserved_class_a
  AND CAST(? AS INTEGER) <= reserved_class_b
  AND CAST(? AS INTEGER) <= reserved_new_bytes
RETURNING slot_id
"""

ACCOUNT_ID_RE = re.compile(r"^[0-9a-fA-F]{32}$")
DATABASE_ID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


class D1LedgerUnavailable(RuntimeError):
    """Stable transport/response error; never exposes credentials or response bodies."""


@dataclass(frozen=True, slots=True)
class D1QueryResult:
    rows: tuple[dict[str, object], ...]
    rows_read: int
    rows_written: int


class D1QueryClient(Protocol):
    def query(self, sql: str, params: tuple[object, ...]) -> D1QueryResult:
        """Execute one parameterized statement and return bounded metadata."""


@dataclass(frozen=True, slots=True)
class D1UsageSnapshot:
    """Account-wide D1 usage evidence plus already-known outstanding reservations."""

    account_wide: bool
    reservation_coverage_complete: bool
    observed_at_ms: int
    measured_through_ms: int
    rows_read_day: int
    rows_written_day: int
    storage_bytes: int
    pending_rows_read_day: int = 0
    pending_rows_written_day: int = 0
    pending_storage_bytes: int = 0


@dataclass(frozen=True, slots=True)
class D1UsagePolicy:
    """Project guardrails below Cloudflare's free-tier limits.

    The storage growth reservation is a conservative project envelope per query;
    it is not a claim about measured D1 row or index size.
    """

    max_evidence_age_ms: int = 60_000
    request_timeout_reserve_ms: int = 10_000
    rows_read_per_day: int = 4_000_000
    rows_written_per_day: int = 75_000
    storage_bytes_total: int = 4_000_000_000
    rows_read_per_query: int = 25_000
    rows_written_per_query: int = 10
    storage_growth_per_query_bytes: int = 16_384


class D1UsageGuard:
    """Fail closed on stale/incomplete account usage before reserving a query.

    Reservations accumulate only within this guard instance. Production use also
    requires an account-wide atomic ledger covering every D1 writer; this class
    does not claim to coordinate independent runners or workflows.
    """

    def __init__(
        self,
        *,
        snapshot: D1UsageSnapshot,
        clock_ms: Callable[[], int],
        policy: D1UsagePolicy = D1UsagePolicy(),
    ) -> None:
        if not callable(clock_ms):
            raise ValueError("a D1 usage evidence clock is required")
        self.snapshot = snapshot
        self.clock_ms = clock_ms
        self.policy = policy
        self._reserved_reads_day = 0
        self._reserved_writes_day = 0
        self._reserved_storage_bytes = 0
        self._lock = threading.Lock()

    def validate_evidence(self) -> None:
        """Check current evidence without consuming a query reservation."""
        with self._lock:
            self._validate_evidence_at(self.clock_ms())

    def reserve_query(self) -> None:
        """Reserve one conservative query envelope before its external request."""
        with self._lock:
            now_ms = self.clock_ms()
            self._validate_evidence_at(now_ms)
            p, s = self.policy, self.snapshot
            if (
                self._reserved_reads_day + p.rows_read_per_query
                + s.rows_read_day + s.pending_rows_read_day > p.rows_read_per_day
            ):
                raise BudgetBlocked("BLOCKED_D1_ROWS_READ_DAILY_LIMIT")
            if (
                self._reserved_writes_day + p.rows_written_per_query
                + s.rows_written_day + s.pending_rows_written_day
                > p.rows_written_per_day
            ):
                raise BudgetBlocked("BLOCKED_D1_ROWS_WRITTEN_DAILY_LIMIT")
            if (
                self._reserved_storage_bytes + p.storage_growth_per_query_bytes
                + s.storage_bytes + s.pending_storage_bytes > p.storage_bytes_total
            ):
                raise BudgetBlocked("BLOCKED_D1_STORAGE_HARD_STOP")
            self._reserved_reads_day += p.rows_read_per_query
            self._reserved_writes_day += p.rows_written_per_query
            self._reserved_storage_bytes += p.storage_growth_per_query_bytes

    def _validate_evidence_at(self, now_ms: int) -> None:
        s, p = self.snapshot, self.policy
        policy_values = (
            p.max_evidence_age_ms,
            p.request_timeout_reserve_ms,
            p.rows_read_per_day,
            p.rows_written_per_day,
            p.storage_bytes_total,
            p.rows_read_per_query,
            p.rows_written_per_query,
            p.storage_growth_per_query_bytes,
        )
        if any(type(value) is not int or value <= 0 for value in policy_values):
            raise BudgetBlocked("BLOCKED_D1_USAGE_POLICY_INVALID")
        if p.max_evidence_age_ms <= p.request_timeout_reserve_ms:
            raise BudgetBlocked("BLOCKED_D1_USAGE_POLICY_INVALID")
        if not s.account_wide or not s.reservation_coverage_complete:
            raise BudgetBlocked("BLOCKED_D1_USAGE_EVIDENCE_INCOMPLETE")
        evidence_values = (
            s.observed_at_ms,
            s.measured_through_ms,
            s.rows_read_day,
            s.rows_written_day,
            s.storage_bytes,
            s.pending_rows_read_day,
            s.pending_rows_written_day,
            s.pending_storage_bytes,
        )
        if any(type(value) is not int or value < 0 for value in evidence_values):
            raise BudgetBlocked("BLOCKED_D1_USAGE_EVIDENCE_UNKNOWN")
        if type(now_ms) is not int or now_ms < 0:
            raise BudgetBlocked("BLOCKED_D1_USAGE_CLOCK_INVALID")
        observed_age = now_ms - s.observed_at_ms
        coverage_age = now_ms - s.measured_through_ms
        if observed_age < 0 or coverage_age < 0:
            raise BudgetBlocked("BLOCKED_D1_USAGE_EVIDENCE_FROM_FUTURE")
        usable_age = p.max_evidence_age_ms - p.request_timeout_reserve_ms
        if max(observed_age, coverage_age) > usable_age:
            raise BudgetBlocked("BLOCKED_D1_USAGE_EVIDENCE_STALE")


class D1QueryUsageBudgetGate(Protocol):
    """Budget gate required by every external D1 query."""

    def reserve_query(self) -> None:
        """Reserve a conservative D1 request envelope or fail closed."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise D1LedgerUnavailable("D1_LEDGER_REDIRECT_REJECTED")


class CloudflareD1QueryClient:
    """Minimal Cloudflare D1 REST adapter. It never retries or logs request data."""

    def __init__(
        self,
        *,
        api_token: str,
        account_id: str,
        database_id: str,
        usage_guard: D1QueryUsageBudgetGate,
        timeout_seconds: float = 10.0,
    ) -> None:
        if not api_token or any(ch in api_token for ch in "\r\n"):
            raise D1LedgerUnavailable("D1_LEDGER_CREDENTIAL_MISSING")
        if not ACCOUNT_ID_RE.fullmatch(account_id):
            raise D1LedgerUnavailable("D1_LEDGER_ACCOUNT_ID_INVALID")
        if not DATABASE_ID_RE.fullmatch(database_id):
            raise D1LedgerUnavailable("D1_LEDGER_DATABASE_ID_INVALID")
        if not callable(getattr(usage_guard, "reserve_query", None)):
            raise D1LedgerUnavailable("D1_LEDGER_USAGE_GUARD_MISSING")
        if not 0 < timeout_seconds <= 10:
            raise D1LedgerUnavailable("D1_LEDGER_TIMEOUT_INVALID")
        self._api_token = api_token
        self._account_id = account_id
        self._database_id = database_id
        self._usage_guard = usage_guard
        self._timeout_seconds = timeout_seconds

    @classmethod
    def from_environment(
        cls, *, usage_guard: D1QueryUsageBudgetGate,
    ) -> CloudflareD1QueryClient:
        return cls(
            api_token=os.environ.get("CLOUDFLARE_D1_API_TOKEN", ""),
            account_id=os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""),
            database_id=os.environ.get("CLOUDFLARE_D1_DATABASE_ID", ""),
            usage_guard=usage_guard,
        )

    def __repr__(self) -> str:
        return "CloudflareD1QueryClient(credentials=REDACTED)"

    def query(self, sql: str, params: tuple[object, ...]) -> D1QueryResult:
        if not sql.strip() or len(sql.encode("utf-8")) > 50_000:
            raise D1LedgerUnavailable("D1_LEDGER_QUERY_INVALID")
        if len(params) > 100:
            raise D1LedgerUnavailable("D1_LEDGER_PARAMETER_LIMIT")
        self._usage_guard.reserve_query()
        payload = json.dumps(
            {"sql": sql, "params": [str(value) for value in params]},
            separators=(",", ":"),
        ).encode("utf-8")
        request = Request(
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{self._account_id}/d1/database/{self._database_id}/query",
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "crypto-autopilot-cloud-paper-ledger-v0.1",
            },
        )
        try:
            with build_opener(_NoRedirect).open(
                request, timeout=self._timeout_seconds
            ) as response:
                body = response.read(256_001)
            if len(body) > 256_000:
                raise D1LedgerUnavailable("D1_LEDGER_RESPONSE_TOO_LARGE")
            decoded = json.loads(body)
        except D1LedgerUnavailable:
            raise
        except (HTTPError, URLError, TimeoutError, OSError, ValueError):
            raise D1LedgerUnavailable("D1_LEDGER_REQUEST_FAILED") from None

        if not isinstance(decoded, dict) or decoded.get("success") is not True:
            raise D1LedgerUnavailable("D1_LEDGER_RESPONSE_INVALID")
        results = decoded.get("result")
        if not isinstance(results, list) or len(results) != 1:
            raise D1LedgerUnavailable("D1_LEDGER_RESPONSE_INVALID")
        result = results[0]
        if not isinstance(result, dict) or result.get("success") is not True:
            raise D1LedgerUnavailable("D1_LEDGER_STATEMENT_FAILED")
        meta = result.get("meta")
        rows = result.get("results")
        if not isinstance(meta, dict) or not isinstance(rows, list):
            raise D1LedgerUnavailable("D1_LEDGER_USAGE_UNKNOWN")
        rows_read = meta.get("rows_read")
        rows_written = meta.get("rows_written")
        if (
            type(rows_read) is not int
            or rows_read < 0
            or type(rows_written) is not int
            or rows_written < 0
        ):
            raise D1LedgerUnavailable("D1_LEDGER_USAGE_UNKNOWN")
        if any(not isinstance(row, dict) for row in rows):
            raise D1LedgerUnavailable("D1_LEDGER_RESPONSE_INVALID")
        return D1QueryResult(tuple(rows), rows_read, rows_written)


@dataclass(frozen=True, slots=True)
class D1LedgerLimits:
    max_evidence_age_ms: int = 60_000
    request_timeout_reserve_ms: int = 10_000
    max_rows_read_per_request: int = 25_000
    max_rows_written_per_request: int = 10
    max_reservations: int = 100_000


@dataclass(frozen=True, slots=True)
class SlotUsage:
    provider_requests: int
    class_a: int
    class_b: int
    new_bytes: int


class D1CloudBudgetLedger:
    """One atomic D1 reservation row per Cloud Paper slot.

    Reserving the slot envelope before provider/R2 access avoids a query/write for
    every object operation. Existing in-run guards still cap actual operations.
    An unsettled slot continues to consume its full envelope.
    """

    def __init__(
        self,
        client: D1QueryClient,
        *,
        policy: CloudBudgetPolicy = CloudBudgetPolicy(),
        limits: D1LedgerLimits = D1LedgerLimits(),
    ) -> None:
        self.client = client
        self.policy = policy
        self.limits = limits

    def reserve_slot(
        self,
        *,
        slot_id: str,
        run_id: str,
        now_ms: int,
        snapshot: R2UsageSnapshot,
    ) -> None:
        self._validate_inputs(slot_id, run_id, now_ms, snapshot)
        month_start_ms, day_start_ms = _period_starts(now_ms)
        rolling_start_ms = now_ms - 31 * 24 * 60 * 60 * 1000
        p = self.policy
        envelope = SlotUsage(
            provider_requests=p.provider_per_run,
            class_a=p.r2_class_a_per_run,
            class_b=p.r2_class_b_per_run,
            new_bytes=p.r2_new_bytes_per_run,
        )
        params: tuple[object, ...] = (
            snapshot.measured_through_ms,
            rolling_start_ms,
            now_ms,
            month_start_ms,
            day_start_ms,
            month_start_ms,
            day_start_ms,
            day_start_ms,
            run_id,
            day_start_ms,
            slot_id,
            run_id,
            now_ms,
            snapshot.measured_through_ms,
            envelope.provider_requests,
            envelope.class_a,
            envelope.class_b,
            envelope.new_bytes,
            self.limits.max_reservations,
            slot_id,
            snapshot.class_a_month + snapshot.pending_class_a_month,
            envelope.class_a,
            min(p.project_class_a_per_month, p.free_class_a_per_month),
            snapshot.class_a_day + snapshot.pending_class_a_day,
            envelope.class_a,
            p.r2_class_a_per_day,
            snapshot.class_a_31_days + snapshot.pending_class_a_31_days,
            envelope.class_a,
            p.r2_class_a_per_31_days,
            snapshot.class_b_month + snapshot.pending_class_b_month,
            envelope.class_b,
            min(p.project_class_b_per_month, p.free_class_b_per_month),
            snapshot.class_b_day + snapshot.pending_class_b_day,
            envelope.class_b,
            p.r2_class_b_per_day,
            snapshot.class_b_31_days + snapshot.pending_class_b_31_days,
            envelope.class_b,
            p.r2_class_b_per_31_days,
            snapshot.provider_requests_day + snapshot.pending_provider_requests_day,
            envelope.provider_requests,
            p.provider_per_day,
            envelope.provider_requests,
            p.provider_per_run,
            snapshot.new_bytes_day + snapshot.pending_new_bytes_day,
            envelope.new_bytes,
            p.r2_new_bytes_per_day,
            snapshot.storage_bytes + snapshot.pending_storage_bytes,
            envelope.new_bytes,
            p.r2_hard_stop_bytes,
        )
        result = self.client.query(RESERVE_SLOT_SQL, params)
        self._validate_query_usage(result)
        if not result.rows or result.rows[0].get("slot_id") != slot_id:
            raise BudgetBlocked("BLOCKED_BUDGET_RESERVATION_REJECTED")

    def settle_slot(
        self,
        *,
        slot_id: str,
        completed_at_ms: int,
        usage: SlotUsage,
    ) -> None:
        if not slot_id or len(slot_id) > 80:
            raise BudgetBlocked("BLOCKED_BUDGET_SLOT_ID_INVALID")
        if type(completed_at_ms) is not int or completed_at_ms < 0:
            raise BudgetBlocked("BLOCKED_BUDGET_CLOCK_INVALID")
        values = (
            usage.provider_requests,
            usage.class_a,
            usage.class_b,
            usage.new_bytes,
        )
        if any(type(value) is not int or value < 0 for value in values):
            raise BudgetBlocked("BLOCKED_BUDGET_USAGE_UNKNOWN")
        p = self.policy
        if (
            usage.provider_requests > p.provider_per_run
            or usage.class_a > p.r2_class_a_per_run
            or usage.class_b > p.r2_class_b_per_run
            or usage.new_bytes > p.r2_new_bytes_per_run
        ):
            raise BudgetBlocked("BLOCKED_BUDGET_SETTLEMENT_EXCEEDS_RESERVATION")
        result = self.client.query(
            SETTLE_SLOT_SQL,
            (
                usage.provider_requests,
                usage.class_a,
                usage.class_b,
                usage.new_bytes,
                slot_id,
                completed_at_ms,
                usage.provider_requests,
                usage.class_a,
                usage.class_b,
                usage.new_bytes,
            ),
        )
        self._validate_query_usage(result)
        if not result.rows or result.rows[0].get("slot_id") != slot_id:
            raise BudgetBlocked("BLOCKED_BUDGET_SETTLEMENT_REVIEW_REQUIRED")

    def _validate_query_usage(self, result: D1QueryResult) -> None:
        if (
            type(result.rows_read) is not int
            or type(result.rows_written) is not int
            or result.rows_read < 0
            or result.rows_written < 0
        ):
            raise D1LedgerUnavailable("D1_LEDGER_USAGE_UNKNOWN")
        if result.rows_read > self.limits.max_rows_read_per_request:
            raise D1LedgerUnavailable("D1_LEDGER_READ_HARD_STOP")
        if result.rows_written > self.limits.max_rows_written_per_request:
            raise D1LedgerUnavailable("D1_LEDGER_WRITE_HARD_STOP")

    def _validate_inputs(
        self,
        slot_id: str,
        run_id: str,
        now_ms: int,
        snapshot: R2UsageSnapshot,
    ) -> None:
        if not slot_id or len(slot_id) > 80 or not run_id or len(run_id) > 100:
            raise BudgetBlocked("BLOCKED_BUDGET_SLOT_ID_INVALID")
        if type(now_ms) is not int or now_ms < 0:
            raise BudgetBlocked("BLOCKED_BUDGET_CLOCK_INVALID")
        if not snapshot.account_wide or not snapshot.reservation_coverage_complete:
            raise BudgetBlocked("BLOCKED_BUDGET_EVIDENCE_INCOMPLETE")
        numeric = (
            snapshot.observed_at_ms,
            snapshot.measured_through_ms,
            snapshot.storage_bytes,
            snapshot.class_a_month,
            snapshot.class_b_month,
            snapshot.class_a_31_days,
            snapshot.class_b_31_days,
            snapshot.class_a_day,
            snapshot.class_b_day,
            snapshot.provider_requests_day,
            snapshot.new_bytes_day,
            snapshot.pending_storage_bytes,
            snapshot.pending_class_a_month,
            snapshot.pending_class_b_month,
            snapshot.pending_class_a_31_days,
            snapshot.pending_class_b_31_days,
            snapshot.pending_class_a_day,
            snapshot.pending_class_b_day,
            snapshot.pending_provider_requests_day,
            snapshot.pending_new_bytes_day,
        )
        if any(type(value) is not int or value < 0 for value in numeric):
            raise BudgetBlocked("BLOCKED_BUDGET_USAGE_UNKNOWN")
        age = now_ms - snapshot.observed_at_ms
        coverage_age = now_ms - snapshot.measured_through_ms
        if age < 0 or coverage_age < 0:
            raise BudgetBlocked("BLOCKED_BUDGET_EVIDENCE_FROM_FUTURE")
        minimum_age = (
            self.limits.max_evidence_age_ms
            - self.limits.request_timeout_reserve_ms
        )
        if minimum_age <= 0 or max(age, coverage_age) > minimum_age:
            raise BudgetBlocked("BLOCKED_BUDGET_EVIDENCE_STALE")


def _period_starts(now_ms: int) -> tuple[int, int]:
    now = datetime.fromtimestamp(now_ms / 1000, tz=UTC)
    month_start = datetime(now.year, now.month, 1, tzinfo=UTC)
    day_start = datetime(now.year, now.month, now.day, tzinfo=UTC)
    return int(month_start.timestamp() * 1000), int(day_start.timestamp() * 1000)
