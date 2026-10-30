"""Prepared binding from a verified GitHub ticket claim to one PAPER run.

No production workflow, runtime or external access is enabled here. Trusted
transport and protection behavior must be established by a merged authority.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import D1UsageSnapshot
from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked, R2UsageSnapshot
from crypto_autopilot.paper.cloud_runtime_v0_4 import build_runtime_composition
from crypto_autopilot.paper.prepaid_d1_client_v0_1 import DatabaseSizeEvidence
from crypto_autopilot.paper.prepaid_query_controller_v0_1 import (
    CONFIG_PATH, AllocationEvidence, GitHubTransport, PrepaidQueryMeter,
    claim_prepaid_query_meter,
)

_CLAIMED = object()


@dataclass(frozen=True, slots=True, init=False)
class RunBoundMeter:
    """Ticket whose run identity is captured by the claim operation."""

    meter: PrepaidQueryMeter
    run_id: int
    writer_id: str
    slot_id: str

    def __init__(
        self, *, meter: PrepaidQueryMeter, run_id: int, writer_id: str,
        slot_id: str, _claim_proof: object = None,
    ) -> None:
        if _claim_proof is not _CLAIMED:
            raise BudgetBlocked("BLOCKED_RUN_BOUND_CLAIM_REQUIRED")
        object.__setattr__(self, "meter", meter)
        object.__setattr__(self, "run_id", run_id)
        object.__setattr__(self, "writer_id", writer_id)
        object.__setattr__(self, "slot_id", slot_id)


def claim_bound_meter(
    *, authority_document: dict[str, object], writer_id: str, slot_id: str,
    run_id: int, transport: GitHubTransport, evidence: AllocationEvidence,
    clock_ms: Callable[[], int], authority_path: str = CONFIG_PATH,
    execution_enabled: bool = False,
) -> RunBoundMeter:
    """Return a bound claim only after the existing verification and readback."""
    if type(execution_enabled) is not bool or not execution_enabled:
        raise BudgetBlocked("BLOCKED_RUN_BOUND_CLAIM_DISABLED")
    if type(run_id) is not int or run_id <= 0:
        raise BudgetBlocked("BLOCKED_RUN_BOUND_ID_INVALID")
    meter = claim_prepaid_query_meter(
        authority_document=authority_document, writer_id=writer_id,
        slot_id=slot_id, run_id=run_id, transport=transport, evidence=evidence,
        clock_ms=clock_ms, authority_path=authority_path,
    )
    return RunBoundMeter(
        meter=meter, run_id=run_id, writer_id=writer_id, slot_id=slot_id,
        _claim_proof=_CLAIMED,
    )


class _RunBoundRuntime:
    def __init__(self, *, bound: RunBoundMeter, inner: object) -> None:
        self._bound = bound
        self._inner = inner

    def run_slot(self, **kwargs):
        if kwargs.get("activation_enabled") is True:
            if kwargs.get("run_id") != str(self._bound.run_id):
                raise BudgetBlocked("BLOCKED_RUN_BOUND_ID_MISMATCH")
            self._bound.meter.validate_binding(
                writer_id=self._bound.writer_id, slot_id=self._bound.slot_id,
            )
        return self._inner.run_slot(**kwargs)


def build_bound_runtime(
    *, bound: RunBoundMeter, r2_snapshot: R2UsageSnapshot,
    d1_snapshot: D1UsageSnapshot, strategy_registry: Mapping[str, object],
    allowed_base_assets: frozenset[str], clock_ms: Callable[[], int],
    writer_id: str, slot_at_ms: int, database_evidence: DatabaseSizeEvidence,
    construction_enabled: bool = False,
) -> _RunBoundRuntime | None:
    """Bind the prepared runtime; enabling construction is not authority."""
    if type(construction_enabled) is not bool:
        raise ValueError("construction_enabled must be boolean")
    if not construction_enabled:
        return None
    if (
        type(bound) is not RunBoundMeter or bound.writer_id != writer_id
        or bound.slot_id != f"slot:{slot_at_ms}"
        or bound.meter._clock_ms is not clock_ms
    ):
        raise BudgetBlocked("BLOCKED_RUN_BOUND_BINDING_MISMATCH")
    bound.meter.validate_binding(writer_id=writer_id, slot_id=bound.slot_id)
    inner = build_runtime_composition(
        r2_snapshot=r2_snapshot, d1_snapshot=d1_snapshot,
        strategy_registry=strategy_registry, allowed_base_assets=allowed_base_assets,
        clock_ms=clock_ms, query_meter=bound.meter, writer_id=writer_id,
        slot_at_ms=slot_at_ms, database_evidence=database_evidence,
        construction_enabled=True,
    )
    if inner is None:
        raise BudgetBlocked("BLOCKED_RUN_BOUND_RUNTIME_UNAVAILABLE")
    return _RunBoundRuntime(bound=bound, inner=inner)
