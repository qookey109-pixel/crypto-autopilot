"""Prepared seal-guarded composition; no cloud activation authority."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace

from crypto_autopilot.paper.cloud_composition_v0_1 import CloudPaperNoTradeComposition
from crypto_autopilot.paper.cloud_loop_v0_1 import CloudLoopReviewRequired
from crypto_autopilot.paper.run_coordinator_v0_1 import verify_live_paper_run_result
from crypto_autopilot.paper.run_coordinator_v0_3 import read_live_paper_run_step_tick


class _SealGuardedStore:
    """Validate each returned result seal against its stored step and tick."""

    def __init__(self, store: object, *, guard: object, before_external: Callable[[], None]):
        self._inner = store
        self.budget_guard = guard
        self._before_external = before_external

    def get_json(self, kind: str, object_id: str):
        value = self._inner.get_json(kind, object_id)
        if kind != "live-run-result" or value is None:
            return value
        try:
            if not isinstance(value, Mapping):
                raise ValueError("result must be a mapping")
            step_id, run_id, sequence = verify_live_paper_run_result(value, request_id=object_id)
            self._before_external()
            step = self._inner.get_json("live-run-step", step_id)
            if not isinstance(step, Mapping):
                raise ValueError("missing step")
            read_live_paper_run_step_tick(
                self._inner, step, before_external=self._before_external,
            )
            if (
                step.get("step_id") != step_id or step.get("request_id") != object_id
                or step.get("run_id") != run_id or step.get("sequence") != sequence
            ):
                raise ValueError("seal binding mismatch")
        except (KeyError, ValueError):
            raise CloudLoopReviewRequired("COORDINATOR_SEAL_INVALID") from None
        return value

    def put_json(self, kind: str, object_id: str, payload: Mapping[str, object]):
        return self._inner.put_json(kind, object_id, payload)

    def put_json_if_absent(self, kind: str, object_id: str, payload: Mapping[str, object]):
        return self._inner.put_json_if_absent(kind, object_id, payload)

    def list_json_ids(self, kind: str):
        return self._inner.list_json_ids(kind)


def build_seal_guarded_composition(
    base: CloudPaperNoTradeComposition, *, enabled: bool = False,
) -> CloudPaperNoTradeComposition | None:
    """Wrap an already prepared composition without constructing cloud clients."""
    if type(enabled) is not bool:
        raise ValueError("enabled must be boolean")
    if not enabled:
        return None
    if not isinstance(base, CloudPaperNoTradeComposition):
        raise ValueError("prepared Cloud Paper composition required")
    guarded = _SealGuardedStore(
        base.store, guard=base.budget_guard, before_external=base.before_external,
    )
    return replace(base, store=guarded)
