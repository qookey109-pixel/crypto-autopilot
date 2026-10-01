"""JSON-safe successor for Cloud Paper report writing.

The frozen V0.1 implementation and its receipt remain byte-identical.
Only newly generated report representation changes; old readers and identities
remain available, and this module grants no runtime or external-access authority.
"""
from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence

from crypto_autopilot.paper import cloud_loop_v0_1 as legacy
from crypto_autopilot.paper.cloud_loop_v0_1 import (
    CloudLoopReviewRequired,
    _report_step,
    committed_report,
    decision_reason_codes,
    digest,
    latest_committed_slot,
    validate_slot_start,
)
from crypto_autopilot.paper.cloud_genesis_v0_1 import initialize_cloud_paper_state
from crypto_autopilot.paper.live_v0_1 import LivePaperMarketFeed, verify_live_paper_state
from crypto_autopilot.paper.run_claim_v0_1 import LivePaperRunClaimPolicy
from crypto_autopilot.paper.run_coordinator_v0_3 import (
    PaperRunStoreLike,
    coordinate_live_paper_run_step,
    read_live_paper_run_step_tick,
)

def run_cloud_step(
    *, tick_ms: int, previous_slot: str | None, store: PaperRunStoreLike,
    feed: LivePaperMarketFeed, market_supplier: Callable[[], Mapping[str, object]],
    candidate_supplier: Callable[[Mapping[str, object], Mapping[str, object]], Sequence[object]],
    strategy_registry: Mapping[str, object],
    before_external: Callable[[], None],
    run_name: str = "cloud-paper-v0-1",
    scheduled_at_ms: int | None = None,
) -> dict[str, object]:
    """One claimed slot, with exact prior-result chaining and immutable readback.

    The complete append-only ledger is scanned and verified before choosing
    genesis or chaining the prior step. Caller still enforces activation/budget
    and supplies a continuity-checking public feed.
    The callbacks also allow cloud CI to exercise the full positive path without
    putting test strategy evidence in a production registry.
    """
    # tick_ms is the actual observation/lifecycle clock. The optional schedule
    # timestamp identifies the immutable slot only; old exact-tick callers retain
    # their existing behavior. Never round a delayed historical slot forward.
    scheduled_at_ms = tick_ms if scheduled_at_ms is None else scheduled_at_ms
    slot = validate_slot_start(scheduled_at_ms=scheduled_at_ms, started_at_ms=tick_ms)
    if strategy_registry.get("schema") != "qookey-cloud-paper-strategy-registry-v0.1":
        raise CloudLoopReviewRequired("INVALID_STRATEGY_REGISTRY")
    registrations = strategy_registry.get("strategies")
    if not isinstance(registrations, list):
        raise CloudLoopReviewRequired("INVALID_STRATEGY_REGISTRY")
    before_external()
    prior_result = committed_report(store, slot)
    if prior_result is not None:
        return {"state": "REPLAYED", "slot_id": slot, "report": prior_result,
                "provider_requests_performed": 0}
    latest_slot = latest_committed_slot(
        store, current_slot=slot, before_external=before_external,
    )
    if previous_slot is not None and (
        not isinstance(previous_slot, str) or not previous_slot.isdigit()
        or str(int(previous_slot)) != previous_slot
    ):
        raise CloudLoopReviewRequired("INVALID_PREVIOUS_SLOT")
    if previous_slot != latest_slot:
        reason = ("PREVIOUS_SLOT_REQUIRED"
                  if latest_slot is not None and previous_slot is None
                  else "PREVIOUS_SLOT_MISMATCH")
        raise CloudLoopReviewRequired(reason)
    previous = None
    if latest_slot is not None:
        old = committed_report(store, latest_slot)
        if old is None:
            raise CloudLoopReviewRequired("PREVIOUS_RESULT_MISSING")
        previous = _report_step(store, old, before_external=before_external)
    if previous is None:
        state = initialize_cloud_paper_state()
    else:
        before_external()
        state = store.get_json("live-state", str(previous["next_state_id"]))
        if state is None or verify_live_paper_state(state) != previous["next_state_id"]:
            raise CloudLoopReviewRequired("PREVIOUS_STATE_PERSISTENCE_MISMATCH")
    before_external()
    store.put_json_if_absent("cloud-slot", slot, {
        "slot_id": slot, "tick_ms": tick_ms, "scheduled_at_ms": scheduled_at_ms,
        "previous_slot": previous_slot,
        "previous_state_id": state["state_id"], "run_name": run_name,
    })
    # An unsealed claim is never taken over, even if the request is identical.
    before_external()
    market = dict(market_supplier())
    market_requests = market.get("provider_requests_performed")
    if type(market_requests) is not int or not 0 <= market_requests <= 8:
        raise CloudLoopReviewRequired("MARKET_REQUEST_COUNT_UNKNOWN_OR_OVER_LIMIT")
    candidates = tuple(candidate_supplier(market, state))
    if not registrations and candidates:
        raise CloudLoopReviewRequired("EMPTY_PRODUCTION_STRATEGY_REGISTRY")
    allowed_ids = {entry.get("strategy_id") for entry in registrations
                   if isinstance(entry, Mapping)}

    def candidate_strategy_id(item: object) -> object:
        if not isinstance(item, Mapping):
            return None
        payload = item.get("candidate")
        if isinstance(payload, Mapping):
            return payload.get("strategy_id", item.get("strategy_id"))
        return item.get("strategy_id")

    if any(candidate_strategy_id(item) not in allowed_ids
           for item in candidates):
        raise CloudLoopReviewRequired("UNREGISTERED_STRATEGY_CANDIDATE")
    if len(candidates) > 5:
        raise CloudLoopReviewRequired("TOO_MANY_CANDIDATES")
    report = coordinate_live_paper_run_step(
        run_name=run_name, tick_time_ms=tick_ms, candidate_specs=candidates,
        feed=feed, store=store,
        initial_state=state if previous is None else None,
        previous_step=previous,
        policy=legacy.LivePaperRunCoordinatorPolicy(
            run_slot_claim_required=True, compact_tick_reference=True,
        ),
        claim_policy=LivePaperRunClaimPolicy(),
    )
    tick = read_live_paper_run_step_tick(
        store, report["run_step"], before_external=before_external,
    )
    next_state = tick["next_state"]
    checkpoint = next_state["checkpoint_report"]
    reasons = decision_reason_codes(
        market=market, registrations=registrations, candidates=candidates,
    )
    outcome = {
        "schema": "qookey-cloud-paper-loop-report-v0.2",
        "state": (
            "REVIEW_REQUIRED"
            if market.get("market_status") == "REVIEW_REQUIRED"
            or market.get("execution_selection_status") == "REVIEW_REQUIRED"
            else "COMMITTED" if candidates or state["active_session"] else "NO_TRADE"
        ),
        "slot_id": slot, "previous_slot": previous_slot, "tick_ms": tick_ms,
        "scheduled_at_ms": scheduled_at_ms,
        "market": market, "candidate_count": len(candidates),
        # V0.2 stores the step once in live-run-step and references its verified
        # content address here. V0.1 reports remain readable through _report_step.
        "coordinator": {key: value for key, value in report.items()
                        if key != "run_step"},
        "operation_counts": {
            "provider_requests": market_requests + int(report.get("provider_requests_performed", 0)),
            "r2_write_attempts": int(report.get("persistent_objects_created", 0)) + 3,
            "r2_write_replays": 0,
            "status": "KNOWN",
        },
        "account": checkpoint["account_snapshot"],
        "reason": reasons[0],
        "reason_codes": list(reasons),
        "authority": {"paper_only": True, "real_money_orders": False,
                      "holdout_access": False, "source_switch": False,
                      "model_promotion": False},
    }
    # JSON arrays are the persistent representation of tuple evidence.
    # Normalization preserves the canonical report hash and exact readback checks.
    outcome = json.loads(json.dumps(
        outcome, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ))
    report_id = digest(outcome)
    before_external()
    store.put_json("cloud-report", report_id, outcome)
    if store.get_json("cloud-report", report_id) != outcome:
        raise CloudLoopReviewRequired("REPORT_READBACK_MISMATCH")
    before_external()
    store.put_json_if_absent("cloud-result", slot, {
        "slot_id": slot, "report_id": report_id,
        "previous_slot": previous_slot, "state": "COMMITTED",
    })
    if committed_report(store, slot) != outcome:
        raise CloudLoopReviewRequired("RESULT_READBACK_MISMATCH")
    return outcome
