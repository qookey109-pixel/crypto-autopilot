from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class PublicTrade:
    symbol: str
    trade_id: str
    price: float
    size: float
    side: str
    time_ms: int


@dataclass(frozen=True, slots=True)
class OrderBookSnapshot:
    symbol: str
    bids: tuple[tuple[float, float], ...]
    asks: tuple[tuple[float, float], ...]
    update_time_ms: int


@dataclass(frozen=True, slots=True)
class FundingRateObservation:
    symbol: str
    funding_time_ms: int
    funding_rate: float


@dataclass(frozen=True, slots=True)
class DerivativeIndexSnapshot:
    symbol: str
    index_price: float
    mark_price: float
    next_funding_rate: float
    next_funding_time_ms: int
    update_time_ms: int


@dataclass(frozen=True, slots=True)
class MicrostructureFeatures:
    trade_imbalance: float | None
    cumulative_volume_delta: float
    order_book_imbalance: float | None
    spread_bps: float | None
    bid_depth_notional: float
    ask_depth_notional: float
    expected_buy_slippage_bps: float | None


@dataclass(frozen=True, slots=True)
class DerivativeFeatures:
    funding_rate: float | None
    funding_percentile: float | None
    mark_index_basis: float | None
    basis_zscore: float | None
    open_interest: float | None
    open_interest_change_fraction: float | None


def _population_zscore(values: Sequence[float], current: float) -> float:
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return 0.0 if variance == 0 else (current - mean) / math.sqrt(variance)


def _expected_buy_slippage_bps(
    asks: Sequence[tuple[float, float]],
    notional_usd: float,
) -> float | None:
    if not asks or notional_usd <= 0:
        return None
    best = asks[0][0]
    remaining = notional_usd
    quantity = 0.0
    cost = 0.0
    for price, size in asks:
        level_notional = price * size
        consumed = min(remaining, level_notional)
        cost += consumed
        quantity += consumed / price
        remaining -= consumed
        if remaining <= 1e-12:
            break
    if remaining > 1e-12 or quantity <= 0 or best <= 0:
        return None
    average = cost / quantity
    return (average / best - 1.0) * 10_000.0


def build_microstructure_features(
    trades: Sequence[PublicTrade],
    book: OrderBookSnapshot,
    *,
    depth_levels: int = 20,
    reference_notional_usd: float = 1_000.0,
) -> MicrostructureFeatures:
    if depth_levels < 1:
        raise ValueError("depth_levels must be positive")
    buy_volume = sum(trade.size for trade in trades if trade.side.upper() == "BUY")
    sell_volume = sum(trade.size for trade in trades if trade.side.upper() == "SELL")
    total_volume = buy_volume + sell_volume
    trade_imbalance = None if total_volume == 0 else (buy_volume - sell_volume) / total_volume
    cumulative_volume_delta = buy_volume - sell_volume

    bids = tuple(book.bids[:depth_levels])
    asks = tuple(book.asks[:depth_levels])
    bid_depth = sum(price * size for price, size in bids)
    ask_depth = sum(price * size for price, size in asks)
    total_depth = bid_depth + ask_depth
    book_imbalance = None if total_depth == 0 else (bid_depth - ask_depth) / total_depth
    spread_bps = None
    if bids and asks and bids[0][0] > 0 and asks[0][0] >= bids[0][0]:
        midpoint = (bids[0][0] + asks[0][0]) / 2.0
        spread_bps = (asks[0][0] - bids[0][0]) / midpoint * 10_000.0

    return MicrostructureFeatures(
        trade_imbalance=trade_imbalance,
        cumulative_volume_delta=cumulative_volume_delta,
        order_book_imbalance=book_imbalance,
        spread_bps=spread_bps,
        bid_depth_notional=bid_depth,
        ask_depth_notional=ask_depth,
        expected_buy_slippage_bps=_expected_buy_slippage_bps(asks, reference_notional_usd),
    )


def build_derivative_features(
    *,
    current: DerivativeIndexSnapshot | None,
    funding_history: Sequence[FundingRateObservation] = (),
    basis_history: Sequence[float] = (),
    open_interest: float | None = None,
    previous_open_interest: float | None = None,
) -> DerivativeFeatures:
    funding_rate = current.next_funding_rate if current else None
    funding_percentile = None
    rates = [item.funding_rate for item in funding_history]
    if funding_rate is not None and rates:
        funding_percentile = sum(value <= funding_rate for value in rates) / len(rates)

    basis = None
    basis_zscore = None
    if current and current.index_price > 0:
        basis = current.mark_price / current.index_price - 1.0
        if basis_history:
            basis_zscore = _population_zscore(tuple(basis_history), basis)

    oi_change = None
    if open_interest is not None and previous_open_interest not in (None, 0.0):
        oi_change = open_interest / float(previous_open_interest) - 1.0

    return DerivativeFeatures(
        funding_rate=funding_rate,
        funding_percentile=funding_percentile,
        mark_index_basis=basis,
        basis_zscore=basis_zscore,
        open_interest=open_interest,
        open_interest_change_fraction=oi_change,
    )
