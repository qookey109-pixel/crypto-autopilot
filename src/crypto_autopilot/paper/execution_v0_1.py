from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass

from crypto_autopilot.exchanges.paper import PaperBroker, PaperOrder
from crypto_autopilot.risk import PositionSizingPlan
from crypto_autopilot.strategy_library import get_strategy_family


FAMILY_REVIEW_READY = "FAMILY_EVIDENCE_READY_FOR_HUMAN_REVIEW"


@dataclass(frozen=True, slots=True)
class PaperExecutionPolicy:
    """Repository Paper Broker authority for explicit research-only submission."""

    long_paper_execution_authorized: bool = True
    short_paper_execution_authorized: bool = False
    require_family_review_ready: bool = True
    automatic_submission_authorized: bool = False
    live_trading_authorized: bool = False

    def __post_init__(self) -> None:
        values = (
            self.long_paper_execution_authorized,
            self.short_paper_execution_authorized,
            self.require_family_review_ready,
            self.automatic_submission_authorized,
            self.live_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in values):
            raise ValueError("paper execution policy flags must be booleans")
        if self.automatic_submission_authorized:
            raise ValueError("automatic paper submission is not authorized in V0.1")
        if self.live_trading_authorized:
            raise ValueError("live trading cannot be authorized by Paper Execution V0.1")


@dataclass(frozen=True, slots=True)
class PaperExecutionIntent:
    intent_id: str
    symbol: str
    strategy_family: str
    direction: str
    as_of_ms: int
    entry_price: float
    stop_price: float
    notional_usd: float
    target_risk_usd: float
    realized_risk_usd: float
    risk_utilization_fraction: float
    status: str = "READY_FOR_PAPER_BROKER"


@dataclass(frozen=True, slots=True)
class PaperExecutionDecision:
    status: str
    reason: str
    intent: PaperExecutionIntent | None = None


@dataclass(frozen=True, slots=True)
class PaperExecutionReceipt:
    status: str
    intent_id: str
    order_id: str
    symbol: str
    side: str
    notional_usd: float
    broker_status: str
    replayed: bool


