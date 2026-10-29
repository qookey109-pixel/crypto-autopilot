"""Default-disabled prepaid runtime with metered result-seal verification."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace

from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import D1UsageSnapshot
from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked, R2UsageSnapshot
from crypto_autopilot.paper.cloud_composition_v0_1 import CloudPaperNoTradeComposition
from crypto_autopilot.paper.cloud_run_store_v0_1 import CloudPaperRunStore
from crypto_autopilot.paper.run_store_v0_1 import R2PaperRunStore
from crypto_autopilot.paper.cloud_runtime_v0_2 import (
    PrepaidCloudPaperBudgetLedger,
    build_runtime_composition as build_prepaid_runtime,
)
from crypto_autopilot.paper.cloud_seal_guarded_composition_v0_1 import (
    build_seal_guarded_composition,
)
from crypto_autopilot.paper.prepaid_d1_client_v0_1 import DatabaseSizeEvidence
from crypto_autopilot.paper.prepaid_query_controller_v0_1 import PrepaidQueryMeter
from crypto_autopilot.paper.validated_tape_client_v0_1 import ValidatedTapeClient


def build_runtime_composition(
    *, r2_snapshot: R2UsageSnapshot, d1_snapshot: D1UsageSnapshot,
    strategy_registry: Mapping[str, object], allowed_base_assets: frozenset[str],
    clock_ms: Callable[[], int], query_meter: PrepaidQueryMeter,
    writer_id: str, slot_at_ms: int, database_evidence: DatabaseSizeEvidence,
    construction_enabled: bool = False,
) -> CloudPaperNoTradeComposition | None:
    """Reuse prepaid admission; construction alone never activates execution."""
    if type(construction_enabled) is not bool:
        raise ValueError("construction_enabled must be boolean")
    if not construction_enabled:
        return None
    base = build_prepaid_runtime(
        r2_snapshot=r2_snapshot, d1_snapshot=d1_snapshot,
        strategy_registry=strategy_registry, allowed_base_assets=allowed_base_assets,
        clock_ms=clock_ms, query_meter=query_meter, writer_id=writer_id,
        slot_at_ms=slot_at_ms, database_evidence=database_evidence,
        construction_enabled=True,
    )
    if not isinstance(base, CloudPaperNoTradeComposition) or not isinstance(
        base.reservation_ledger, PrepaidCloudPaperBudgetLedger,
    ):
        raise BudgetBlocked("BLOCKED_PREPAID_SHARED_LEDGER_REQUIRED")
    ledger = base.reservation_ledger
    if (
        ledger._meter is not query_meter or ledger._writer != writer_id
        or ledger._slot_at_ms != slot_at_ms or ledger._admitted
    ):
        raise BudgetBlocked("BLOCKED_PREPAID_RUNTIME_BINDING_MISMATCH")
    ledger.client.validate_runtime_binding(
        meter=query_meter, writer_id=writer_id, slot_id=f"slot:{slot_at_ms}",
    )
    if not isinstance(base.store, R2PaperRunStore):
        raise BudgetBlocked("BLOCKED_CLOUD_PAPER_RUN_STORE_REQUIRED")
    strict_store = CloudPaperRunStore(base.store.store, prefix=base.store.prefix)
    base = replace(base, client=ValidatedTapeClient(base.client), store=strict_store)
    return build_seal_guarded_composition(base, enabled=True)
