"""Deterministic, paper-only ranking for registered strategy challengers.

The arena is an evaluation view over :mod:`experiment_registry`; it does not
run agents, fetch providers, write R2, or create trade plans.  Candidates must
already have comparable experiment evidence before they can be ranked.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

from .experiment_registry import ExperimentRecord


class AgentArenaError(ValueError):
    """Raised when challenger evidence cannot be compared safely."""


@dataclass(frozen=True, slots=True)
class AgentArenaPolicy:
    """Fail-closed eligibility rules for a research-only ranking."""

    minimum_completed_folds: int = 4
    minimum_trade_count: int = 0
    maximum_drawdown_pct: float | None = 50.0

    def __post_init__(self) -> None:
        if isinstance(self.minimum_completed_folds, bool) or self.minimum_completed_folds < 1:
            raise AgentArenaError("minimum_completed_folds must be >= 1")
        if isinstance(self.minimum_trade_count, bool) or self.minimum_trade_count < 0:
            raise AgentArenaError("minimum_trade_count must be >= 0")
        if self.maximum_drawdown_pct is not None and (
            not math.isfinite(self.maximum_drawdown_pct) or self.maximum_drawdown_pct < 0
        ):
            raise AgentArenaError("maximum_drawdown_pct must be finite and >= 0")


@dataclass(frozen=True, slots=True)
class ArenaCandidate:
    """A human-readable label bound to one immutable experiment record."""

    agent_id: str
    record: ExperimentRecord

    def __post_init__(self) -> None:
        if not self.agent_id.strip():
            raise AgentArenaError("agent_id is required")


@dataclass(frozen=True, slots=True)
class ArenaDecision:
    agent_id: str
    experiment_id: str
    eligible: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArenaRanking:
    rank: int
    agent_id: str
    experiment_id: str
    score: float
    baseline_score: float
    improvement: float


@dataclass(frozen=True, slots=True)
class AgentArenaResult:
    """Stable ranking output with explicit zero-authority fields."""

    comparison_fingerprint: str | None
    decisions: tuple[ArenaDecision, ...]
    rankings: tuple[ArenaRanking, ...]
    holdout_accessed: bool = False
    promotion_authority: int = 0
    trade_plan_authorized: bool = False

    def __post_init__(self) -> None:
        if self.holdout_accessed or self.promotion_authority != 0 or self.trade_plan_authorized:
            raise AgentArenaError("agent arena has zero holdout, promotion, and trade authority")


def _metric(metrics: Mapping[str, object], *names: str) -> float | int | None:
    for name in names:
        value = metrics.get(name)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise AgentArenaError(f"metric {name} must be numeric")
        if not math.isfinite(float(value)):
            raise AgentArenaError(f"metric {name} must be finite")
        return value
    return None


def _eligibility(candidate: ArenaCandidate, policy: AgentArenaPolicy) -> tuple[str, ...]:
    record = candidate.record
    reasons: list[str] = []
    if record.outcome != "completed":
        reasons.append(f"outcome:{record.outcome}")
    folds = _metric(record.metrics, "foldCount", "fold_count", "completedFolds", "completed_folds")
    if folds is None:
        reasons.append("missing-fold-count")
    elif folds < policy.minimum_completed_folds:
        reasons.append("insufficient-folds")
    trade_count = _metric(record.metrics, "tradeCount", "trade_count")
    if trade_count is not None and trade_count < policy.minimum_trade_count:
        reasons.append("insufficient-trades")
    drawdown = _metric(record.metrics, "maxDrawdownPct", "max_drawdown_pct")
    if policy.maximum_drawdown_pct is not None:
        if drawdown is None:
            reasons.append("missing-max-drawdown")
        elif drawdown > policy.maximum_drawdown_pct:
            reasons.append("drawdown-limit")
    return tuple(reasons)


def rank_candidates(
    candidates: tuple[ArenaCandidate, ...] | list[ArenaCandidate],
    *,
    policy: AgentArenaPolicy = AgentArenaPolicy(),
) -> AgentArenaResult:
    """Rank comparable challenger records without executing any strategy.

    The first candidate's comparison key is the canonical key.  Any provider,
    universe, feature, interval, or evaluation mismatch fails closed instead
    of producing a misleading leaderboard.
    """

    ordered = tuple(candidates)
    if not ordered:
        return AgentArenaResult(None, (), ())
    if len({candidate.agent_id for candidate in ordered}) != len(ordered):
        raise AgentArenaError("agent_id values must be unique")
    if len({candidate.record.experiment_id for candidate in ordered}) != len(ordered):
        raise AgentArenaError("experiment_id values must be unique")

    comparison = ordered[0].record.comparison
    for candidate in ordered[1:]:
        if candidate.record.comparison.fingerprint != comparison.fingerprint:
            raise AgentArenaError("comparison-key-mismatch")

    decisions_list: list[ArenaDecision] = []
    for candidate in ordered:
        reasons = _eligibility(candidate, policy)
        decisions_list.append(
            ArenaDecision(
                agent_id=candidate.agent_id,
                experiment_id=candidate.record.experiment_id,
                eligible=not reasons,
                reasons=reasons,
            )
        )
    decisions = tuple(decisions_list)
    eligible = [
        candidate for candidate, decision in zip(ordered, decisions) if decision.eligible
    ]
    reverse = comparison.direction == "higher"
    eligible.sort(key=lambda candidate: candidate.agent_id)
    eligible.sort(key=lambda candidate: candidate.record.candidate_score, reverse=reverse)
    rankings = tuple(
        ArenaRanking(
            rank=index,
            agent_id=candidate.agent_id,
            experiment_id=candidate.record.experiment_id,
            score=candidate.record.candidate_score,
            baseline_score=candidate.record.baseline_score,
            improvement=candidate.record.improvement,
        )
        for index, candidate in enumerate(eligible, start=1)
    )
    return AgentArenaResult(comparison.fingerprint, decisions, rankings)
