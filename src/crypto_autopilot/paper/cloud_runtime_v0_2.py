"""Disabled successor runtime with prepaid D1 and shared-writer admission.

Reuse the existing account, risk, coordinator and immutable R2 protocol.
Construction does no IO; activation still requires a separate merged authority.
"""
from __future__ import annotations

import os
from collections.abc import Callable, Mapping

from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import (
    D1CloudBudgetLedger,
    D1SlotReservation,
    D1UsageGuard,
    D1UsageSnapshot,
    SlotUsage,
)
from crypto_autopilot.paper.cloud_budget_v0_1 import (
    BudgetBlocked,
    CloudBudgetGuard,
    R2UsageSnapshot,
)
from crypto_autopilot.paper.cloud_candidate_adapter_v0_1 import validate_strategy_registry
from crypto_autopilot.paper.cloud_composition_v0_1 import CloudPaperNoTradeComposition
from crypto_autopilot.paper.cloud_loop_v0_1 import SLOT_MS, SLOT_OFFSET_MS
from crypto_autopilot.paper.cloud_pionex_client_v0_1 import CloudPaperPionexPublicClient
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.cloud_runtime_v0_1 import CLOUD_PAPER_PREFIX
from crypto_autopilot.paper.live_v0_1 import LivePaperPolicy
from crypto_autopilot.paper.prepaid_d1_client_v0_1 import (
    DatabaseSizeEvidence,
    PrepaidCloudflareD1QueryClient,
)
from crypto_autopilot.paper.prepaid_query_controller_v0_1 import PrepaidQueryMeter
from crypto_autopilot.paper.run_store_v0_1 import R2PaperRunStore
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import (
    SharedWriterReservation,
    reserve_shared_writer_envelope,
)


