from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Candle:
    time_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True, slots=True)
class MarketTicker:
    symbol: str
    close: float
    base_volume: float
    quote_amount: float
    trade_count: int


@dataclass(frozen=True, slots=True)
class BookTicker:
    symbol: str
    bid_price: float
    bid_size: float
    ask_price: float
    ask_size: float
    timestamp_ms: int


@dataclass(frozen=True, slots=True)
class SStateContext:
    state: str
    probability: float | None
    samples: int
    available: bool = True


@dataclass(frozen=True, slots=True)
class SetupFeatures:
    ema20_above_ema50: bool
    ema20_slope_positive: bool
    close_above_ema20: bool
    not_overextended: bool


@dataclass(frozen=True, slots=True)
class EntryFeatures:
    pullback_seen: bool
    reclaimed_ema20: bool
    broke_previous_high: bool
    volume_confirmed: bool


@dataclass(frozen=True, slots=True)
class OpportunityInput:
    symbol: str
    sstate: SStateContext
    setup: SetupFeatures
    entry: EntryFeatures
    reward_risk: float
    liquidity_ok: bool
    funding_ok: bool


@dataclass(frozen=True, slots=True)
class StrategyDecision:
    symbol: str
    eligible: bool
    score: float
    reason: str


@dataclass(frozen=True, slots=True)
class RiskDecision:
    approved: bool
    reason: str
    risk_usd: float = 0.0
    notional_usd: float = 0.0
    required_leverage: float = 0.0
