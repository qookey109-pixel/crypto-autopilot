from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .features.regime import MarketRegimeSnapshot
from .technical import TechnicalSnapshot
from .universe import UniverseCandidate


@dataclass(frozen=True, slots=True)
class DailyOpportunityPolicy:
    """Transparent V0.1 research-ranking policy.

    The score ranks attention candidates only. It is not a strategy decision,
    position-sizing instruction, trade plan, or order authority.
    """

    maximum_candidates: int = 5
    minimum_attention_score: float = 65.0
    maximum_spread_bps: float = 30.0
    volume_ratio_floor: float = 1.0
    bullish_rsi_floor: float = 55.0
    bearish_rsi_ceiling: float = 45.0
    bullish_bollinger_position_floor: float = 0.55
    bearish_bollinger_position_ceiling: float = 0.45
    require_ready_regime: bool = True

    def __post_init__(self) -> None:
        numeric = (
            self.minimum_attention_score,
            self.maximum_spread_bps,
            self.volume_ratio_floor,
            self.bullish_rsi_floor,
            self.bearish_rsi_ceiling,
            self.bullish_bollinger_position_floor,
            self.bearish_bollinger_position_ceiling,
        )
        if not all(math.isfinite(value) for value in numeric):
            raise ValueError("daily opportunity policy values must be finite")
        if self.maximum_candidates < 1:
            raise ValueError("maximum_candidates must be positive")
        if not 0.0 <= self.minimum_attention_score <= 100.0:
            raise ValueError("minimum_attention_score must be in [0, 100]")
        if self.maximum_spread_bps <= 0.0:
            raise ValueError("maximum_spread_bps must be positive")
        if self.volume_ratio_floor <= 0.0:
            raise ValueError("volume_ratio_floor must be positive")
        if not 0.0 <= self.bullish_rsi_floor <= 100.0:
            raise ValueError("bullish_rsi_floor must be in [0, 100]")
        if not 0.0 <= self.bearish_rsi_ceiling <= 100.0:
            raise ValueError("bearish_rsi_ceiling must be in [0, 100]")


@dataclass(frozen=True, slots=True)
class DailyOpportunityDecision:
    symbol: str
    eligible: bool
    attention_score: float
    bias: str
    liquidity_score: float
    directional_score: float
    regime_state: str
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DailyOpportunityReport:
    as_of_ms: int
    status: str
    regime_state: str
    evaluated: tuple[DailyOpportunityDecision, ...]
    selected: tuple[DailyOpportunityDecision, ...]


def _liquidity_score(
    *,
    index: int,
    count: int,
    spread_bps: float,
    maximum_spread_bps: float,
) -> float:
    if count <= 1:
        turnover_points = 15.0
    else:
        turnover_points = 15.0 * (count - index - 1) / (count - 1)
    spread_points = 10.0 * max(0.0, 1.0 - spread_bps / maximum_spread_bps)
    return turnover_points + spread_points


def _directional_score(
    snapshot: TechnicalSnapshot,
    *,
    direction: str,
    policy: DailyOpportunityPolicy,
) -> tuple[float, tuple[str, ...]]:
    assert snapshot.ema20 is not None
    assert snapshot.ema50 is not None
    assert snapshot.ema200 is not None
    assert snapshot.ema20_slope_atr is not None
    assert snapshot.macd_histogram is not None
    assert snapshot.rsi14 is not None
    assert snapshot.bollinger_position is not None
    assert snapshot.volume_ratio is not None

    reasons: list[str] = []
    score = 0.0

    if direction == "LONG_BIAS":
        if snapshot.ema20 > snapshot.ema50 > snapshot.ema200:
            score += 20.0
            reasons.append("bullish_ema_stack")
        if snapshot.close > snapshot.ema20:
            score += 10.0
            reasons.append("close_above_ema20")
        if snapshot.ema20_slope_atr > 0.0:
            score += 10.0
            reasons.append("positive_ema20_slope")
        if snapshot.macd_histogram > 0.0:
            score += 15.0
            reasons.append("positive_macd_histogram")
        if snapshot.rsi14 >= policy.bullish_rsi_floor:
            score += 10.0
            reasons.append("bullish_rsi")
        if snapshot.bollinger_position >= policy.bullish_bollinger_position_floor:
            score += 5.0
            reasons.append("upper_bollinger_position")
    elif direction == "SHORT_BIAS":
        if snapshot.ema20 < snapshot.ema50 < snapshot.ema200:
            score += 20.0
            reasons.append("bearish_ema_stack")
        if snapshot.close < snapshot.ema20:
            score += 10.0
            reasons.append("close_below_ema20")
        if snapshot.ema20_slope_atr < 0.0:
            score += 10.0
            reasons.append("negative_ema20_slope")
        if snapshot.macd_histogram < 0.0:
            score += 15.0
            reasons.append("negative_macd_histogram")
        if snapshot.rsi14 <= policy.bearish_rsi_ceiling:
            score += 10.0
            reasons.append("bearish_rsi")
        if snapshot.bollinger_position <= policy.bearish_bollinger_position_ceiling:
            score += 5.0
            reasons.append("lower_bollinger_position")
    else:
        raise ValueError(f"unsupported direction: {direction}")

    if snapshot.volume_ratio >= policy.volume_ratio_floor:
        score += 5.0
        reasons.append("volume_participation")

    return score, tuple(reasons)


