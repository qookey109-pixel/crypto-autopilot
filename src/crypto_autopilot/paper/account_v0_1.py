from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass

from crypto_autopilot.portfolio.admission_v0_1 import PortfolioExposure
from crypto_autopilot.strategy_library import get_strategy_family


@dataclass(frozen=True, slots=True)
class PaperAccountPolicy:
    """Deterministic paper-account materialization policy."""

    insolvency_equity_floor_usd: float = 0.0
    require_single_mark_timestamp: bool = True
    reject_mark_crossing_protective_boundary: bool = True
    export_portfolio_exposures: bool = True

    def __post_init__(self) -> None:
        if isinstance(self.insolvency_equity_floor_usd, bool):
            raise ValueError("insolvency_equity_floor_usd cannot be boolean")
        if not math.isfinite(self.insolvency_equity_floor_usd):
            raise ValueError("insolvency_equity_floor_usd must be finite")
        flags = (
            self.require_single_mark_timestamp,
            self.reject_mark_crossing_protective_boundary,
            self.export_portfolio_exposures,
        )
        if any(not isinstance(value, bool) for value in flags):
            raise ValueError("paper account policy flags must be booleans")


@dataclass(frozen=True, slots=True)
class PaperMark:
    symbol: str
    time_ms: int
    price: float

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("mark symbol is required")
        if not isinstance(self.time_ms, int) or isinstance(self.time_ms, bool):
            raise ValueError("mark time_ms must be an integer")
        if self.time_ms < 0:
            raise ValueError("mark time_ms cannot be negative")
        if isinstance(self.price, bool) or not math.isfinite(self.price):
            raise ValueError("mark price must be finite numeric")
        if self.price <= 0.0:
            raise ValueError("mark price must be positive")


@dataclass(frozen=True, slots=True)
class PaperOpenPosition:
    lifecycle_id: str
    intent_id: str
    symbol: str
    strategy_family: str
    side: str
    quantity: float
    average_entry_price: float
    mark_price: float
    mark_time_ms: int
    stop_price: float
    target_price: float
    entry_notional_usd: float
    mark_notional_usd: float
    entry_fees_usd: float
    unrealized_gross_pnl_usd: float
    portfolio_stop_risk_usd: float
    last_lifecycle_event_time_ms: int


@dataclass(frozen=True, slots=True)
class PaperAccountSnapshot:
    snapshot_id: str
    status: str
    as_of_ms: int
    initial_equity_usd: float
    cash_usd: float
    equity_usd: float
    realized_closed_net_pnl_usd: float
    open_entry_fees_usd: float
    unrealized_gross_pnl_usd: float
    open_position_count: int
    closed_position_count: int
    cancelled_order_count: int
    open_positions: tuple[PaperOpenPosition, ...]
    lifecycle_report_sha256s: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _NormalizedLifecycleRecord:
    lifecycle_id: str
    intent_id: str
    symbol: str
    strategy_family: str
    side: str
    lifecycle_status: str
    lifecycle_reason: str
    stop_price: float
    target_price: float
    filled_notional_usd: float
    average_entry_price: float | None
    total_quantity: float
    entry_fees_usd: float
    net_pnl_usd: float | None
    last_event_time_ms: int
    report_sha256: str


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


