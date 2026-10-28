"""Prepared bounded recovery for the Cloud Paper namespace only."""
from __future__ import annotations

from collections.abc import Callable, Mapping

from crypto_autopilot.paper.cloud_budget_v0_1 import CloudBudgetGuard
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.cloud_runtime_v0_1 import CLOUD_PAPER_PREFIX
from crypto_autopilot.paper.run_store_v0_1 import R2PaperRunStore
from crypto_autopilot.paper.shared_run_recovery_v0_1 import _SealOnlyStore, _run_scoped_run_recovery
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import (
    AdmissionQueryMeter, Query, SharedWriterReservation,
)

WRITER = "crypto-autopilot:cloud-paper-run-recovery-v0-1"


class _CloudPaperSealOnlyStore(_SealOnlyStore):
    def __init__(self, store: BudgetedR2Store, *, repair: bool):
        R2PaperRunStore.__init__(self, store, prefix=CLOUD_PAPER_PREFIX)
        self._repair = repair
        self._seal_attempts = 0
        self._listed_ids: set[tuple[str, str]] = set()


def run_shared_cloud_paper_recovery(
    *, run_id: str, reservation: SharedWriterReservation, guard: CloudBudgetGuard,
    execute: Query, query_meter: AdmissionQueryMeter, validate_binding: Callable[[], None],
    credentials: Mapping[str, str], repair_missing_result_seals: bool = False,
    execution_enabled: bool = False,
) -> dict[str, object]:
    """Bound the recovery writer and namespace; caller proves exclusive ownership."""
    return _run_scoped_run_recovery(
        writer_id=WRITER, recovery_store_type=_CloudPaperSealOnlyStore,
        run_id=run_id, reservation=reservation, guard=guard, execute=execute,
        query_meter=query_meter, validate_binding=validate_binding, credentials=credentials,
        repair_missing_result_seals=repair_missing_result_seals, execution_enabled=execution_enabled,
    )
