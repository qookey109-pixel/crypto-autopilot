from __future__ import annotations

from dataclasses import dataclass, field

from .base import LiveTradingDisabledError


@dataclass(frozen=True, slots=True)
class PaperOrder:
    order_id: str
    symbol: str
    side: str
    notional_usd: float
    status: str = "ACCEPTED"


@dataclass(slots=True)
class PaperBroker:
    """Minimal paper-only order intent recorder.

    This is not yet a realistic fill simulator; settlement/slippage/funding are M2 work.
    """

    orders: list[PaperOrder] = field(default_factory=list)

    def submit_long(self, *, order_id: str, symbol: str, notional_usd: float) -> PaperOrder:
        if not order_id:
            raise ValueError("order_id is required for idempotency")
        existing = next(
            (order for order in self.orders if order.order_id == order_id),
            None,
        )
        if existing is not None:
            if (
                existing.symbol != symbol
                or existing.side != "LONG"
                or existing.notional_usd != notional_usd
            ):
                raise ValueError(
                    "idempotency key collision: existing paper order payload differs"
                )
            return existing
        if notional_usd <= 0:
            raise ValueError("notional_usd must be positive")
        order = PaperOrder(order_id, symbol, "LONG", notional_usd)
        self.orders.append(order)
        return order

    def submit_live_order(self, *args: object, **kwargs: object) -> None:
        raise LiveTradingDisabledError("Live trading is disabled in V0.1")
