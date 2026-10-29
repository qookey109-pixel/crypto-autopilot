"""Prepared V0.5 shared admission for the existing seal-guarded Paper runtime.

Synthetic assembly only; construction is not production execution authority.
"""
from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import replace

from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import D1UsageSnapshot
from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked, R2UsageSnapshot
from crypto_autopilot.paper.cloud_composition_v0_1 import CloudPaperNoTradeComposition
from crypto_autopilot.paper.cloud_runtime_v0_2 import PrepaidCloudPaperBudgetLedger
from crypto_autopilot.paper.cloud_runtime_v0_3 import build_runtime_composition as build_guarded_runtime
from crypto_autopilot.paper.prepaid_d1_client_v0_1 import DatabaseSizeEvidence
from crypto_autopilot.paper.prepaid_paper_d1_v0_2 import PaperPrepaidD1Client
from crypto_autopilot.paper.prepaid_query_controller_v0_1 import PrepaidQueryMeter
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import (
    SharedWriterReservation, reserve_shared_writer_envelope,
)


class PrepaidPaperV05Ledger(PrepaidCloudPaperBudgetLedger):
    """Central V0.5 admission before the existing Paper slot ledger."""

    def __init__(self, *, client: PaperPrepaidD1Client, meter: PrepaidQueryMeter,
                 writer_id: str, slot_at_ms: int, clock_ms: Callable[[], int]) -> None:
        if not isinstance(client, PaperPrepaidD1Client) or client._guard.clock_ms is not clock_ms:
            raise BudgetBlocked("BLOCKED_PAPER_V05_CLIENT_OR_CLOCK")
        super().__init__(client=client, meter=meter, writer_id=writer_id, slot_at_ms=slot_at_ms)
        self._clock_ms = clock_ms

    def reserve_slot(self, *, slot_id: str, run_id: str, now_ms: int,
                     snapshot: R2UsageSnapshot) -> None:
        self._legacy._validate_inputs(slot_id, run_id, now_ms, snapshot)
        if slot_id != self._slot or self._admitted:
            raise BudgetBlocked("BLOCKED_PREPAID_SLOT_ALREADY_USED_OR_MISMATCH")
        p = self._legacy.policy
        envelope = self._meter.report()["ticket_envelope_charged_in_full"]
        reservation = SharedWriterReservation(
            writer_id=self._writer, slot_id=self._shared_slot, idempotency_key=self._shared_slot,
            slot_at_ms=self._slot_at_ms, reserved_at_ms=now_ms, provider_requests=p.provider_per_run,
            r2_class_a=p.r2_class_a_per_run, r2_class_b=p.r2_class_b_per_run,
            r2_new_bytes=p.r2_new_bytes_per_run, d1_queries=envelope["queries"],
            d1_rows_read=envelope["rows_read"], d1_rows_written=envelope["rows_written"],
            d1_storage_growth_bytes=envelope["storage_bytes"],
        )
        result = reserve_shared_writer_envelope(
            execute=self.client.query, query_meter=self._meter, reservation=reservation,
            clock_ms=self._clock_ms, execution_enabled=True,
        )
        if result != "RESERVED":
            raise BudgetBlocked("BLOCKED_PREPAID_SHARED_SLOT_ALREADY_RESERVED")
        self._legacy.reserve_slot(slot_id=slot_id, run_id=run_id, now_ms=now_ms, snapshot=snapshot)
        self._admitted = True


def build_runtime_composition(
    *, r2_snapshot: R2UsageSnapshot, d1_snapshot: D1UsageSnapshot,
    strategy_registry: Mapping[str, object], allowed_base_assets: frozenset[str],
    clock_ms: Callable[[], int], query_meter: PrepaidQueryMeter, writer_id: str,
    slot_at_ms: int, database_evidence: DatabaseSizeEvidence,
    construction_enabled: bool = False,
) -> CloudPaperNoTradeComposition | None:
    """Build no-network prepared composition; True is not runtime authority."""
    if type(construction_enabled) is not bool:
        raise ValueError("construction_enabled must be boolean")
    if not construction_enabled:
        return None
    base = build_guarded_runtime(
        r2_snapshot=r2_snapshot, d1_snapshot=d1_snapshot,
        strategy_registry=strategy_registry, allowed_base_assets=allowed_base_assets,
        clock_ms=clock_ms, query_meter=query_meter, writer_id=writer_id,
        slot_at_ms=slot_at_ms, database_evidence=database_evidence, construction_enabled=True,
    )
    if not isinstance(base, CloudPaperNoTradeComposition) or not isinstance(
        base.reservation_ledger, PrepaidCloudPaperBudgetLedger,
    ):
        raise BudgetBlocked("BLOCKED_PREPAID_SHARED_LEDGER_REQUIRED")
    prior = base.reservation_ledger
    if (
        prior._meter is not query_meter or prior._writer != writer_id
        or prior._slot_at_ms != slot_at_ms or prior._admitted
        or base.d1_usage_guard.clock_ms is not clock_ms
    ):
        raise BudgetBlocked("BLOCKED_PREPAID_RUNTIME_BINDING_MISMATCH")
    client = PaperPrepaidD1Client(
        api_token=os.environ.get("CLOUDFLARE_D1_API_TOKEN", ""),
        account_id=os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""),
        database_id=os.environ.get("CLOUDFLARE_D1_DATABASE_ID", ""),
        usage_guard=base.d1_usage_guard, query_meter=query_meter, writer_id=writer_id,
        slot_id=f"slot:{slot_at_ms}", database_evidence=database_evidence,
        execution_enabled=True,
    )
    ledger = PrepaidPaperV05Ledger(
        client=client, meter=query_meter, writer_id=writer_id,
        slot_at_ms=slot_at_ms, clock_ms=clock_ms,
    )
    return replace(base, reservation_ledger=ledger)
