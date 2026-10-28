"""Disabled prepaid assembly for a freshly admitted result-seal recovery."""
from __future__ import annotations

import os
from collections.abc import Callable, Mapping

from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import D1UsageGuard, D1UsageSnapshot
from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked, CloudBudgetGuard, R2UsageSnapshot
from crypto_autopilot.paper.cloud_loop_v0_1 import SLOT_MS, SLOT_OFFSET_MS
from crypto_autopilot.paper.prepaid_d1_client_v0_1 import (
    DatabaseSizeEvidence, PrepaidCloudflareD1QueryClient,
)
from crypto_autopilot.paper.prepaid_query_controller_v0_1 import PrepaidQueryMeter
from crypto_autopilot.paper.shared_cloud_paper_recovery_v0_1 import (
    WRITER, run_shared_cloud_paper_recovery,
)
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import SharedWriterReservation


def run_prepaid_cloud_paper_recovery(
    *, run_id: str, r2_snapshot: R2UsageSnapshot, d1_snapshot: D1UsageSnapshot,
    query_meter: PrepaidQueryMeter, clock_ms: Callable[[], int], slot_at_ms: int,
    database_evidence: DatabaseSizeEvidence, credentials: Mapping[str, str],
    repair_missing_result_seals: bool = False, execution_enabled: bool = False,
) -> dict[str, object]:
    """Use a fresh recovery ticket, never an old PAPER slot's workload envelope.

    Serialized ownership of the complete R2 namespace and finite production
    authority remain independent prerequisites and are not established here.
    """
    if type(execution_enabled) is not bool:
        raise BudgetBlocked("BLOCKED_RECOVERY_EXECUTION_FLAG")
    if not execution_enabled:
        return {"status": "SKIPPED_DISABLED", "external_access_performed": False}
    if type(slot_at_ms) is not int or slot_at_ms <= 0 or (
        slot_at_ms - SLOT_OFFSET_MS
    ) % SLOT_MS:
        raise BudgetBlocked("BLOCKED_PREPAID_SLOT_INVALID")
    if not isinstance(r2_snapshot, R2UsageSnapshot) or not isinstance(d1_snapshot, D1UsageSnapshot):
        raise BudgetBlocked("BLOCKED_RECOVERY_USAGE_EVIDENCE_REQUIRED")
    if not isinstance(database_evidence, DatabaseSizeEvidence):
        raise BudgetBlocked("BLOCKED_PREPAID_DATABASE_EVIDENCE_REQUIRED")
    r2_guard = CloudBudgetGuard(snapshot=r2_snapshot, clock_ms=clock_ms)
    d1_guard = D1UsageGuard(snapshot=d1_snapshot, clock_ms=clock_ms)
    slot_id = f"slot:{slot_at_ms}"
    PrepaidCloudflareD1QueryClient.validate_inputs(
        usage_guard=d1_guard, query_meter=query_meter, writer_id=WRITER, slot_id=slot_id,
    )
    if not isinstance(credentials, Mapping) or set(credentials) != {
        "account_id", "bucket", "access_key_id", "secret_access_key",
    } or any(not isinstance(value, str) or not value.strip() for value in credentials.values()):
        raise BudgetBlocked("BLOCKED_RECOVERY_CREDENTIAL_BINDING")
    if credentials["account_id"] != os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""):
        raise BudgetBlocked("BLOCKED_RECOVERY_ACCOUNT_MISMATCH")
    database_id = os.environ.get("CLOUDFLARE_D1_DATABASE_ID", "")
    database_evidence.validate(database_id=database_id, guard=d1_guard)
    client = PrepaidCloudflareD1QueryClient.from_environment(
        usage_guard=d1_guard, query_meter=query_meter, writer_id=WRITER,
        slot_id=slot_id, database_evidence=database_evidence,
    )
    def validate_binding() -> None:
        PrepaidCloudflareD1QueryClient.validate_inputs(
            usage_guard=d1_guard, query_meter=query_meter, writer_id=WRITER, slot_id=slot_id,
        )
        database_evidence.validate(database_id=database_id, guard=d1_guard)
        client.validate_runtime_binding(meter=query_meter, writer_id=WRITER, slot_id=slot_id)

    envelope = query_meter.report()["ticket_envelope_charged_in_full"]
    reservation = SharedWriterReservation(
        writer_id=WRITER, slot_id=slot_id, idempotency_key=slot_id,
        slot_at_ms=slot_at_ms, reserved_at_ms=clock_ms(), provider_requests=0,
        r2_class_a=8, r2_class_b=64, r2_new_bytes=16384,
        d1_queries=envelope["queries"], d1_rows_read=envelope["rows_read"],
        d1_rows_written=envelope["rows_written"],
        d1_storage_growth_bytes=envelope["storage_bytes"],
    )
    return run_shared_cloud_paper_recovery(
        run_id=run_id, reservation=reservation, guard=r2_guard,
        execute=client.query, query_meter=query_meter, validate_binding=validate_binding,
        credentials=credentials, repair_missing_result_seals=repair_missing_result_seals,
        execution_enabled=True,
    )
