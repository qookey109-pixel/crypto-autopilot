from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from crypto_autopilot.paper.run_store_v0_1 import (
    PaperRunObjectAlreadyExistsError,
    PaperRunStoreReceipt,
)


class LivePaperRunClaimConflictError(ValueError):
    """Raised when another request already owns the deterministic run slot."""


class PaperRunClaimStore(Protocol):
    def get_json(
        self,
        kind: str,
        object_id: str,
    ) -> dict[str, object] | None: ...

    def put_json_if_absent(
        self,
        kind: str,
        object_id: str,
        payload: Mapping[str, object],
    ) -> PaperRunStoreReceipt: ...


@dataclass(frozen=True, slots=True)
class LivePaperRunClaimPolicy:
    coordinator_integration_authorized: bool = True
    atomic_create_if_absent_required: bool = True
    claim_expiry_authorized: bool = False
    claim_takeover_authorized: bool = False
    automatic_retry_after_conflict_authorized: bool = False
    provider_access_authorized: bool = False
    live_market_data_access_authorized: bool = False
    account_state_mutation_authorized: bool = False
    automatic_schedule_authorized: bool = False
    private_exchange_api_authorized: bool = False
    holdout_access_authorized: bool = False
    real_money_order_authorized: bool = False
    live_real_trading_authorized: bool = False

    def __post_init__(self) -> None:
        values = (
            self.coordinator_integration_authorized,
            self.atomic_create_if_absent_required,
            self.claim_expiry_authorized,
            self.claim_takeover_authorized,
            self.automatic_retry_after_conflict_authorized,
            self.provider_access_authorized,
            self.live_market_data_access_authorized,
            self.account_state_mutation_authorized,
            self.automatic_schedule_authorized,
            self.private_exchange_api_authorized,
            self.holdout_access_authorized,
            self.real_money_order_authorized,
            self.live_real_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in values):
            raise ValueError("live paper run claim policy flags must be booleans")
        if not self.coordinator_integration_authorized:
            raise ValueError("run claim V0.1 requires explicit coordinator integration")
        if not self.atomic_create_if_absent_required:
            raise ValueError("run claim V0.1 requires atomic create-if-absent")
        if any(values[2:]):
            raise ValueError(
                "run claim V0.1 cannot expire, transfer, auto-retry, access providers, "
                "mutate account state, schedule itself or grant trading authority"
            )