class PrepaidCloudPaperBudgetLedger:
    """Reserve central workload first, then reuse the legacy slot ledger.

    Central reservations are never refunded. Admission conservatively debits
    twice: V0.4 gate and the HTTP adapter both check the same finite ticket.
    Historical recovery needs a distinct fresh R2 workload reservation and
    remains blocked in this successor instead of spending an old envelope.
    """

    def __init__(
        self, *, client: PrepaidCloudflareD1QueryClient,
        meter: PrepaidQueryMeter, writer_id: str, slot_at_ms: int,
    ) -> None:
        if not isinstance(client, PrepaidCloudflareD1QueryClient) or not isinstance(
            meter, PrepaidQueryMeter,
        ):
            raise BudgetBlocked("BLOCKED_PREPAID_RUNTIME_ADAPTER_REQUIRED")
        if type(slot_at_ms) is not int or slot_at_ms <= 0 or (
            slot_at_ms - SLOT_OFFSET_MS
        ) % SLOT_MS:
            raise BudgetBlocked("BLOCKED_PREPAID_SLOT_INVALID")
        self.client = client
        self._meter = meter
        self._writer = writer_id
        self._slot_at_ms = slot_at_ms
        self._slot = str((slot_at_ms - SLOT_OFFSET_MS) // SLOT_MS)
        self._shared_slot = f"slot:{slot_at_ms}"
        client.validate_runtime_binding(
            meter=meter, writer_id=writer_id, slot_id=self._shared_slot,
        )
        self._legacy = D1CloudBudgetLedger(client)
        self._admitted = False

    def reserve_slot(
        self, *, slot_id: str, run_id: str, now_ms: int, snapshot: R2UsageSnapshot,
    ) -> None:
        self._legacy._validate_inputs(slot_id, run_id, now_ms, snapshot)
        if slot_id != self._slot or self._admitted:
            raise BudgetBlocked("BLOCKED_PREPAID_SLOT_ALREADY_USED_OR_MISMATCH")
        p = self._legacy.policy
        envelope = self._meter.report()["ticket_envelope_charged_in_full"]
        reservation = SharedWriterReservation(
            writer_id=self._writer, slot_id=self._shared_slot,
            idempotency_key=self._shared_slot, slot_at_ms=self._slot_at_ms,
            reserved_at_ms=now_ms, provider_requests=p.provider_per_run,
            r2_class_a=p.r2_class_a_per_run, r2_class_b=p.r2_class_b_per_run,
            r2_new_bytes=p.r2_new_bytes_per_run,
            d1_queries=envelope["queries"], d1_rows_read=envelope["rows_read"],
            d1_rows_written=envelope["rows_written"],
            d1_storage_growth_bytes=envelope["storage_bytes"],
        )
        result = reserve_shared_writer_envelope(
            execute=self.client.query, query_meter=self._meter, reservation=reservation,
        )
        if result != "RESERVED":
            raise BudgetBlocked("BLOCKED_PREPAID_SHARED_SLOT_ALREADY_RESERVED")
        self._legacy.reserve_slot(
            slot_id=slot_id, run_id=run_id, now_ms=now_ms, snapshot=snapshot,
        )
        self._admitted = True

    def _require_admission(self, slot_id: str) -> None:
        if not self._admitted or slot_id != self._slot:
            raise BudgetBlocked("BLOCKED_PREPAID_FRESH_WORKLOAD_ADMISSION_REQUIRED")
        self._meter.validate_binding(writer_id=self._writer, slot_id=self._shared_slot)

    def settle_slot(self, *, slot_id: str, completed_at_ms: int, usage: SlotUsage) -> None:
        self._require_admission(slot_id)
        self._legacy.settle_slot(slot_id=slot_id, completed_at_ms=completed_at_ms, usage=usage)

    def get_slot_reservation(self, *, slot_id: str) -> D1SlotReservation | None:
        self._require_admission(slot_id)
        return self._legacy.get_slot_reservation(slot_id=slot_id)

    def record_verified_result_recovery(
        self, *, slot_id: str, run_id: str, report_id: str, recovered_at_ms: int,
    ) -> None:
        self._require_admission(slot_id)
        self._legacy.record_verified_result_recovery(
            slot_id=slot_id, run_id=run_id, report_id=report_id,
            recovered_at_ms=recovered_at_ms,
        )


def build_runtime_composition(
    *, r2_snapshot: R2UsageSnapshot, d1_snapshot: D1UsageSnapshot,
    strategy_registry: Mapping[str, object], allowed_base_assets: frozenset[str],
    clock_ms: Callable[[], int], query_meter: PrepaidQueryMeter,
    writer_id: str, slot_at_ms: int, database_evidence: DatabaseSizeEvidence,
    construction_enabled: bool = False,
) -> CloudPaperNoTradeComposition | None:
    """Off before credentials; enabled assembly is IO-free, not execution authority."""
    if type(construction_enabled) is not bool:
        raise ValueError("construction_enabled must be boolean")
    if not construction_enabled:
        return None
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
    if type(slot_at_ms) is not int or slot_at_ms <= 0 or (
        slot_at_ms - SLOT_OFFSET_MS
    ) % SLOT_MS:
        raise BudgetBlocked("BLOCKED_PREPAID_SLOT_INVALID")
    shared_slot = f"slot:{slot_at_ms}"

    def check_freshness() -> None:
        if r2_guard.storage_capacity_state() == "HARD_STOP":
            raise BudgetBlocked("BLOCKED_BUDGET_STORAGE_HARD_STOP")
        PrepaidCloudflareD1QueryClient.validate_inputs(
            usage_guard=d1_guard, query_meter=query_meter,
            writer_id=writer_id, slot_id=shared_slot,
        )

    check_freshness()
    # Validate D1 evidence/credentials before constructing the R2 SDK.
    d1 = PrepaidCloudflareD1QueryClient.from_environment(
        usage_guard=d1_guard, query_meter=query_meter,
        writer_id=writer_id, slot_id=shared_slot, database_evidence=database_evidence,
    )
    r2 = BudgetedR2Store.from_credentials(
        account_id=os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""),
        bucket=os.environ.get("R2_BUCKET_NAME", ""),
        access_key_id=os.environ.get("R2_ACCESS_KEY_ID", ""),
        secret_access_key=os.environ.get("R2_SECRET_ACCESS_KEY", ""),
        budget_guard=r2_guard, freshness_check=check_freshness,
    )
    return CloudPaperNoTradeComposition(
        client=CloudPaperPionexPublicClient(before_send=check_freshness),
        store=R2PaperRunStore(r2, prefix=CLOUD_PAPER_PREFIX),
        strategy_registry=strategy_registry, allowed_base_assets=allowed_base_assets,
        paper_policy=LivePaperPolicy(), budget_guard=r2_guard,
        before_external=check_freshness, completion_clock_ms=clock_ms,
        reservation_ledger=PrepaidCloudPaperBudgetLedger(
            client=d1, meter=query_meter, writer_id=writer_id, slot_at_ms=slot_at_ms,
        ),
        d1_usage_guard=d1_guard,
    )
