"""Prepared V0.5 shared admission for the existing seal-guarded Paper runtime.

Synthetic assembly only; construction is not production execution authority.
"""
from __future__ import annotations

import os
from collections.abc import Callable, Mapping

from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import D1UsageGuard
from crypto_autopilot.paper.cloud_budget_v0_1 import CloudBudgetGuard
from crypto_autopilot.paper.cloud_candidate_adapter_v0_1 import validate_strategy_registry
from crypto_autopilot.paper.cloud_pionex_client_v0_1 import CloudPaperPionexPublicClient
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.cloud_runtime_v0_1 import CLOUD_PAPER_PREFIX
from crypto_autopilot.paper.cloud_run_store_v0_1 import CloudPaperRunStore
from crypto_autopilot.paper.cloud_seal_guarded_composition_v0_1 import build_seal_guarded_composition
from crypto_autopilot.paper.live_v0_1 import LivePaperPolicy
from crypto_autopilot.paper.validated_tape_client_v0_1 import ValidatedTapeClient
from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import D1UsageSnapshot
from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked, R2UsageSnapshot
from crypto_autopilot.paper.cloud_composition_v0_1 import CloudPaperNoTradeComposition
from crypto_autopilot.paper.cloud_runtime_v0_2 import PrepaidCloudPaperBudgetLedger
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
    if not isinstance(query_meter, PrepaidQueryMeter) or query_meter._clock_ms is not clock_ms:
        raise BudgetBlocked("BLOCKED_PREPAID_RUNTIME_CLOCK_MISMATCH")
    if not isinstance(r2_snapshot, R2UsageSnapshot) or not isinstance(d1_snapshot, D1UsageSnapshot):
        raise ValueError("typed R2 and D1 evidence is required")
    if (
        not isinstance(allowed_base_assets, frozenset) or not allowed_base_assets
        or any(not isinstance(asset, str) or not asset for asset in allowed_base_assets)
    ):
        raise ValueError("a governed base-asset allowlist is required")
    validate_strategy_registry(strategy_registry)
    r2_guard = CloudBudgetGuard(snapshot=r2_snapshot, clock_ms=clock_ms)
    d1_guard = D1UsageGuard(snapshot=d1_snapshot, clock_ms=clock_ms)
    shared_slot = f"slot:{slot_at_ms}"

    def check_freshness() -> None:
        if r2_guard.storage_capacity_state() == "HARD_STOP":
            raise BudgetBlocked("BLOCKED_BUDGET_STORAGE_HARD_STOP")
        PaperPrepaidD1Client.validate_inputs(
            usage_guard=d1_guard, query_meter=query_meter, writer_id=writer_id, slot_id=shared_slot,
        )

    check_freshness()
    client = PaperPrepaidD1Client(
        api_token=os.environ.get("CLOUDFLARE_D1_API_TOKEN", ""),
        account_id=os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""),
        database_id=os.environ.get("CLOUDFLARE_D1_DATABASE_ID", ""),
        usage_guard=d1_guard, query_meter=query_meter, writer_id=writer_id,
        slot_id=shared_slot, database_evidence=database_evidence, execution_enabled=True,
    )
    ledger = PrepaidPaperV05Ledger(
        client=client, meter=query_meter, writer_id=writer_id,
        slot_at_ms=slot_at_ms, clock_ms=clock_ms,
    )

    def check_admitted() -> None:
        check_freshness()
        ledger._require_admission(ledger._slot)

    r2 = BudgetedR2Store.from_credentials(
        account_id=os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""),
        bucket=os.environ.get("R2_BUCKET_NAME", ""),
        access_key_id=os.environ.get("R2_ACCESS_KEY_ID", ""),
        secret_access_key=os.environ.get("R2_SECRET_ACCESS_KEY", ""),
        budget_guard=r2_guard, freshness_check=check_admitted,
    )
    base = CloudPaperNoTradeComposition(
        client=ValidatedTapeClient(CloudPaperPionexPublicClient(before_send=check_admitted)),
        store=CloudPaperRunStore(r2, prefix=CLOUD_PAPER_PREFIX),
        strategy_registry=strategy_registry, allowed_base_assets=allowed_base_assets,
        paper_policy=LivePaperPolicy(), budget_guard=r2_guard,
        before_external=check_freshness, completion_clock_ms=clock_ms,
        reservation_ledger=ledger, d1_usage_guard=d1_guard,
    )
    return build_seal_guarded_composition(base, enabled=True)
