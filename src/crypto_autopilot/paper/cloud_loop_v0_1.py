"""Persistent cloud-loop composition; no scheduler or provider is started here."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence

from crypto_autopilot.paper.cloud_genesis_v0_1 import initialize_cloud_paper_state
from crypto_autopilot.paper.live_v0_1 import LivePaperMarketFeed, verify_live_paper_state
from crypto_autopilot.exchanges.pionex_public import PionexPublicClient
from crypto_autopilot.paper.live_v0_1 import LivePaperMarketFrame, LivePaperPolicy
from crypto_autopilot.paper.run_claim_v0_1 import LivePaperRunClaimPolicy
from crypto_autopilot.paper.run_coordinator_v0_3 import (
    LivePaperRunCoordinatorPolicy, PaperRunStoreLike,
    coordinate_live_paper_run_step, read_live_paper_run_step_tick,
)

SLOT_MS = 900_000
SLOT_OFFSET_MS = 420_000
MAXIMUM_START_DELAY_MS = 600_000


class CloudLoopReviewRequired(ValueError):
    """A stable reason code; never includes provider errors or secret values."""




class CompleteTapePionexFeed:
    """Fail-closed paper feed requiring the complete recent-trade window.

    The provider endpoint returns at most 500 recent records. A saturated page
    or a first returned trade later than the prior lifecycle time cannot prove
    continuity and cannot safely advance an open paper position.
    """
    def __init__(self, *, client: PionexPublicClient,
                 policy: LivePaperPolicy,
                 before_request: Callable[[], None]) -> None:
        self.client = client
        self.policy = policy
        self.before_request = before_request

    def fetch_frame(self, symbol: str, *, tick_time_ms: int,
                    since_ms: int) -> LivePaperMarketFrame:
        if tick_time_ms <= since_ms:
            raise CloudLoopReviewRequired("INVALID_MARKET_FRAME_WINDOW")
        self.before_request()
        book = self.client.get_order_book(symbol, limit=self.policy.order_book_depth_limit)
        self.before_request()
        trades = self.client.get_recent_trades(symbol, limit=500)
        if not trades:
            raise CloudLoopReviewRequired("TRADE_TAPE_EMPTY_UNPROVEN")
        if len(trades) >= 500:
            raise CloudLoopReviewRequired("TRADE_TAPE_PAGE_SATURATED")
        if any(t.symbol != symbol or not t.trade_id or t.price <= 0
               or t.time_ms <= 0 or t.time_ms > tick_time_ms for t in trades):
            raise CloudLoopReviewRequired("TRADE_TAPE_INVALID")
        if len({t.trade_id for t in trades}) != len(trades):
            raise CloudLoopReviewRequired("TRADE_TAPE_DUPLICATE")
        causal = [t for t in trades if since_ms < t.time_ms <= tick_time_ms]
        if min(t.time_ms for t in trades) > since_ms:
            raise CloudLoopReviewRequired("TRADE_TAPE_GAP_UNPROVEN")
        if not book.bids or not book.asks:
            raise CloudLoopReviewRequired("EMPTY_ORDER_BOOK")
        bid, ask = max(book.bids, key=lambda x: x[0]), min(book.asks, key=lambda x: x[0])
        if (bid[0] <= 0 or ask[0] < bid[0] or ask[0] <= 0
            or book.update_time_ms <= 0 or book.update_time_ms > tick_time_ms
            or tick_time_ms - book.update_time_ms > self.policy.maximum_source_age_ms):
            raise CloudLoopReviewRequired("ORDER_BOOK_INVALID_OR_STALE")
        midpoint = (bid[0] + ask[0]) / 2.0
        prices = [bid[0], ask[0], midpoint] + [trade.price for trade in causal]
        return LivePaperMarketFrame(
            provider="PIONEX_PUBLIC", symbol=symbol, time_ms=tick_time_ms,
            source_time_ms=max([book.update_time_ms] + [t.time_ms for t in causal]),
            open=causal[0].price if causal else ask[0],
            high=max(prices), low=min(prices),
            close=causal[-1].price if causal else midpoint,
            mark_price=midpoint,
            available_notional_usd=sum(p*q for p,q in book.asks if p > 0 and q > 0),
            provider_request_count=2, source_trade_count=len(causal),
        )

def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def slot_id(tick_ms: int) -> str:
    if type(tick_ms) is not int or tick_ms < SLOT_OFFSET_MS:
        raise CloudLoopReviewRequired("INVALID_TICK")
    if tick_ms % SLOT_MS != SLOT_OFFSET_MS:
        raise CloudLoopReviewRequired("OFF_SCHEDULE_TICK")
    return str((tick_ms - SLOT_OFFSET_MS) // SLOT_MS)


def validate_slot_start(*, scheduled_at_ms: int, started_at_ms: int) -> str:
    """Bind a real start to one canonical slot without rounding or backfill."""
    slot = slot_id(scheduled_at_ms)
    if type(started_at_ms) is not int or started_at_ms < scheduled_at_ms:
        raise CloudLoopReviewRequired("INVALID_SLOT_START")
    if started_at_ms - scheduled_at_ms > MAXIMUM_START_DELAY_MS:
        raise CloudLoopReviewRequired("STALE_SLOT_START")
    return slot


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
    elif schema == "qookey-cloud-paper-loop-report-v0.2":
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
    if schema == "qookey-cloud-paper-loop-report-v0.2" and coordinator.get("step_id") != step_id:
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


def decision_reason_codes(
    *, market: Mapping[str, object], registrations: Sequence[object],
    candidates: Sequence[object],
) -> tuple[str, ...]:
    """Summarize why a slot did or did not produce eligible paper candidates."""
    reasons: list[str] = []
    if market.get("market_status") == "REVIEW_REQUIRED":
        reasons.append("MARKET_INPUT_REVIEW_REQUIRED")
    context_status = market.get("context_status")
    if context_status != "AVAILABLE":
        reasons.append(
            "REGIME_UNAVAILABLE"
            if context_status == "REGIME_UNAVAILABLE"
            else "MARKET_CONTEXT_UNAVAILABLE"
        )
    if market.get("execution_selection_status") == "REVIEW_REQUIRED":
        reasons.append("CANDIDATE_SELECTION_REVIEW_REQUIRED")
    selection_reasons = market.get("execution_selection_reasons")
    if isinstance(selection_reasons, Sequence) and not isinstance(selection_reasons, str):
        reasons.extend(
            item for item in selection_reasons
            if isinstance(item, str) and item
        )
    if candidates:
        reasons.append("QUALIFIED_CANDIDATES")
    elif not registrations:
        reasons.append("NO_ELIGIBLE_STRATEGY")
    else:
        reasons.append("NO_QUALIFIED_CANDIDATE")
    return tuple(dict.fromkeys(reasons))


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
        policy=LivePaperRunCoordinatorPolicy(
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
