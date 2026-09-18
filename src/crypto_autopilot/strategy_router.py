from __future__ import annotations

import math
from dataclasses import dataclass

from .features.regime import MarketRegimeSnapshot
from .features.structure import MarketStructureSnapshot
from .opportunity_engine import DailyOpportunityDecision
from .strategy_library import strategy_family_ids
from .technical import TechnicalSnapshot


STRATEGY_FAMILIES = strategy_family_ids()


@dataclass(frozen=True, slots=True)
class StrategyRouterPolicy:
    """Deterministic research-only strategy-family compatibility policy."""

    trend_slope_atr_floor: float = 0.15
    momentum_rsi_long_floor: float = 60.0
    momentum_rsi_short_ceiling: float = 40.0
    momentum_volume_ratio_floor: float = 1.10
    breakout_volume_ratio_floor: float = 1.00
    high_volatility_atr_fraction_floor: float = 0.03
    low_volatility_atr_fraction_ceiling: float = 0.015
    mean_reversion_rsi_long_ceiling: float = 35.0
    mean_reversion_rsi_short_floor: float = 65.0
    mean_reversion_bollinger_long_ceiling: float = 0.20
    mean_reversion_bollinger_short_floor: float = 0.80
    require_ready_regime: bool = True

    def __post_init__(self) -> None:
        values = (
            self.trend_slope_atr_floor,
            self.momentum_rsi_long_floor,
            self.momentum_rsi_short_ceiling,
            self.momentum_volume_ratio_floor,
            self.breakout_volume_ratio_floor,
            self.high_volatility_atr_fraction_floor,
            self.low_volatility_atr_fraction_ceiling,
            self.mean_reversion_rsi_long_ceiling,
            self.mean_reversion_rsi_short_floor,
            self.mean_reversion_bollinger_long_ceiling,
            self.mean_reversion_bollinger_short_floor,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("strategy router policy values must be finite")
        if self.trend_slope_atr_floor < 0.0:
            raise ValueError("trend_slope_atr_floor cannot be negative")
        if self.momentum_volume_ratio_floor <= 0.0:
            raise ValueError("momentum_volume_ratio_floor must be positive")
        if self.breakout_volume_ratio_floor <= 0.0:
            raise ValueError("breakout_volume_ratio_floor must be positive")
        if self.high_volatility_atr_fraction_floor < 0.0:
            raise ValueError("high_volatility_atr_fraction_floor cannot be negative")
        if self.low_volatility_atr_fraction_ceiling < 0.0:
            raise ValueError("low_volatility_atr_fraction_ceiling cannot be negative")
        if not 0.0 <= self.momentum_rsi_short_ceiling < self.momentum_rsi_long_floor <= 100.0:
            raise ValueError("momentum RSI bounds must be ordered within [0, 100]")
        if not 0.0 <= self.mean_reversion_rsi_long_ceiling < self.mean_reversion_rsi_short_floor <= 100.0:
            raise ValueError("mean-reversion RSI bounds must be ordered within [0, 100]")
        if not (
            0.0
            <= self.mean_reversion_bollinger_long_ceiling
            < self.mean_reversion_bollinger_short_floor
            <= 1.0
        ):
            raise ValueError("mean-reversion Bollinger bounds must be ordered within [0, 1]")


@dataclass(frozen=True, slots=True)
class StrategyRouteMatch:
    family: str
    direction: str
    regime_state: str
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StrategyRoutingDecision:
    symbol: str
    status: str
    regime_state: str
    matches: tuple[StrategyRouteMatch, ...]
    reasons: tuple[str, ...]


def _direction_from_bias(bias: str) -> str | None:
    if bias == "LONG_BIAS":
        return "LONG"
    if bias == "SHORT_BIAS":
        return "SHORT"
    return None


def _macro_direction_allowed(direction: str, regime_state: str) -> bool:
    """Conservative research compatibility, not a profitability claim."""

    if direction == "LONG":
        return regime_state != "BROAD_RISK_OFF"
    if direction == "SHORT":
        return regime_state != "ALT_EXPANSION"
    raise ValueError(f"unsupported direction: {direction}")


def _trend_match(
    opportunity: DailyOpportunityDecision,
    technical: TechnicalSnapshot,
    structure: MarketStructureSnapshot | None,
    regime: MarketRegimeSnapshot,
    policy: StrategyRouterPolicy,
) -> StrategyRouteMatch | None:
    if opportunity.attention_profile != "DIRECTIONAL" or structure is None:
        return None

    direction = _direction_from_bias(opportunity.bias)
    if direction is None or not _macro_direction_allowed(direction, regime.state):
        return None

    assert technical.ema20 is not None
    assert technical.ema50 is not None
    assert technical.ema200 is not None
    assert technical.ema20_slope_atr is not None
    assert technical.macd_histogram is not None

    if direction == "LONG":
        matched = (
            technical.ema20 > technical.ema50 > technical.ema200
            and technical.ema20_slope_atr >= policy.trend_slope_atr_floor
            and technical.macd_histogram > 0.0
            and structure.market_structure_state == "UP"
        )
        reasons = (
            "bullish_ema_stack",
            "positive_ema20_slope",
            "positive_macd_histogram",
            "up_market_structure",
            "macro_not_broad_risk_off",
        )
    else:
        matched = (
            technical.ema20 < technical.ema50 < technical.ema200
            and technical.ema20_slope_atr <= -policy.trend_slope_atr_floor
            and technical.macd_histogram < 0.0
            and structure.market_structure_state == "DOWN"
        )
        reasons = (
            "bearish_ema_stack",
            "negative_ema20_slope",
            "negative_macd_histogram",
            "down_market_structure",
            "macro_not_alt_expansion",
        )

    if not matched:
        return None
    return StrategyRouteMatch("TREND_FOLLOWING", direction, regime.state, reasons)


def _breakout_match(
    opportunity: DailyOpportunityDecision,
    technical: TechnicalSnapshot,
    structure: MarketStructureSnapshot | None,
    regime: MarketRegimeSnapshot,
    policy: StrategyRouterPolicy,
) -> StrategyRouteMatch | None:
    if structure is None:
        return None

    direction = _direction_from_bias(opportunity.bias)
    if direction is None or not _macro_direction_allowed(direction, regime.state):
        return None

    assert technical.volume_ratio is not None
    if technical.volume_ratio < policy.breakout_volume_ratio_floor:
        return None

    if direction == "LONG" and structure.breakout_above_previous_range:
        return StrategyRouteMatch(
            "BREAKOUT",
            "LONG",
            regime.state,
            (
                "closed_bar_breakout_above_previous_range",
                "volume_participation",
                "macro_not_broad_risk_off",
            ),
        )
    if direction == "SHORT" and structure.breakdown_below_previous_range:
        return StrategyRouteMatch(
            "BREAKOUT",
            "SHORT",
            regime.state,
            (
                "closed_bar_breakdown_below_previous_range",
                "volume_participation",
                "macro_not_alt_expansion",
            ),
        )
    return None


def _momentum_match(
    opportunity: DailyOpportunityDecision,
    technical: TechnicalSnapshot,
    regime: MarketRegimeSnapshot,
    policy: StrategyRouterPolicy,
) -> StrategyRouteMatch | None:
    if opportunity.attention_profile != "DIRECTIONAL":
        return None

    direction = _direction_from_bias(opportunity.bias)
    if direction is None or not _macro_direction_allowed(direction, regime.state):
        return None

    assert technical.ema20_slope_atr is not None
    assert technical.macd_histogram is not None
    assert technical.rsi14 is not None
    assert technical.volume_ratio is not None

    if direction == "LONG":
        matched = (
            technical.ema20_slope_atr > 0.0
            and technical.macd_histogram > 0.0
            and technical.rsi14 >= policy.momentum_rsi_long_floor
            and technical.volume_ratio >= policy.momentum_volume_ratio_floor
        )
        reasons = (
            "positive_ema20_slope",
            "positive_macd_histogram",
            "bullish_momentum_rsi",
            "elevated_volume",
            "macro_not_broad_risk_off",
        )
    else:
        matched = (
            technical.ema20_slope_atr < 0.0
            and technical.macd_histogram < 0.0
            and technical.rsi14 <= policy.momentum_rsi_short_ceiling
            and technical.volume_ratio >= policy.momentum_volume_ratio_floor
        )
        reasons = (
            "negative_ema20_slope",
            "negative_macd_histogram",
            "bearish_momentum_rsi",
            "elevated_volume",
            "macro_not_alt_expansion",
        )

    if not matched:
        return None
    return StrategyRouteMatch("MOMENTUM", direction, regime.state, reasons)


def _mean_reversion_direction(
    technical: TechnicalSnapshot,
    policy: StrategyRouterPolicy,
) -> tuple[str, tuple[str, ...]] | None:
    assert technical.rsi14 is not None
    assert technical.bollinger_position is not None

    if (
        technical.rsi14 <= policy.mean_reversion_rsi_long_ceiling
        and technical.bollinger_position <= policy.mean_reversion_bollinger_long_ceiling
    ):
        return "LONG", ("oversold_rsi", "lower_bollinger_extreme")
    if (
        technical.rsi14 >= policy.mean_reversion_rsi_short_floor
        and technical.bollinger_position >= policy.mean_reversion_bollinger_short_floor
    ):
        return "SHORT", ("overbought_rsi", "upper_bollinger_extreme")
    return None


def _mean_reversion_match(
    opportunity: DailyOpportunityDecision,
    technical: TechnicalSnapshot,
    structure: MarketStructureSnapshot | None,
    regime: MarketRegimeSnapshot,
    policy: StrategyRouterPolicy,
) -> StrategyRouteMatch | None:
    if (
        opportunity.attention_profile != "RANGE_EXTREMITY"
        or structure is None
        or structure.market_structure_state != "RANGE"
    ):
        return None

    direction_info = _mean_reversion_direction(technical, policy)
    if direction_info is None:
        return None
    direction, reasons = direction_info
    if not _macro_direction_allowed(direction, regime.state):
        return None
    return StrategyRouteMatch(
        "MEAN_REVERSION",
        direction,
        regime.state,
        reasons + ("range_market_structure", "macro_direction_compatible"),
    )


def _high_volatility_trend_match(
    opportunity: DailyOpportunityDecision,
    technical: TechnicalSnapshot,
    structure: MarketStructureSnapshot | None,
    regime: MarketRegimeSnapshot,
    policy: StrategyRouterPolicy,
) -> StrategyRouteMatch | None:
    if opportunity.attention_profile != "DIRECTIONAL" or structure is None:
        return None

    direction = _direction_from_bias(opportunity.bias)
    if direction is None or not _macro_direction_allowed(direction, regime.state):
        return None

    assert technical.atr14_fraction is not None
    assert technical.ema20_slope_atr is not None
    assert technical.macd_histogram is not None
    assert technical.volume_ratio is not None

    if technical.atr14_fraction < policy.high_volatility_atr_fraction_floor:
        return None

    if direction == "LONG":
        matched = (
            technical.ema20_slope_atr >= policy.trend_slope_atr_floor
            and technical.macd_histogram > 0.0
            and technical.volume_ratio >= policy.breakout_volume_ratio_floor
            and structure.market_structure_state == "UP"
        )
    else:
        matched = (
            technical.ema20_slope_atr <= -policy.trend_slope_atr_floor
            and technical.macd_histogram < 0.0
            and technical.volume_ratio >= policy.breakout_volume_ratio_floor
            and structure.market_structure_state == "DOWN"
        )
    if not matched:
        return None

    return StrategyRouteMatch(
        "HIGH_VOLATILITY_TREND",
        direction,
        regime.state,
        (
            "high_atr_fraction",
            "directional_slope",
            "directional_macd",
            "volume_participation",
            "directional_market_structure",
        ),
    )


def _low_volatility_range_match(
    opportunity: DailyOpportunityDecision,
    technical: TechnicalSnapshot,
    structure: MarketStructureSnapshot | None,
    regime: MarketRegimeSnapshot,
    policy: StrategyRouterPolicy,
) -> StrategyRouteMatch | None:
    if (
        opportunity.attention_profile != "RANGE_EXTREMITY"
        or structure is None
        or structure.market_structure_state != "RANGE"
    ):
        return None

    assert technical.atr14_fraction is not None
    if technical.atr14_fraction > policy.low_volatility_atr_fraction_ceiling:
        return None

    direction_info = _mean_reversion_direction(technical, policy)
    if direction_info is None:
        return None
    direction, reasons = direction_info
    if not _macro_direction_allowed(direction, regime.state):
        return None

    return StrategyRouteMatch(
        "LOW_VOLATILITY_RANGE",
        direction,
        regime.state,
        reasons + ("range_market_structure", "low_atr_fraction"),
    )


def route_strategy_families(
    opportunity: DailyOpportunityDecision,
    technical: TechnicalSnapshot | None,
    regime: MarketRegimeSnapshot | None,
    structure: MarketStructureSnapshot | None,
    *,
    as_of_ms: int,
    policy: StrategyRouterPolicy = StrategyRouterPolicy(),
) -> StrategyRoutingDecision:
    """Route one attention candidate to zero or more research strategy families.

    The router performs no provider/storage I/O, position sizing, portfolio
    selection, strategy promotion, order planning, or execution. Multiple
    matches are intentionally preserved for downstream portfolio/risk logic.
    """

    if as_of_ms < 0:
        raise ValueError("as_of_ms cannot be negative")
    if not opportunity.eligible:
        return StrategyRoutingDecision(
            opportunity.symbol,
            "NO_TRADE",
            "UNAVAILABLE",
            (),
            ("candidate_not_eligible",),
        )
    if (
        technical is None
        or technical.available_at_ms > as_of_ms
        or not technical.ready_v0_2
    ):
        return StrategyRoutingDecision(
            opportunity.symbol,
            "NO_TRADE",
            "UNAVAILABLE",
            (),
            ("technical_evidence_unavailable",),
        )
    if (
        regime is None
        or regime.available_at_ms > as_of_ms
        or (policy.require_ready_regime and not regime.ready)
    ):
        return StrategyRoutingDecision(
            opportunity.symbol,
            "NO_TRADE",
            "UNAVAILABLE",
            (),
            ("regime_evidence_unavailable",),
        )

    visible_structure = structure
    if (
        visible_structure is not None
        and (
            visible_structure.available_at_ms > as_of_ms
            or not visible_structure.ready
        )
    ):
        visible_structure = None

    matches = tuple(
        match
        for match in (
            _trend_match(opportunity, technical, visible_structure, regime, policy),
            _breakout_match(opportunity, technical, visible_structure, regime, policy),
            _momentum_match(opportunity, technical, regime, policy),
            _mean_reversion_match(
                opportunity, technical, visible_structure, regime, policy
            ),
            _high_volatility_trend_match(
                opportunity, technical, visible_structure, regime, policy
            ),
            _low_volatility_range_match(
                opportunity, technical, visible_structure, regime, policy
            ),
        )
        if match is not None
    )

    registered = set(STRATEGY_FAMILIES)
    if any(match.family not in registered for match in matches):
        raise ValueError("router emitted an unregistered strategy family")

    if not matches:
        return StrategyRoutingDecision(
            opportunity.symbol,
            "NO_TRADE",
            regime.state,
            (),
            ("no_strategy_family_matched",),
        )

    return StrategyRoutingDecision(
        opportunity.symbol,
        "ROUTES_READY",
        regime.state,
        matches,
        ("research_compatibility_only", "downstream_portfolio_risk_required"),
    )
