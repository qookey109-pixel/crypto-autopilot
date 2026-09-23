from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, cast

from crypto_autopilot.paper.execution_v0_1 import (
    PaperExecutionDecision,
    PaperExecutionIntent,
    PaperExecutionReceipt,
)


@dataclass(frozen=True, slots=True)
class PaperLifecyclePolicy:
    """Deterministic paper fill/lifecycle policy over normalized market bars."""

    taker_fee_bps: float = 5.0
    entry_slippage_bps: float = 2.0
    exit_slippage_bps: float = 2.0
    maximum_bar_participation_fraction: float = 0.05
    maximum_entry_bars: int = 3
    conservative_same_bar_exit: bool = True
    cancel_if_stop_invalidated_before_first_fill: bool = True
    cancel_if_target_crossed_before_first_fill: bool = True
    close_at_end_of_data: bool = False

    def __post_init__(self) -> None:
        numeric = (
            self.taker_fee_bps,
            self.entry_slippage_bps,
            self.exit_slippage_bps,
            self.maximum_bar_participation_fraction,
        )
        if any(isinstance(value, bool) for value in numeric):
            raise ValueError("paper lifecycle numeric policy values cannot be booleans")
        if not all(math.isfinite(value) for value in numeric):
            raise ValueError("paper lifecycle numeric policy values must be finite")
        if self.taker_fee_bps < 0.0:
            raise ValueError("taker_fee_bps cannot be negative")
        if self.entry_slippage_bps < 0.0 or self.exit_slippage_bps < 0.0:
            raise ValueError("slippage bps cannot be negative")
        if not 0.0 < self.maximum_bar_participation_fraction <= 1.0:
            raise ValueError(
                "maximum_bar_participation_fraction must be in (0, 1]"
            )
        if not isinstance(self.maximum_entry_bars, int) or isinstance(
            self.maximum_entry_bars, bool
        ):
            raise ValueError("maximum_entry_bars must be an integer")
        if self.maximum_entry_bars < 1:
            raise ValueError("maximum_entry_bars must be positive")
        flags = (
            self.conservative_same_bar_exit,
            self.cancel_if_stop_invalidated_before_first_fill,
            self.cancel_if_target_crossed_before_first_fill,
            self.close_at_end_of_data,
        )
        if any(not isinstance(value, bool) for value in flags):
            raise ValueError("paper lifecycle policy flags must be booleans")


@dataclass(frozen=True, slots=True)
class PaperLiquidityBar:
    """Normalized OHLC + executable paper-liquidity budget.

    available_notional_usd is supplied explicitly. V0.1 does not infer USD
    liquidity from provider volume units.
    """

    time_ms: int
    open: float
    high: float
    low: float
    close: float
    available_notional_usd: float

    def __post_init__(self) -> None:
        if not isinstance(self.time_ms, int) or isinstance(self.time_ms, bool):
            raise ValueError("bar time_ms must be an integer")
        if self.time_ms < 0:
            raise ValueError("bar time_ms cannot be negative")
        values = (
            self.open,
            self.high,
            self.low,
            self.close,
            self.available_notional_usd,
        )
        if any(isinstance(value, bool) for value in values):
            raise ValueError("paper lifecycle bar values cannot be booleans")
        if not all(math.isfinite(value) for value in values):
            raise ValueError("paper lifecycle bar values must be finite")
        if min(self.open, self.high, self.low, self.close) <= 0.0:
            raise ValueError("paper lifecycle OHLC must be positive")
        if self.available_notional_usd < 0.0:
            raise ValueError("available_notional_usd cannot be negative")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("paper lifecycle bar low is invalid")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("paper lifecycle bar high is invalid")


@dataclass(frozen=True, slots=True)
class PaperLifecycleEvent:
    sequence: int
    time_ms: int
    kind: str
    details: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class PaperFill:
    time_ms: int
    raw_price: float
    fill_price: float
    notional_usd: float
    quantity: float
    fee_usd: float


