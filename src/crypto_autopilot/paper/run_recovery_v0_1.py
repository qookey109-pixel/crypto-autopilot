from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from crypto_autopilot.paper.live_v0_1 import (
    live_paper_tick_report_id_from_mapping,
    verify_live_paper_state,
)
from crypto_autopilot.paper.run_coordinator_v0_1 import (
    build_live_paper_run_result,
    verify_live_paper_run_header,
    verify_live_paper_run_result,
    verify_live_paper_run_step,
)
from crypto_autopilot.paper.run_store_v0_1 import run_store_receipt_evidence


class PaperRunRecoveryStore(Protocol):
    def get_json(
        self,
        kind: str,
        object_id: str,
    ) -> dict[str, object] | None: ...

    def put_json(
        self,
        kind: str,
        object_id: str,
        payload: Mapping[str, object],
    ) -> object: ...

    def list_json_ids(self, kind: str) -> tuple[str, ...]: ...


@dataclass(frozen=True, slots=True)
class LivePaperRunRecoveryPolicy:
    require_verified_run_header: bool = True
    require_contiguous_step_chain: bool = True
    require_persisted_state_evidence: bool = True
    require_persisted_tick_evidence: bool = True
    allow_missing_result_seal_repair: bool = True
    result_seal_repair_only: bool = True
    provider_access_authorized: bool = False
    live_market_data_access_authorized: bool = False
    account_state_mutation_authorized: bool = False
    step_state_tick_rewrite_authorized: bool = False
    automatic_schedule_authorized: bool = False
    private_exchange_api_authorized: bool = False
    holdout_access_authorized: bool = False
    real_money_order_authorized: bool = False
    live_real_trading_authorized: bool = False

    def __post_init__(self) -> None:
        flags = (
            self.require_verified_run_header,
            self.require_contiguous_step_chain,
            self.require_persisted_state_evidence,
            self.require_persisted_tick_evidence,
            self.allow_missing_result_seal_repair,
            self.result_seal_repair_only,
            self.provider_access_authorized,
            self.live_market_data_access_authorized,
            self.account_state_mutation_authorized,
            self.step_state_tick_rewrite_authorized,
            self.automatic_schedule_authorized,
            self.private_exchange_api_authorized,
            self.holdout_access_authorized,
            self.real_money_order_authorized,
            self.live_real_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in flags):
            raise ValueError("Live Paper Run Recovery policy flags must be booleans")
        if not all(flags[:6]):
            raise ValueError(
                "Live Paper Run Recovery V0.1 requires strict verification and "
                "result-seal-only repair"
            )
        if any(flags[6:]):
            raise ValueError(
                "Live Paper Run Recovery V0.1 cannot access providers or mutate "
                "trading/account evidence"
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


def _required_store_object(
    store: PaperRunRecoveryStore,
    kind: str,
    object_id: str,
) -> dict[str, object]:
    payload = store.get_json(kind, object_id)
    if payload is None:
        raise ValueError(f"missing {kind} object: {object_id}")
    if not isinstance(payload, dict):
        raise ValueError(f"{kind} object must be a JSON object")
    return payload


def _authority() -> dict[str, object]:
    return {
        "audit_and_result_seal_repair_only": True,
        "provider_access_authorized": False,
        "live_market_data_access_authorized": False,
        "account_state_mutation_authorized": False,
        "step_state_tick_rewrite_authorized": False,
        "automatic_schedule_authorized": False,
        "private_exchange_api_authorized": False,
        "holdout_access_authorized": False,
        "real_money_order_authorized": False,
        "live_real_trading_authorized": False,
    }


def _validate_step_evidence(
    *,
    store: PaperRunRecoveryStore,
    step: Mapping[str, object],
) -> tuple[str, str, str]:
    step_id = verify_live_paper_run_step(step)
    if step.get("step_id") != step_id:
        raise ValueError("stored live paper run step id mismatch")

    previous_state_id = step.get("previous_state_id")
    next_state_id = step.get("next_state_id")
    tick_id = step.get("tick_id")
    if not isinstance(previous_state_id, str) or not previous_state_id:
        raise ValueError("stored run step previous_state_id is required")
    if not isinstance(next_state_id, str) or not next_state_id:
        raise ValueError("stored run step next_state_id is required")
    if not isinstance(tick_id, str) or not tick_id:
        raise ValueError("stored run step tick_id is required")

    previous_state = _required_store_object(
        store,
        "live-state",
        previous_state_id,
    )
    if verify_live_paper_state(previous_state) != previous_state_id:
        raise ValueError("persisted previous live state id mismatch")

    next_state = _required_store_object(
        store,
        "live-state",
        next_state_id,
    )
    if verify_live_paper_state(next_state) != next_state_id:
        raise ValueError("persisted next live state id mismatch")

    tick = _required_store_object(store, "live-tick", tick_id)
    if live_paper_tick_report_id_from_mapping(tick) != tick_id:
        raise ValueError("persisted live tick id mismatch")
    embedded_tick = step.get("tick_report")
    if not isinstance(embedded_tick, Mapping):
        raise ValueError("stored run step embedded tick is required")
    if _canonicalize(tick) != _canonicalize(embedded_tick):
        raise ValueError("persisted live tick differs from run-step tick evidence")

    return previous_state_id, next_state_id, tick_id


def _scan_target_steps(
    *,
    store: PaperRunRecoveryStore,
    run_id: str,
) -> tuple[dict[int, dict[str, object]], list[str]]:
    by_sequence: dict[int, dict[str, object]] = {}
    issues: list[str] = []
    for object_id in store.list_json_ids("live-run-step"):
        payload = store.get_json("live-run-step", object_id)
        if payload is None or payload.get("run_id") != run_id:
            continue
        try:
            verified = verify_live_paper_run_step(payload)
        except ValueError as error:
            issues.append(f"invalid_step:{object_id}:{error}")
            continue
        if verified != object_id or payload.get("step_id") != object_id:
            issues.append(f"step_object_id_mismatch:{object_id}")
            continue
        sequence = payload.get("sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
            issues.append(f"invalid_step_sequence:{object_id}")
            continue
        if sequence in by_sequence:
            issues.append(
                f"duplicate_step_sequence:{sequence}:{by_sequence[sequence]['step_id']}:{object_id}"
            )
            continue
        by_sequence[sequence] = payload
    return by_sequence, issues


def _scan_target_results(
    *,
    store: PaperRunRecoveryStore,
    run_id: str,
) -> tuple[dict[str, dict[str, object]], list[str]]:
    by_request: dict[str, dict[str, object]] = {}
    issues: list[str] = []
    for object_id in store.list_json_ids("live-run-result"):
        payload = store.get_json("live-run-result", object_id)
        if payload is None or payload.get("run_id") != run_id:
            continue
        try:
            step_id, verified_run_id, _ = verify_live_paper_run_result(
                payload,
                request_id=object_id,
            )
        except ValueError as error:
            issues.append(f"invalid_result:{object_id}:{error}")
            continue
        if verified_run_id != run_id:
            issues.append(f"result_run_mismatch:{object_id}")
            continue
        if payload.get("request_id") != object_id:
            issues.append(f"result_object_id_mismatch:{object_id}")
            continue
        if object_id in by_request:
            issues.append(f"duplicate_result_request:{object_id}")
            continue
        row = dict(payload)
        row["_verified_step_id"] = step_id
        by_request[object_id] = row
    return by_request, issues


def _orphan_ticks_after_terminal_state(
    *,
    store: PaperRunRecoveryStore,
    known_tick_ids: set[str],
    terminal_state_id: str,
) -> tuple[str, ...]:
    orphan_ids: list[str] = []
    for object_id in store.list_json_ids("live-tick"):
        if object_id in known_tick_ids:
            continue
        payload = store.get_json("live-tick", object_id)
        if payload is None:
            continue
        if payload.get("previous_state_id") != terminal_state_id:
            continue
        try:
            verified = live_paper_tick_report_id_from_mapping(payload)
        except ValueError:
            continue
        if verified == object_id and payload.get("tick_id") == object_id:
            orphan_ids.append(object_id)
    return tuple(sorted(orphan_ids))


def reconcile_live_paper_run(
    *,
    run_id: str,
    store: PaperRunRecoveryStore,
    repair_missing_result_seals: bool = False,
    policy: LivePaperRunRecoveryPolicy = LivePaperRunRecoveryPolicy(),
) -> dict[str, object]:
    """Audit one append-only Live Paper run and optionally seal complete steps.

    Repair is limited to a missing immutable live-run-result object after the
    run step, both states and tick report have all been fully verified.
    """

    if not isinstance(run_id, str) or not run_id:
        raise ValueError("live paper recovery run_id is required")
    if not isinstance(repair_missing_result_seals, bool):
        raise ValueError("repair_missing_result_seals must be boolean")
    if repair_missing_result_seals and not policy.allow_missing_result_seal_repair:
        raise ValueError("missing result-seal repair is not authorized")

    header = _required_store_object(store, "live-run", run_id)
    if verify_live_paper_run_header(header) != run_id:
        raise ValueError("live paper run header id mismatch")
    initial_state_id = header.get("initial_state_id")
    if not isinstance(initial_state_id, str) or not initial_state_id:
        raise ValueError("live paper run initial_state_id is required")

    initial_state = _required_store_object(store, "live-state", initial_state_id)
    if verify_live_paper_state(initial_state) != initial_state_id:
        raise ValueError("live paper run initial state id mismatch")

    steps, step_scan_issues = _scan_target_steps(store=store, run_id=run_id)
    results, result_scan_issues = _scan_target_results(store=store, run_id=run_id)
    issues = [*step_scan_issues, *result_scan_issues]

    if not steps:
        orphan_results = sorted(results)
        if orphan_results:
            issues.extend(
                f"result_without_step:{request_id}"
                for request_id in orphan_results
            )
        orphan_ticks = _orphan_ticks_after_terminal_state(
            store=store,
            known_tick_ids=set(),
            terminal_state_id=initial_state_id,
        )
        if orphan_ticks:
            issues.extend(
                f"ambiguous_orphan_tick_after_initial_state:{tick_id}"
                for tick_id in orphan_ticks
            )
        state = (
            "REVIEW_REQUIRED"
            if issues
            else "RUN_EMPTY_RETRY_FROM_INITIAL_STATE_SAFE"
        )
        report = {
            "schema": "qookey-live-paper-run-recovery-report-v0.1",
            "state": state,
            "run_id": run_id,
            "step_count": 0,
            "terminal_step_id": None,
            "terminal_state_id": initial_state_id,
            "repairable_request_ids": [],
            "repaired_request_ids": [],
            "issues": sorted(issues),
            "provider_requests_performed": 0,
            "live_market_data_requests_performed": 0,
            "account_state_mutations_performed": 0,
            "step_state_tick_rewrites_performed": 0,
            "result_seal_writes_performed": 0,
            "storage_receipts": [],
            "authority": _authority(),
        }
        report["recovery_id"] = (
            "live-paper-run-recovery-v0-1-" + _sha256(report)
        )
        return report

    sequences = sorted(steps)
    expected_sequences = list(range(1, sequences[-1] + 1))
    if sequences != expected_sequences:
        issues.append(
            "non_contiguous_step_sequences:"
            + ",".join(str(item) for item in sequences)
        )

    known_tick_ids: set[str] = set()
    repairable: list[str] = []
    complete_step_ids: set[str] = set()
    prior_step_id: str | None = None
    prior_state_id = initial_state_id
    terminal_step_id: str | None = None
    terminal_state_id = initial_state_id

    for sequence in sequences:
        step = steps[sequence]
        step_id = str(step["step_id"])
        if sequence == 1:
            if step.get("previous_step_id") is not None:
                issues.append(f"first_step_previous_step_not_null:{step_id}")
        elif step.get("previous_step_id") != prior_step_id:
            issues.append(f"step_chain_previous_id_mismatch:{step_id}")
        if step.get("previous_state_id") != prior_state_id:
            issues.append(f"step_chain_previous_state_mismatch:{step_id}")

        try:
            previous_state_id, next_state_id, tick_id = _validate_step_evidence(
                store=store,
                step=step,
            )
        except ValueError as error:
            issues.append(f"incomplete_step_evidence:{step_id}:{error}")
            prior_step_id = step_id
            next_id = step.get("next_state_id")
            if isinstance(next_id, str) and next_id:
                prior_state_id = next_id
            continue

        if previous_state_id != prior_state_id:
            issues.append(f"verified_previous_state_chain_mismatch:{step_id}")
        known_tick_ids.add(tick_id)
        complete_step_ids.add(step_id)

        request_id = step.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            issues.append(f"step_missing_request_id:{step_id}")
        else:
            result = results.get(request_id)
            if result is None:
                repairable.append(request_id)
            else:
                if result.get("_verified_step_id") != step_id:
                    issues.append(f"result_step_mismatch:{request_id}")
                if result.get("sequence") != sequence:
                    issues.append(f"result_sequence_mismatch:{request_id}")

        prior_step_id = step_id
        prior_state_id = next_state_id
        terminal_step_id = step_id
        terminal_state_id = next_state_id

    step_request_ids = {
        str(step["request_id"])
        for step in steps.values()
        if isinstance(step.get("request_id"), str) and step.get("request_id")
    }
    for request_id, result in results.items():
        if request_id not in step_request_ids:
            issues.append(f"result_without_matching_step:{request_id}")
            continue
        referenced_step = result.get("_verified_step_id")
        if isinstance(referenced_step, str) and referenced_step not in complete_step_ids:
            issues.append(f"result_references_incomplete_step:{request_id}")

    orphan_ticks = _orphan_ticks_after_terminal_state(
        store=store,
        known_tick_ids=known_tick_ids,
        terminal_state_id=terminal_state_id,
    )
    issues.extend(
        f"ambiguous_orphan_tick_after_terminal_state:{tick_id}"
        for tick_id in orphan_ticks
    )

    receipts: list[object] = []
    repaired: list[str] = []
    if repair_missing_result_seals and not issues:
        request_to_step = {
            str(step["request_id"]): step
            for step in steps.values()
            if isinstance(step.get("request_id"), str)
        }
        for request_id in sorted(repairable):
            step = request_to_step[request_id]
            step_id = str(step["step_id"])
            sequence = int(step["sequence"])
            result_payload = build_live_paper_run_result(
                request_id=request_id,
                step_id=step_id,
                run_id=run_id,
                sequence=sequence,
            )
            receipt = store.put_json(
                "live-run-result",
                request_id,
                result_payload,
            )
            receipts.append(receipt)
            persisted = _required_store_object(
                store,
                "live-run-result",
                request_id,
            )
            verified_step_id, verified_run_id, verified_sequence = (
                verify_live_paper_run_result(
                    persisted,
                    request_id=request_id,
                )
            )
            if (
                verified_step_id != step_id
                or verified_run_id != run_id
                or verified_sequence != sequence
            ):
                raise ValueError("repaired live paper result seal failed verification")
            repaired.append(request_id)

    receipt_evidence = [run_store_receipt_evidence(item) for item in receipts]
    result_writes = sum(
        evidence["receipt"]["replayed"] is False  # type: ignore[index]
        for evidence in receipt_evidence
    )

    if issues:
        state = "REVIEW_REQUIRED"
    elif repairable and not repair_missing_result_seals:
        state = "MISSING_RESULT_SEALS_REPAIRABLE"
    elif repaired:
        state = "MISSING_RESULT_SEALS_REPAIRED"
    else:
        state = "RUN_CONSISTENT"

    report = {
        "schema": "qookey-live-paper-run-recovery-report-v0.1",
        "state": state,
        "run_id": run_id,
        "step_count": len(steps),
        "terminal_step_id": terminal_step_id,
        "terminal_state_id": terminal_state_id,
        "repairable_request_ids": sorted(repairable),
        "repaired_request_ids": sorted(repaired),
        "issues": sorted(issues),
        "provider_requests_performed": 0,
        "live_market_data_requests_performed": 0,
        "account_state_mutations_performed": 0,
        "step_state_tick_rewrites_performed": 0,
        "result_seal_writes_performed": result_writes,
        "storage_receipts": receipt_evidence,
        "authority": _authority(),
    }
    report["recovery_id"] = (
        "live-paper-run-recovery-v0-1-" + _sha256(report)
    )
    return report


def live_paper_run_recovery_policy_from_config(
    payload: Mapping[str, object],
) -> LivePaperRunRecoveryPolicy:
    if payload.get("schema") != "qookey-live-paper-run-recovery-v0.1":
        raise ValueError("unsupported live paper run recovery config")
    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("live paper run recovery policy object is required")
    keys = (
        "require_verified_run_header",
        "require_contiguous_step_chain",
        "require_persisted_state_evidence",
        "require_persisted_tick_evidence",
        "allow_missing_result_seal_repair",
        "result_seal_repair_only",
        "provider_access_authorized",
        "live_market_data_access_authorized",
        "account_state_mutation_authorized",
        "step_state_tick_rewrite_authorized",
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
    return LivePaperRunRecoveryPolicy(**values)