def _canonical_intent_id(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return f"paper-v0-1-{digest}"


def prepare_paper_execution(
    *,
    symbol: str,
    strategy_family: str,
    family_review_state: str,
    as_of_ms: int,
    sizing_plan: PositionSizingPlan,
    policy: PaperExecutionPolicy = PaperExecutionPolicy(),
) -> PaperExecutionDecision:
    """Prepare one deterministic Repository Paper Broker intent.

    The function performs no provider, storage, holdout or broker I/O. It only
    converts an already-approved sizing plan into a paper-only intent after the
    family-generalization gate passes.
    """

    if not symbol.strip():
        return PaperExecutionDecision("NO_EXECUTION", "symbol_required")
    if as_of_ms < 0:
        return PaperExecutionDecision("NO_EXECUTION", "invalid_as_of_ms")

    try:
        family = get_strategy_family(strategy_family)
    except ValueError:
        return PaperExecutionDecision("NO_EXECUTION", "unregistered_strategy_family")

    if policy.require_family_review_ready and family_review_state != FAMILY_REVIEW_READY:
        return PaperExecutionDecision("NO_EXECUTION", "family_review_not_ready")

    if sizing_plan.status != "SIZING_READY":
        return PaperExecutionDecision("NO_EXECUTION", "position_sizing_not_ready")
    if sizing_plan.direction not in family.directions:
        return PaperExecutionDecision(
            "NO_EXECUTION", "sizing_direction_not_supported_by_family"
        )
    if sizing_plan.direction == "LONG" and not policy.long_paper_execution_authorized:
        return PaperExecutionDecision("NO_EXECUTION", "long_paper_execution_not_authorized")
    if sizing_plan.direction == "SHORT":
        if not policy.short_paper_execution_authorized:
            return PaperExecutionDecision(
                "NO_EXECUTION", "short_paper_execution_not_authorized"
            )
        return PaperExecutionDecision(
            "NO_EXECUTION", "short_paper_broker_path_not_implemented"
        )

    numeric = (
        sizing_plan.entry_price,
        sizing_plan.stop_price,
        sizing_plan.approved_notional_usd,
        sizing_plan.target_risk_usd,
        sizing_plan.realized_risk_usd,
        sizing_plan.risk_utilization_fraction,
    )
    if not all(math.isfinite(value) and value >= 0.0 for value in numeric):
        return PaperExecutionDecision("NO_EXECUTION", "non_finite_sizing_plan")
    if sizing_plan.approved_notional_usd <= 0.0:
        return PaperExecutionDecision("NO_EXECUTION", "non_positive_paper_notional")

    payload: dict[str, object] = {
        "schema": "qookey-paper-execution-intent-v0.1",
        "symbol": symbol,
        "strategy_family": strategy_family,
        "family_review_state": family_review_state,
        "direction": sizing_plan.direction,
        "as_of_ms": as_of_ms,
        "entry_price": sizing_plan.entry_price,
        "stop_price": sizing_plan.stop_price,
        "notional_usd": sizing_plan.approved_notional_usd,
        "target_risk_usd": sizing_plan.target_risk_usd,
        "realized_risk_usd": sizing_plan.realized_risk_usd,
        "risk_utilization_fraction": sizing_plan.risk_utilization_fraction,
    }
    intent = PaperExecutionIntent(
        intent_id=_canonical_intent_id(payload),
        symbol=symbol,
        strategy_family=strategy_family,
        direction=sizing_plan.direction,
        as_of_ms=as_of_ms,
        entry_price=sizing_plan.entry_price,
        stop_price=sizing_plan.stop_price,
        notional_usd=sizing_plan.approved_notional_usd,
        target_risk_usd=sizing_plan.target_risk_usd,
        realized_risk_usd=sizing_plan.realized_risk_usd,
        risk_utilization_fraction=sizing_plan.risk_utilization_fraction,
    )
    return PaperExecutionDecision("READY_FOR_PAPER_BROKER", "paper_intent_ready", intent)


def submit_paper_execution(
    decision: PaperExecutionDecision,
    broker: PaperBroker,
    *,
    policy: PaperExecutionPolicy = PaperExecutionPolicy(),
) -> PaperExecutionReceipt:
    """Submit an explicit ready intent to the existing Repository Paper Broker."""

    if decision.status != "READY_FOR_PAPER_BROKER" or decision.intent is None:
        raise ValueError("paper execution decision is not ready")
    intent = decision.intent
    if intent.direction != "LONG":
        raise ValueError("PaperBroker V0.1 only supports LONG paper orders")
    if not policy.long_paper_execution_authorized:
        raise ValueError("LONG paper execution is not authorized by policy")
    if policy.automatic_submission_authorized or policy.live_trading_authorized:
        raise ValueError("invalid Paper Execution V0.1 authority policy")

    preexisting = any(order.order_id == intent.intent_id for order in broker.orders)
    order: PaperOrder = broker.submit_long(
        order_id=intent.intent_id,
        symbol=intent.symbol,
        notional_usd=intent.notional_usd,
    )
    return PaperExecutionReceipt(
        status="PAPER_ACCEPTED",
        intent_id=intent.intent_id,
        order_id=order.order_id,
        symbol=order.symbol,
        side=order.side,
        notional_usd=order.notional_usd,
        broker_status=order.status,
        replayed=preexisting,
    )


def paper_execution_evidence(
    decision: PaperExecutionDecision,
    receipt: PaperExecutionReceipt | None = None,
) -> dict[str, object]:
    """Return an auditable zero-live-authority evidence payload."""

    return {
        "schema": "qookey-paper-execution-evidence-v0.1",
        "decision": {
            "status": decision.status,
            "reason": decision.reason,
            "intent": None if decision.intent is None else asdict(decision.intent),
        },
        "receipt": None if receipt is None else asdict(receipt),
        "authority": {
            "repository_paper_broker_only": True,
            "provider_requests_performed": False,
            "r2_accessed": False,
            "holdout_accessed": False,
            "automatic_submission_authorized": False,
            "short_paper_execution_authorized": False,
            "formal_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
        "limitations": [
            "Repository Paper Broker records intent only and is not a realistic fill simulator.",
            "Settlement, slippage and funding simulation remain separate downstream work.",
            "Paper acceptance is not evidence of strategy profitability.",
        ],
    }
