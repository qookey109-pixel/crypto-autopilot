from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from crypto_autopilot.paper.lifecycle_v0_1 import (
    PaperLifecyclePolicy,
    build_paper_lifecycle_plan,
    lifecycle_evidence,
    lifecycle_input_from_dict,
    simulate_paper_lifecycle,
)
from crypto_autopilot.paper.session_v0_1 import (
    paper_submission_session_report_id_from_mapping,
)


@dataclass(frozen=True, slots=True)
class PaperLifecycleBatchPolicy:
    maximum_intents: int = 5
    require_exact_session_id_confirmation: bool = True
    require_complete_session_basket: bool = True
    explicit_lifecycle_simulation_authorized: bool = True
    automatic_lifecycle_simulation_authorized: bool = False
    scheduled_lifecycle_simulation_authorized: bool = False
    provider_access_authorized: bool = False
    persistent_state_write_authorized: bool = False
    live_trading_authorized: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.maximum_intents, int) or isinstance(
            self.maximum_intents, bool
        ):
            raise ValueError("maximum_intents must be an integer")
        if self.maximum_intents < 1:
            raise ValueError("maximum_intents must be positive")
        flags = (
            self.require_exact_session_id_confirmation,
            self.require_complete_session_basket,
            self.explicit_lifecycle_simulation_authorized,
            self.automatic_lifecycle_simulation_authorized,
            self.scheduled_lifecycle_simulation_authorized,
            self.provider_access_authorized,
            self.persistent_state_write_authorized,
            self.live_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in flags):
            raise ValueError("paper lifecycle batch policy flags must be booleans")
        if not self.require_exact_session_id_confirmation:
            raise ValueError("exact session-id confirmation is required in V0.1")
        if not self.require_complete_session_basket:
            raise ValueError("complete session basket is required in V0.1")
        if not self.explicit_lifecycle_simulation_authorized:
            raise ValueError("explicit lifecycle simulation must be authorized in V0.1")
        if (
            self.automatic_lifecycle_simulation_authorized
            or self.scheduled_lifecycle_simulation_authorized
            or self.provider_access_authorized
            or self.persistent_state_write_authorized
            or self.live_trading_authorized
        ):
            raise ValueError("Paper Lifecycle Batch V0.1 authority exceeds its scope")


@dataclass(frozen=True, slots=True)
class _BatchItem:
    proposal_id: str
    paper_execution_evidence: Mapping[str, object]
    target_price: float
    bars: tuple[Mapping[str, object], ...]


