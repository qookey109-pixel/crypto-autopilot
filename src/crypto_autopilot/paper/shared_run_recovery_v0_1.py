"""Disabled shared-admitted recovery; no workflow cutover or production access."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked, CloudBudgetGuard
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Policy, BudgetedR2Store
from crypto_autopilot.paper.run_recovery_v0_2 import reconcile_live_paper_run
from crypto_autopilot.paper.run_store_v0_1 import (
    R2PaperRunStore, _canonical_bytes, _clean_component,
)
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import (
    AdmissionQueryMeter, Query, SharedWriterReservation,
)
from crypto_autopilot.paper.shared_writer_r2_budget_v0_1 import SharedWriterR2Budget

WRITER = "crypto-autopilot:live-paper-run-recovery-v0-1"
_PREFIX = "paper-run-store/v0.1"
_KINDS = frozenset({
    "live-run", "live-state", "live-tick", "live-run-step",
    "live-run-result", "live-run-claim",
})
_LIST_KINDS = _KINDS - {"live-run", "live-state"}


class _SealOnlyStore(R2PaperRunStore):
    """Bound reads/listings and permit only immutable result-seal creation."""

    def __init__(self, store: BudgetedR2Store, *, repair: bool):
        super().__init__(store, prefix=_PREFIX)
        self._repair = repair
        self._seal_attempts = 0
        self._listed_ids: set[tuple[str, str]] = set()

    def _key(self, kind: str, object_id: str) -> str:
        if kind not in _KINDS:
            raise ValueError("recovery object kind is outside scope")
        return super()._key(kind, object_id)

    def get_json(self, kind: str, object_id: str) -> dict[str, object] | None:
        key = self._key(kind, object_id)
        try:
            response = self.store.client.get_object(Bucket=self.store.bucket, Key=key)
        except Exception as exc:
            details = getattr(exc, "response", {}) or {}
            if str(details.get("Error", {}).get("Code", "")) in {
                "NoSuchKey", "NotFound", "404",
            } or details.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404:
                if (kind, object_id) in self._listed_ids:
                    raise ValueError("listed recovery object disappeared") from None
                return None
            raise
        stream = response["Body"]
        try:
            body = stream.read(262_145)
        finally:
            stream.close()
        if not isinstance(body, bytes) or len(body) > 262_144:
            raise ValueError("recovery object exceeds bounded read")
        expected = response.get("Metadata", {}).get("sha256")
        if expected and hashlib.sha256(body).hexdigest() != expected:
            raise ValueError("recovery object digest mismatch")
        value = json.loads(body)
        if not isinstance(value, dict):
            raise ValueError("recovery object is not a mapping")
        return value

    def list_json_ids(self, kind: str) -> tuple[str, ...]:
        if kind not in _LIST_KINDS:
            raise ValueError("recovery listing kind is outside scope")
        prefix = f"{self.prefix}/{kind}/"
        page = self.store.client.list_objects_v2(
            Bucket=self.store.bucket, Prefix=prefix, MaxKeys=4)
        rows = page.get("Contents", [])
        if page.get("IsTruncated") is not False or not isinstance(rows, list) or len(rows) > 4:
            raise ValueError("recovery inventory is incomplete or oversized")
        identities = []
        for row in rows:
            key = row.get("Key") if isinstance(row, dict) else None
            if not isinstance(key, str) or not key.startswith(prefix) or not key.endswith(".json"):
                raise ValueError("recovery inventory key is invalid")
            identity = key[len(prefix):-5]
            if _clean_component(identity, "object id") != identity or identity in identities:
                raise ValueError("recovery inventory identity is invalid")
            identities.append(identity)
        self._listed_ids.update((kind, identity) for identity in identities)
        return tuple(sorted(identities))

    def put_json(self, kind: str, object_id: str, payload: Mapping[str, object]):
        body = _canonical_bytes(payload)
        if not self._repair or kind != "live-run-result" or self._seal_attempts >= 4 or len(body) > 4096:
            raise ValueError("recovery result-seal write is outside scope")
        self._seal_attempts += 1
        receipt = super().put_json_if_absent(kind, object_id, payload)
        persisted = self.get_json(kind, object_id)
        if persisted is None or _canonical_bytes(persisted) != body:
            raise ValueError("recovery seal readback mismatch")
        return receipt


def run_shared_run_recovery(
    *, run_id: str, reservation: SharedWriterReservation, guard: CloudBudgetGuard,
    execute: Query, query_meter: AdmissionQueryMeter,
    validate_binding: Callable[[], None], credentials: Mapping[str, str],
    repair_missing_result_seals: bool = False, execution_enabled: bool = False,
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
        reservation.writer_id != WRITER or reservation.provider_requests != 0
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
    budget = SharedWriterR2Budget.admit(
        reservation=reservation, guard=guard, execute=execute,
        query_meter=query_meter, validate_binding=validate_binding,
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
            store=_SealOnlyStore(raw_store, repair=repair_missing_result_seals),
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
