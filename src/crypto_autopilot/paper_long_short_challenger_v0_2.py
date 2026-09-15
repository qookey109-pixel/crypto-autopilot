"""Bounded LONG/SHORT paper challenger for research-only replay.

This module is deliberately separate from the governed V0.1 long-only path.
It produces directional candidates and independent paper samples; it never
creates a formal trade plan, writes R2, or calls a private exchange API.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Literal, Mapping, Sequence

from .advanced_technical import AdvancedTechnicalSnapshot
from .backtest import FundingPoint
from .models import Candle
from .technical import TechnicalSnapshot


Side = Literal["LONG", "SHORT"]


@dataclass(frozen=True, slots=True)
class DirectionalPlan:
    plan_id: str
    symbol: str
    side: Side
    signal_time_ms: int
    stop_price: float
    target_price: float

    def __post_init__(self) -> None:
        if not self.plan_id.strip() or not self.symbol.strip():
            raise ValueError("plan_id and symbol are required")
        if self.side not in ("LONG", "SHORT"):
            raise ValueError("side must be LONG or SHORT")
        if self.signal_time_ms < 0:
            raise ValueError("signal_time_ms cannot be negative")
        if min(self.stop_price, self.target_price) <= 0:
            raise ValueError("stop_price and target_price must be positive")
        if self.side == "LONG" and self.target_price <= self.stop_price:
            raise ValueError("long target must be above long stop")
        if self.side == "SHORT" and self.target_price >= self.stop_price:
            raise ValueError("short target must be below short stop")


@dataclass(frozen=True, slots=True)
class DirectionalCandidate:
    plan: DirectionalPlan
    score: float
    eligible: bool
    reasons: tuple[str, ...]
    reference_price: float
    features: tuple[tuple[str, float], ...]


@dataclass(frozen=True, slots=True)
class DirectionalTrade:
    plan_id: str
    symbol: str
    side: Side
    signal_time_ms: int
    entry_time_ms: int
    exit_time_ms: int
    raw_entry_price: float
    entry_price: float
    raw_exit_price: float
    exit_price: float
    quantity: float
    risk_usd: float
    notional_usd: float
    gross_pnl_usd: float
    fees_usd: float
    funding_usd: float
    slippage_cost_usd: float
    net_pnl_usd: float
    r_multiple: float
    exit_reason: str


def _r8(value: float) -> float:
    return round(float(value), 8)


def _day_key(time_ms: int) -> str:
    return datetime.fromtimestamp(time_ms / 1000.0, tz=UTC).date().isoformat()


def _trend_vote(snapshot: TechnicalSnapshot, side: Side) -> bool:
    if not snapshot.ready_v0_2:
        return False
    if side == "LONG":
        return bool(
            snapshot.ema20 is not None
            and snapshot.ema50 is not None
            and snapshot.ema200 is not None
            and snapshot.ema20_slope is not None
            and snapshot.ema20 > snapshot.ema50
            and snapshot.close > snapshot.ema200
            and snapshot.ema20_slope > 0
        )
    return bool(
        snapshot.ema20 is not None
        and snapshot.ema50 is not None
        and snapshot.ema200 is not None
        and snapshot.ema20_slope is not None
        and snapshot.ema20 < snapshot.ema50
        and snapshot.close < snapshot.ema200
        and snapshot.ema20_slope < 0
    )


def _build_candidate(
    *,
    symbol: str,
    side: Side,
    technical: TechnicalSnapshot,
    advanced: AdvancedTechnicalSnapshot,
    higher: Sequence[TechnicalSnapshot],
    config: Mapping[str, Any],
) -> DirectionalCandidate:
    thresholds = config["candidate_thresholds"]
    risk = config["paper_risk"]
    trend_agreement = sum(_trend_vote(snapshot, side) for snapshot in higher) / len(higher)
    di_ok = (
        advanced.plus_di14 > advanced.minus_di14
        if side == "LONG"
        else advanced.minus_di14 > advanced.plus_di14
    )
    vwap_ok = (
        advanced.vwap_distance_fraction > 0
        if side == "LONG"
        else advanced.vwap_distance_fraction < 0
    )
    macd_ok = (
        (technical.macd_histogram or 0.0) > 0
        if side == "LONG"
        else (technical.macd_histogram or 0.0) < 0
    )
    donchian = advanced.donchian_position20 or 0.0
    donchian_ok = (
        donchian >= float(thresholds["minimum_donchian_position"])
        if side == "LONG"
        else donchian <= float(thresholds["maximum_donchian_position"])
    )
    rsi = technical.rsi14 or -1.0
    rsi_ok = (
        float(thresholds["minimum_rsi14"]) <= rsi <= float(thresholds["maximum_rsi14"])
        if side == "LONG"
        else float(thresholds["short_minimum_rsi14"]) <= rsi <= float(thresholds["short_maximum_rsi14"])
    )

    reasons: list[str] = []
    if not technical.ready_v0_2 or not advanced.ready:
        reasons.append("feature_warmup_incomplete")
    if trend_agreement < float(thresholds["minimum_trend_agreement"]):
        reasons.append("higher_timeframe_trend_not_aligned")
    if (advanced.adx14 or 0.0) < float(thresholds["minimum_adx14"]):
        reasons.append("trend_strength_below_gate")
    if not di_ok:
        reasons.append("directional_index_not_aligned")
    if not vwap_ok:
        reasons.append("vwap_side_not_aligned")
    if not rsi_ok:
        reasons.append("rsi_outside_gate")
    if not macd_ok:
        reasons.append("macd_histogram_not_aligned")
    if not donchian_ok:
        reasons.append("donchian_position_not_aligned")
    if (advanced.volume_zscore20 or -99.0) < float(thresholds["minimum_volume_zscore"]):
        reasons.append("relative_volume_below_gate")
    if (advanced.kaufman_efficiency_ratio10 or 0.0) < float(thresholds["minimum_efficiency_ratio"]):
        reasons.append("efficiency_ratio_below_gate")

    directional_donchian = donchian if side == "LONG" else 1.0 - donchian
    score = 0.0
    score += 25.0 * trend_agreement
    score += 15.0 * min(1.0, max(0.0, (advanced.adx14 or 0.0) / 40.0))
    score += 10.0 if di_ok else 0.0
    score += 10.0 if vwap_ok else 0.0
    score += 10.0 if macd_ok else 0.0
    score += 10.0 * min(1.0, max(0.0, directional_donchian))
    score += 10.0 * min(1.0, max(0.0, ((advanced.volume_zscore20 or 0.0) + 1.0) / 3.0))
    score += 10.0 * min(1.0, max(0.0, advanced.kaufman_efficiency_ratio10 or 0.0))
    score = round(min(100.0, score), 8)
    if score < float(thresholds["minimum_candidate_score"]):
        reasons.append("candidate_score_below_gate")

    atr = float(technical.atr14 or 0.0)
    if side == "LONG":
        stop = technical.close - atr * float(risk["stop_atr_multiple"])
        target = technical.close + atr * float(risk["target_atr_multiple"])
    else:
        stop = technical.close + atr * float(risk["stop_atr_multiple"])
        target = technical.close - atr * float(risk["target_atr_multiple"])
    if atr <= 0 or target <= 0 or stop <= 0:
        reasons.append("invalid_atr_risk_geometry")

    features = {
        "adx14": advanced.adx14 or 0.0,
        "plus_di14": advanced.plus_di14 or 0.0,
        "minus_di14": advanced.minus_di14 or 0.0,
        "vwap_distance_fraction": advanced.vwap_distance_fraction or 0.0,
        "volume_zscore20": advanced.volume_zscore20 or 0.0,
        "donchian_position20": advanced.donchian_position20 or 0.0,
        "trend_agreement": trend_agreement,
    }
    plan = DirectionalPlan(
        plan_id=f"challenger-{symbol}-{technical.bar_time_ms}-{side.lower()}",
        symbol=symbol,
        side=side,
        signal_time_ms=technical.bar_time_ms,
        stop_price=stop,
        target_price=target,
    )
    return DirectionalCandidate(
        plan=plan,
        score=score,
        eligible=not reasons,
        reasons=tuple(reasons) if reasons else ("eligible_paper_challenger",),
        reference_price=technical.close,
        features=tuple(sorted((key, round(value, 12)) for key, value in features.items())),
    )


def build_directional_candidates(
    *,
    symbol: str,
    technical: TechnicalSnapshot,
    advanced: AdvancedTechnicalSnapshot,
    higher: Sequence[TechnicalSnapshot],
    config: Mapping[str, Any],
) -> tuple[DirectionalCandidate, DirectionalCandidate]:
    """Build independent long and short candidates from the same closed bar."""
    if not higher:
        raise ValueError("higher timeframe snapshots are required")
    return tuple(
        _build_candidate(
            symbol=symbol,
            side=side,
            technical=technical,
            advanced=advanced,
            higher=higher,
            config=config,
        )
        for side in ("LONG", "SHORT")
    )  # type: ignore[return-value]


def _validate_candles(candles: Sequence[Candle], symbol: str) -> tuple[Candle, ...]:
    values = tuple(candles)
    previous = -1
    for candle in values:
        if candle.time_ms <= previous:
            raise ValueError(f"candles must be strictly increasing for {symbol}")
        if not all(math.isfinite(value) for value in (candle.open, candle.high, candle.low, candle.close, candle.volume)):
            raise ValueError(f"non-finite candle value for {symbol}")
        if min(candle.open, candle.high, candle.low, candle.close) <= 0 or candle.volume < 0:
            raise ValueError(f"invalid candle value for {symbol}")
        if candle.low > min(candle.open, candle.close, candle.high) or candle.high < max(candle.open, candle.close, candle.low):
            raise ValueError(f"invalid candle range for {symbol}")
        previous = candle.time_ms
    return values


def _simulate_plan(
    *,
    plan: DirectionalPlan,
    candles: Sequence[Candle],
    funding_points: Sequence[FundingPoint],
    initial_equity_usd: float,
    risk_fraction: float,
    max_leverage: float,
    taker_fee_bps: float,
    slippage_bps: float,
    conservative_same_bar_exit: bool,
) -> tuple[DirectionalTrade | None, str | None]:
    prepared = _validate_candles(candles, plan.symbol)
    entry_index = next((i for i, candle in enumerate(prepared) if candle.time_ms > plan.signal_time_ms), None)
    if entry_index is None:
        return None, "no_future_entry_bar"
    entry_candle = prepared[entry_index]
    slip = slippage_bps / 10_000.0
    fee = taker_fee_bps / 10_000.0
    raw_entry = entry_candle.open
    entry_price = raw_entry * (1.0 + slip if plan.side == "LONG" else 1.0 - slip)
    if plan.side == "LONG" and not plan.stop_price < entry_price < plan.target_price:
        return None, "invalid_long_risk_geometry"
    if plan.side == "SHORT" and not plan.target_price < entry_price < plan.stop_price:
        return None, "invalid_short_risk_geometry"
    stop_distance = (
        (entry_price - plan.stop_price) / entry_price
        if plan.side == "LONG"
        else (plan.stop_price - entry_price) / entry_price
    )
    if stop_distance <= 0:
        return None, "invalid_stop_distance"
    risk_usd = initial_equity_usd * risk_fraction
    notional = risk_usd / stop_distance
    leverage = notional / initial_equity_usd
    if leverage > max_leverage:
        return None, "required_leverage_exceeds_cap"

    exit_time = prepared[-1].time_ms
    raw_exit = prepared[-1].close
    exit_reason = "end_of_data"
    for candle in prepared[entry_index:]:
        stop_hit = candle.low <= plan.stop_price if plan.side == "LONG" else candle.high >= plan.stop_price
        target_hit = candle.high >= plan.target_price if plan.side == "LONG" else candle.low <= plan.target_price
        if stop_hit and target_hit:
            exit_time, raw_exit, exit_reason = (
                candle.time_ms,
                plan.stop_price if conservative_same_bar_exit else plan.target_price,
                "stop_same_bar_collision" if conservative_same_bar_exit else "target_same_bar_collision",
            )
            break
        if stop_hit:
            exit_time, raw_exit, exit_reason = candle.time_ms, plan.stop_price, "stop"
            break
        if target_hit:
            exit_time, raw_exit, exit_reason = candle.time_ms, plan.target_price, "target"
            break
    exit_price = raw_exit * (1.0 - slip if plan.side == "LONG" else 1.0 + slip)
    quantity = notional / entry_price
    gross_pnl = quantity * (exit_price - entry_price if plan.side == "LONG" else entry_price - exit_price)
    fees = (quantity * entry_price + quantity * exit_price) * fee
    funding_rate = sum(
        point.rate
        for point in funding_points
        if point.symbol == plan.symbol and entry_candle.time_ms <= point.time_ms <= exit_time
    )
    funding = notional * funding_rate * (1.0 if plan.side == "LONG" else -1.0)
    slippage_cost = quantity * (
        (entry_price - raw_entry) + (raw_exit - exit_price)
        if plan.side == "LONG"
        else (raw_entry - entry_price) + (exit_price - raw_exit)
    )
    net_pnl = gross_pnl - fees - funding
    trade = DirectionalTrade(
        plan_id=plan.plan_id,
        symbol=plan.symbol,
        side=plan.side,
        signal_time_ms=plan.signal_time_ms,
        entry_time_ms=entry_candle.time_ms,
        exit_time_ms=exit_time,
        raw_entry_price=_r8(raw_entry),
        entry_price=_r8(entry_price),
        raw_exit_price=_r8(raw_exit),
        exit_price=_r8(exit_price),
        quantity=_r8(quantity),
        risk_usd=_r8(risk_usd),
        notional_usd=_r8(notional),
        gross_pnl_usd=_r8(gross_pnl),
        fees_usd=_r8(fees),
        funding_usd=_r8(funding),
        slippage_cost_usd=_r8(slippage_cost),
        net_pnl_usd=_r8(net_pnl),
        r_multiple=_r8(net_pnl / risk_usd),
        exit_reason=exit_reason,
    )
    return trade, None


def _side_metrics(trades: Sequence[DirectionalTrade], initial_equity_usd: float) -> dict[str, Any]:
    ordered = sorted(trades, key=lambda item: (item.exit_time_ms, item.plan_id))
    equity = initial_equity_usd
    peak = equity
    max_drawdown = 0.0
    for trade in ordered:
        equity += trade.net_pnl_usd
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak if peak else 0.0)
    wins = [trade for trade in ordered if trade.net_pnl_usd > 0]
    losses = [trade for trade in ordered if trade.net_pnl_usd < 0]
    gross_loss = -sum(item.net_pnl_usd for item in losses)
    return {
        "trade_count": len(ordered),
        "win_count": len(wins),
        "loss_count": len(losses),
        "win_rate": _r8(len(wins) / len(ordered)) if ordered else 0.0,
        "net_pnl_usd": _r8(sum(item.net_pnl_usd for item in ordered)),
        "descriptive_max_drawdown_pct": _r8(max_drawdown * 100.0),
        "profit_factor": None if gross_loss == 0 else _r8(sum(item.net_pnl_usd for item in wins) / gross_loss),
        "average_r_multiple": _r8(sum(item.r_multiple for item in ordered) / len(ordered)) if ordered else 0.0,
        "total_fees_usd": _r8(sum(item.fees_usd for item in ordered)),
        "total_funding_usd": _r8(sum(item.funding_usd for item in ordered)),
        "total_slippage_cost_usd": _r8(sum(item.slippage_cost_usd for item in ordered)),
    }


def run_long_short_exploration(
    *,
    candles_by_symbol: Mapping[str, Sequence[Candle]],
    plans: Sequence[DirectionalPlan],
    funding_points: Sequence[FundingPoint] = (),
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay bounded independent LONG/SHORT samples without portfolio claims."""
    if len({plan.plan_id for plan in plans}) != len(plans):
        raise ValueError("challenger plan_id values must be unique")
    limits = config["limits"]
    accepted: list[DirectionalTrade] = []
    rejected: list[tuple[str, str]] = []
    by_day: dict[str, int] = {}
    by_symbol_day: dict[tuple[str, str], int] = {}
    for plan in sorted(plans, key=lambda item: (item.signal_time_ms, item.symbol, item.side, item.plan_id)):
        trade, reason = _simulate_plan(
            plan=plan,
            candles=candles_by_symbol.get(plan.symbol, ()),
            funding_points=funding_points,
            initial_equity_usd=float(limits["initial_equity_usd"]),
            risk_fraction=float(limits["risk_fraction_per_sample"]),
            max_leverage=float(limits["max_leverage"]),
            taker_fee_bps=float(limits["taker_fee_bps"]),
            slippage_bps=float(limits["slippage_bps"]),
            conservative_same_bar_exit=True,
        )
        if trade is None:
            rejected.append((plan.plan_id, reason or "no_trade"))
            continue
        day = _day_key(trade.entry_time_ms)
        symbol_day = (trade.symbol, day)
        if by_day.get(day, 0) >= int(limits["max_samples_per_utc_day"]):
            rejected.append((plan.plan_id, "challenger_daily_sample_gate"))
            continue
        if by_symbol_day.get(symbol_day, 0) >= int(limits["max_samples_per_symbol_per_utc_day"]):
            rejected.append((plan.plan_id, "challenger_symbol_daily_sample_gate"))
            continue
        accepted.append(trade)
        by_day[day] = by_day.get(day, 0) + 1
        by_symbol_day[symbol_day] = by_symbol_day.get(symbol_day, 0) + 1

    initial = float(limits["initial_equity_usd"])
    return {
        "schema": "paper-long-short-challenger-v0.2",
        "status": "PASS",
        "mode": "INDEPENDENT_DIRECTIONAL_SHADOW_SAMPLES",
        "sample_count": len(accepted),
        "accepted_sides": sorted({trade.side for trade in accepted}),
        "rejected_count": len(rejected),
        "by_side": {
            side.lower(): _side_metrics([trade for trade in accepted if trade.side == side], initial)
            for side in ("LONG", "SHORT")
        },
        "samples": [asdict(trade) for trade in accepted],
        "rejected_plans": [list(item) for item in rejected],
        "limits": dict(limits),
        "interpretation": {
            "independent_samples_not_portfolio_equity": True,
            "overlapping_samples_allowed": True,
            "long_short_comparison_only": True,
            "composite_equity_curve_authorized": False,
        },
        "authority": dict(config["authority"]),
    }
