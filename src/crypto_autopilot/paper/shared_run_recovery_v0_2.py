"""Prepared V0.6 admission for scoped recovery; no production authority."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked, CloudBudgetGuard
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Policy, BudgetedR2Store
from crypto_autopilot.paper.run_recovery_v0_2 import reconcile_live_paper_run
from crypto_autopilot.paper.run_store_v0_1 import _clean_component
from crypto_autopilot.paper.shared_run_recovery_v0_1 import _SealOnlyStore
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import (
    AdmissionQueryMeter, Query, SharedWriterReservation,
)
from crypto_autopilot.paper.shared_writer_r2_budget_v0_3 import SharedWriterR2BudgetV06

def _run_scoped_run_recovery(
    *, writer_id: str, recovery_store_type: type[_SealOnlyStore],
    run_id: str, reservation: SharedWriterReservation, guard: CloudBudgetGuard,
    execute: Query, query_meter: AdmissionQueryMeter,
    validate_binding: Callable[[], None], credentials: Mapping[str, str],
    repair_missing_result_seals: bool = False, execution_enabled: bool = False,
    budget_version: str = "V0.6",
) -> dict[str, object]:
    """Caller must prove finite authority and serialized namespace ownership."""
    if type(execution_enabled) is not bool:
        raise BudgetBlocked("BLOCKED_RECOVERY_EXECUTION_FLAG")
    if not execution_enabled:
        return {"status": "SKIPPED_DISABLED", "external_access_performed": False}
    if type(repair_missing_result_seals) is not bool:
        raise BudgetBlocked("BLOCKED_RECOVERY_REPAIR_FLAG")
    if not isinstance(run_id, str) or _clean_component(run_id, "run id") != run_id:
        raise BudgetBlocked("BLOCKED_RECOVERY_RUN_ID")
    reservation.validate()
    if (
        reservation.writer_id != writer_id or reservation.provider_requests != 0
        or reservation.r2_class_a != 8 or reservation.r2_class_b != 64
        or reservation.r2_new_bytes != 16384
    ):
        raise BudgetBlocked("BLOCKED_RECOVERY_ENVELOPE_MISMATCH")
    if set(credentials) != {"account_id", "bucket", "access_key_id", "secret_access_key"} or any(
        not isinstance(value, str) or not value.strip() for value in credentials.values()
    ):
        raise BudgetBlocked("BLOCKED_RECOVERY_CREDENTIAL_BINDING")
    if guard.storage_capacity_state() == "HARD_STOP" or (
        guard.snapshot.storage_bytes + guard.snapshot.pending_storage_bytes + 16384
        >= guard.policy.r2_hard_stop_bytes
    ):
        raise BudgetBlocked("BLOCKED_BUDGET_STORAGE_HARD_STOP")
    if budget_version != "V0.6":
        raise BudgetBlocked("BLOCKED_RECOVERY_BUDGET_VERSION")
    budget = SharedWriterR2BudgetV06.admit(
        reservation=reservation, guard=guard, execute=execute,
        query_meter=query_meter, validate_binding=validate_binding, execution_enabled=True,
    )
    stage = "CONSTRUCT_STORE"
    try:
        raw_store = BudgetedR2Store.from_credentials(
            account_id=credentials["account_id"], bucket=credentials["bucket"],
            access_key_id=credentials["access_key_id"],
            secret_access_key=credentials["secret_access_key"],
            before_external=budget.reserve,
            policy=BudgetedR2Policy(maximum_list_pages=1, maximum_list_keys_per_page=4),
        )
        stage = "VERIFY_AND_REPAIR"
        report = reconcile_live_paper_run(
            run_id=run_id,
            store=recovery_store_type(raw_store, repair=repair_missing_result_seals),
            repair_missing_result_seals=repair_missing_result_seals,
        )
        return {
            "status": "REVIEW_REQUIRED" if report["state"] == "REVIEW_REQUIRED" else "AUDITED",
            "state": report["state"], "run_id": run_id,
            "step_count": report["step_count"], "claim_count": report["claim_count"],
            "result_seal_writes_performed": report["result_seal_writes_performed"],
            "repaired_request_ids": report["repaired_request_ids"],
            "issue_count": len(report["issues"]),
            "attempted_usage": budget.attempted_usage(),
            "provider_requests_performed": 0, "central_reservation_retained": True,
            "automatic_retry_allowed": False, "paper_activation_allowed": False,
        }
    except Exception:
        return {
            "status": "REVIEW_REQUIRED", "state": "REVIEW_REQUIRED", "stage": stage,
            "reason_code": "RECOVERY_EVIDENCE_OR_OPERATION_FAILED", "run_id": run_id,
            "result_seal_writes_performed": None,
            "attempted_usage": budget.attempted_usage(),
            "provider_requests_performed": 0, "central_reservation_retained": True,
            "automatic_retry_allowed": False, "paper_activation_allowed": False,
        }
