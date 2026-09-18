from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from crypto_autopilot.paper.run_store_v0_1 import (
    PaperRunObjectAlreadyExistsError,
    PaperRunStoreReceipt,
    run_store_receipt_evidence,
)


class PaperRunConditionalWriteStore(Protocol):
    def put_json_if_absent(
        self,
        kind: str,
        object_id: str,
        payload: Mapping[str, object],
    ) -> PaperRunStoreReceipt: ...


@dataclass(frozen=True, slots=True)
class PaperRunConditionalWritePolicy:
    atomic_create_if_absent_required: bool = True
    overwrite_existing_authorized: bool = False
    coordinator_integration_authorized: bool = False
    automatic_retry_authorized: bool = False
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
            self.atomic_create_if_absent_required,
            self.overwrite_existing_authorized,
            self.coordinator_integration_authorized,
            self.automatic_retry_authorized,
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
            raise ValueError("conditional-write policy flags must be booleans")
        if not self.atomic_create_if_absent_required:
            raise ValueError("conditional-write V0.1 requires atomic create-if-absent")
        if any(values[1:]):
            raise ValueError(
                "conditional-write V0.1 is a storage primitive only and cannot "
                "grant overwrite, execution, retry, provider or trading authority"
            )


def create_paper_run_object_if_absent(
    *,
    store: PaperRunConditionalWriteStore,
    kind: str,
    object_id: str,
    payload: Mapping[str, object],
    policy: PaperRunConditionalWritePolicy = PaperRunConditionalWritePolicy(),
) -> dict[str, object]:
    """Attempt one atomic create-only paper-run write.

    An existing key is always a conflict. V0.1 deliberately does not interpret
    that conflict as a safe retry, lease takeover or coordinator continuation.
    """

    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("conditional-write kind is required")
    if not isinstance(object_id, str) or not object_id.strip():
        raise ValueError("conditional-write object_id is required")
    if not isinstance(payload, Mapping):
        raise ValueError("conditional-write payload must be a mapping")

    receipt = store.put_json_if_absent(kind, object_id, payload)
    evidence = run_store_receipt_evidence(receipt)
    return {
        "schema": "qookey-paper-run-conditional-write-report-v0.1",
        "state": "CREATED",
        "kind": kind,
        "object_id": object_id,
        "storage_receipt": evidence,
        "provider_requests_performed": 0,
        "live_market_data_requests_performed": 0,
        "account_state_mutations_performed": 0,
        "authority": {
            "storage_primitive_only": True,
            "overwrite_existing_authorized": policy.overwrite_existing_authorized,
            "coordinator_integration_authorized": (
                policy.coordinator_integration_authorized
            ),
            "automatic_retry_authorized": policy.automatic_retry_authorized,
            "provider_access_authorized": policy.provider_access_authorized,
            "live_market_data_access_authorized": (
                policy.live_market_data_access_authorized
            ),
            "account_state_mutation_authorized": (
                policy.account_state_mutation_authorized
            ),
            "automatic_schedule_authorized": policy.automatic_schedule_authorized,
            "private_exchange_api_authorized": (
                policy.private_exchange_api_authorized
            ),
            "holdout_access_authorized": policy.holdout_access_authorized,
            "real_money_order_authorized": policy.real_money_order_authorized,
            "live_real_trading_authorized": policy.live_real_trading_authorized,
        },
    }


def paper_run_conditional_write_policy_from_config(
    payload: Mapping[str, object],
) -> PaperRunConditionalWritePolicy:
    if payload.get("schema") != "qookey-paper-run-conditional-write-v0.1":
        raise ValueError("unsupported paper-run conditional-write config")
    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("paper-run conditional-write policy object is required")

    keys = (
        "atomic_create_if_absent_required",
        "overwrite_existing_authorized",
        "coordinator_integration_authorized",
        "automatic_retry_authorized",
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
    return PaperRunConditionalWritePolicy(**values)


__all__ = [
    "PaperRunConditionalWritePolicy",
    "PaperRunObjectAlreadyExistsError",
    "create_paper_run_object_if_absent",
    "paper_run_conditional_write_policy_from_config",
]
