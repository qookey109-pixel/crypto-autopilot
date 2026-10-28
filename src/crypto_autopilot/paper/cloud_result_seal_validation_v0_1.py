"""Pure successor guard for Cloud Paper committed-result seal verification.

The legacy reader remains frozen. This helper is not wired to a production
runtime and grants no recovery or trading authority. Callers must budget all
additional reads and separately authorize any future integration.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping

from crypto_autopilot.paper.cloud_loop_v0_1 import CloudLoopReviewRequired, committed_report
from crypto_autopilot.paper.run_coordinator_v0_1 import verify_live_paper_run_result
from crypto_autopilot.paper.run_coordinator_v0_3 import (
    PaperRunStoreLike, read_live_paper_run_step_tick,
)


def committed_report_with_seal_validation(
    store: PaperRunStoreLike, slot: str, *, before_external: Callable[[], None] | None = None,
) -> dict[str, object] | None:
    """Return only an existing result whose seal binds the verified persisted step."""
    report = committed_report(store, slot, before_external=before_external)
    if report is None:
        return None
    coordinator = report.get("coordinator")
    if not isinstance(coordinator, Mapping):
        raise CloudLoopReviewRequired("COORDINATOR_SEAL_INVALID")
    if report.get("schema") == "qookey-cloud-paper-loop-report-v0.1":
        embedded = coordinator.get("run_step")
        step_id = embedded.get("step_id") if isinstance(embedded, Mapping) else None
    else:
        step_id = coordinator.get("step_id")
    if not isinstance(step_id, str) or not step_id:
        raise CloudLoopReviewRequired("COORDINATOR_SEAL_INVALID")
    if before_external is not None:
        before_external()
    step = store.get_json("live-run-step", step_id)
    if not isinstance(step, Mapping):
        raise CloudLoopReviewRequired("COORDINATOR_SEAL_INVALID")
    try:
        read_live_paper_run_step_tick(store, step, before_external=before_external)
        request_id = step["request_id"]
        if not isinstance(request_id, str) or not request_id or step.get("step_id") != step_id:
            raise ValueError("invalid step binding")
        if before_external is not None:
            before_external()
        seal = store.get_json("live-run-result", request_id)
        if not isinstance(seal, Mapping):
            raise ValueError("missing seal")
        actual = verify_live_paper_run_result(seal, request_id=request_id)
        if actual != (step_id, step.get("run_id"), step.get("sequence")):
            raise ValueError("result seal binding mismatch")
    except (KeyError, ValueError):
        raise CloudLoopReviewRequired("COORDINATOR_SEAL_INVALID") from None
    return report
