"""Prepared V0.5 admission for the manual Live-Paper coordinator.

Disabled by default; not a production entrypoint or an identity boundary.
"""
from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence

from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import D1UsageGuard, D1UsageSnapshot
from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked, CloudBudgetGuard, R2UsageSnapshot
from crypto_autopilot.paper.cloud_loop_v0_1 import SLOT_MS, SLOT_OFFSET_MS
from crypto_autopilot.paper.cloud_pionex_client_v0_1 import CloudPaperPionexPublicClient
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.live_v0_1 import PionexLivePaperFeed, verify_live_paper_state
from crypto_autopilot.paper.prepaid_d1_client_v0_1 import DatabaseSizeEvidence
from crypto_autopilot.paper.prepaid_paper_d1_v0_2 import PaperPrepaidD1Client
from crypto_autopilot.paper.prepaid_query_controller_v0_1 import PrepaidQueryMeter
from crypto_autopilot.paper.run_claim_v0_1 import LivePaperRunClaimPolicy
from crypto_autopilot.paper.run_coordinator_v0_1 import _run_id, _validate_run_name
from crypto_autopilot.paper.run_coordinator_v0_3 import (
    LivePaperRunCoordinatorPolicy, coordinate_live_paper_run_step,
)
from crypto_autopilot.paper.run_recovery_v0_2 import reconcile_live_paper_run
from crypto_autopilot.paper.run_store_v0_1 import R2PaperRunStore
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import SharedWriterReservation
from crypto_autopilot.paper.shared_writer_r2_budget_v0_2 import SharedWriterR2BudgetV05

WRITER = "crypto-autopilot:live-paper-run-coordinator-v0-1"