def _sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(
        dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _strict_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{label} must be finite")
    return converted


def _validate_session_authority(payload: Mapping[str, object]) -> None:
    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("paper submission session authority object is required")
    if authority.get("explicit_in_memory_paper_submission_only") is not True:
        raise ValueError("paper submission session must remain explicit paper-only")
    for key in (
        "provider_requests_performed",
        "r2_accessed",
        "holdout_accessed",
        "automatic_submission_authorized",
        "scheduled_submission_authorized",
        "persistent_broker_state_authorized",
        "lifecycle_simulation_authorized",
        "short_paper_execution_authorized",
        "formal_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"paper submission session authority must remain closed: {key}")


def _validate_bar_mapping(
    payload: Mapping[str, object],
    *,
    label: str,
) -> Mapping[str, object]:
    time_ms = payload.get("time_ms")
    if not isinstance(time_ms, int) or isinstance(time_ms, bool):
        raise ValueError(f"{label}.time_ms must be a JSON integer")
    numeric_keys = (
        "open",
        "high",
        "low",
        "close",
        "available_notional_usd",
    )
    for key in numeric_keys:
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{label}.{key} must be JSON numeric")
        if not math.isfinite(float(value)):
            raise ValueError(f"{label}.{key} must be finite")
    return payload


def _preflight_batch(
    *,
    session_report: Mapping[str, object],
    confirmation_session_id: str,
    lifecycle_inputs: Sequence[object],
    policy: PaperLifecycleBatchPolicy,
) -> tuple[str, tuple[_BatchItem, ...]]:
    if session_report.get("schema") != "qookey-paper-submission-session-report-v0.1":
        raise ValueError("unsupported paper submission session report schema")
    if session_report.get("state") != "PAPER_SESSION_ACCEPTED":
        raise ValueError("paper submission session is not accepted")
    for key in (
        "lifecycle_simulations_performed",
        "persistent_state_writes_performed",
    ):
        value = session_report.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value != 0:
            raise ValueError(f"paper submission session {key} must equal zero")
    _validate_session_authority(session_report)

    session_id = session_report.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        raise ValueError("paper submission session id is required")
    recomputed = paper_submission_session_report_id_from_mapping(session_report)
    if recomputed != session_id:
        raise ValueError("paper submission session id does not match report contents")
    if (
        policy.require_exact_session_id_confirmation
        and confirmation_session_id != session_id
    ):
        raise ValueError("exact session-id confirmation does not match report")

    intent_count = session_report.get("intent_count")
    if (
        not isinstance(intent_count, int)
        or isinstance(intent_count, bool)
        or intent_count < 1
        or intent_count > policy.maximum_intents
    ):
        raise ValueError("paper submission session intent_count is outside batch bounds")
    if len(lifecycle_inputs) != intent_count:
        raise ValueError("lifecycle input count must equal session intent_count")

    evidence_rows = session_report.get("paper_execution_evidence")
    receipt_rows = session_report.get("receipts")
    if not isinstance(evidence_rows, list) or not isinstance(receipt_rows, list):
        raise ValueError("paper submission session evidence/receipts must be arrays")
    if len(evidence_rows) != intent_count or len(receipt_rows) != intent_count:
        raise ValueError("paper submission session evidence/receipt counts do not match")

    evidence_by_proposal: dict[str, Mapping[str, object]] = {}
    for index, row in enumerate(evidence_rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"paper_execution_evidence[{index}] must be an object")
        proposal_id = row.get("proposal_id")
        evidence = row.get("paper_execution_evidence")
        if not isinstance(proposal_id, str) or not proposal_id:
            raise ValueError(f"paper_execution_evidence[{index}].proposal_id is required")
        if proposal_id in evidence_by_proposal:
            raise ValueError("duplicate paper execution evidence proposal id")
        if not isinstance(evidence, Mapping):
            raise ValueError(
                f"paper_execution_evidence[{index}].paper_execution_evidence must be object"
            )
        evidence_by_proposal[proposal_id] = evidence

    receipt_proposals: set[str] = set()
    for index, row in enumerate(receipt_rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"receipts[{index}] must be an object")
        proposal_id = row.get("proposal_id")
        receipt = row.get("receipt")
        if not isinstance(proposal_id, str) or not proposal_id:
            raise ValueError(f"receipts[{index}].proposal_id is required")
        if proposal_id in receipt_proposals:
            raise ValueError("duplicate paper session receipt proposal id")
        if not isinstance(receipt, Mapping):
            raise ValueError(f"receipts[{index}].receipt must be an object")
        receipt_proposals.add(proposal_id)

    if set(evidence_by_proposal) != receipt_proposals:
        raise ValueError("paper session evidence and receipt proposal sets differ")

    input_by_proposal: dict[str, _BatchItem] = {}
    for index, raw in enumerate(lifecycle_inputs):
        if not isinstance(raw, Mapping):
            raise ValueError(f"lifecycle_inputs[{index}] must be a JSON object")
        proposal_id = raw.get("proposal_id")
        if not isinstance(proposal_id, str) or not proposal_id:
            raise ValueError(f"lifecycle_inputs[{index}].proposal_id is required")
        if proposal_id in input_by_proposal:
            raise ValueError("duplicate lifecycle input proposal id")
        evidence = evidence_by_proposal.get(proposal_id)
        if evidence is None:
            raise ValueError("lifecycle input proposal is not in paper session")

        target_price = _strict_number(
            raw.get("target_price"),
            f"lifecycle_inputs[{index}].target_price",
        )
        if target_price <= 0.0:
            raise ValueError(f"lifecycle_inputs[{index}].target_price must be positive")

        bars_raw = raw.get("bars")
        if not isinstance(bars_raw, list):
            raise ValueError(f"lifecycle_inputs[{index}].bars must be a JSON array")
        bars: list[Mapping[str, object]] = []
        for bar_index, bar in enumerate(bars_raw):
            if not isinstance(bar, Mapping):
                raise ValueError(
                    f"lifecycle_inputs[{index}].bars[{bar_index}] must be an object"
                )
            bars.append(
                _validate_bar_mapping(
                    bar,
                    label=f"lifecycle_inputs[{index}].bars[{bar_index}]",
                )
            )

        lifecycle_payload: dict[str, object] = {
            "schema": "qookey-paper-fill-lifecycle-input-v0.1",
            "paper_execution_evidence": evidence,
            "target_price": target_price,
            "bars": [dict(bar) for bar in bars],
        }
        decision, receipt, parsed_target, _ = lifecycle_input_from_dict(
            lifecycle_payload
        )
        if decision.intent is None:
            raise ValueError("paper execution evidence intent is missing")
        if decision.intent.portfolio_proposal_id != proposal_id:
            raise ValueError("lifecycle proposal id does not match execution intent")
        if receipt.intent_id != decision.intent.intent_id:
            raise ValueError("paper lifecycle receipt intent id mismatch")
        input_by_proposal[proposal_id] = _BatchItem(
            proposal_id=proposal_id,
            paper_execution_evidence=evidence,
            target_price=parsed_target,
            bars=tuple(bars),
        )

    if set(input_by_proposal) != set(evidence_by_proposal):
        raise ValueError("batch requires one lifecycle input for every session proposal")

    return session_id, tuple(
        input_by_proposal[key] for key in sorted(input_by_proposal)
    )


def simulate_paper_lifecycle_batch(
    *,
    session_report: Mapping[str, object],
    confirmation_session_id: str,
    lifecycle_inputs: Sequence[object],
    batch_policy: PaperLifecycleBatchPolicy = PaperLifecycleBatchPolicy(),
    lifecycle_policy: PaperLifecyclePolicy = PaperLifecyclePolicy(),
) -> dict[str, object]:
    """Explicitly simulate the complete accepted paper-session basket."""

    session_id, items = _preflight_batch(
        session_report=session_report,
        confirmation_session_id=confirmation_session_id,
        lifecycle_inputs=lifecycle_inputs,
        policy=batch_policy,
    )

    results: list[dict[str, object]] = []
    account_records: list[dict[str, object]] = []
    status_counts: dict[str, int] = {
        "OPEN_POSITION": 0,
        "CLOSED": 0,
        "CANCELLED_UNFILLED": 0,
    }

    for item in items:
        lifecycle_payload: dict[str, object] = {
            "schema": "qookey-paper-fill-lifecycle-input-v0.1",
            "paper_execution_evidence": item.paper_execution_evidence,
            "target_price": item.target_price,
            "bars": [dict(bar) for bar in item.bars],
        }
        decision, receipt, target_price, bars = lifecycle_input_from_dict(
            lifecycle_payload
        )
        plan = build_paper_lifecycle_plan(
            decision=decision,
            receipt=receipt,
            target_price=target_price,
        )
        result = simulate_paper_lifecycle(
            plan=plan,
            bars=bars,
            policy=lifecycle_policy,
        )
        evidence = lifecycle_evidence(
            plan=plan,
            result=result,
            policy=lifecycle_policy,
        )
        status_counts[result.status] = status_counts.get(result.status, 0) + 1
        results.append(
            {
                "proposal_id": item.proposal_id,
                "lifecycle_id": plan.lifecycle_id,
                "status": result.status,
                "reason": result.reason,
                "paper_lifecycle_report": evidence,
            }
        )
        account_records.append(
            {
                "paper_execution_evidence": dict(item.paper_execution_evidence),
                "paper_lifecycle_report": evidence,
            }
        )

    report_hashes = [
        _sha256(row["paper_lifecycle_report"])
        for row in results
    ]
    batch_payload: dict[str, object] = {
        "schema": "qookey-paper-lifecycle-batch-id-v0.1",
        "session_id": session_id,
        "proposal_ids": [item.proposal_id for item in items],
        "lifecycle_report_sha256s": report_hashes,
    }
    batch_id = f"paper-lifecycle-batch-v0-1-{_sha256(batch_payload)}"

    return {
        "schema": "qookey-paper-lifecycle-batch-report-v0.1",
        "batch_id": batch_id,
        "session_id": session_id,
        "state": "PAPER_LIFECYCLE_BATCH_COMPLETE",
        "intent_count": len(items),
        "status_counts": status_counts,
        "results": results,
        "account_records": account_records,
        "provider_requests_performed": 0,
        "persistent_state_writes_performed": 0,
        "authority": {
            "explicit_paper_lifecycle_simulation_only": True,
            "provider_requests_performed": False,
            "r2_accessed": False,
            "holdout_accessed": False,
            "automatic_lifecycle_simulation_authorized": False,
            "scheduled_lifecycle_simulation_authorized": False,
            "persistent_state_write_authorized": False,
            "short_paper_execution_authorized": False,
            "formal_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
        "limitations": [
            "Lifecycle bars and normalized liquidity are explicit caller inputs.",
            "Batch V0.1 performs no provider request and persists no account state.",
            "Funding, liquidation and exchange rejection remain unmodeled.",
        ],
    }


def paper_lifecycle_batch_policy_from_config(
    payload: Mapping[str, object],
) -> PaperLifecycleBatchPolicy:
    if payload.get("schema") != "qookey-paper-lifecycle-batch-v0.1":
        raise ValueError("unsupported paper lifecycle batch config")
    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("policy object is required")

    maximum = policy.get("maximum_intents")
    if not isinstance(maximum, int) or isinstance(maximum, bool):
        raise ValueError("policy.maximum_intents must be a JSON integer")
    keys = (
        "require_exact_session_id_confirmation",
        "require_complete_session_basket",
        "explicit_lifecycle_simulation_authorized",
        "automatic_lifecycle_simulation_authorized",
        "scheduled_lifecycle_simulation_authorized",
        "provider_access_authorized",
        "persistent_state_write_authorized",
        "live_trading_authorized",
    )
    for key in keys:
        if not isinstance(policy.get(key), bool):
            raise ValueError(f"policy.{key} must be a JSON boolean")

    return PaperLifecycleBatchPolicy(
        maximum_intents=maximum,
        require_exact_session_id_confirmation=policy[
            "require_exact_session_id_confirmation"
        ],
        require_complete_session_basket=policy["require_complete_session_basket"],
        explicit_lifecycle_simulation_authorized=policy[
            "explicit_lifecycle_simulation_authorized"
        ],
        automatic_lifecycle_simulation_authorized=policy[
            "automatic_lifecycle_simulation_authorized"
        ],
        scheduled_lifecycle_simulation_authorized=policy[
            "scheduled_lifecycle_simulation_authorized"
        ],
        provider_access_authorized=policy["provider_access_authorized"],
        persistent_state_write_authorized=policy[
            "persistent_state_write_authorized"
        ],
        live_trading_authorized=policy["live_trading_authorized"],
    )


def paper_lifecycle_batch_input_from_dict(
    payload: Mapping[str, object],
) -> tuple[Mapping[str, object], tuple[object, ...]]:
    if payload.get("schema") != "qookey-paper-lifecycle-batch-input-v0.1":
        raise ValueError("unsupported paper lifecycle batch input schema")
    session_report = payload.get("session_report")
    lifecycle_inputs = payload.get("lifecycle_inputs")
    if not isinstance(session_report, Mapping):
        raise ValueError("session_report object is required")
    if not isinstance(lifecycle_inputs, list):
        raise ValueError("lifecycle_inputs must be a JSON array")
    return session_report, tuple(lifecycle_inputs)
