"""Prepared monotonic-clock wrapper for shared writer budget V0.5.

This successor retains the existing SQL and budget rules. It is disabled by
default and does not establish a trusted clock, D1 metering, account coverage,
or production execution authority.
"""
from collections.abc import Callable
from typing import Literal

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import (
    AdmissionQueryMeter,
    Query,
    SharedWriterReservation,
    reserve_shared_writer_envelope as reserve_v0_5,
)


def reserve_shared_writer_envelope(
    *, execute: Query, reservation: SharedWriterReservation,
    clock_ms: Callable[[], int], query_meter: AdmissionQueryMeter | None = None,
    execution_enabled: bool = False,
) -> Literal["RESERVED", "EXISTING_RESERVATION"]:
    if execution_enabled is not True:
        raise BudgetBlocked("BLOCKED_SHARED_WRITER_EXECUTION_DISABLED")
    if not callable(clock_ms):
        raise BudgetBlocked("BLOCKED_SHARED_WRITER_CLOCK_REQUIRED")
    previous: int | None = None

    def nondecreasing_clock() -> int:
        nonlocal previous
        value = clock_ms()
        if type(value) is not int or (previous is not None and value < previous):
            raise BudgetBlocked("BLOCKED_SHARED_WRITER_CLOCK_ROLLBACK")
        previous = value
        return value

    return reserve_v0_5(
        execute=execute, reservation=reservation, clock_ms=nondecreasing_clock,
        query_meter=query_meter, execution_enabled=True,
    )