def run_prepaid_live_coordinator(
    *, run_name: str, tick_time_ms: int, candidate_specs: Sequence[object],
    initial_state: Mapping[str, object] | None, previous_step_id: str | None,
    r2_snapshot: R2UsageSnapshot, d1_snapshot: D1UsageSnapshot,
    query_meter: PrepaidQueryMeter, clock_ms: Callable[[], int], slot_at_ms: int,
    database_evidence: DatabaseSizeEvidence, credentials: Mapping[str, str],
    execution_enabled: bool = False,
) -> dict[str, object]:
    """Reserve before any R2/provider operation; caller proves exclusive ownership."""
    if type(execution_enabled) is not bool:
        raise BudgetBlocked("BLOCKED_COORDINATOR_EXECUTION_FLAG")
    if not execution_enabled:
        return {"status": "SKIPPED_DISABLED", "external_access_performed": False}
    if type(slot_at_ms) is not int or slot_at_ms <= 0 or (slot_at_ms - SLOT_OFFSET_MS) % SLOT_MS:
        raise BudgetBlocked("BLOCKED_PREPAID_SLOT_INVALID")
    if type(tick_time_ms) is not int or tick_time_ms < slot_at_ms:
        raise BudgetBlocked("BLOCKED_COORDINATOR_TICK_INVALID")
    now = clock_ms()
    if type(now) is not int or not 0 <= now - tick_time_ms <= 60_000:
        raise BudgetBlocked("BLOCKED_COORDINATOR_TICK_STALE")
    if (initial_state is None) == (previous_step_id is None):
        raise BudgetBlocked("BLOCKED_COORDINATOR_LINEAGE_INPUT")
    if not isinstance(candidate_specs, (list, tuple)) or len(candidate_specs) > 5:
        raise BudgetBlocked("BLOCKED_COORDINATOR_CANDIDATES")
    name = _validate_run_name(run_name)
    if initial_state is not None:
        if not isinstance(initial_state, Mapping):
            raise BudgetBlocked("BLOCKED_COORDINATOR_INITIAL_STATE")
        initial_id = verify_live_paper_state(initial_state)
        run_id = _run_id(name, initial_id)
    else:
        if not isinstance(previous_step_id, str) or not previous_step_id:
            raise BudgetBlocked("BLOCKED_COORDINATOR_PREVIOUS_STEP")
        run_id = None
    if not isinstance(r2_snapshot, R2UsageSnapshot) or not isinstance(d1_snapshot, D1UsageSnapshot):
        raise BudgetBlocked("BLOCKED_COORDINATOR_USAGE_REQUIRED")
    if not isinstance(database_evidence, DatabaseSizeEvidence):
        raise BudgetBlocked("BLOCKED_COORDINATOR_DATABASE_EVIDENCE")
    if not isinstance(credentials, Mapping) or set(credentials) != {
        "account_id", "bucket", "access_key_id", "secret_access_key",
    } or any(not isinstance(v, str) or not v.strip() for v in credentials.values()):
        raise BudgetBlocked("BLOCKED_COORDINATOR_CREDENTIAL_BINDING")
    credentials = dict(credentials)
    r2_guard = CloudBudgetGuard(snapshot=r2_snapshot, clock_ms=clock_ms)
    d1_guard = D1UsageGuard(snapshot=d1_snapshot, clock_ms=clock_ms)
    slot_id = f"slot:{slot_at_ms}"
    database_id = os.environ.get("CLOUDFLARE_D1_DATABASE_ID", "")

    def validate_binding() -> None:
        if credentials["account_id"] != os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""):
            raise BudgetBlocked("BLOCKED_COORDINATOR_ACCOUNT_MISMATCH")
        if credentials["bucket"] != os.environ.get("R2_BUCKET_NAME", ""):
            raise BudgetBlocked("BLOCKED_COORDINATOR_BUCKET_MISMATCH")
        if database_id != os.environ.get("CLOUDFLARE_D1_DATABASE_ID", ""):
            raise BudgetBlocked("BLOCKED_COORDINATOR_DATABASE_MISMATCH")
        PaperPrepaidD1Client.validate_inputs(
            usage_guard=d1_guard, query_meter=query_meter, writer_id=WRITER, slot_id=slot_id,
        )
        database_evidence.validate(database_id=database_id, guard=d1_guard)
        current = clock_ms()
        if type(current) is not int or current < tick_time_ms or current - tick_time_ms > 60_000:
            raise BudgetBlocked("BLOCKED_COORDINATOR_TICK_STALE")

    validate_binding()
    client = PaperPrepaidD1Client(
        api_token=os.environ.get("CLOUDFLARE_D1_API_TOKEN", ""),
        account_id=credentials["account_id"], database_id=database_id,
        usage_guard=d1_guard, query_meter=query_meter, writer_id=WRITER, slot_id=slot_id,
        database_evidence=database_evidence, execution_enabled=True,
    )
    p = r2_guard.policy
    if r2_snapshot.storage_bytes + r2_snapshot.pending_storage_bytes + p.r2_new_bytes_per_run >= p.r2_hard_stop_bytes:
        raise BudgetBlocked("BLOCKED_BUDGET_STORAGE_HARD_STOP")
    ticket = query_meter.report()["ticket_envelope_charged_in_full"]
    reservation = SharedWriterReservation(
        writer_id=WRITER, slot_id=slot_id, idempotency_key=slot_id,
        slot_at_ms=slot_at_ms, reserved_at_ms=now, provider_requests=p.provider_per_run,
        r2_class_a=p.r2_class_a_per_run, r2_class_b=p.r2_class_b_per_run,
        r2_new_bytes=p.r2_new_bytes_per_run, d1_queries=ticket["queries"],
        d1_rows_read=ticket["rows_read"], d1_rows_written=ticket["rows_written"],
        d1_storage_growth_bytes=ticket["storage_bytes"],
    )
    budget = SharedWriterR2BudgetV05.admit(
        reservation=reservation, guard=r2_guard, execute=client.query,
        query_meter=query_meter, validate_binding=validate_binding, execution_enabled=True,
    )
    provider_count = 0

    def before_provider() -> None:
        nonlocal provider_count
        validate_binding()
        if r2_guard.storage_capacity_state() == "HARD_STOP":
            raise BudgetBlocked("BLOCKED_BUDGET_STORAGE_HARD_STOP")
        if provider_count >= reservation.provider_requests:
            raise BudgetBlocked("BLOCKED_COORDINATOR_PROVIDER_LIMIT")
        r2_guard.reserve_provider_request()
        provider_count += 1

    stage = "CONSTRUCT_STORE"
    try:
        r2 = BudgetedR2Store.from_credentials(
            account_id=credentials["account_id"], bucket=credentials["bucket"],
            access_key_id=credentials["access_key_id"],
            secret_access_key=credentials["secret_access_key"], before_external=budget.reserve,
        )
        store = R2PaperRunStore(r2)
        stage = "VERIFY_LINEAGE"
        previous = None
        if previous_step_id is not None:
            previous = store.get_json("live-run-step", previous_step_id)
            if previous is None or previous.get("run_name") != name:
                raise ValueError("previous step unavailable")
            run_id = previous.get("run_id")
            if not isinstance(run_id, str) or not run_id:
                raise ValueError("previous run identity unavailable")
            audit = reconcile_live_paper_run(run_id=run_id, store=store)
            if audit["state"] != "RUN_CONSISTENT" or audit["terminal_step_id"] != previous_step_id:
                raise ValueError("run evidence requires review")
        elif store.get_json("live-run", run_id) is not None:
            raise ValueError("existing run requires explicit verified continuation")
        stage = "COORDINATE"
        feed = PionexLivePaperFeed(client=CloudPaperPionexPublicClient(before_send=before_provider))
        report = coordinate_live_paper_run_step(
            run_name=name, tick_time_ms=tick_time_ms, candidate_specs=candidate_specs,
            feed=feed, store=store, initial_state=initial_state, previous_step=previous,
            policy=LivePaperRunCoordinatorPolicy(run_slot_claim_required=True, compact_tick_reference=True),
            claim_policy=LivePaperRunClaimPolicy(),
        )
        stage = "FINAL_VALIDATION"
        validate_binding()
        if r2_guard.storage_capacity_state() == "HARD_STOP":
            raise BudgetBlocked("BLOCKED_BUDGET_STORAGE_HARD_STOP")
        return {
            "status": "COMMITTED", "run_id": report["run_id"], "step_id": report["step_id"],
            "state": report["state"], "provider_requests_performed": provider_count,
            "provider_requests_attempted": provider_count,
            "attempted_usage": budget.attempted_usage(), "central_reservation_retained": True,
            "automatic_retry_allowed": False, "paper_activation_allowed": False,
        }
    except Exception:
        return {
            "status": "REVIEW_REQUIRED", "stage": stage,
            "reason_code": "COORDINATOR_EVIDENCE_OR_OPERATION_FAILED",
            "run_id": run_id, "provider_requests_performed": 0 if provider_count == 0 else None,
            "provider_requests_attempted": provider_count,
            "attempted_usage": budget.attempted_usage(), "central_reservation_retained": True,
            "automatic_retry_allowed": False, "paper_activation_allowed": False,
        }
