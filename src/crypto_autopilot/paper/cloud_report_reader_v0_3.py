"""Successor reader for V0.1/V0.2 and truthful V0.3 Cloud Paper reports.

Retains digest, state, step and ledger checks; performs no IO on import.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping

from crypto_autopilot.paper.cloud_loop_v0_1 import CloudLoopReviewRequired, digest
from crypto_autopilot.paper.live_v0_1 import verify_live_paper_state
from crypto_autopilot.paper.run_coordinator_v0_3 import (
    PaperRunStoreLike, read_live_paper_run_step_tick,
)


def _report_step(
    store: PaperRunStoreLike,
    report: Mapping[str, object],
    *,
    before_external: Callable[[], None] | None = None,
) -> dict[str, object]:
    """Load the verified step referenced by either supported loop-report schema."""
    coordinator = report.get("coordinator")
    if not isinstance(coordinator, Mapping):
        raise CloudLoopReviewRequired("RESULT_COORDINATOR_MISSING")
    schema = report.get("schema")
    if schema == "qookey-cloud-paper-loop-report-v0.1":
        embedded = coordinator.get("run_step")
        if not isinstance(embedded, Mapping):
            raise CloudLoopReviewRequired("RESULT_STEP_MISSING")
        try:
            read_live_paper_run_step_tick(store, embedded, before_external=before_external)
            step_id = str(embedded["step_id"])
        except ValueError:
            raise CloudLoopReviewRequired("RESULT_STEP_INVALID") from None
    elif schema in {"qookey-cloud-paper-loop-report-v0.2", "qookey-cloud-paper-loop-report-v0.3"}:
        if "run_step" in coordinator:
            raise CloudLoopReviewRequired("COMPACT_REPORT_EMBEDS_STEP")
        step_id = coordinator.get("step_id")
        if not isinstance(step_id, str) or not step_id:
            raise CloudLoopReviewRequired("RESULT_STEP_REFERENCE_MISSING")
        embedded = None
    else:
        raise CloudLoopReviewRequired("RESULT_REPORT_SCHEMA_UNSUPPORTED")

    if before_external is not None:
        before_external()
    persisted = store.get_json("live-run-step", step_id)
    if persisted is None:
        raise CloudLoopReviewRequired("RESULT_STEP_PERSISTENCE_MISSING")
    try:
        read_live_paper_run_step_tick(store, persisted, before_external=before_external)
        verified = str(persisted["step_id"])
    except ValueError:
        raise CloudLoopReviewRequired("RESULT_STEP_PERSISTENCE_INVALID") from None
    if verified != step_id or persisted.get("step_id") != step_id:
        raise CloudLoopReviewRequired("RESULT_STEP_REFERENCE_MISMATCH")
    if embedded is not None and persisted != embedded:
        raise CloudLoopReviewRequired("RESULT_STEP_PERSISTENCE_MISMATCH")
    if schema in {"qookey-cloud-paper-loop-report-v0.2", "qookey-cloud-paper-loop-report-v0.3"} and coordinator.get("step_id") != step_id:
        raise CloudLoopReviewRequired("RESULT_STEP_REFERENCE_MISMATCH")
    return persisted


def committed_report(
    store: PaperRunStoreLike,
    slot: str,
    *,
    before_external: Callable[[], None] | None = None,
) -> dict[str, object] | None:
    def get_json(kind: str, object_id: str) -> dict[str, object] | None:
        if before_external is not None:
            before_external()
        return store.get_json(kind, object_id)

    result = get_json("cloud-result", slot)
    if result is None:
        return None
    if result.get("slot_id") != slot or result.get("state") != "COMMITTED":
        raise CloudLoopReviewRequired("RESULT_POINTER_MISMATCH")
    report = get_json("cloud-report", str(result.get("report_id", "")))
    if report is None or digest(report) != result.get("report_id"):
        raise CloudLoopReviewRequired("RESULT_REPORT_MISMATCH")
    if report.get("slot_id") != slot:
        raise CloudLoopReviewRequired("RESULT_SLOT_MISMATCH")
    step = _report_step(store, report, before_external=before_external)
    state = get_json("live-state", str(step["next_state_id"]))
    if state is None or verify_live_paper_state(state) != step["next_state_id"]:
        raise CloudLoopReviewRequired("RESULT_PERSISTENCE_MISMATCH")
    seal = get_json("live-run-result", str(step["request_id"]))
    if seal is None or seal.get("step_id") != step["step_id"]:
        raise CloudLoopReviewRequired("COORDINATOR_SEAL_MISSING")
    return report


def latest_committed_slot(
    store: PaperRunStoreLike, *, current_slot: str,
    before_external: Callable[[], None],
) -> str | None:
    """Resolve the latest commit with bounded reads and complete namespace coverage.

    Genesis is accepted only when slot, claim, run-step, and state namespaces
    are empty. Non-empty history is checked by complete object listings, exact
    coverage counts, a verified latest report, and its verified parent step.
    """
    list_ids = getattr(store, "list_json_ids", None)
    if not callable(list_ids):
        raise CloudLoopReviewRequired("COMPLETE_LEDGER_SCAN_UNAVAILABLE")

    # The store adapter must reserve each page before its R2 list request.
    before_external()
    result_ids = tuple(list_ids("cloud-result"))
    before_external()
    claim_ids = tuple(list_ids("cloud-slot"))
    before_external()
    step_ids = tuple(list_ids("live-run-step"))
    before_external()
    state_ids = tuple(list_ids("live-state"))

    def valid_slot_id(value: object) -> bool:
        return (
            isinstance(value, str) and value.isdigit() and len(value) <= 20
            and str(int(value)) == value
        )

    if any(not valid_slot_id(value) for value in (*result_ids, *claim_ids)):
        raise CloudLoopReviewRequired("LEDGER_SLOT_ID_INVALID")
    if any(not isinstance(value, str) or not value for value in (*step_ids, *state_ids)):
        raise CloudLoopReviewRequired("LEDGER_OBJECT_ID_INVALID")

    result_slots = set(result_ids)
    if not result_slots:
        if claim_ids or step_ids or state_ids:
            raise CloudLoopReviewRequired("GENESIS_LEDGER_NOT_EMPTY")
        return None
    if set(claim_ids) != result_slots:
        raise CloudLoopReviewRequired("LEDGER_CLAIM_RESULT_COVERAGE_MISMATCH")
    if any(int(value) >= int(current_slot) for value in result_slots):
        raise CloudLoopReviewRequired("LEDGER_CONTAINS_CURRENT_OR_FUTURE_SLOT")
    if len(step_ids) != len(result_slots):
        raise CloudLoopReviewRequired("LEDGER_STEP_RESULT_COVERAGE_MISMATCH")
    if len(state_ids) != len(result_slots) + 1:
        raise CloudLoopReviewRequired("LEDGER_STATE_RESULT_COVERAGE_MISMATCH")

    latest_slot = max(result_slots, key=int)
    before_external()
    latest = committed_report(store, latest_slot)
    if latest is None:
        raise CloudLoopReviewRequired("LEDGER_COMMITTED_RESULT_MISSING")
    step = _report_step(store, latest, before_external=before_external)

    sequence = step.get("sequence")
    step_id = step.get("step_id")
    previous_step_id = step.get("previous_step_id")
    previous_state_id = step.get("previous_state_id")
    next_state_id = step.get("next_state_id")
    if sequence != len(result_slots):
        raise CloudLoopReviewRequired("LEDGER_SEQUENCE_GAP")
    if not isinstance(step_id, str) or step_id not in step_ids:
        raise CloudLoopReviewRequired("LEDGER_STEP_ID_MISSING")
    if not isinstance(previous_state_id, str) or previous_state_id not in state_ids:
        raise CloudLoopReviewRequired("LEDGER_PREVIOUS_STATE_MISSING")
    if not isinstance(next_state_id, str) or next_state_id not in state_ids:
        raise CloudLoopReviewRequired("LEDGER_NEXT_STATE_MISSING")
    if sequence == 1:
        if previous_step_id is not None:
            raise CloudLoopReviewRequired("LEDGER_GENESIS_LINK_INVALID")
    else:
        if not isinstance(previous_step_id, str) or previous_step_id not in step_ids:
            raise CloudLoopReviewRequired("LEDGER_PREVIOUS_STEP_MISSING")
        before_external()
        previous_step = store.get_json("live-run-step", previous_step_id)
        if previous_step is None:
            raise CloudLoopReviewRequired("LEDGER_PREVIOUS_STEP_READBACK_MISSING")
        try:
            read_live_paper_run_step_tick(
                store, previous_step, before_external=before_external,
            )
        except ValueError:
            raise CloudLoopReviewRequired("LEDGER_PREVIOUS_STEP_INVALID") from None
        if (
            previous_step.get("sequence") != sequence - 1
            or previous_step.get("next_state_id") != previous_state_id
            or previous_step.get("run_id") != step.get("run_id")
        ):
            raise CloudLoopReviewRequired("LEDGER_CHAIN_MISMATCH")
    return latest_slot


