"""Shared-admitted per-operation R2 budget; no client, workflow or authority.

Call admit before constructing a BudgetedR2Store with before_external=reserve.
This bridge does not establish production writer coverage, evidence freshness
sources, calibrated D1 costs, or external execution authority.
"""
from __future__ import annotations

import threading
from collections.abc import Callable

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked, CloudBudgetGuard
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import (
    AdmissionQueryMeter, Query, SharedWriterReservation, reserve_shared_writer_envelope,
)


class SharedWriterR2Budget:
    """Central reservation followed by bounded, nonrefundable local attempts."""

    def __init__(self) -> None:
        raise TypeError("use SharedWriterR2Budget.admit")

    @classmethod
    def admit(
        cls, *, reservation: SharedWriterReservation, guard: CloudBudgetGuard,
        execute: Query, query_meter: AdmissionQueryMeter,
        validate_binding: Callable[[], None],
    ) -> SharedWriterR2Budget:
        reservation.validate()
        if not isinstance(guard, CloudBudgetGuard) or not callable(validate_binding):
            raise BudgetBlocked("BLOCKED_SHARED_R2_BINDING_INVALID")
        validate_binding()
        if guard.storage_capacity_state() == "HARD_STOP":
            raise BudgetBlocked("BLOCKED_BUDGET_STORAGE_HARD_STOP")
        now = guard.clock_ms()
        if now < reservation.reserved_at_ms or now - reservation.slot_at_ms > 600_000:
            raise BudgetBlocked("BLOCKED_SHARED_R2_RESERVATION_STALE")
        result = reserve_shared_writer_envelope(
            execute=execute, reservation=reservation, query_meter=query_meter,
        )
        if result != "RESERVED":
            raise BudgetBlocked("BLOCKED_SHARED_R2_EXISTING_RESERVATION")
        # A failed post-admission check leaves the full central envelope consumed.
        validate_binding()
        if guard.storage_capacity_state() == "HARD_STOP":
            raise BudgetBlocked("BLOCKED_BUDGET_STORAGE_HARD_STOP")
        instance = cls.__new__(cls)
        instance._reservation = reservation
        instance._guard = guard
        instance._binding = validate_binding
        instance._lock = threading.Lock()
        instance._class_a = 0
        instance._class_b = 0
        instance._bytes = 0
        return instance

    def reserve(self, operation: str, new_bytes: int = 0) -> None:
        """Use only as the budgeted store's callback, before the actual S3 call."""
        with self._lock:
            self._binding()
            now = self._guard.clock_ms()
            if (
                type(now) is not int or now < self._reservation.reserved_at_ms
                or now - self._reservation.slot_at_ms > 600_000
            ):
                raise BudgetBlocked("BLOCKED_SHARED_R2_RESERVATION_STALE")
            if type(new_bytes) is not int or new_bytes < 0:
                raise BudgetBlocked("BLOCKED_SHARED_R2_BYTES_INVALID")
            a, b = (1, 0) if operation == "R2_CLASS_A" else (0, 1)
            if operation not in {"R2_CLASS_A", "R2_CLASS_B"}:
                raise BudgetBlocked("BLOCKED_SHARED_R2_OPERATION_INVALID")
            if operation == "R2_CLASS_B" and new_bytes:
                raise BudgetBlocked("BLOCKED_SHARED_R2_BYTES_INVALID")
            r = self._reservation
            if (
                self._class_a + a > r.r2_class_a
                or self._class_b + b > r.r2_class_b
                or self._bytes + new_bytes > r.r2_new_bytes
            ):
                raise BudgetBlocked("BLOCKED_SHARED_R2_ENVELOPE_EXHAUSTED")
            self._guard.reserve(operation, new_bytes)
            self._class_a += a
            self._class_b += b
            self._bytes += new_bytes

    def attempted_usage(self) -> dict[str, int]:
        with self._lock:
            return {"r2_class_a": self._class_a, "r2_class_b": self._class_b,
                    "r2_new_bytes": self._bytes}