def rank_daily_opportunities(
    universe: Sequence[UniverseCandidate],
    technical_by_symbol: Mapping[str, TechnicalSnapshot],
    regime: MarketRegimeSnapshot | None,
    *,
    as_of_ms: int,
    policy: DailyOpportunityPolicy = DailyOpportunityPolicy(),
) -> DailyOpportunityReport:
    """Rank multi-asset attention candidates from already-computed evidence.

    This function performs no provider access, storage access, strategy routing,
    position sizing, order planning, or trading. Regime is required only as
    causal context in V0.1; it deliberately does not add hidden score points.
    """

    if as_of_ms < 0:
        raise ValueError("as_of_ms cannot be negative")

    if (
        regime is None
        or regime.available_at_ms > as_of_ms
        or (policy.require_ready_regime and not regime.ready)
    ):
        return DailyOpportunityReport(
            as_of_ms=as_of_ms,
            status="REGIME_UNAVAILABLE",
            regime_state="UNAVAILABLE",
            evaluated=(),
            selected=(),
        )

    ordered_universe = tuple(
        sorted(
            universe,
            key=lambda item: (-item.quote_amount_24h, item.spread_bps, item.symbol),
        )
    )
    if len({item.symbol for item in ordered_universe}) != len(ordered_universe):
        raise ValueError("universe contains duplicate symbols")

    decisions: list[DailyOpportunityDecision] = []
    count = len(ordered_universe)

    for index, item in enumerate(ordered_universe):
        snapshot = technical_by_symbol.get(item.symbol)
        if (
            item.quote_amount_24h <= 0.0
            or item.spread_bps < 0.0
            or item.spread_bps > policy.maximum_spread_bps
        ):
            decisions.append(
                DailyOpportunityDecision(
                    symbol=item.symbol,
                    eligible=False,
                    attention_score=0.0,
                    bias="UNAVAILABLE",
                    liquidity_score=0.0,
                    directional_score=0.0,
                    regime_state=regime.state,
                    reasons=("liquidity_or_spread_gate_failed",),
                )
            )
            continue
        if (
            snapshot is None
            or snapshot.available_at_ms > as_of_ms
            or not snapshot.ready_v0_2
        ):
            decisions.append(
                DailyOpportunityDecision(
                    symbol=item.symbol,
                    eligible=False,
                    attention_score=0.0,
                    bias="UNAVAILABLE",
                    liquidity_score=0.0,
                    directional_score=0.0,
                    regime_state=regime.state,
                    reasons=("technical_evidence_unavailable",),
                )
            )
            continue

        liquidity = _liquidity_score(
            index=index,
            count=count,
            spread_bps=item.spread_bps,
            maximum_spread_bps=policy.maximum_spread_bps,
        )
        long_score, long_reasons = _directional_score(
            snapshot, direction="LONG_BIAS", policy=policy
        )
        short_score, short_reasons = _directional_score(
            snapshot, direction="SHORT_BIAS", policy=policy
        )

        if long_score > short_score:
            bias = "LONG_BIAS"
            directional = long_score
            reasons = long_reasons
        elif short_score > long_score:
            bias = "SHORT_BIAS"
            directional = short_score
            reasons = short_reasons
        else:
            bias = "NEUTRAL"
            directional = long_score
            reasons = tuple(sorted(set(long_reasons + short_reasons)))

        attention = round(min(100.0, liquidity + directional), 2)
        eligible = attention >= policy.minimum_attention_score and bias != "NEUTRAL"
        decisions.append(
            DailyOpportunityDecision(
                symbol=item.symbol,
                eligible=eligible,
                attention_score=attention,
                bias=bias,
                liquidity_score=round(liquidity, 2),
                directional_score=round(directional, 2),
                regime_state=regime.state,
                reasons=reasons + (("attention_gate_passed",) if eligible else ("attention_gate_failed",)),
            )
        )

    ranked = tuple(
        sorted(
            decisions,
            key=lambda item: (
                not item.eligible,
                -item.attention_score,
                item.symbol,
            ),
        )
    )
    selected = tuple(item for item in ranked if item.eligible)[: policy.maximum_candidates]
    return DailyOpportunityReport(
        as_of_ms=as_of_ms,
        status="CANDIDATES_READY" if selected else "NO_CANDIDATE",
        regime_state=regime.state,
        evaluated=ranked,
        selected=selected,
    )
