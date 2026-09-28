"""Fail-closed reservation checks for the inactive Cloud Paper Loop.

This module does not fetch usage data or create a reservation ledger. Callers must
supply a fresh account-wide snapshot plus verified reservations not yet reflected
in it. This primitive is not production activation evidence.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


class BudgetBlocked(RuntimeError):
    """Stable fail-closed reason without provider or credential details."""


@dataclass(frozen=True, slots=True)
class R2UsageSnapshot:
    account_wide: bool
    reservation_coverage_complete: bool
    observed_at_ms: int
    measured_through_ms: int
    storage_bytes: int
    class_a_month: int
    class_b_month: int
    class_a_31_days: int
    class_b_31_days: int
    class_a_day: int
    class_b_day: int
    provider_requests_day: int
    new_bytes_day: int
    pending_storage_bytes: int = 0
    pending_class_a_month: int = 0
    pending_class_b_month: int = 0
    pending_class_a_31_days: int = 0
    pending_class_b_31_days: int = 0
    pending_class_a_day: int = 0
    pending_class_b_day: int = 0
    pending_provider_requests_day: int = 0
    pending_new_bytes_day: int = 0


@dataclass(frozen=True, slots=True)
class CloudBudgetUsage:
    """Provider and R2 operation reservations recorded for one completed slot."""

    provider_requests: int
    class_a_requests: int
    class_b_requests: int
    new_bytes: int


@dataclass(frozen=True, slots=True)
class CloudBudgetPolicy:
    max_evidence_age_ms: int = 60_000
    provider_per_run: int = 18
    provider_per_day: int = 1_728
    r2_class_a_per_run: int = 128
    r2_class_b_per_run: int = 128
    r2_new_bytes_per_run: int = 2_097_152
    r2_class_a_per_day: int = 12_288
    r2_class_b_per_day: int = 12_288
    r2_new_bytes_per_day: int = 201_326_592
    r2_class_a_per_31_days: int = 380_928
    r2_class_b_per_31_days: int = 380_928
    free_class_a_per_month: int = 1_000_000
    free_class_b_per_month: int = 10_000_000
    project_class_a_per_month: int = 750_000
    project_class_b_per_month: int = 7_500_000
    r2_hard_stop_bytes: int = 8_000_000_000
    r2_object_max_bytes: int = 262_144


class CloudBudgetGuard:
    """Reserve one bounded operation before its provider or R2 call."""

    def __init__(
        self,
        *,
        snapshot: R2UsageSnapshot,
        clock_ms: Callable[[], int],
        policy: CloudBudgetPolicy = CloudBudgetPolicy(),
    ) -> None:
        self.snapshot = snapshot
        if not callable(clock_ms):
            raise ValueError("a live budget-evidence clock is required")
        self.clock_ms = clock_ms
        self.policy = policy
        self._provider_run = 0
        self._class_a_run = 0
        self._class_b_run = 0
        self._new_bytes_run = 0
        self._new_bytes_day = 0

    def attempted_usage(self) -> CloudBudgetUsage:
        """Return operation counts reserved immediately before external calls.

        The composition settles these counters only after a complete run returns.
        On any exception it leaves the full slot envelope reserved for review.
        """
        return CloudBudgetUsage(
            provider_requests=self._provider_run,
            class_a_requests=self._class_a_run,
            class_b_requests=self._class_b_run,
            new_bytes=self._new_bytes_run,
        )

    def _validate_evidence(self) -> None:
        s = self.snapshot
        if not s.account_wide or not s.reservation_coverage_complete:
            raise BudgetBlocked("BLOCKED_BUDGET_EVIDENCE_INCOMPLETE")
        current_time_ms = self.clock_ms()
        if type(current_time_ms) is not int or current_time_ms < 0:
            raise BudgetBlocked("BLOCKED_BUDGET_CLOCK_INVALID")
        numeric = (
            s.observed_at_ms, s.measured_through_ms, s.storage_bytes,
            s.class_a_month, s.class_b_month, s.class_a_31_days,
            s.class_b_31_days, s.class_a_day, s.class_b_day,
            s.provider_requests_day, s.new_bytes_day, s.pending_storage_bytes,
            s.pending_class_a_month, s.pending_class_b_month,
            s.pending_class_a_31_days, s.pending_class_b_31_days,
            s.pending_class_a_day, s.pending_class_b_day,
            s.pending_provider_requests_day, s.pending_new_bytes_day,
        )
        if any(type(value) is not int or value < 0 for value in numeric):
            raise BudgetBlocked("BLOCKED_BUDGET_USAGE_UNKNOWN")
        age = current_time_ms - s.observed_at_ms
        coverage_age = current_time_ms - s.measured_through_ms
        if age < 0 or coverage_age < 0:
            raise BudgetBlocked("BLOCKED_BUDGET_EVIDENCE_FROM_FUTURE")
        if max(age, coverage_age) > self.policy.max_evidence_age_ms:
            raise BudgetBlocked("BLOCKED_BUDGET_EVIDENCE_STALE")

    def reserve_provider_request(self) -> None:
        self._validate_evidence()
        s, p = self.snapshot, self.policy
        used = s.provider_requests_day + s.pending_provider_requests_day
        if self._provider_run >= p.provider_per_run:
            raise BudgetBlocked("BLOCKED_BUDGET_PROVIDER_RUN_LIMIT")
        if used + self._provider_run >= p.provider_per_day:
            raise BudgetBlocked("BLOCKED_BUDGET_PROVIDER_DAILY_LIMIT")
        self._provider_run += 1

    def reserve(self, operation: str, new_bytes: int = 0) -> None:
        """Callback-compatible reservation entry point for provider/R2 adapters."""
        if operation == "PIONEX_PUBLIC":
            if new_bytes != 0:
                raise BudgetBlocked("BLOCKED_BUDGET_PROVIDER_BYTES_INVALID")
            self.reserve_provider_request()
        elif operation == "R2_CLASS_A":
            self.reserve_r2_class_a(new_bytes=new_bytes)
        elif operation == "R2_CLASS_B":
            if new_bytes != 0:
                raise BudgetBlocked("BLOCKED_BUDGET_CLASS_B_BYTES_INVALID")
            self.reserve_r2_class_b()
        else:
            raise BudgetBlocked("BLOCKED_BUDGET_OPERATION_UNKNOWN")

    def reserve_r2_class_a(self, *, new_bytes: int = 0) -> None:
        self._reserve_r2(operation="A", new_bytes=new_bytes)

    def reserve_r2_class_b(self) -> None:
        self._reserve_r2(operation="B", new_bytes=0)

    def _reserve_r2(self, *, operation: str, new_bytes: int) -> None:
        self._validate_evidence()
        if type(new_bytes) is not int or new_bytes < 0:
            raise BudgetBlocked("BLOCKED_BUDGET_BYTES_UNKNOWN")
        if new_bytes > self.policy.r2_object_max_bytes:
            raise BudgetBlocked("BLOCKED_BUDGET_OBJECT_LIMIT")
        s, p = self.snapshot, self.policy
        if self._new_bytes_run + new_bytes > p.r2_new_bytes_per_run:
            raise BudgetBlocked("BLOCKED_BUDGET_RUN_BYTES_LIMIT")
        if s.new_bytes_day + s.pending_new_bytes_day + self._new_bytes_day + new_bytes > p.r2_new_bytes_per_day:
            raise BudgetBlocked("BLOCKED_BUDGET_DAILY_BYTES_LIMIT")
        if s.storage_bytes + s.pending_storage_bytes + self._new_bytes_run + new_bytes > p.r2_hard_stop_bytes:
            raise BudgetBlocked("BLOCKED_BUDGET_STORAGE_HARD_STOP")

        if operation == "A":
            month = s.class_a_month + s.pending_class_a_month
            rolling = s.class_a_31_days + s.pending_class_a_31_days
            daily = s.class_a_day + s.pending_class_a_day
            if self._class_a_run >= p.r2_class_a_per_run:
                raise BudgetBlocked("BLOCKED_BUDGET_CLASS_A_RUN_LIMIT")
            if daily + self._class_a_run >= p.r2_class_a_per_day:
                raise BudgetBlocked("BLOCKED_BUDGET_CLASS_A_DAILY_LIMIT")
            if month + self._class_a_run >= min(p.project_class_a_per_month, p.free_class_a_per_month):
                raise BudgetBlocked("BLOCKED_BUDGET_CLASS_A_MONTHLY_LIMIT")
            if rolling + self._class_a_run >= p.r2_class_a_per_31_days:
                raise BudgetBlocked("BLOCKED_BUDGET_CLASS_A_31_DAY_LIMIT")
            self._class_a_run += 1
        else:
            month = s.class_b_month + s.pending_class_b_month
            rolling = s.class_b_31_days + s.pending_class_b_31_days
            daily = s.class_b_day + s.pending_class_b_day
            if self._class_b_run >= p.r2_class_b_per_run:
                raise BudgetBlocked("BLOCKED_BUDGET_CLASS_B_RUN_LIMIT")
            if daily + self._class_b_run >= p.r2_class_b_per_day:
                raise BudgetBlocked("BLOCKED_BUDGET_CLASS_B_DAILY_LIMIT")
            if month + self._class_b_run >= min(p.project_class_b_per_month, p.free_class_b_per_month):
                raise BudgetBlocked("BLOCKED_BUDGET_CLASS_B_MONTHLY_LIMIT")
            if rolling + self._class_b_run >= p.r2_class_b_per_31_days:
                raise BudgetBlocked("BLOCKED_BUDGET_CLASS_B_31_DAY_LIMIT")
            self._class_b_run += 1
        self._new_bytes_run += new_bytes
        self._new_bytes_day += new_bytes
