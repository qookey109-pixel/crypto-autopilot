from __future__ import annotations

from .models import OpportunityInput, StrategyDecision


STATE_POINTS = {"S3": 25.0, "S0.5": 22.0, "S2": 18.0, "S1": 15.0}


def _bool_fraction(values: tuple[bool, ...]) -> float:
    return sum(values) / len(values)


def evaluate_opportunity(
    opportunity: OpportunityInput,
    *,
    minimum_probability: float = 0.60,
    minimum_samples: int = 50,
    minimum_score: float = 80.0,
) -> StrategyDecision:
    """Deterministic V0.1 gate.

    This consumes precomputed features. Indicator calculation and historical
    probability production belong to upstream/data layers.
    """
    s = opportunity.sstate
    if s.state not in STATE_POINTS:
        return StrategyDecision(opportunity.symbol, False, 0.0, "state_not_allowed")
    if not s.available or s.probability is None:
        return StrategyDecision(opportunity.symbol, False, 0.0, "probability_unavailable")
    if s.samples < minimum_samples:
        return StrategyDecision(opportunity.symbol, False, 0.0, "insufficient_samples")
    if s.probability < minimum_probability:
        return StrategyDecision(opportunity.symbol, False, 0.0, "probability_below_gate")
    if not opportunity.liquidity_ok:
        return StrategyDecision(opportunity.symbol, False, 0.0, "liquidity_gate_failed")
    if not opportunity.funding_ok:
        return StrategyDecision(opportunity.symbol, False, 0.0, "funding_gate_failed")

    score = STATE_POINTS[s.state]

    # Probability component: 60% starts at 12/20; 80%+ caps at 20/20.
    probability_points = min(20.0, max(0.0, 12.0 + (s.probability - 0.60) * 40.0))
    score += probability_points

    setup = opportunity.setup
    score += 20.0 * _bool_fraction(
        (
            setup.ema20_above_ema50,
            setup.ema20_slope_positive,
            setup.close_above_ema20,
            setup.not_overextended,
        )
    )

    entry = opportunity.entry
    score += 20.0 * _bool_fraction(
        (
            entry.pullback_seen,
            entry.reclaimed_ema20,
            entry.broke_previous_high,
            entry.volume_confirmed,
        )
    )

    # Reward/risk: 1R -> 4 points, 1.5R -> 6, 2R -> 8, 2.5R+ -> 10.
    score += min(10.0, max(0.0, opportunity.reward_risk * 4.0))
    score += 5.0  # liquidity/funding already passed deterministically above.

    score = round(min(100.0, score), 2)
    eligible = score >= minimum_score
    return StrategyDecision(
        opportunity.symbol,
        eligible,
        score,
        "eligible" if eligible else "score_below_gate",
    )