def _validate_paper_execution_evidence(
    payload: Mapping[str, object],
) -> Mapping[str, object]:
    if payload.get("schema") != "qookey-paper-execution-evidence-v0.1":
        raise ValueError("unsupported paper execution evidence schema")
    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("paper execution authority object is required")
    if authority.get("repository_paper_broker_only") is not True:
        raise ValueError("paper execution evidence must be Repository Paper Broker only")
    for key in (
        "provider_requests_performed",
        "r2_accessed",
        "holdout_accessed",
        "automatic_submission_authorized",
        "short_paper_execution_authorized",
        "formal_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"paper execution authority must remain closed: {key}")

    decision = payload.get("decision")
    receipt = payload.get("receipt")
    if not isinstance(decision, Mapping) or not isinstance(receipt, Mapping):
        raise ValueError("paper execution decision and receipt are required")
    if decision.get("status") != "READY_FOR_PAPER_BROKER":
        raise ValueError("paper execution decision is not ready")
    intent = decision.get("intent")
    if not isinstance(intent, Mapping):
        raise ValueError("paper execution intent object is required")
    if receipt.get("status") != "PAPER_ACCEPTED":
        raise ValueError("paper execution receipt is not accepted")

    intent_id = intent.get("intent_id")
    if not isinstance(intent_id, str) or not intent_id:
        raise ValueError("paper execution intent_id is required")
    if receipt.get("intent_id") != intent_id or receipt.get("order_id") != intent_id:
        raise ValueError("paper execution receipt does not match intent")
    if receipt.get("symbol") != intent.get("symbol") or receipt.get("side") != intent.get(
        "direction"
    ):
        raise ValueError("paper execution receipt symbol/side does not match intent")
    if not isinstance(receipt.get("replayed"), bool):
        raise ValueError("paper execution receipt replayed must be boolean")

    family = intent.get("strategy_family")
    if not isinstance(family, str):
        raise ValueError("paper execution strategy_family is required")
    get_strategy_family(family)
    if intent.get("direction") != "LONG":
        raise ValueError("Paper Account V0.1 supports LONG paper positions only")
    return intent


def _validate_lifecycle_evidence(
    payload: Mapping[str, object],
    intent: Mapping[str, object],
) -> _NormalizedLifecycleRecord:
    if payload.get("schema") != "qookey-paper-fill-lifecycle-report-v0.1":
        raise ValueError("unsupported paper lifecycle report schema")
    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("paper lifecycle authority object is required")
    if authority.get("paper_simulation_only") is not True:
        raise ValueError("paper lifecycle evidence must remain simulation-only")
    for key in (
        "provider_requests_performed",
        "r2_accessed",
        "holdout_accessed",
        "persistent_broker_state_written",
        "automatic_submission_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"paper lifecycle authority must remain closed: {key}")

    plan = payload.get("plan")
    result = payload.get("result")
    if not isinstance(plan, Mapping) or not isinstance(result, Mapping):
        raise ValueError("paper lifecycle plan and result are required")

    lifecycle_id = plan.get("lifecycle_id")
    intent_id = plan.get("intent_id")
    if not isinstance(lifecycle_id, str) or not lifecycle_id:
        raise ValueError("lifecycle_id is required")
    if not isinstance(intent_id, str) or intent_id != intent.get("intent_id"):
        raise ValueError("lifecycle intent_id does not match paper execution intent")
    if result.get("lifecycle_id") != lifecycle_id or result.get("intent_id") != intent_id:
        raise ValueError("lifecycle result lineage does not match plan")
    if plan.get("symbol") != intent.get("symbol") or result.get("symbol") != intent.get(
        "symbol"
    ):
        raise ValueError("lifecycle symbol does not match paper execution intent")
    if plan.get("side") != intent.get("direction") or result.get("side") != intent.get(
        "direction"
    ):
        raise ValueError("lifecycle side does not match paper execution intent")

    stop_price = _strict_number(plan.get("stop_price"), "lifecycle stop_price")
    target_price = _strict_number(plan.get("target_price"), "lifecycle target_price")
    requested_notional = _strict_number(
        plan.get("requested_notional_usd"), "lifecycle requested_notional_usd"
    )
    intent_notional = _strict_number(intent.get("notional_usd"), "intent notional_usd")
    if not math.isclose(requested_notional, intent_notional, rel_tol=0.0, abs_tol=1e-8):
        raise ValueError("lifecycle requested notional does not match paper intent")

    status = result.get("status")
    reason = result.get("reason")
    if status not in {"OPEN_POSITION", "CLOSED", "CANCELLED_UNFILLED"}:
        raise ValueError("unsupported paper lifecycle status")
    if not isinstance(reason, str) or not reason:
        raise ValueError("paper lifecycle reason is required")

    filled_notional = _strict_number(
        result.get("filled_notional_usd"), "result filled_notional_usd"
    )
    quantity = _strict_number(result.get("total_quantity"), "result total_quantity")
    entry_fees = _strict_number(result.get("entry_fees_usd"), "result entry_fees_usd")
    if filled_notional < 0.0 or quantity < 0.0 or entry_fees < 0.0:
        raise ValueError("paper lifecycle fill values cannot be negative")

    average_entry_raw = result.get("average_entry_price")
    average_entry = (
        None
        if average_entry_raw is None
        else _strict_number(average_entry_raw, "result average_entry_price")
    )
    net_pnl_raw = result.get("net_pnl_usd")
    net_pnl = (
        None
        if net_pnl_raw is None
        else _strict_number(net_pnl_raw, "result net_pnl_usd")
    )

    events = result.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError("paper lifecycle events must be a non-empty array")
    event_times: list[int] = []
    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            raise ValueError(f"lifecycle events[{index}] must be an object")
        time_ms = event.get("time_ms")
        if not isinstance(time_ms, int) or isinstance(time_ms, bool) or time_ms < 0:
            raise ValueError(f"lifecycle events[{index}].time_ms must be non-negative integer")
        event_times.append(time_ms)
    if event_times != sorted(event_times):
        raise ValueError("paper lifecycle event times must be non-decreasing")
    last_event_time = event_times[-1]

    if status == "CANCELLED_UNFILLED":
        if filled_notional != 0.0 or quantity != 0.0 or average_entry is not None:
            raise ValueError("cancelled-unfilled lifecycle cannot contain an open fill")
        if net_pnl is not None:
            raise ValueError("cancelled-unfilled lifecycle cannot contain net PnL")
    else:
        if filled_notional <= 0.0 or quantity <= 0.0 or average_entry is None:
            raise ValueError("open/closed lifecycle requires positive filled position")
        if not stop_price < average_entry < target_price:
            raise ValueError("paper lifecycle LONG geometry is inconsistent")

    if status == "OPEN_POSITION" and net_pnl is not None:
        raise ValueError("open lifecycle cannot contain realized net PnL")
    if status == "CLOSED" and net_pnl is None:
        raise ValueError("closed lifecycle requires realized net PnL")

    return _NormalizedLifecycleRecord(
        lifecycle_id=lifecycle_id,
        intent_id=intent_id,
        symbol=str(intent["symbol"]),
        strategy_family=str(intent["strategy_family"]),
        side=str(intent["direction"]),
        lifecycle_status=status,
        lifecycle_reason=reason,
        stop_price=stop_price,
        target_price=target_price,
        filled_notional_usd=filled_notional,
        average_entry_price=average_entry,
        total_quantity=quantity,
        entry_fees_usd=entry_fees,
        net_pnl_usd=net_pnl,
        last_event_time_ms=last_event_time,
        report_sha256=_sha256(payload),
    )


def _normalize_record(item: Mapping[str, object]) -> _NormalizedLifecycleRecord:
    execution = item.get("paper_execution_evidence")
    lifecycle = item.get("paper_lifecycle_report")
    if not isinstance(execution, Mapping) or not isinstance(lifecycle, Mapping):
        raise ValueError(
            "each account record requires paper_execution_evidence and paper_lifecycle_report"
        )
    intent = _validate_paper_execution_evidence(execution)
    return _validate_lifecycle_evidence(lifecycle, intent)


def materialize_paper_account(
    *,
    initial_equity_usd: float,
    records: Sequence[Mapping[str, object]],
    marks: Sequence[PaperMark] = (),
    policy: PaperAccountPolicy = PaperAccountPolicy(),
) -> PaperAccountSnapshot:
    """Rebuild one immutable paper-account snapshot from latest lifecycle evidence."""

    if isinstance(initial_equity_usd, bool) or not math.isfinite(initial_equity_usd):
        raise ValueError("initial_equity_usd must be finite numeric")
    if initial_equity_usd <= 0.0:
        raise ValueError("initial_equity_usd must be positive")

    normalized = tuple(_normalize_record(item) for item in records)
    lifecycle_ids = tuple(item.lifecycle_id for item in normalized)
    if len(set(lifecycle_ids)) != len(lifecycle_ids):
        raise ValueError("account input must contain one latest report per lifecycle_id")
    intent_ids = tuple(item.intent_id for item in normalized)
    if len(set(intent_ids)) != len(intent_ids):
        raise ValueError("account input cannot contain multiple lifecycles for one paper intent")

    mark_by_symbol: dict[str, PaperMark] = {}
    for mark in marks:
        if mark.symbol in mark_by_symbol:
            raise ValueError("duplicate mark symbol")
        mark_by_symbol[mark.symbol] = mark

    open_records = tuple(
        item for item in normalized if item.lifecycle_status == "OPEN_POSITION"
    )
    open_symbols = {item.symbol for item in open_records}
    if set(mark_by_symbol) != open_symbols:
        missing = sorted(open_symbols - set(mark_by_symbol))
        extra = sorted(set(mark_by_symbol) - open_symbols)
        raise ValueError(f"marks must match open symbols exactly; missing={missing}, extra={extra}")

    if policy.require_single_mark_timestamp and mark_by_symbol:
        mark_times = {mark.time_ms for mark in mark_by_symbol.values()}
        if len(mark_times) != 1:
            raise ValueError("all marks must share one account snapshot timestamp")

    positions: list[PaperOpenPosition] = []
    unrealized = 0.0
    open_entry_fees = 0.0
    for item in open_records:
        mark = mark_by_symbol[item.symbol]
        if mark.time_ms < item.last_event_time_ms:
            raise ValueError("mark timestamp cannot precede latest lifecycle event")
        if policy.reject_mark_crossing_protective_boundary and not (
            item.stop_price < mark.price < item.target_price
        ):
            raise ValueError(
                "open-position mark crosses stop/target; advance lifecycle before account materialization"
            )
        assert item.average_entry_price is not None
        gross = (mark.price - item.average_entry_price) * item.total_quantity
        mark_notional = mark.price * item.total_quantity
        stop_risk = max(
            0.0,
            (mark.price - item.stop_price) * item.total_quantity,
        )
        open_entry_fees += item.entry_fees_usd
        unrealized += gross
        positions.append(
            PaperOpenPosition(
                lifecycle_id=item.lifecycle_id,
                intent_id=item.intent_id,
                symbol=item.symbol,
                strategy_family=item.strategy_family,
                side=item.side,
                quantity=round(item.total_quantity, 12),
                average_entry_price=round(item.average_entry_price, 8),
                mark_price=round(mark.price, 8),
                mark_time_ms=mark.time_ms,
                stop_price=round(item.stop_price, 8),
                target_price=round(item.target_price, 8),
                entry_notional_usd=round(item.filled_notional_usd, 8),
                mark_notional_usd=round(mark_notional, 8),
                entry_fees_usd=round(item.entry_fees_usd, 8),
                unrealized_gross_pnl_usd=round(gross, 8),
                portfolio_stop_risk_usd=round(stop_risk, 8),
                last_lifecycle_event_time_ms=item.last_event_time_ms,
            )
        )

    closed = tuple(item for item in normalized if item.lifecycle_status == "CLOSED")
    cancelled = tuple(
        item for item in normalized if item.lifecycle_status == "CANCELLED_UNFILLED"
    )
    realized_closed = sum(item.net_pnl_usd or 0.0 for item in closed)
    cash = initial_equity_usd + realized_closed - open_entry_fees
    equity = cash + unrealized

    all_times = [item.last_event_time_ms for item in normalized]
    if mark_by_symbol:
        all_times.extend(mark.time_ms for mark in mark_by_symbol.values())
    as_of_ms = max(all_times, default=0)

    status = (
        "ACCOUNT_INSOLVENT"
        if equity <= policy.insolvency_equity_floor_usd
        else "ACCOUNT_ACTIVE"
    )
    report_hashes = tuple(sorted(item.report_sha256 for item in normalized))
    snapshot_payload: dict[str, object] = {
        "schema": "qookey-paper-account-snapshot-v0.1",
        "status": status,
        "as_of_ms": as_of_ms,
        "initial_equity_usd": round(initial_equity_usd, 8),
        "cash_usd": round(cash, 8),
        "equity_usd": round(equity, 8),
        "realized_closed_net_pnl_usd": round(realized_closed, 8),
        "open_entry_fees_usd": round(open_entry_fees, 8),
        "unrealized_gross_pnl_usd": round(unrealized, 8),
        "open_positions": [asdict(item) for item in sorted(
            positions, key=lambda value: (value.symbol, value.lifecycle_id)
        )],
        "lifecycle_report_sha256s": list(report_hashes),
    }

    return PaperAccountSnapshot(
        snapshot_id=f"paper-account-v0-1-{_sha256(snapshot_payload)}",
        status=status,
        as_of_ms=as_of_ms,
        initial_equity_usd=round(initial_equity_usd, 8),
        cash_usd=round(cash, 8),
        equity_usd=round(equity, 8),
        realized_closed_net_pnl_usd=round(realized_closed, 8),
        open_entry_fees_usd=round(open_entry_fees, 8),
        unrealized_gross_pnl_usd=round(unrealized, 8),
        open_position_count=len(positions),
        closed_position_count=len(closed),
        cancelled_order_count=len(cancelled),
        open_positions=tuple(
            sorted(positions, key=lambda value: (value.symbol, value.lifecycle_id))
        ),
        lifecycle_report_sha256s=report_hashes,
    )


def portfolio_exposures_from_account(
    snapshot: PaperAccountSnapshot,
    *,
    policy: PaperAccountPolicy = PaperAccountPolicy(),
) -> tuple[PortfolioExposure, ...]:
    """Export current open paper positions into Portfolio Admission V0.1 exposure."""

    if not policy.export_portfolio_exposures:
        raise ValueError("portfolio exposure export is disabled by policy")
    if snapshot.status == "ACCOUNT_INSOLVENT":
        return ()
    return tuple(
        PortfolioExposure(
            exposure_id=position.lifecycle_id,
            symbol=position.symbol,
            strategy_family=position.strategy_family,
            direction=position.side,
            notional_usd=position.mark_notional_usd,
            realized_risk_usd=position.portfolio_stop_risk_usd,
        )
        for position in snapshot.open_positions
        if position.portfolio_stop_risk_usd > 0.0
    )


def paper_account_evidence(
    snapshot: PaperAccountSnapshot,
    policy: PaperAccountPolicy,
) -> dict[str, object]:
    return {
        "schema": "qookey-paper-account-state-report-v0.1",
        "snapshot": asdict(snapshot),
        "policy": asdict(policy),
        "authority": {
            "paper_state_materialization_only": True,
            "provider_requests_performed": False,
            "r2_accessed": False,
            "holdout_accessed": False,
            "persistent_state_written": False,
            "automatic_submission_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
        "limitations": [
            "V0.1 rebuilds immutable state from supplied latest lifecycle evidence.",
            "Derivatives notional is not treated as a cash debit.",
            "Open-position equity uses gross mark-to-market after already-paid entry fees.",
            "Funding, liquidation and margin maintenance are not modeled.",
            "Protective-boundary-crossing marks require lifecycle advancement first.",
        ],
    }


def paper_account_policy_from_config(payload: Mapping[str, object]) -> PaperAccountPolicy:
    if payload.get("schema") != "qookey-paper-account-state-v0.1":
        raise ValueError("unsupported paper account config")
    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("policy object is required")

    floor = policy.get("insolvency_equity_floor_usd")
    if isinstance(floor, bool) or not isinstance(floor, (int, float)):
        raise ValueError("policy.insolvency_equity_floor_usd must be numeric")
    for key in (
        "require_single_mark_timestamp",
        "reject_mark_crossing_protective_boundary",
        "export_portfolio_exposures",
    ):
        if not isinstance(policy.get(key), bool):
            raise ValueError(f"policy.{key} must be a JSON boolean")

    return PaperAccountPolicy(
        insolvency_equity_floor_usd=float(floor),
        require_single_mark_timestamp=policy["require_single_mark_timestamp"],
        reject_mark_crossing_protective_boundary=policy[
            "reject_mark_crossing_protective_boundary"
        ],
        export_portfolio_exposures=policy["export_portfolio_exposures"],
    )


def paper_account_input_from_dict(
    payload: Mapping[str, object],
) -> tuple[float, tuple[Mapping[str, object], ...], tuple[PaperMark, ...]]:
    if payload.get("schema") != "qookey-paper-account-state-input-v0.1":
        raise ValueError("unsupported paper account input schema")
    initial = payload.get("initial_equity_usd")
    if isinstance(initial, bool) or not isinstance(initial, (int, float)):
        raise ValueError("initial_equity_usd must be numeric")

    records_raw = payload.get("records")
    marks_raw = payload.get("marks", [])
    if not isinstance(records_raw, list):
        raise ValueError("records must be a JSON array")
    if not isinstance(marks_raw, list):
        raise ValueError("marks must be a JSON array")

    records: list[Mapping[str, object]] = []
    for index, item in enumerate(records_raw):
        if not isinstance(item, Mapping):
            raise ValueError(f"records[{index}] must be a JSON object")
        records.append(item)

    marks: list[PaperMark] = []
    for index, item in enumerate(marks_raw):
        if not isinstance(item, Mapping):
            raise ValueError(f"marks[{index}] must be a JSON object")
        if not isinstance(item.get("time_ms"), int) or isinstance(
            item.get("time_ms"), bool
        ):
            raise ValueError(f"marks[{index}].time_ms must be a JSON integer")
        if isinstance(item.get("price"), bool):
            raise ValueError(f"marks[{index}].price cannot be boolean")
        try:
            marks.append(
                PaperMark(
                    symbol=str(item["symbol"]),
                    time_ms=item["time_ms"],
                    price=float(item["price"]),
                )
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"invalid marks[{index}]: {error}") from error

    return float(initial), tuple(records), tuple(marks)