def _canonicalize(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(item)
            for key, item in sorted(value.items())
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    return value


def _sha256(value: object) -> str:
    encoded = json.dumps(
        _canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def live_paper_run_slot_id(
    *,
    run_id: str,
    sequence: int,
    previous_step_id: str | None,
    previous_state_id: str,
) -> str:
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("run claim run_id is required")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise ValueError("run claim sequence must be positive integer")
    if sequence == 1:
        if previous_step_id is not None:
            raise ValueError("first run slot cannot have previous_step_id")
    elif not isinstance(previous_step_id, str) or not previous_step_id:
        raise ValueError("continued run slot requires previous_step_id")
    if not isinstance(previous_state_id, str) or not previous_state_id:
        raise ValueError("run claim previous_state_id is required")
    payload = {
        "schema": "qookey-live-paper-run-slot-id-v0.1",
        "run_id": run_id,
        "sequence": sequence,
        "previous_step_id": previous_step_id,
        "previous_state_id": previous_state_id,
    }
    return f"live-paper-run-slot-v0-1-{_sha256(payload)}"


def build_live_paper_run_claim(
    *,
    run_id: str,
    sequence: int,
    previous_step_id: str | None,
    previous_state_id: str,
    request_id: str,
    tick_time_ms: int,
    candidate_specs_sha256: str,
) -> dict[str, object]:
    slot_id = live_paper_run_slot_id(
        run_id=run_id,
        sequence=sequence,
        previous_step_id=previous_step_id,
        previous_state_id=previous_state_id,
    )
    if not isinstance(request_id, str) or not request_id:
        raise ValueError("run claim request_id is required")
    if (
        not isinstance(tick_time_ms, int)
        or isinstance(tick_time_ms, bool)
        or tick_time_ms < 0
    ):
        raise ValueError("run claim tick_time_ms is invalid")
    if (
        not isinstance(candidate_specs_sha256, str)
        or len(candidate_specs_sha256) != 64
        or any(c not in "0123456789abcdef" for c in candidate_specs_sha256)
    ):
        raise ValueError("run claim candidate_specs_sha256 is invalid")
    return {
        "schema": "qookey-live-paper-run-slot-claim-v0.1",
        "state": "CLAIMED",
        "slot_id": slot_id,
        "run_id": run_id,
        "sequence": sequence,
        "previous_step_id": previous_step_id,
        "previous_state_id": previous_state_id,
        "request_id": request_id,
        "tick_time_ms": tick_time_ms,
        "candidate_specs_sha256": candidate_specs_sha256,
        "authority": {
            "coordinator_gate_only": True,
            "provider_access_authorized": False,
            "live_market_data_access_authorized": False,
            "account_state_mutation_authorized": False,
            "claim_expiry_authorized": False,
            "claim_takeover_authorized": False,
            "automatic_retry_after_conflict_authorized": False,
            "automatic_schedule_authorized": False,
            "private_exchange_api_authorized": False,
            "holdout_access_authorized": False,
            "real_money_order_authorized": False,
            "live_real_trading_authorized": False,
        },
    }


def verify_live_paper_run_claim(payload: Mapping[str, object]) -> str:
    if payload.get("schema") != "qookey-live-paper-run-slot-claim-v0.1":
        raise ValueError("unsupported live paper run claim schema")
    if payload.get("state") != "CLAIMED":
        raise ValueError("live paper run claim state is invalid")
    run_id = payload.get("run_id")
    sequence = payload.get("sequence")
    previous_step_id = payload.get("previous_step_id")
    previous_state_id = payload.get("previous_state_id")
    request_id = payload.get("request_id")
    tick_time_ms = payload.get("tick_time_ms")
    candidate_specs_sha256 = payload.get("candidate_specs_sha256")
    if not isinstance(run_id, str):
        raise ValueError("live paper run claim run_id is required")
    if not isinstance(sequence, int) or isinstance(sequence, bool):
        raise ValueError("live paper run claim sequence is invalid")
    if previous_step_id is not None and not isinstance(previous_step_id, str):
        raise ValueError("live paper run claim previous_step_id is invalid")
    if not isinstance(previous_state_id, str):
        raise ValueError("live paper run claim previous_state_id is required")
    expected_slot = live_paper_run_slot_id(
        run_id=run_id,
        sequence=sequence,
        previous_step_id=previous_step_id,
        previous_state_id=previous_state_id,
    )
    if payload.get("slot_id") != expected_slot:
        raise ValueError("live paper run claim slot id mismatch")
    if not isinstance(request_id, str) or not request_id:
        raise ValueError("live paper run claim request_id is required")
    if (
        not isinstance(tick_time_ms, int)
        or isinstance(tick_time_ms, bool)
        or tick_time_ms < 0
    ):
        raise ValueError("live paper run claim tick time is invalid")
    if (
        not isinstance(candidate_specs_sha256, str)
        or len(candidate_specs_sha256) != 64
        or any(c not in "0123456789abcdef" for c in candidate_specs_sha256)
    ):
        raise ValueError("live paper run claim candidate hash is invalid")
    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("live paper run claim authority is required")
    if authority.get("coordinator_gate_only") is not True:
        raise ValueError("live paper run claim must be coordinator-gate-only")
    for key in (
        "provider_access_authorized",
        "live_market_data_access_authorized",
        "account_state_mutation_authorized",
        "claim_expiry_authorized",
        "claim_takeover_authorized",
        "automatic_retry_after_conflict_authorized",
        "automatic_schedule_authorized",
        "private_exchange_api_authorized",
        "holdout_access_authorized",
        "real_money_order_authorized",
        "live_real_trading_authorized",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"live paper run claim authority must remain closed: {key}")
    return expected_slot


def acquire_live_paper_run_claim(
    *,
    store: PaperRunClaimStore,
    run_id: str,
    sequence: int,
    previous_step_id: str | None,
    previous_state_id: str,
    request_id: str,
    tick_time_ms: int,
    candidate_specs_sha256: str,
    policy: LivePaperRunClaimPolicy = LivePaperRunClaimPolicy(),
) -> tuple[dict[str, object], PaperRunStoreReceipt]:
    claim = build_live_paper_run_claim(
        run_id=run_id,
        sequence=sequence,
        previous_step_id=previous_step_id,
        previous_state_id=previous_state_id,
        request_id=request_id,
        tick_time_ms=tick_time_ms,
        candidate_specs_sha256=candidate_specs_sha256,
    )
    slot_id = verify_live_paper_run_claim(claim)
    try:
        receipt = store.put_json_if_absent("live-run-claim", slot_id, claim)
    except PaperRunObjectAlreadyExistsError as exc:
        existing = store.get_json("live-run-claim", slot_id)
        if existing is None:
            raise LivePaperRunClaimConflictError(
                f"live paper run slot claim conflict without readable claim: {slot_id}"
            ) from exc
        verify_live_paper_run_claim(existing)
        owner = existing.get("request_id")
        relation = "same_request" if owner == request_id else "different_request"
        raise LivePaperRunClaimConflictError(
            f"live paper run slot already claimed ({relation}): {slot_id}"
        ) from exc
    if receipt.replayed:
        raise ValueError("atomic run claim receipt cannot be replayed")
    return claim, receipt


def live_paper_run_claim_policy_from_config(
    payload: Mapping[str, object],
) -> LivePaperRunClaimPolicy:
    if payload.get("schema") != "qookey-live-paper-run-slot-claim-v0.1":
        raise ValueError("unsupported live paper run claim config")
    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("live paper run claim policy object is required")
    keys = (
        "coordinator_integration_authorized",
        "atomic_create_if_absent_required",
        "claim_expiry_authorized",
        "claim_takeover_authorized",
        "automatic_retry_after_conflict_authorized",
        "provider_access_authorized",
        "live_market_data_access_authorized",
        "account_state_mutation_authorized",
        "automatic_schedule_authorized",
        "private_exchange_api_authorized",
        "holdout_access_authorized",
        "real_money_order_authorized",
        "live_real_trading_authorized",
    )
    values: dict[str, bool] = {}
    for key in keys:
        value = policy.get(key)
        if not isinstance(value, bool):
            raise ValueError(f"policy.{key} must be a JSON boolean")
        values[key] = value
    return LivePaperRunClaimPolicy(**values)


__all__ = [
    "LivePaperRunClaimConflictError",
    "LivePaperRunClaimPolicy",
    "acquire_live_paper_run_claim",
    "build_live_paper_run_claim",
    "live_paper_run_claim_policy_from_config",
    "live_paper_run_slot_id",
    "verify_live_paper_run_claim",
]
