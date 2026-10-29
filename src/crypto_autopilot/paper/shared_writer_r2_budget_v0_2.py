"""Prepared V0.5 shared admission bridge for metered R2 operations."""
from __future__ import annotations

import threading
from collections.abc import Callable

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked, CloudBudgetGuard
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import (
    AdmissionQueryMeter, Query, SharedWriterReservation, reserve_shared_writer_envelope,
)
from crypto_autopilot.paper.shared_writer_r2_budget_v0_1 import SharedWriterR2Budget


class SharedWriterR2BudgetV05(SharedWriterR2Budget):
    """Prepared bridge; explicit enable does not grant production authority."""

    @classmethod
    def admit(
        cls, *, reservation: SharedWriterReservation, guard: CloudBudgetGuard,
        execute: Query, query_meter: AdmissionQueryMeter,
        validate_binding: Callable[[], None], execution_enabled: bool = False,
    ) -> SharedWriterR2BudgetV05:
        if execution_enabled is not True:
            raise BudgetBlocked("BLOCKED_SHARED_R2_EXECUTION_DISABLED")
        reservation.validate()
        if not isinstance(guard, CloudBudgetGuard) or not callable(validate_binding):
            raise BudgetBlocked("BLOCKED_SHARED_R2_BINDING_INVALID")
        validate_binding()
        if guard.storage_capacity_state() == "HARD_STOP":
            raise BudgetBlocked("BLOCKED_BUDGET_STORAGE_HARD_STOP")
        result = reserve_shared_writer_envelope(
            execute=execute, reservation=reservation, query_meter=query_meter,
            clock_ms=guard.clock_ms, execution_enabled=True,
        )
        if result != "RESERVED":
            raise BudgetBlocked("BLOCKED_SHARED_R2_EXISTING_RESERVATION")
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
