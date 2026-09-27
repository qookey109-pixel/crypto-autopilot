"""Persistent cloud-loop composition; no scheduler or provider is started here."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence

from crypto_autopilot.paper.cloud_genesis_v0_1 import initialize_cloud_paper_state
from crypto_autopilot.paper.live_v0_1 import LivePaperMarketFeed, verify_live_paper_state
from crypto_autopilot.exchanges.pionex_public import PionexPublicClient
from crypto_autopilot.features.market import OrderBookSnapshot, PublicTrade
from crypto_autopilot.paper.live_v0_1 import LivePaperMarketFrame, LivePaperPolicy
from crypto_autopilot.paper.run_claim_v0_1 import LivePaperRunClaimPolicy
from crypto_autopilot.paper.run_coordinator_v0_1 import (
    LivePaperRunCoordinatorPolicy, PaperRunStoreLike,
    coordinate_live_paper_run_step, verify_live_paper_run_step,
)

SLOT_MS = 900_000
SLOT_OFFSET_MS = 420_000


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
        if len(trades) >= 500:
            raise CloudLoopReviewRequired("TRADE_TAPE_PAGE_SATURATED")
        if any(t.symbol != symbol or not t.trade_id or t.price <= 0
               or t.time_ms <= 0 or t.time_ms > tick_time_ms for t in trades):
            raise CloudLoopReviewRequired("TRADE_TAPE_INVALID")
        if len({t.trade_id for t in trades}) != len(trades):
            raise CloudLoopReviewRequired("TRADE_TAPE_DUPLICATE")
        causal = [t for t in trades if since_ms < t.time_ms <= tick_time_ms]
        if trades and min(t.time_ms for t in trades) > since_ms:
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


def committed_report(store: PaperRunStoreLike, slot: str) -> dict[str, object] | None:
    result = store.get_json("cloud-result", slot)
    if result is None:
        return None
    report = store.get_json("cloud-report", str(result.get("report_id", "")))
    if report is None or digest(report) != result.get("report_id"):
        raise CloudLoopReviewRequired("RESULT_REPORT_MISMATCH")
    if report.get("slot_id") != slot:
        raise CloudLoopReviewRequired("RESULT_SLOT_MISMATCH")
    coordinator = report.get("coordinator")
    if not isinstance(coordinator, Mapping):
        raise CloudLoopReviewRequired("RESULT_COORDINATOR_MISSING")
    step = coordinator.get("run_step")
    if not isinstance(step, Mapping):
        raise CloudLoopReviewRequired("RESULT_STEP_MISSING")
    verified = verify_live_paper_run_step(step)
    persisted = store.get_json("live-run-step", verified)
    state = store.get_json("live-state", str(step["next_state_id"]))
    if persisted != step or state is None or verify_live_paper_state(state) != step["next_state_id"]:
        raise CloudLoopReviewRequired("RESULT_PERSISTENCE_MISMATCH")
    seal = store.get_json("live-run-result", str(step["request_id"]))
    if seal is None or seal.get("step_id") != verified:
        raise CloudLoopReviewRequired("COORDINATOR_SEAL_MISSING")
    return report


def run_cloud_step(
    *, tick_ms: int, previous_slot: str | None, store: PaperRunStoreLike,
    feed: LivePaperMarketFeed, market_supplier: Callable[[], Mapping[str, object]],
    candidate_supplier: Callable[[Mapping[str, object], Mapping[str, object]], Sequence[object]],
    strategy_registry: Mapping[str, object],
    before_external: Callable[[], None],
    run_name: str = "cloud-paper-v0-1",
) -> dict[str, object]:
    """One claimed slot, with exact prior-result chaining and immutable readback.

    Caller must discover the verified prior slot from the complete append-only
    ledger, enforce budget/activation and use a continuity-checking public feed.
    The callbacks also allow cloud CI to exercise the full positive path without
    putting test strategy evidence in a production registry.
    """
    slot = slot_id(tick_ms)
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
    previous = None
    if previous_slot is not None:
        if not previous_slot.isdigit() or int(previous_slot) >= int(slot):
            raise CloudLoopReviewRequired("INVALID_PREVIOUS_SLOT")
        old = committed_report(store, previous_slot)
        if old is None:
            raise CloudLoopReviewRequired("PREVIOUS_RESULT_MISSING")
        previous = old["coordinator"]["run_step"]
    state = (initialize_cloud_paper_state() if previous is None
             else previous["tick_report"]["next_state"])
    verify_live_paper_state(state)
    before_external()
    store.put_json_if_absent("cloud-slot", slot, {
        "slot_id": slot, "tick_ms": tick_ms, "previous_slot": previous_slot,
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
    if any(not isinstance(item, Mapping)
           or item.get("strategy_id") not in allowed_ids
           for item in candidates):
        raise CloudLoopReviewRequired("UNREGISTERED_STRATEGY_CANDIDATE")
    if len(candidates) > 5:
        raise CloudLoopReviewRequired("TOO_MANY_CANDIDATES")
    report = coordinate_live_paper_run_step(
        run_name=run_name, tick_time_ms=tick_ms, candidate_specs=candidates,
        feed=feed, store=store,
        initial_state=state if previous is None else None,
        previous_step=previous,
        policy=LivePaperRunCoordinatorPolicy(run_slot_claim_required=True),
        claim_policy=LivePaperRunClaimPolicy(),
    )
    next_state = report["run_step"]["tick_report"]["next_state"]
    checkpoint = next_state["checkpoint_report"]
    outcome = {
        "schema": "qookey-cloud-paper-loop-report-v0.1",
        "state": "COMMITTED" if candidates or state["active_session"] else "NO_TRADE",
        "slot_id": slot, "previous_slot": previous_slot, "tick_ms": tick_ms,
        "market": market, "candidate_count": len(candidates),
        "coordinator": report,
        "operation_counts": {
            "provider_requests": market_requests + int(report.get("provider_requests_performed", 0)),
            "r2_write_attempts": int(report.get("persistent_objects_created", 0)) + 3,
            "r2_write_replays": 0,
            "status": "KNOWN",
        },
        "account": checkpoint["account_snapshot"],
        "reason": ("NO_ELIGIBLE_STRATEGY" if not candidates else "QUALIFIED_CANDIDATES"),
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
