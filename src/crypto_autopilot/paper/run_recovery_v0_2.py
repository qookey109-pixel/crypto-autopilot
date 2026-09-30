"""Audit both run-step formats without changing frozen recovery V0.1."""
from __future__ import annotations

from collections.abc import Mapping

from crypto_autopilot.paper.live_v0_1 import verify_live_paper_state
from crypto_autopilot.paper.run_claim_v0_1 import live_paper_run_slot_id
from crypto_autopilot.paper.run_coordinator_v0_1 import (
    build_live_paper_run_result,
    verify_live_paper_run_header,
    verify_live_paper_run_result,
)
from crypto_autopilot.paper.run_coordinator_v0_3 import (
    read_live_paper_run_step_tick,
    verify_live_paper_run_step,
)
from crypto_autopilot.paper.run_recovery_v0_1 import (
    LivePaperRunRecoveryPolicy,
    PaperRunRecoveryStore,
    _authority,
    _orphan_ticks_after_terminal_state,
    _required_store_object,
    _scan_target_claims,
    _scan_target_results,
    _sha256,
)
from crypto_autopilot.paper.run_store_v0_1 import run_store_receipt_evidence


def _validate_step_evidence(
    *,
    store: PaperRunRecoveryStore,
    step: Mapping[str, object],
) -> tuple[str, str, str]:
    read_live_paper_run_step_tick(store, step)

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
            if payload.get("schema") == "qookey-live-paper-run-step-report-v0.1":
                verified = verify_live_paper_run_step(payload)
            else:
                read_live_paper_run_step_tick(store, payload)
                verified = str(payload["step_id"])
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
    claims, claim_scan_issues = _scan_target_claims(store=store, run_id=run_id)
    issues = [*step_scan_issues, *result_scan_issues, *claim_scan_issues]

    if not steps:
        unresolved_claim_slots = sorted(claims)
        if unresolved_claim_slots:
            issues.extend(
                "unresolved_claim_without_step:"
                + slot_id
                + ":"
                + str(claims[slot_id].get("request_id"))
                for slot_id in unresolved_claim_slots
            )
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
            "claim_count": len(claims),
            "unresolved_claim_slot_ids": unresolved_claim_slots,
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

    unresolved_claim_slots: list[str] = []
    complete_steps_by_request = {
        str(step["request_id"]): step
        for step in steps.values()
        if (
            isinstance(step.get("request_id"), str)
            and step.get("request_id")
            and str(step.get("step_id")) in complete_step_ids
        )
    }
    for slot_id, claim in claims.items():
        request_id = claim.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            issues.append(f"claim_missing_request_id:{slot_id}")
            unresolved_claim_slots.append(slot_id)
            continue
        step = complete_steps_by_request.get(request_id)
        if step is None:
            issues.append(f"unresolved_claim_without_complete_step:{slot_id}:{request_id}")
            unresolved_claim_slots.append(slot_id)
            continue
        expected_slot = live_paper_run_slot_id(
            run_id=run_id,
            sequence=int(step["sequence"]),
            previous_step_id=step.get("previous_step_id"),
            previous_state_id=str(step["previous_state_id"]),
        )
        if expected_slot != slot_id:
            issues.append(f"claim_step_slot_mismatch:{slot_id}:{request_id}")
            unresolved_claim_slots.append(slot_id)
            continue
        result = results.get(request_id)
        if result is not None and result.get("_verified_step_id") != step.get("step_id"):
            issues.append(f"claim_result_step_mismatch:{slot_id}:{request_id}")
            unresolved_claim_slots.append(slot_id)

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
        "claim_count": len(claims),
        "unresolved_claim_slot_ids": sorted(set(unresolved_claim_slots)),
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
