"""Integrated, research-only paper strategy challenger V0.2.

The module bridges the governed SState V0.1 decision, the directional technical
challenger, asset-class admission and a deterministic partial/runner paper
replay.  It does not mutate the SState core or expose provider, persistence,
promotion or live-execution capabilities.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Literal, Mapping, Sequence

from .advanced_technical import AdvancedTechnicalSnapshot
from .backtest import FundingPoint
from .models import Candle, OpportunityInput, StrategyDecision
from .paper_long_short_challenger_v0_2 import (
    DirectionalCandidate,
    DirectionalPlan,
    Side,
    build_directional_candidates,
)
from .strategy import evaluate_opportunity
from .technical import TechnicalSnapshot
from .tokenized_equity_challenger_v0_1 import (
    TokenizedEquityMarket,
    tokenized_market_reasons,
)


Regime = Literal["TREND_UP", "TREND_DOWN", "RANGE"]


@dataclass(frozen=True, slots=True)
class IntegratedMarket:
    symbol: str
    asset_class: str
    provider: str
    status: str
    intervals: tuple[str, ...]
    spread_bps: float
    session_model_verified: bool = False
    corporate_action_policy: bool = False


@dataclass(frozen=True, slots=True)
class ResearchContext:
    status: str = "UNAVAILABLE"
    source_count: int = 0
    observed_at_ms: int | None = None

    def __post_init__(self) -> None:
        if self.status not in {"UNAVAILABLE", "NEUTRAL", "ALIGNED", "CONTRADICTORY"}:
            raise ValueError("invalid research-context status")
        if self.source_count < 0:
            raise ValueError("research-context source_count cannot be negative")
        if self.observed_at_ms is not None and self.observed_at_ms < 0:
            raise ValueError("research-context observed_at_ms cannot be negative")


@dataclass(frozen=True, slots=True)
class IntegratedCandidate:
    market: IntegratedMarket
    directional: DirectionalCandidate
    regime: Regime
    volatility_regime: str
    sstate_bridge_mode: str
    formal_strategy_decision: StrategyDecision | None
    research_context: ResearchContext
    stop_source: str
    stop_distance_atr: float
    eligible: bool
    reasons: tuple[str, ...]

    @property
    def plan(self) -> DirectionalPlan | None:
        return self.directional.plan if self.eligible else None

    def evidence(self) -> dict[str, Any]:
        formal = self.formal_strategy_decision
        return {
            "planId": self.directional.plan.plan_id,
            "symbol": self.market.symbol,
            "assetClass": self.market.asset_class,
            "provider": self.market.provider,
            "side": self.directional.plan.side,
            "regime": self.regime,
            "volatilityRegime": self.volatility_regime,
            "eligible": self.eligible,
            "reasons": list(self.reasons),
            "sstateBridgeMode": self.sstate_bridge_mode,
            "formalStrategyScore": formal.score if formal else None,
            "formalStrategyReason": formal.reason if formal else None,
            "technicalCandidateScore": self.directional.score,
            "technicalCandidateReasons": list(self.directional.reasons),
            "technicalFeatures": dict(self.directional.features),
            "stopSource": self.stop_source,
            "stopDistanceAtr": self.stop_distance_atr,
            "researchContext": asdict(self.research_context),
            "researchContextChangesEligibility": False,
        }


@dataclass(frozen=True, slots=True)
class IntegratedPaperTrade:
    plan_id: str
    symbol: str
    asset_class: str
    side: Side
    regime: Regime
    signal_time_ms: int
    entry_time_ms: int
    exit_time_ms: int
    entry_price: float
    initial_stop_price: float
    partial_trigger_price: float
    partial_exit_time_ms: int | None
    partial_exit_price: float | None
    partial_fraction: float
    runner_exit_price: float
    runner_fraction: float
    final_runner_stop_price: float
    quantity: float
    risk_usd: float
    effective_risk_fraction: float
    notional_usd: float
    required_leverage: float
    gross_pnl_usd: float
    fees_usd: float
    funding_usd: float
    slippage_cost_usd: float
    net_pnl_usd: float
    r_multiple: float
    exit_reason: str
    holding_minutes: float


def _r8(value: float) -> float:
    return round(float(value), 8)


def _day_key(time_ms: int) -> str:
    return datetime.fromtimestamp(time_ms / 1000.0, tz=UTC).date().isoformat()


def _classify_regime(advanced: AdvancedTechnicalSnapshot) -> Regime:
    if (advanced.adx14 or 0.0) < 25.0:
        return "RANGE"
    return (
        "TREND_UP"
        if (advanced.plus_di14 or 0.0) >= (advanced.minus_di14 or 0.0)
        else "TREND_DOWN"
    )


def _volatility_regime(advanced: AdvancedTechnicalSnapshot) -> str:
    percentile = advanced.atr_percentile100
    if percentile is None:
        return "UNKNOWN"
    if percentile >= 0.70:
        return "HIGH"
    if percentile <= 0.30:
        return "LOW"
    return "NORMAL"


def _asset_reasons(market: IntegratedMarket, policy: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if market.asset_class not in set(policy["allowed_asset_classes"]):
        reasons.append("asset_class_not_allowed")
        return reasons
    if market.asset_class == "tokenized_stock_candidate":
        tokenized = TokenizedEquityMarket(
            symbol=market.symbol,
            asset_class=market.asset_class,
            status=market.status,
            provider=market.provider,
            intervals=market.intervals,
            session_model_verified=market.session_model_verified,
            corporate_action_policy=market.corporate_action_policy,
            spread_bps=market.spread_bps,
        )
        return tokenized_market_reasons(
            tokenized,
            required_intervals=policy["required_intervals"],
            maximum_spread_bps=float(policy["tokenized_maximum_spread_bps"]),
        )
    if market.provider != policy["required_provider"]:
        reasons.append("provider_not_authorized_for_challenger")
    if market.status != policy["required_status"]:
        reasons.append("market_not_trading")
    if not set(policy["required_intervals"]).issubset(market.intervals):
        reasons.append("required_interval_coverage_missing")
    if not math.isfinite(market.spread_bps) or not (
        0 <= market.spread_bps <= float(policy["crypto_maximum_spread_bps"])
    ):
        reasons.append("spread_gate_failed")
    return reasons


def _short_sstate_reasons(opportunity: OpportunityInput, bridge: Mapping[str, Any]) -> list[str]:
    context = opportunity.sstate
    reasons: list[str] = []
    if context.state not in set(bridge["allowed_states"]):
        reasons.append("short_sstate_state_not_allowed")
    if not context.available or context.probability is None:
        reasons.append("short_sstate_probability_unavailable")
    elif context.probability < float(bridge["minimum_probability"]):
        reasons.append("short_sstate_probability_below_gate")
    if context.samples < int(bridge["minimum_samples"]):
        reasons.append("short_sstate_insufficient_samples")
    return reasons


def _structural_candidate(
    candidate: DirectionalCandidate,
    technical: TechnicalSnapshot,
    policy: Mapping[str, Any],
) -> tuple[DirectionalCandidate, str, float]:
    """Select a bounded structural stop without changing the technical score."""

    atr = float(technical.atr14 or 0.0)
    if atr <= 0:
        return candidate, "INVALID_ATR", 0.0
    minimum_atr = float(policy["minimum_distance_atr"])
    maximum_atr = float(policy["maximum_distance_atr"])
    buffer_atr = float(policy["structure_buffer_atr"])
    half_band_fraction = float(policy["bollinger_half_band_fraction"])
    if not 0 < minimum_atr <= maximum_atr:
        raise ValueError("invalid structural-stop ATR bounds")
    if buffer_atr < 0:
        raise ValueError("structural-stop ATR buffer cannot be negative")
    if not 0 <= half_band_fraction <= 1:
        raise ValueError("Bollinger half-band fraction must be between zero and one")
    side = candidate.plan.side
    reference = float(technical.close)
    configured_sources = set(policy["candidate_sources"])
    values: list[tuple[str, float]] = []
    if "DIRECTIONAL_ATR" in configured_sources:
        values.append(("DIRECTIONAL_ATR", candidate.plan.stop_price))
    for name, attribute in (("EMA20", "ema20"), ("BOLLINGER_MID", "bollinger_mid")):
        if name not in configured_sources:
            continue
        value = getattr(technical, attribute, None)
        if value is None:
            continue
        numeric = float(value)
        if (side == "LONG" and 0 < numeric < reference) or (
            side == "SHORT" and numeric > reference
        ):
            values.append((name, numeric))
    if "BOLLINGER_HALF_BAND" in configured_sources:
        mid = getattr(technical, "bollinger_mid", None)
        outer = (
            getattr(technical, "bollinger_lower", None)
            if side == "LONG"
            else getattr(technical, "bollinger_upper", None)
        )
        if mid is not None and outer is not None:
            half_band = float(mid) + (float(outer) - float(mid)) * half_band_fraction
            if (side == "LONG" and 0 < half_band < reference) or (
                side == "SHORT" and half_band > reference
            ):
                values.append(("BOLLINGER_HALF_BAND", half_band))
    if not values:
        return candidate, "NO_VALID_STRUCTURAL_SOURCE", 0.0
    source, raw_stop = (
        min(values, key=lambda item: item[1])
        if side == "LONG"
        else max(values, key=lambda item: item[1])
    )
    buffer = atr * buffer_atr
    buffered_stop = raw_stop - buffer if side == "LONG" else raw_stop + buffer
    if buffer > 0:
        source = f"{source}_BUFFERED"
    minimum = atr * minimum_atr
    maximum = atr * maximum_atr
    distance = min(max(abs(reference - buffered_stop), minimum), maximum)
    stop = reference - distance if side == "LONG" else reference + distance
    if not math.isclose(stop, buffered_stop, abs_tol=1e-12):
        source = f"{source}_ATR_BOUNDED"
    plan = DirectionalPlan(
        plan_id=candidate.plan.plan_id,
        symbol=candidate.plan.symbol,
        side=side,
        signal_time_ms=candidate.plan.signal_time_ms,
        stop_price=stop,
        target_price=candidate.plan.target_price,
    )
    return (
        DirectionalCandidate(
            plan=plan,
            score=candidate.score,
            eligible=candidate.eligible,
            reasons=candidate.reasons,
            reference_price=candidate.reference_price,
            features=candidate.features,
        ),
        source,
        distance / atr,
    )


def build_integrated_candidates(
    *,
    market: IntegratedMarket,
    opportunity: OpportunityInput,
    technical: TechnicalSnapshot,
    advanced: AdvancedTechnicalSnapshot,
    higher: Sequence[TechnicalSnapshot],
    config: Mapping[str, Any],
    research_context: ResearchContext = ResearchContext(),
) -> tuple[IntegratedCandidate, IntegratedCandidate]:
    """Bridge formal and challenger evidence without adding their scores."""

    if market.symbol != opportunity.symbol:
        raise ValueError("market and SState opportunity symbols must match")
    directional_config = config["technical_candidate"]
    directional = build_directional_candidates(
        symbol=market.symbol,
        technical=technical,
        advanced=advanced,
        higher=higher,
        config=directional_config,
    )
    asset_reasons = _asset_reasons(market, config["asset_policy"])
    bridge = config["sstate_bridge"]
    formal_long = evaluate_opportunity(
        opportunity,
        minimum_probability=float(bridge["minimum_probability"]),
        minimum_samples=int(bridge["minimum_samples"]),
        minimum_score=float(bridge["minimum_long_strategy_score"]),
    )
    regime = _classify_regime(advanced)
    volatility = _volatility_regime(advanced)
    output: list[IntegratedCandidate] = []
    for raw_candidate in directional:
        candidate, stop_source, stop_distance_atr = _structural_candidate(
            raw_candidate, technical, config["stop_policy"]
        )
        side = candidate.plan.side
        reasons = list(asset_reasons)
        formal: StrategyDecision | None = None
        if side == "LONG":
            formal = formal_long
            mode = str(bridge["long_mode"])
            if not formal.eligible:
                reasons.append(f"formal_strategy_{formal.reason}")
        else:
            mode = str(bridge["short_mode"])
            reasons.extend(_short_sstate_reasons(opportunity, bridge))
        if not candidate.eligible:
            reasons.extend(f"technical_{reason}" for reason in candidate.reasons)
        if stop_distance_atr <= 0 or stop_source in {
            "INVALID_ATR",
            "NO_VALID_STRUCTURAL_SOURCE",
        }:
            reasons.append("structural_stop_unavailable")
        reasons = list(dict.fromkeys(reasons))
        output.append(
            IntegratedCandidate(
                market=market,
                directional=candidate,
                regime=regime,
                volatility_regime=volatility,
                sstate_bridge_mode=mode,
                formal_strategy_decision=formal,
                research_context=research_context,
                stop_source=stop_source,
                stop_distance_atr=stop_distance_atr,
                eligible=not reasons,
                reasons=tuple(reasons) if reasons else ("eligible_integrated_paper_candidate",),
            )
        )
    return tuple(output)  # type: ignore[return-value]


def _validate_candles(candles: Sequence[Candle], symbol: str) -> tuple[Candle, ...]:
    prepared = tuple(candles)
    previous = -1
    for candle in prepared:
        if candle.time_ms <= previous:
            raise ValueError(f"candles must be strictly increasing for {symbol}")
        values = (candle.open, candle.high, candle.low, candle.close, candle.volume)
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"non-finite candle value for {symbol}")
        if min(candle.open, candle.high, candle.low, candle.close) <= 0 or candle.volume < 0:
            raise ValueError(f"invalid candle value for {symbol}")
        if (
            candle.low > candle.high
            or candle.low > min(candle.open, candle.close)
            or candle.high < max(candle.open, candle.close)
        ):
            raise ValueError(f"invalid candle range for {symbol}")
        previous = candle.time_ms
    return prepared


def _entry_index(candles: Sequence[Candle], signal_time_ms: int) -> int | None:
    return next(
        (index for index, candle in enumerate(candles) if candle.time_ms > signal_time_ms),
        None,
    )


def _adverse_price(raw_price: float, *, side: Side, entry: bool, slip: float) -> float:
    if (side == "LONG") == entry:
        return raw_price * (1.0 + slip)
    return raw_price * (1.0 - slip)


def _signed_pnl(side: Side, quantity: float, entry: float, exit_price: float) -> float:
    return quantity * (exit_price - entry if side == "LONG" else entry - exit_price)


def _stop_hit(candle: Candle, side: Side, stop: float) -> bool:
    return candle.low <= stop if side == "LONG" else candle.high >= stop


def _level_hit(candle: Candle, side: Side, level: float) -> bool:
    return candle.high >= level if side == "LONG" else candle.low <= level


def _cost_adjusted_breakeven(entry: float, side: Side, fee: float, slip: float) -> float:
    cost = 2.0 * (fee + slip)
    return entry * (1.0 + cost if side == "LONG" else 1.0 - cost)


def _simulate_integrated_plan(
    *,
    candidate: IntegratedCandidate,
    candles: Sequence[Candle],
    funding_points: Sequence[FundingPoint],
    equity_usd: float,
    config: Mapping[str, Any],
) -> tuple[IntegratedPaperTrade | None, str | None, dict[str, float]]:
    plan = candidate.directional.plan
    prepared = _validate_candles(candles, plan.symbol)
    index = _entry_index(prepared, plan.signal_time_ms)
    if index is None:
        return None, "no_future_entry_bar", {}
    risk_config = config["portfolio_risk"]
    exit_config = config["exit_policy"]
    cost_config = config["cost_model"]
    fee = float(cost_config["taker_fee_bps"]) / 10_000.0
    slip = float(cost_config["slippage_bps"]) / 10_000.0
    entry_candle = prepared[index]
    entry_price = _adverse_price(entry_candle.open, side=plan.side, entry=True, slip=slip)
    if plan.side == "LONG" and not plan.stop_price < entry_price < plan.target_price:
        return None, "invalid_long_risk_geometry", {}
    if plan.side == "SHORT" and not plan.target_price < entry_price < plan.stop_price:
        return None, "invalid_short_risk_geometry", {}

    risk_distance = abs(entry_price - plan.stop_price)
    stop_fraction = risk_distance / entry_price
    risk_usd = equity_usd * float(risk_config["maximum_risk_fraction_per_trade"])
    notional = risk_usd / stop_fraction
    leverage = notional / equity_usd
    diagnostics = {
        "risk_usd": risk_usd,
        "notional_usd": notional,
        "required_leverage": leverage,
        "effective_risk_fraction": risk_usd / equity_usd,
    }
    if leverage > float(risk_config["maximum_leverage"]):
        return None, "required_leverage_exceeds_cap", diagnostics

    sign = 1.0 if plan.side == "LONG" else -1.0
    partial_trigger = entry_price + sign * risk_distance * float(exit_config["partial_at_r"])
    if plan.side == "LONG" and not entry_price < partial_trigger <= plan.target_price:
        return None, "partial_trigger_outside_long_geometry", diagnostics
    if plan.side == "SHORT" and not plan.target_price <= partial_trigger < entry_price:
        return None, "partial_trigger_outside_short_geometry", diagnostics

    quantity = notional / entry_price
    partial_fraction = float(exit_config["partial_fraction"])
    runner_fraction = float(exit_config["runner_fraction"])
    partial_quantity = quantity * partial_fraction
    runner_quantity = quantity * runner_fraction
    if not math.isclose(partial_fraction + runner_fraction, 1.0, abs_tol=1e-12):
        raise ValueError("partial and runner fractions must sum to one")

    deadline = entry_candle.time_ms + int(exit_config["maximum_holding_minutes"]) * 60_000
    current_stop = plan.stop_price
    trailing_distance = risk_distance * float(exit_config["runner_trailing_distance_r"])
    extreme = entry_price
    partial_time: int | None = None
    partial_price: float | None = None
    runner_time: int | None = None
    runner_price: float | None = None
    runner_raw_exit: float | None = None
    exit_reason = "end_of_data"

    for candle in prepared[index:]:
        if bool(exit_config["hard_time_exit"]) and candle.time_ms >= deadline:
            runner_time = candle.time_ms
            runner_raw_exit = candle.open
            runner_price = _adverse_price(
                runner_raw_exit, side=plan.side, entry=False, slip=slip
            )
            exit_reason = "time_exit"
            break

        stop_hit = _stop_hit(candle, plan.side, current_stop)
        target_hit = bool(exit_config["fixed_directional_target_enabled"]) and _level_hit(
            candle, plan.side, plan.target_price
        )
        if partial_time is None:
            partial_hit = _level_hit(candle, plan.side, partial_trigger)
            if stop_hit and (partial_hit or target_hit):
                runner_time = candle.time_ms
                runner_raw_exit = current_stop
                runner_price = _adverse_price(
                    current_stop, side=plan.side, entry=False, slip=slip
                )
                exit_reason = "stop_same_bar_collision"
                break
            if stop_hit:
                runner_time = candle.time_ms
                runner_raw_exit = current_stop
                runner_price = _adverse_price(
                    current_stop, side=plan.side, entry=False, slip=slip
                )
                exit_reason = "stop"
                break
            if partial_hit:
                partial_time = candle.time_ms
                partial_price = _adverse_price(
                    partial_trigger, side=plan.side, entry=False, slip=slip
                )
                if target_hit:
                    runner_time = candle.time_ms
                    runner_raw_exit = plan.target_price
                    runner_price = _adverse_price(
                        plan.target_price, side=plan.side, entry=False, slip=slip
                    )
                    exit_reason = "target_after_partial_same_bar"
                    break
                if bool(exit_config["move_runner_stop_to_cost_adjusted_breakeven"]):
                    breakeven = _cost_adjusted_breakeven(entry_price, plan.side, fee, slip)
                    current_stop = (
                        max(current_stop, breakeven)
                        if plan.side == "LONG"
                        else min(current_stop, breakeven)
                    )
                extreme = candle.high if plan.side == "LONG" else candle.low
                trailing = (
                    extreme - trailing_distance
                    if plan.side == "LONG"
                    else extreme + trailing_distance
                )
                current_stop = (
                    max(current_stop, trailing)
                    if plan.side == "LONG"
                    else min(current_stop, trailing)
                )
            continue

        if stop_hit and target_hit:
            runner_time = candle.time_ms
            runner_raw_exit = current_stop
            runner_price = _adverse_price(current_stop, side=plan.side, entry=False, slip=slip)
            exit_reason = "runner_stop_same_bar_collision"
            break
        if stop_hit:
            runner_time = candle.time_ms
            runner_raw_exit = current_stop
            runner_price = _adverse_price(current_stop, side=plan.side, entry=False, slip=slip)
            exit_reason = "runner_stop"
            break
        if target_hit:
            runner_time = candle.time_ms
            runner_raw_exit = plan.target_price
            runner_price = _adverse_price(
                plan.target_price, side=plan.side, entry=False, slip=slip
            )
            exit_reason = "runner_target"
            break
        extreme = (
            max(extreme, candle.high) if plan.side == "LONG" else min(extreme, candle.low)
        )
        trailing = (
            extreme - trailing_distance if plan.side == "LONG" else extreme + trailing_distance
        )
        current_stop = (
            max(current_stop, trailing) if plan.side == "LONG" else min(current_stop, trailing)
        )

    if runner_time is None or runner_price is None or runner_raw_exit is None:
        final = prepared[-1]
        runner_time = final.time_ms
        runner_raw_exit = final.close
        runner_price = _adverse_price(final.close, side=plan.side, entry=False, slip=slip)

    if partial_time is None:
        gross_pnl = _signed_pnl(plan.side, quantity, entry_price, runner_price)
        exit_notional = quantity * runner_price
        slippage_cost = quantity * abs(entry_price - entry_candle.open) + quantity * abs(
            runner_price - runner_raw_exit
        )
        actual_partial_fraction = 0.0
        actual_runner_fraction = 1.0
    else:
        assert partial_price is not None
        gross_pnl = _signed_pnl(
            plan.side, partial_quantity, entry_price, partial_price
        ) + _signed_pnl(plan.side, runner_quantity, entry_price, runner_price)
        exit_notional = partial_quantity * partial_price + runner_quantity * runner_price
        slippage_cost = (
            quantity * abs(entry_price - entry_candle.open)
            + partial_quantity * abs(partial_price - partial_trigger)
            + runner_quantity * abs(runner_price - runner_raw_exit)
        )
        actual_partial_fraction = partial_fraction
        actual_runner_fraction = runner_fraction

    fees = notional * fee + exit_notional * fee
    funding = 0.0
    for point in funding_points:
        if point.symbol != plan.symbol or not entry_candle.time_ms <= point.time_ms <= runner_time:
            continue
        exposure_fraction = (
            1.0 if partial_time is None or point.time_ms <= partial_time else runner_fraction
        )
        direction = 1.0 if plan.side == "LONG" else -1.0
        funding += notional * exposure_fraction * point.rate * direction
    net_pnl = gross_pnl - fees - funding
    return (
        IntegratedPaperTrade(
            plan_id=plan.plan_id,
            symbol=plan.symbol,
            asset_class=candidate.market.asset_class,
            side=plan.side,
            regime=candidate.regime,
            signal_time_ms=plan.signal_time_ms,
            entry_time_ms=entry_candle.time_ms,
            exit_time_ms=runner_time,
            entry_price=_r8(entry_price),
            initial_stop_price=_r8(plan.stop_price),
            partial_trigger_price=_r8(partial_trigger),
            partial_exit_time_ms=partial_time,
            partial_exit_price=None if partial_price is None else _r8(partial_price),
            partial_fraction=_r8(actual_partial_fraction),
            runner_exit_price=_r8(runner_price),
            runner_fraction=_r8(actual_runner_fraction),
            final_runner_stop_price=_r8(current_stop),
            quantity=_r8(quantity),
            risk_usd=_r8(risk_usd),
            effective_risk_fraction=_r8(risk_usd / equity_usd),
            notional_usd=_r8(notional),
            required_leverage=_r8(leverage),
            gross_pnl_usd=_r8(gross_pnl),
            fees_usd=_r8(fees),
            funding_usd=_r8(funding),
            slippage_cost_usd=_r8(slippage_cost),
            net_pnl_usd=_r8(net_pnl),
            r_multiple=_r8(net_pnl / risk_usd),
            exit_reason=exit_reason,
            holding_minutes=_r8((runner_time - entry_candle.time_ms) / 60_000.0),
        ),
        None,
        diagnostics,
    )


def _aggregate_metrics(
    trades: Sequence[IntegratedPaperTrade],
    *,
    initial_equity: float,
    final_equity: float,
    equity_curve: Sequence[float],
) -> dict[str, Any]:
    wins = [trade for trade in trades if trade.net_pnl_usd > 0]
    losses = [trade for trade in trades if trade.net_pnl_usd < 0]
    peak = initial_equity
    maximum_drawdown = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        maximum_drawdown = max(
            maximum_drawdown, (peak - equity) / peak if peak > 0 else 0.0
        )
    gross_loss = -sum(trade.net_pnl_usd for trade in losses)
    by_side: dict[str, dict[str, float | int]] = {}
    for side in ("LONG", "SHORT"):
        selected = [trade for trade in trades if trade.side == side]
        by_side[side] = {
            "trade_count": len(selected),
            "net_pnl_usd": _r8(sum(trade.net_pnl_usd for trade in selected)),
            "average_r_multiple": _r8(
                sum(trade.r_multiple for trade in selected) / len(selected)
            )
            if selected
            else 0.0,
        }
    return {
        "trade_count": len(trades),
        "win_count": len(wins),
        "loss_count": len(losses),
        "win_rate": _r8(len(wins) / len(trades)) if trades else 0.0,
        "net_pnl_usd": _r8(final_equity - initial_equity),
        "return_pct": _r8((final_equity / initial_equity - 1.0) * 100.0),
        "maximum_drawdown_pct": _r8(maximum_drawdown * 100.0),
        "profit_factor": None
        if gross_loss == 0
        else _r8(sum(trade.net_pnl_usd for trade in wins) / gross_loss),
        "average_r_multiple": _r8(
            sum(trade.r_multiple for trade in trades) / len(trades)
        )
        if trades
        else 0.0,
        "partial_exit_count": sum(trade.partial_exit_time_ms is not None for trade in trades),
        "total_fees_usd": _r8(sum(trade.fees_usd for trade in trades)),
        "total_funding_usd": _r8(sum(trade.funding_usd for trade in trades)),
        "total_slippage_cost_usd": _r8(
            sum(trade.slippage_cost_usd for trade in trades)
        ),
        "by_side": by_side,
        "by_asset_class": dict(Counter(trade.asset_class for trade in trades)),
        "by_regime": dict(Counter(trade.regime for trade in trades)),
        "by_exit_reason": dict(Counter(trade.exit_reason for trade in trades)),
    }


def run_integrated_paper_replay(
    *,
    candidates: Sequence[IntegratedCandidate],
    candles_by_symbol: Mapping[str, Sequence[Candle]],
    funding_points: Sequence[FundingPoint] = (),
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Run the integrated candidate stream as a one-position paper portfolio."""

    plan_ids = [candidate.directional.plan.plan_id for candidate in candidates]
    if len(plan_ids) != len(set(plan_ids)):
        raise ValueError("integrated candidate plan_id values must be unique")
    risk_config = config["portfolio_risk"]
    if int(risk_config["maximum_concurrent_positions"]) != 1:
        raise ValueError("V0.2 supports exactly one concurrent portfolio position")

    initial = float(risk_config["initial_equity_usd"])
    equity = initial
    equity_curve = [initial]
    portfolio_available_after_ms = -1
    trades: list[IntegratedPaperTrade] = []
    rejected_candidates: list[list[str]] = []
    rejected_plans: list[list[str]] = []
    new_trades_by_day: dict[str, int] = defaultdict(int)
    realized_r_by_day: dict[str, float] = defaultdict(float)
    leverage_evaluated = 0
    leverage_rejections = 0
    accepted_effective_risk: list[float] = []

    for candidate in sorted(
        candidates,
        key=lambda item: (
            item.directional.plan.signal_time_ms,
            item.market.symbol,
            item.directional.plan.side,
            item.directional.plan.plan_id,
        ),
    ):
        plan = candidate.plan
        if plan is None:
            rejected_candidates.append(
                [candidate.directional.plan.plan_id, *candidate.reasons]
            )
            continue
        if plan.signal_time_ms < portfolio_available_after_ms:
            rejected_plans.append([plan.plan_id, "position_overlap"])
            continue
        candles = candles_by_symbol.get(plan.symbol, ())
        prepared = _validate_candles(candles, plan.symbol)
        entry_index = _entry_index(prepared, plan.signal_time_ms)
        if entry_index is None:
            rejected_plans.append([plan.plan_id, "no_future_entry_bar"])
            continue
        entry_day = _day_key(prepared[entry_index].time_ms)
        if realized_r_by_day[entry_day] <= -float(risk_config["daily_loss_limit_r"]):
            rejected_plans.append([plan.plan_id, "daily_loss_gate"])
            continue
        if new_trades_by_day[entry_day] >= int(
            risk_config["maximum_new_trades_per_utc_day"]
        ):
            rejected_plans.append([plan.plan_id, "daily_trade_count_gate"])
            continue
        trade, reason, diagnostics = _simulate_integrated_plan(
            candidate=candidate,
            candles=prepared,
            funding_points=funding_points,
            equity_usd=equity,
            config=config,
        )
        if diagnostics:
            leverage_evaluated += 1
        if trade is None:
            rejected_plans.append([plan.plan_id, reason or "no_trade"])
            leverage_rejections += int(reason == "required_leverage_exceeds_cap")
            continue
        trades.append(trade)
        new_trades_by_day[entry_day] += 1
        accepted_effective_risk.append(trade.effective_risk_fraction)
        equity = _r8(equity + trade.net_pnl_usd)
        equity_curve.append(equity)
        realized_r_by_day[_day_key(trade.exit_time_ms)] += trade.r_multiple
        portfolio_available_after_ms = trade.exit_time_ms

    symbol_counts = Counter(trade.symbol for trade in trades)
    maximum_symbol_fraction = (
        max(symbol_counts.values()) / len(trades) if trades else 0.0
    )
    return {
        "schema": "integrated-paper-strategy-replay-v0.2",
        "status": "PASS",
        "mode": "INTEGRATED_PAPER_CHALLENGER_ONLY",
        "candidateCount": len(candidates),
        "eligibleCandidateCount": sum(candidate.eligible for candidate in candidates),
        "candidateEvidence": [candidate.evidence() for candidate in candidates],
        "paperTrades": [asdict(trade) for trade in trades],
        "rejectedCandidates": rejected_candidates,
        "rejectedPlans": rejected_plans,
        "initialEquityUsd": _r8(initial),
        "finalEquityUsd": _r8(equity),
        "equityCurve": [_r8(value) for value in equity_curve],
        "metrics": _aggregate_metrics(
            trades,
            initial_equity=initial,
            final_equity=equity,
            equity_curve=equity_curve,
        ),
        "riskDiagnostics": {
            "leverage_evaluated_count": leverage_evaluated,
            "required_leverage_exceeds_cap_count": leverage_rejections,
            "leverage_rejection_fraction": _r8(
                leverage_rejections / leverage_evaluated
            )
            if leverage_evaluated
            else 0.0,
            "average_effective_risk_fraction": _r8(
                sum(accepted_effective_risk) / len(accepted_effective_risk)
            )
            if accepted_effective_risk
            else 0.0,
            "maximum_single_symbol_fraction": _r8(maximum_symbol_fraction),
            "maximum_concurrent_positions": 1,
        },
        "interpretation": {
            "sstate_and_technical_scores_not_added": True,
            "short_sstate_semantics_context_only": True,
            "research_context_changes_eligibility": False,
            "tokenized_asset_class_isolated": True,
            "results_are_research_evidence_not_profitability_proof": True,
        },
        "authority": dict(config["authority"]),
    }
