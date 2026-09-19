from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class StatisticalEdgePolicy:
    """Research-only evidence gate for one already-selected candidate.

    This gate is deliberately downstream of candidate selection. It does not
    search parameters, choose a strategy, access data, or authorize trading.
    """

    minimum_samples: int = 30
    alpha: float = 0.05
    bootstrap_resamples: int = 5_000
    bootstrap_seed: int = 20260918
    maximum_edge_decay_fraction: float = 0.50

    def __post_init__(self) -> None:
        if self.minimum_samples < 2:
            raise ValueError("minimum_samples must be at least 2")
        if not 0.0 < self.alpha < 1.0:
            raise ValueError("alpha must be within (0, 1)")
        if self.bootstrap_resamples < 500:
            raise ValueError("bootstrap_resamples must be at least 500")
        if not 0.0 <= self.maximum_edge_decay_fraction < 1.0:
            raise ValueError("maximum_edge_decay_fraction must be within [0, 1)")


@dataclass(frozen=True, slots=True)
class StatisticalEdgeEvidence:
    sample_count: int
    mean_net_pnl: float
    median_net_pnl: float
    win_rate: float
    centered_bootstrap_p_value: float
    positive_mean: bool
    bootstrap_significant: bool
    decay_fraction_vs_development: float | None
    decay_gate_passed: bool | None
    passed: bool
    reasons: tuple[str, ...]
    bootstrap_seed: int
    bootstrap_resamples: int
    research_only: bool = True
    iid_assumption_warning: bool = True
    formal_holdout_accessed: bool = False
    strategy_mutation_authorized: bool = False
    live_trading_authorized: bool = False


def _validated_samples(values: Sequence[float]) -> tuple[float, ...]:
    samples = tuple(float(value) for value in values)
    if not samples:
        raise ValueError("at least one sample is required")
    if not all(math.isfinite(value) for value in samples):
        raise ValueError("samples must be finite")
    return samples


def centered_bootstrap_one_sided_p_value(
    values: Sequence[float],
    *,
    resamples: int = 5_000,
    seed: int = 20260918,
) -> float:
    """Test H0: mean <= 0 with a centered non-parametric bootstrap.

    The observed sample is shifted to mean zero, then resampled with
    replacement. The empirical one-sided p-value is the fraction of null
    resamples whose mean is at least the observed mean. A +1 correction keeps
    the reported p-value nonzero and deterministic for a fixed seed.
    """

    samples = _validated_samples(values)
    if resamples < 1:
        raise ValueError("resamples must be positive")

    observed_mean = statistics.fmean(samples)
    if observed_mean <= 0.0:
        return 1.0

    centered = tuple(value - observed_mean for value in samples)
    rng = random.Random(seed)
    exceedances = 0
    count = len(centered)
    for _ in range(resamples):
        null_mean = sum(centered[rng.randrange(count)] for _ in range(count)) / count
        if null_mean >= observed_mean:
            exceedances += 1
    return (exceedances + 1.0) / (resamples + 1.0)


def holm_step_down(
    p_values: Mapping[str, float],
    *,
    alpha: float = 0.05,
) -> dict[str, bool]:
    """Holm family-wise error correction for exploratory hypothesis families."""

    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be within (0, 1)")
    if not p_values:
        return {}

    rows: list[tuple[str, float]] = []
    for name, value in p_values.items():
        if not str(name).strip():
            raise ValueError("hypothesis names must be non-empty")
        p_value = float(value)
        if not math.isfinite(p_value) or not 0.0 <= p_value <= 1.0:
            raise ValueError("p-values must be finite and within [0, 1]")
        rows.append((str(name), p_value))

    rows.sort(key=lambda item: (item[1], item[0]))
    rejected = {name: False for name, _ in rows}
    family_size = len(rows)
    still_rejecting = True
    for index, (name, p_value) in enumerate(rows):
        threshold = alpha / (family_size - index)
        if still_rejecting and p_value <= threshold:
            rejected[name] = True
        else:
            still_rejecting = False
    return rejected


def evaluate_selected_candidate_edge(
    validation_net_pnl: Sequence[float],
    *,
    development_mean_net_pnl: float | None = None,
    policy: StatisticalEdgePolicy = StatisticalEdgePolicy(),
) -> StatisticalEdgeEvidence:
    """Evaluate statistical evidence for one candidate selected before validation.

    The function intentionally cannot rank or switch candidates. If a family
    of exploratory hypotheses is tested elsewhere, callers should first use
    :func:`holm_step_down` and preserve that family-level evidence separately.
    """

    samples = _validated_samples(validation_net_pnl)
    mean_value = statistics.fmean(samples)
    median_value = statistics.median(samples)
    win_rate = sum(value > 0.0 for value in samples) / len(samples)
    p_value = centered_bootstrap_one_sided_p_value(
        samples,
        resamples=policy.bootstrap_resamples,
        seed=policy.bootstrap_seed,
    )

    reasons: list[str] = []
    if len(samples) < policy.minimum_samples:
        reasons.append("sample_count_below_minimum")
    if mean_value <= 0.0:
        reasons.append("mean_net_pnl_not_positive")
    if p_value >= policy.alpha:
        reasons.append("centered_bootstrap_not_significant")

    decay_fraction: float | None = None
    decay_passed: bool | None = None
    if development_mean_net_pnl is not None:
        development_mean = float(development_mean_net_pnl)
        if not math.isfinite(development_mean):
            raise ValueError("development_mean_net_pnl must be finite")
        if development_mean <= 0.0:
            decay_passed = False
            reasons.append("development_mean_not_positive")
        else:
            decay_fraction = max(0.0, 1.0 - mean_value / development_mean)
            decay_passed = (
                mean_value > 0.0
                and decay_fraction <= policy.maximum_edge_decay_fraction
            )
            if not decay_passed:
                reasons.append("edge_decay_above_maximum")

    positive_mean = mean_value > 0.0
    significant = p_value < policy.alpha
    passed = (
        len(samples) >= policy.minimum_samples
        and positive_mean
        and significant
        and decay_passed is not False
    )
    return StatisticalEdgeEvidence(
        sample_count=len(samples),
        mean_net_pnl=mean_value,
        median_net_pnl=median_value,
        win_rate=win_rate,
        centered_bootstrap_p_value=p_value,
        positive_mean=positive_mean,
        bootstrap_significant=significant,
        decay_fraction_vs_development=decay_fraction,
        decay_gate_passed=decay_passed,
        passed=passed,
        reasons=tuple(reasons) if reasons else ("research_statistical_gate_pass",),
        bootstrap_seed=policy.bootstrap_seed,
        bootstrap_resamples=policy.bootstrap_resamples,
    )
