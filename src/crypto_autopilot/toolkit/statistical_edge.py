from __future__ import annotations

import math
import random
from statistics import fmean
from typing import Any

from .registry import SAFETY_BOUNDARY

_MAX_SERIES_LENGTH = 100_000
_MAX_BOOTSTRAP_WORK = 5_000_000
_MAX_RUIN_WORK = 1_000_000
_DEFAULT_BOOTSTRAP_ITERATIONS = 2_000
_DEFAULT_SEED = 0


def _finite_series(value: Any, *, name: str, minimum: int = 2) -> tuple[float, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a JSON list")
    if len(value) < minimum:
        raise ValueError(f"{name} requires at least {minimum} observations")
    if len(value) > _MAX_SERIES_LENGTH:
        raise ValueError(f"{name} exceeds {_MAX_SERIES_LENGTH} observations")
    result = tuple(float(item) for item in value)
    if not all(math.isfinite(item) for item in result):
        raise ValueError(f"{name} must contain only finite numbers")
    if any(item < -1.0 for item in result):
        raise ValueError(f"{name} contains a fractional return below -1.0")
    return result


def _sample_std(values: tuple[float, ...]) -> float:
    mean = fmean(values)
    return math.sqrt(sum((item - mean) ** 2 for item in values) / (len(values) - 1))


def _quantile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("quantile requires observations")
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def _bootstrap_positive_mean(
    values: tuple[float, ...],
    *,
    iterations: int,
    seed: int,
    alpha: float,
) -> dict[str, Any]:
    if iterations < 200 or iterations > 20_000:
        raise ValueError("bootstrap_iterations must be between 200 and 20000")
    if len(values) * iterations > _MAX_BOOTSTRAP_WORK:
        raise ValueError(
            "bootstrap workload too large; reduce observations or bootstrap_iterations"
        )
    if not 0.0 < alpha < 0.5:
        raise ValueError("alpha must be between 0 and 0.5")

    observed_mean = fmean(values)
    centered = tuple(item - observed_mean for item in values)
    rng = random.Random(seed)
    centered_means: list[float] = []
    greater_or_equal = 0
    count = len(values)
    for _ in range(iterations):
        sample_mean = sum(centered[rng.randrange(count)] for _ in range(count)) / count
        centered_means.append(sample_mean)
        if sample_mean >= observed_mean:
            greater_or_equal += 1

    p_value = (greater_or_equal + 1) / (iterations + 1)
    centered_means.sort()
    lower = _quantile(centered_means, alpha / 2.0) + observed_mean
    upper = _quantile(centered_means, 1.0 - alpha / 2.0) + observed_mean
    return {
        "method": "centered_nonparametric_bootstrap_one_sided_positive_mean",
        "iterations": iterations,
        "seed": seed,
        "alpha": alpha,
        "p_value": round(p_value, 10),
        "mean_confidence_interval": [round(lower, 10), round(upper, 10)],
        "significant_positive_mean": observed_mean > 0.0 and p_value <= alpha,
    }


def _descriptive(values: tuple[float, ...]) -> dict[str, Any]:
    mean = fmean(values)
    std = _sample_std(values)
    standard_error = std / math.sqrt(len(values))
    t_statistic = None if standard_error == 0.0 else mean / standard_error
    positive = sum(item > 0.0 for item in values)
    negative = sum(item < 0.0 for item in values)
    return {
        "count": len(values),
        "mean_return": round(mean, 10),
        "sample_std": round(std, 10),
        "standard_error": round(standard_error, 10),
        "t_statistic_vs_zero": None if t_statistic is None else round(t_statistic, 10),
        "positive_count": positive,
        "negative_count": negative,
        "zero_count": len(values) - positive - negative,
        "win_rate": round(positive / len(values), 10),
        "cumulative_compounded_return": round(
            math.prod(1.0 + item for item in values) - 1.0,
            10,
        ),
    }


def _concentration(values: tuple[float, ...], *, top_n: int) -> dict[str, Any]:
    if top_n < 1 or top_n > min(100, len(values)):
        raise ValueError("concentration_top_n must be between 1 and min(100, sample_count)")
    absolute = sorted((abs(item) for item in values), reverse=True)
    total_absolute = sum(absolute)
    top_absolute = sum(absolute[:top_n])
    positive = sorted((item for item in values if item > 0.0), reverse=True)
    total_positive = sum(positive)
    return {
        "top_n": top_n,
        "top_n_absolute_return_share": (
            0.0 if total_absolute == 0.0 else round(top_absolute / total_absolute, 10)
        ),
        "top_n_positive_profit_share": (
            None
            if total_positive == 0.0
            else round(sum(positive[: min(top_n, len(positive))]) / total_positive, 10)
        ),
    }


def _decay(values: tuple[float, ...]) -> dict[str, Any]:
    split = len(values) // 2
    early = values[:split]
    recent = values[split:]
    early_mean = fmean(early)
    recent_mean = fmean(recent)
    ratio = None if early_mean == 0.0 else recent_mean / early_mean
    return {
        "split_index": split,
        "early_count": len(early),
        "recent_count": len(recent),
        "early_mean_return": round(early_mean, 10),
        "recent_mean_return": round(recent_mean, 10),
        "recent_minus_early_mean": round(recent_mean - early_mean, 10),
        "recent_to_early_mean_ratio": None if ratio is None else round(ratio, 10),
        "recent_mean_lower_than_early": recent_mean < early_mean,
    }


def _oos(payload: dict[str, Any]) -> dict[str, Any] | None:
    has_train = "train_returns" in payload
    has_test = "test_returns" in payload
    if has_train != has_test:
        raise ValueError("train_returns and test_returns must be supplied together")
    if not has_train:
        return None
    train = _finite_series(payload["train_returns"], name="train_returns")
    test = _finite_series(payload["test_returns"], name="test_returns")
    train_mean = fmean(train)
    test_mean = fmean(test)
    ratio = None if train_mean == 0.0 else test_mean / train_mean
    return {
        "train": _descriptive(train),
        "test": _descriptive(test),
        "test_minus_train_mean": round(test_mean - train_mean, 10),
        "test_to_train_mean_ratio": None if ratio is None else round(ratio, 10),
        "test_positive_mean": test_mean > 0.0,
    }


def _ruin(values: tuple[float, ...], config: Any, *, seed: int) -> dict[str, Any] | None:
    if config is None:
        return None
    if not isinstance(config, dict):
        raise ValueError("ruin must be an object when supplied")

    initial_equity = float(config.get("initial_equity", 1.0))
    ruin_fraction = float(config.get("ruin_fraction", 0.5))
    horizon = int(config.get("horizon_trades", 100))
    simulations = int(config.get("simulations", 1_000))
    max_probability_raw = config.get("max_ruin_probability")
    max_probability = None if max_probability_raw is None else float(max_probability_raw)

    if not math.isfinite(initial_equity) or initial_equity <= 0.0:
        raise ValueError("ruin.initial_equity must be finite and positive")
    if not 0.0 < ruin_fraction < 1.0:
        raise ValueError("ruin.ruin_fraction must be between 0 and 1")
    if horizon < 1 or simulations < 1 or horizon * simulations > _MAX_RUIN_WORK:
        raise ValueError("ruin simulation workload must be positive and at most 1000000 steps")
    if max_probability is not None and not 0.0 <= max_probability <= 1.0:
        raise ValueError("ruin.max_ruin_probability must be between 0 and 1")

    threshold = initial_equity * ruin_fraction
    rng = random.Random(seed + 1)
    ruined = 0
    ending_equities: list[float] = []
    count = len(values)
    for _ in range(simulations):
        equity = initial_equity
        hit = False
        for _ in range(horizon):
            equity *= 1.0 + values[rng.randrange(count)]
            if equity <= threshold:
                hit = True
                break
        if hit:
            ruined += 1
        ending_equities.append(equity)

    probability = ruined / simulations
    ending_equities.sort()
    return {
        "method": "iid_empirical_return_path_bootstrap",
        "initial_equity": initial_equity,
        "ruin_fraction": ruin_fraction,
        "ruin_equity_threshold": round(threshold, 10),
        "horizon_trades": horizon,
        "simulations": simulations,
        "seed": seed + 1,
        "ruin_probability": round(probability, 10),
        "ending_equity_median": round(_quantile(ending_equities, 0.5), 10),
        "ending_equity_p05": round(_quantile(ending_equities, 0.05), 10),
        "max_ruin_probability": max_probability,
        "below_configured_maximum": (
            None if max_probability is None else probability <= max_probability
        ),
        "limitations": [
            "iid_resampling_does_not_preserve_serial_dependence",
            "historical_return_distribution_may_not_repeat",
            "research_only_not_a_capital_guarantee",
        ],
    }


def validate_statistical_edge(payload: dict[str, Any]) -> dict[str, Any]:
    """Analyze supplied research returns without promotion or trading side effects."""
    if not isinstance(payload, dict):
        raise ValueError("statistical edge input must be an object")
    returns = _finite_series(payload.get("returns"), name="returns")
    iterations = int(payload.get("bootstrap_iterations", _DEFAULT_BOOTSTRAP_ITERATIONS))
    seed = int(payload.get("seed", _DEFAULT_SEED))
    alpha = float(payload.get("alpha", 0.05))
    top_n = int(payload.get("concentration_top_n", min(5, len(returns))))

    descriptive = _descriptive(returns)
    bootstrap = _bootstrap_positive_mean(
        returns,
        iterations=iterations,
        seed=seed,
        alpha=alpha,
    )
    oos = _oos(payload)
    ruin = _ruin(returns, payload.get("ruin"), seed=seed)

    evidence_flags = {
        "positive_mean": descriptive["mean_return"] > 0.0,
        "bootstrap_significant_positive_mean": bootstrap["significant_positive_mean"],
        "oos_positive_mean": None if oos is None else oos["test_positive_mean"],
        "ruin_below_configured_maximum": (
            None if ruin is None else ruin["below_configured_maximum"]
        ),
    }
    return {
        "schema": "qookey-crypto-toolkit-statistical-edge-v0.1",
        "status": "ANALYZED",
        "mode": "RESEARCH_ONLY",
        "return_unit": "fraction_of_equity_per_observation",
        "descriptive": descriptive,
        "bootstrap": bootstrap,
        "out_of_sample": oos,
        "concentration": _concentration(returns, top_n=top_n),
        "edge_decay": _decay(returns),
        "ruin_simulation": ruin,
        "evidence_flags": evidence_flags,
        "methodology": {
            "inspiration": "statistical validation patterns cataloged from Anti-Gambling Trader",
            "implementation": "independent_stdlib_reimplementation",
            "upstream_runtime_dependency": False,
            "automatic_quality_gate_change": False,
            "automatic_strategy_mutation": False,
            "automatic_model_promotion": False,
        },
        "authority": dict(SAFETY_BOUNDARY),
    }