@dataclass(frozen=True, slots=True)
class PaperLifecyclePlan:
    lifecycle_id: str
    intent_id: str
    symbol: str
    side: str
    as_of_ms: int
    requested_notional_usd: float
    stop_price: float
    target_price: float


@dataclass(frozen=True, slots=True)
class PaperLifecycleResult:
    lifecycle_id: str
    intent_id: str
    symbol: str
    side: str
    status: str
    reason: str
    requested_notional_usd: float
    filled_notional_usd: float
    unfilled_notional_usd: float
    fill_fraction: float
    average_entry_price: float | None
    total_quantity: float
    entry_fees_usd: float
    exit_time_ms: int | None
    raw_exit_price: float | None
    exit_price: float | None
    exit_fee_usd: float
    gross_pnl_usd: float | None
    net_pnl_usd: float | None
    fills: tuple[PaperFill, ...]
    events: tuple[PaperLifecycleEvent, ...]


def _sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(
        dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_paper_lifecycle_plan(
    *,
    decision: PaperExecutionDecision,
    receipt: PaperExecutionReceipt,
    target_price: float,
) -> PaperLifecyclePlan:
    """Bind an accepted Repository Paper Broker receipt to lifecycle simulation."""

    if decision.status != "READY_FOR_PAPER_BROKER" or decision.intent is None:
        raise ValueError("paper execution decision is not ready")
    intent = decision.intent
    if receipt.status != "PAPER_ACCEPTED":
        raise ValueError("paper execution receipt is not accepted")
    if intent.status != "READY_FOR_PAPER_BROKER":
        raise ValueError("paper execution intent is not ready")
    if intent.as_of_ms < 0:
        raise ValueError("paper execution intent as_of_ms cannot be negative")
    numeric_intent = (
        intent.entry_price,
        intent.stop_price,
        intent.notional_usd,
        intent.target_risk_usd,
        intent.realized_risk_usd,
        intent.risk_utilization_fraction,
    )
    if not all(math.isfinite(value) for value in numeric_intent):
        raise ValueError("paper execution intent numeric fields must be finite")
    if intent.entry_price <= 0.0 or intent.stop_price <= 0.0 or intent.notional_usd <= 0.0:
        raise ValueError("paper execution intent price/notional values must be positive")
    if receipt.intent_id != intent.intent_id or receipt.order_id != intent.intent_id:
        raise ValueError("paper receipt does not match execution intent")
    if receipt.symbol != intent.symbol or receipt.side != intent.direction:
        raise ValueError("paper receipt symbol/side does not match execution intent")
    if not math.isclose(
        receipt.notional_usd,
        intent.notional_usd,
        rel_tol=0.0,
        abs_tol=1e-8,
    ):
        raise ValueError("paper receipt notional does not match execution intent")
    if intent.direction != "LONG":
        raise ValueError("Paper Lifecycle V0.1 supports LONG paper intents only")
    if not math.isfinite(target_price) or target_price <= 0.0:
        raise ValueError("target_price must be finite and positive")
    if not intent.stop_price < intent.entry_price < target_price:
        raise ValueError("LONG lifecycle geometry must be stop < entry < target")

    payload: dict[str, object] = {
        "schema": "qookey-paper-lifecycle-plan-v0.1",
        "intent_id": intent.intent_id,
        "symbol": intent.symbol,
        "side": intent.direction,
        "as_of_ms": intent.as_of_ms,
        "requested_notional_usd": intent.notional_usd,
        "stop_price": intent.stop_price,
        "target_price": target_price,
    }
    return PaperLifecyclePlan(
        lifecycle_id=f"paper-life-v0-1-{_sha256(payload)}",
        intent_id=intent.intent_id,
        symbol=intent.symbol,
        side=intent.direction,
        as_of_ms=intent.as_of_ms,
        requested_notional_usd=intent.notional_usd,
        stop_price=intent.stop_price,
        target_price=target_price,
    )


def _adverse_long_entry(raw_price: float, bps: float) -> float:
    return raw_price * (1.0 + bps / 10_000.0)


def _adverse_long_exit(raw_price: float, bps: float) -> float:
    return raw_price * (1.0 - bps / 10_000.0)


def _exit_reason_for_long(
    bar: PaperLiquidityBar,
    *,
    stop_price: float,
    target_price: float,
    conservative_same_bar_exit: bool,
) -> tuple[float, str] | None:
    if bar.open <= stop_price:
        return bar.open, "STOP_GAP"
    if bar.open >= target_price:
        return target_price, "TARGET_GAP"

    stop_hit = bar.low <= stop_price
    target_hit = bar.high >= target_price
    if stop_hit and target_hit:
        if conservative_same_bar_exit:
            return stop_price, "STOP_SAME_BAR_COLLISION"
        return target_price, "TARGET_SAME_BAR_COLLISION"
    if stop_hit:
        return stop_price, "STOP"
    if target_hit:
        return target_price, "TARGET"
    return None


def simulate_paper_lifecycle(
    *,
    plan: PaperLifecyclePlan,
    bars: Sequence[PaperLiquidityBar],
    policy: PaperLifecyclePolicy = PaperLifecyclePolicy(),
) -> PaperLifecycleResult:
    """Simulate causal paper fills and LONG stop/target lifecycle.

    Only bars strictly later than plan.as_of_ms may participate.
    """

    ordered = tuple(bars)
    if any(
        ordered[index].time_ms >= ordered[index + 1].time_ms
        for index in range(len(ordered) - 1)
    ):
        raise ValueError("paper lifecycle bars must be strictly increasing")

    future = tuple(bar for bar in ordered if bar.time_ms > plan.as_of_ms)
    events: list[PaperLifecycleEvent] = []
    fills: list[PaperFill] = []
    sequence = 0

    def emit(time_ms: int, kind: str, **details: object) -> None:
        nonlocal sequence
        sequence += 1
        events.append(
            PaperLifecycleEvent(
                sequence=sequence,
                time_ms=time_ms,
                kind=kind,
                details=tuple(
                    sorted((key, str(value)) for key, value in details.items())
                ),
            )
        )

    emit(plan.as_of_ms, "ORDER_ACCEPTED", notional_usd=plan.requested_notional_usd)

    if not future:
        emit(plan.as_of_ms, "ORDER_CANCELLED", reason="no_future_market_bar")
        return _result(
            plan=plan,
            status="CANCELLED_UNFILLED",
            reason="no_future_market_bar",
            fills=fills,
            events=events,
        )

    remaining = plan.requested_notional_usd
    total_quantity = 0.0
    filled_notional = 0.0
    entry_fees = 0.0
    entry_bars_seen = 0
    entry_complete = False

    for bar in future:
        has_position = total_quantity > 0.0

        if not has_position and entry_bars_seen < policy.maximum_entry_bars:
            if (
                policy.cancel_if_stop_invalidated_before_first_fill
                and bar.open <= plan.stop_price
            ):
                emit(
                    bar.time_ms,
                    "ORDER_CANCELLED",
                    reason="stop_invalidated_before_first_fill",
                )
                return _result(
                    plan=plan,
                    status="CANCELLED_UNFILLED",
                    reason="stop_invalidated_before_first_fill",
                    fills=fills,
                    events=events,
                )
            if (
                policy.cancel_if_target_crossed_before_first_fill
                and bar.open >= plan.target_price
            ):
                emit(
                    bar.time_ms,
                    "ORDER_CANCELLED",
                    reason="target_crossed_before_first_fill",
                )
                return _result(
                    plan=plan,
                    status="CANCELLED_UNFILLED",
                    reason="target_crossed_before_first_fill",
                    fills=fills,
                    events=events,
                )

        if not entry_complete and entry_bars_seen < policy.maximum_entry_bars:
            entry_bars_seen += 1

            if total_quantity > 0.0:
                prefill_exit = _exit_reason_for_long(
                    bar,
                    stop_price=plan.stop_price,
                    target_price=plan.target_price,
                    conservative_same_bar_exit=policy.conservative_same_bar_exit,
                )
                if prefill_exit is not None and (
                    bar.open <= plan.stop_price or bar.open >= plan.target_price
                ):
                    raw_exit, reason = prefill_exit
                    emit(
                        bar.time_ms,
                        "UNFILLED_REMAINDER_CANCELLED",
                        notional_usd=remaining,
                        reason="position_exited_before_additional_fill",
                    )
                    return _closed_result(
                        plan=plan,
                        fills=fills,
                        events=events,
                        time_ms=bar.time_ms,
                        raw_exit_price=raw_exit,
                        exit_reason=reason,
                        policy=policy,
                    )

            fill_capacity = (
                bar.available_notional_usd
                * policy.maximum_bar_participation_fraction
            )
            fill_notional = min(remaining, fill_capacity)
            if fill_notional > 0.0:
                fill_price = _adverse_long_entry(
                    bar.open, policy.entry_slippage_bps
                )
                if fill_price >= plan.target_price:
                    if total_quantity <= 0.0:
                        emit(
                            bar.time_ms,
                            "ORDER_CANCELLED",
                            reason="target_not_above_executable_entry",
                        )
                        return _result(
                            plan=plan,
                            status="CANCELLED_UNFILLED",
                            reason="target_not_above_executable_entry",
                            fills=fills,
                            events=events,
                        )
                    emit(
                        bar.time_ms,
                        "ENTRY_NO_FILL",
                        reason="target_not_above_executable_entry",
                    )
                    fill_notional = 0.0
                if fill_notional <= 0.0:
                    exit_hit = _exit_reason_for_long(
                        bar,
                        stop_price=plan.stop_price,
                        target_price=plan.target_price,
                        conservative_same_bar_exit=policy.conservative_same_bar_exit,
                    )
                    if exit_hit is not None:
                        raw_exit, reason = exit_hit
                        emit(
                            bar.time_ms,
                            "UNFILLED_REMAINDER_CANCELLED",
                            notional_usd=round(remaining, 8),
                            reason="position_exited_during_entry_window",
                        )
                        return _closed_result(
                            plan=plan,
                            fills=fills,
                            events=events,
                            time_ms=bar.time_ms,
                            raw_exit_price=raw_exit,
                            exit_reason=reason,
                            policy=policy,
                        )
                    emit(
                        bar.time_ms,
                        "UNFILLED_REMAINDER_CANCELLED",
                        notional_usd=round(remaining, 8),
                        reason="target_not_above_executable_entry",
                    )
                    entry_complete = True
                    continue
                quantity = fill_notional / fill_price
                fee = fill_notional * policy.taker_fee_bps / 10_000.0
                fill = PaperFill(
                    time_ms=bar.time_ms,
                    raw_price=round(bar.open, 8),
                    fill_price=round(fill_price, 8),
                    notional_usd=round(fill_notional, 8),
                    quantity=round(quantity, 12),
                    fee_usd=round(fee, 8),
                )
                fills.append(fill)
                remaining = max(0.0, remaining - fill_notional)
                filled_notional += fill_notional
                total_quantity += quantity
                entry_fees += fee
                emit(
                    bar.time_ms,
                    "ENTRY_FILL",
                    fill_notional_usd=round(fill_notional, 8),
                    fill_price=round(fill_price, 8),
                    remaining_notional_usd=round(remaining, 8),
                )
            else:
                emit(bar.time_ms, "ENTRY_NO_FILL", reason="zero_liquidity_capacity")

            if remaining <= 1e-8:
                remaining = 0.0
                entry_complete = True
                emit(bar.time_ms, "ENTRY_FILLED")

            if total_quantity > 0.0:
                exit_hit = _exit_reason_for_long(
                    bar,
                    stop_price=plan.stop_price,
                    target_price=plan.target_price,
                    conservative_same_bar_exit=policy.conservative_same_bar_exit,
                )
                if exit_hit is not None:
                    raw_exit, reason = exit_hit
                    if remaining > 0.0:
                        emit(
                            bar.time_ms,
                            "UNFILLED_REMAINDER_CANCELLED",
                            notional_usd=round(remaining, 8),
                            reason="position_exited_during_entry_window",
                        )
                    return _closed_result(
                        plan=plan,
                        fills=fills,
                        events=events,
                        time_ms=bar.time_ms,
                        raw_exit_price=raw_exit,
                        exit_reason=reason,
                        policy=policy,
                    )

            if (
                not entry_complete
                and entry_bars_seen >= policy.maximum_entry_bars
            ):
                emit(
                    bar.time_ms,
                    "UNFILLED_REMAINDER_CANCELLED",
                    notional_usd=round(remaining, 8),
                    reason="entry_window_expired",
                )
                entry_complete = True
                if total_quantity <= 0.0:
                    return _result(
                        plan=plan,
                        status="CANCELLED_UNFILLED",
                        reason="entry_window_expired",
                        fills=fills,
                        events=events,
                    )
                emit(
                    bar.time_ms,
                    "POSITION_OPEN_PARTIAL",
                    filled_notional_usd=round(filled_notional, 8),
                )
            continue

        if total_quantity > 0.0:
            exit_hit = _exit_reason_for_long(
                bar,
                stop_price=plan.stop_price,
                target_price=plan.target_price,
                conservative_same_bar_exit=policy.conservative_same_bar_exit,
            )
            if exit_hit is not None:
                raw_exit, reason = exit_hit
                return _closed_result(
                    plan=plan,
                    fills=fills,
                    events=events,
                    time_ms=bar.time_ms,
                    raw_exit_price=raw_exit,
                    exit_reason=reason,
                    policy=policy,
                )

    if total_quantity <= 0.0:
        return _result(
            plan=plan,
            status="CANCELLED_UNFILLED",
            reason="entry_window_expired",
            fills=fills,
            events=events,
        )

    if policy.close_at_end_of_data:
        last = future[-1]
        return _closed_result(
            plan=plan,
            fills=fills,
            events=events,
            time_ms=last.time_ms,
            raw_exit_price=last.close,
            exit_reason="END_OF_DATA",
            policy=policy,
        )

    emit(
        future[-1].time_ms,
        "POSITION_REMAINS_OPEN",
        filled_notional_usd=round(filled_notional, 8),
    )
    return _result(
        plan=plan,
        status="OPEN_POSITION",
        reason="no_exit_before_end_of_data",
        fills=fills,
        events=events,
    )


def _entry_stats(
    fills: Sequence[PaperFill],
) -> tuple[float, float, float, float | None]:
    filled_notional = sum(item.notional_usd for item in fills)
    total_quantity = sum(item.quantity for item in fills)
    entry_fees = sum(item.fee_usd for item in fills)
    average_entry = (
        None if total_quantity <= 0.0 else filled_notional / total_quantity
    )
    return filled_notional, total_quantity, entry_fees, average_entry


def _closed_result(
    *,
    plan: PaperLifecyclePlan,
    fills: Sequence[PaperFill],
    events: list[PaperLifecycleEvent],
    time_ms: int,
    raw_exit_price: float,
    exit_reason: str,
    policy: PaperLifecyclePolicy,
) -> PaperLifecycleResult:
    filled_notional, total_quantity, entry_fees, average_entry = _entry_stats(fills)
    if total_quantity <= 0.0 or average_entry is None:
        raise ValueError("cannot close a paper lifecycle with zero filled quantity")

    exit_price = _adverse_long_exit(raw_exit_price, policy.exit_slippage_bps)
    exit_notional = total_quantity * exit_price
    exit_fee = exit_notional * policy.taker_fee_bps / 10_000.0
    gross_pnl = (exit_price - average_entry) * total_quantity
    net_pnl = gross_pnl - entry_fees - exit_fee

    sequence = len(events) + 1
    events.append(
        PaperLifecycleEvent(
            sequence=sequence,
            time_ms=time_ms,
            kind="POSITION_CLOSED",
            details=tuple(
                sorted(
                    (
                        ("exit_price", str(round(exit_price, 8))),
                        ("reason", exit_reason),
                    )
                )
            ),
        )
    )

    return PaperLifecycleResult(
        lifecycle_id=plan.lifecycle_id,
        intent_id=plan.intent_id,
        symbol=plan.symbol,
        side=plan.side,
        status="CLOSED",
        reason=exit_reason,
        requested_notional_usd=round(plan.requested_notional_usd, 8),
        filled_notional_usd=round(filled_notional, 8),
        unfilled_notional_usd=round(
            max(0.0, plan.requested_notional_usd - filled_notional), 8
        ),
        fill_fraction=round(filled_notional / plan.requested_notional_usd, 8),
        average_entry_price=round(average_entry, 8),
        total_quantity=round(total_quantity, 12),
        entry_fees_usd=round(entry_fees, 8),
        exit_time_ms=time_ms,
        raw_exit_price=round(raw_exit_price, 8),
        exit_price=round(exit_price, 8),
        exit_fee_usd=round(exit_fee, 8),
        gross_pnl_usd=round(gross_pnl, 8),
        net_pnl_usd=round(net_pnl, 8),
        fills=tuple(fills),
        events=tuple(events),
    )


def _result(
    *,
    plan: PaperLifecyclePlan,
    status: str,
    reason: str,
    fills: Sequence[PaperFill],
    events: Sequence[PaperLifecycleEvent],
) -> PaperLifecycleResult:
    filled_notional, total_quantity, entry_fees, average_entry = _entry_stats(fills)
    return PaperLifecycleResult(
        lifecycle_id=plan.lifecycle_id,
        intent_id=plan.intent_id,
        symbol=plan.symbol,
        side=plan.side,
        status=status,
        reason=reason,
        requested_notional_usd=round(plan.requested_notional_usd, 8),
        filled_notional_usd=round(filled_notional, 8),
        unfilled_notional_usd=round(
            max(0.0, plan.requested_notional_usd - filled_notional), 8
        ),
        fill_fraction=round(
            filled_notional / plan.requested_notional_usd
            if plan.requested_notional_usd > 0.0
            else 0.0,
            8,
        ),
        average_entry_price=(
            None if average_entry is None else round(average_entry, 8)
        ),
        total_quantity=round(total_quantity, 12),
        entry_fees_usd=round(entry_fees, 8),
        exit_time_ms=None,
        raw_exit_price=None,
        exit_price=None,
        exit_fee_usd=0.0,
        gross_pnl_usd=None,
        net_pnl_usd=None,
        fills=tuple(fills),
        events=tuple(events),
    )


def lifecycle_evidence(
    *,
    plan: PaperLifecyclePlan,
    result: PaperLifecycleResult,
    policy: PaperLifecyclePolicy,
) -> dict[str, object]:
    return {
        "schema": "qookey-paper-fill-lifecycle-report-v0.1",
        "plan": asdict(plan),
        "result": asdict(result),
        "policy": asdict(policy),
        "authority": {
            "paper_simulation_only": True,
            "provider_requests_performed": False,
            "r2_accessed": False,
            "holdout_accessed": False,
            "persistent_broker_state_written": False,
            "automatic_submission_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
        "limitations": [
            "available_notional_usd is normalized input, not inferred order-book depth.",
            "V0.1 models LONG paper lifecycle only.",
            "Funding, liquidation and exchange rejection are not modeled.",
            "Bar-level stop/target collisions use the configured deterministic policy.",
        ],
    }


def lifecycle_input_from_dict(
    payload: Mapping[str, object],
) -> tuple[
    PaperExecutionDecision,
    PaperExecutionReceipt,
    float,
    tuple[PaperLiquidityBar, ...],
]:
    if payload.get("schema") != "qookey-paper-fill-lifecycle-input-v0.1":
        raise ValueError("unsupported paper fill lifecycle input schema")
    execution = payload.get("paper_execution_evidence")
    if not isinstance(execution, Mapping):
        raise ValueError("paper_execution_evidence object is required")
    if execution.get("schema") != "qookey-paper-execution-evidence-v0.1":
        raise ValueError("unsupported paper execution evidence schema")

    execution_authority = execution.get("authority")
    if not isinstance(execution_authority, Mapping):
        raise ValueError("paper execution authority object is required")
    if execution_authority.get("repository_paper_broker_only") is not True:
        raise ValueError("paper execution evidence must be Repository Paper Broker only")
    for key in (
        "provider_requests_performed",
        "r2_accessed",
        "holdout_accessed",
    ):
        if execution_authority.get(key) is not False:
            raise ValueError(f"paper execution evidence must remain offline: {key}")
    for key in (
        "automatic_submission_authorized",
        "short_paper_execution_authorized",
        "formal_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if execution_authority.get(key) is not False:
            raise ValueError(f"paper execution authority must remain closed: {key}")

    decision_payload = execution.get("decision")
    receipt_payload = execution.get("receipt")
    if not isinstance(decision_payload, Mapping):
        raise ValueError("paper execution decision object is required")
    if not isinstance(receipt_payload, Mapping):
        raise ValueError("accepted paper execution receipt object is required")
    intent_payload = decision_payload.get("intent")
    if not isinstance(intent_payload, Mapping):
        raise ValueError("paper execution intent object is required")

    intent_numeric_keys = (
        "as_of_ms",
        "entry_price",
        "stop_price",
        "notional_usd",
        "target_risk_usd",
        "realized_risk_usd",
        "risk_utilization_fraction",
    )
    if any(isinstance(intent_payload.get(key), bool) for key in intent_numeric_keys):
        raise ValueError("paper execution intent numeric fields cannot be booleans")
    if not isinstance(intent_payload.get("as_of_ms"), int):
        raise ValueError("paper execution intent as_of_ms must be a JSON integer")
    if not isinstance(receipt_payload.get("replayed"), bool):
        raise ValueError("paper execution receipt replayed must be a JSON boolean")
    if isinstance(receipt_payload.get("notional_usd"), bool):
        raise ValueError("paper execution receipt notional cannot be boolean")

    try:
        intent = PaperExecutionIntent(
            intent_id=str(intent_payload["intent_id"]),
            symbol=str(intent_payload["symbol"]),
            strategy_family=str(intent_payload["strategy_family"]),
            family_validation_report_sha256=str(
                intent_payload["family_validation_report_sha256"]
            ),
            portfolio_proposal_id=str(intent_payload["portfolio_proposal_id"]),
            portfolio_admission_report_sha256=str(
                intent_payload["portfolio_admission_report_sha256"]
            ),
            direction=str(intent_payload["direction"]),
            as_of_ms=intent_payload["as_of_ms"],
            entry_price=float(intent_payload["entry_price"]),
            stop_price=float(intent_payload["stop_price"]),
            notional_usd=float(intent_payload["notional_usd"]),
            target_risk_usd=float(intent_payload["target_risk_usd"]),
            realized_risk_usd=float(intent_payload["realized_risk_usd"]),
            risk_utilization_fraction=float(
                intent_payload["risk_utilization_fraction"]
            ),
            status=str(
                intent_payload.get("status", "READY_FOR_PAPER_BROKER")
            ),
        )
        decision = PaperExecutionDecision(
            status=str(decision_payload["status"]),
            reason=str(decision_payload["reason"]),
            intent=intent,
        )
        receipt = PaperExecutionReceipt(
            status=str(receipt_payload["status"]),
            intent_id=str(receipt_payload["intent_id"]),
            order_id=str(receipt_payload["order_id"]),
            symbol=str(receipt_payload["symbol"]),
            side=str(receipt_payload["side"]),
            notional_usd=float(receipt_payload["notional_usd"]),
            broker_status=str(receipt_payload["broker_status"]),
            replayed=receipt_payload["replayed"],
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"invalid paper execution evidence: {error}") from error

    if isinstance(payload.get("target_price"), bool):
        raise ValueError("target_price cannot be boolean")
    try:
        target_price = float(cast(Any, payload["target_price"]))
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"invalid target_price: {error}") from error

    bar_items = payload.get("bars")
    if not isinstance(bar_items, list):
        raise ValueError("bars must be a JSON array")
    bars: list[PaperLiquidityBar] = []
    for index, item in enumerate(bar_items):
        if not isinstance(item, Mapping):
            raise ValueError(f"bars[{index}] must be a JSON object")
        if not isinstance(item.get("time_ms"), int) or isinstance(
            item.get("time_ms"), bool
        ):
            raise ValueError(f"bars[{index}].time_ms must be a JSON integer")
        numeric_keys = (
            "open",
            "high",
            "low",
            "close",
            "available_notional_usd",
        )
        if any(isinstance(item.get(key), bool) for key in numeric_keys):
            raise ValueError(f"bars[{index}] numeric fields cannot be booleans")
        try:
            bars.append(
                PaperLiquidityBar(
                    time_ms=item["time_ms"],
                    open=float(item["open"]),
                    high=float(item["high"]),
                    low=float(item["low"]),
                    close=float(item["close"]),
                    available_notional_usd=float(
                        item["available_notional_usd"]
                    ),
                )
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"invalid bars[{index}]: {error}") from error

    return decision, receipt, target_price, tuple(bars)


def lifecycle_policy_from_config(
    payload: Mapping[str, object],
) -> PaperLifecyclePolicy:
    if payload.get("schema") != "qookey-paper-fill-lifecycle-v0.1":
        raise ValueError("unsupported paper fill lifecycle config")
    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("policy object is required")

    numeric_keys = (
        "taker_fee_bps",
        "entry_slippage_bps",
        "exit_slippage_bps",
        "maximum_bar_participation_fraction",
        "maximum_entry_bars",
    )
    if any(isinstance(policy.get(key), bool) for key in numeric_keys):
        raise ValueError("paper lifecycle numeric policy fields cannot be booleans")
    if not isinstance(policy.get("maximum_entry_bars"), int):
        raise ValueError("policy.maximum_entry_bars must be a JSON integer")
    for key in (
        "conservative_same_bar_exit",
        "cancel_if_stop_invalidated_before_first_fill",
        "cancel_if_target_crossed_before_first_fill",
        "close_at_end_of_data",
    ):
        if not isinstance(policy.get(key), bool):
            raise ValueError(f"policy.{key} must be a JSON boolean")

    try:
        return PaperLifecyclePolicy(
            taker_fee_bps=float(policy["taker_fee_bps"]),
            entry_slippage_bps=float(policy["entry_slippage_bps"]),
            exit_slippage_bps=float(policy["exit_slippage_bps"]),
            maximum_bar_participation_fraction=float(
                policy["maximum_bar_participation_fraction"]
            ),
            maximum_entry_bars=policy["maximum_entry_bars"],
            conservative_same_bar_exit=policy["conservative_same_bar_exit"],
            cancel_if_stop_invalidated_before_first_fill=policy[
                "cancel_if_stop_invalidated_before_first_fill"
            ],
            cancel_if_target_crossed_before_first_fill=policy[
                "cancel_if_target_crossed_before_first_fill"
            ],
            close_at_end_of_data=policy["close_at_end_of_data"],
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"invalid paper lifecycle config: {error}") from error
