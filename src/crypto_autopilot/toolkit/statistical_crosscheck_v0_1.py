from __future__ import annotations

import math
import random
import statistics
from collections.abc import Mapping, Sequence
from typing import Any

from crypto_autopilot.strategy_edge_validation import stationary_bootstrap_mean_test


class StatisticalCrosscheckError(ValueError):
    """Raised when the research-only cross-check contract is violated."""


_ALLOWED_INPUT_CLASSES = {
    "synthetic_fixture",
    "existing_non_holdout_fixture",
}


def _finite_values(values: Sequence[float], *, minimum_observations: int) -> tuple[float, ...]:
    if len(values) < minimum_observations:
        raise StatisticalCrosscheckError(
            f"cross-check requires at least {minimum_observations} observations"
        )
    normalized = tuple(float(value) for value in values)
    if any(isinstance(value, bool) or not math.isfinite(float(value)) for value in values):
        raise StatisticalCrosscheckError("cross-check values must be finite numeric observations")
    return normalized


def iid_centered_bootstrap_mean_test(
    values: Sequence[float],
    *,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    """Independent IID centered-bootstrap semantic cross-check.

    This is independently authored from the documented statistical semantics reviewed in the
    upstream candidate. It does not import or execute upstream code and is not an integration.
    """

    if samples < 99:
        raise StatisticalCrosscheckError("IID bootstrap requires at least 99 samples")
    normalized = tuple(float(value) for value in values)
    if not normalized:
        raise StatisticalCrosscheckError("IID bootstrap values cannot be empty")
    if any(not math.isfinite(value) for value in normalized):
        raise StatisticalCrosscheckError("IID bootstrap values must be finite")

    observed = float(statistics.fmean(normalized))
    centered = tuple(value - observed for value in normalized)
    rng = random.Random(seed)
    greater_or_equal = 0
    length = len(centered)

    for _ in range(samples):
        boot_mean = sum(centered[rng.randrange(length)] for _ in range(length)) / length
        greater_or_equal += boot_mean >= observed

    p_value = (greater_or_equal + 1) / (samples + 1)
    return {
        "method": "iid_centered_bootstrap_one_sided_mean",
        "observed_mean": observed,
        "p_value": p_value,
        "samples": samples,
        "seed": seed,
    }


def run_statistical_crosscheck(
    values: Sequence[float],
    policy: Mapping[str, Any],
    *,
    input_class: str,
) -> dict[str, Any]:
    """Compare IID centered bootstrap with Crypto Autopilot's stationary bootstrap.

    The result is descriptive research evidence only. It cannot authorize holdout access,
    strategy admission, model promotion, broker connectivity, or trading.
    """

    allowed = policy.get("allowed_input_classes")
    statistics_policy = policy.get("statistics")
    authority = policy.get("authority")
    interpretation = policy.get("interpretation")
    if not isinstance(allowed, list) or set(allowed) != _ALLOWED_INPUT_CLASSES:
        raise StatisticalCrosscheckError("allowed_input_classes must remain the frozen safe set")
    if input_class not in _ALLOWED_INPUT_CLASSES:
        raise StatisticalCrosscheckError("input class is not authorized for research cross-check")
    if not isinstance(statistics_policy, Mapping):
        raise StatisticalCrosscheckError("statistics policy must be an object")
    if not isinstance(authority, Mapping) or not authority:
        raise StatisticalCrosscheckError("authority policy must be a non-empty object")
    if any(value is not False for value in authority.values()):
        raise StatisticalCrosscheckError("all cross-check authority flags must remain false")
    if not isinstance(interpretation, Mapping):
        raise StatisticalCrosscheckError("interpretation policy must be an object")
    if interpretation.get("formal_edge_gate") is not False:
        raise StatisticalCrosscheckError("cross-check cannot become a formal edge gate")
    if interpretation.get("promotion_signal") is not False:
        raise StatisticalCrosscheckError("cross-check cannot become a promotion signal")
    if interpretation.get("upstream_code_equivalence_claimed") is not False:
        raise StatisticalCrosscheckError("cross-check cannot claim upstream code equivalence")

    minimum_observations = int(statistics_policy.get("minimum_observations", 20))
    alpha = float(statistics_policy.get("alpha", 0.05))
    iid_samples = int(statistics_policy.get("iid_bootstrap_samples", 999))
    stationary_samples = int(statistics_policy.get("stationary_bootstrap_samples", 999))
    mean_block_length = float(statistics_policy.get("stationary_mean_block_length", 10.0))
    seed = int(statistics_policy.get("deterministic_seed", 77))
    if not 0 < alpha < 0.5:
        raise StatisticalCrosscheckError("alpha must be between zero and 0.5")
    if minimum_observations < 20:
        raise StatisticalCrosscheckError("minimum_observations cannot be below 20")

    normalized = _finite_values(values, minimum_observations=minimum_observations)
    iid = iid_centered_bootstrap_mean_test(normalized, samples=iid_samples, seed=seed)
    stationary = stationary_bootstrap_mean_test(
        normalized,
        samples=stationary_samples,
        mean_block_length=mean_block_length,
        seed=seed,
    )

    iid_significant = iid["p_value"] < alpha
    stationary_significant = stationary["p_value"] < alpha
    if iid_significant and stationary_significant:
        comparison = "BOTH_SIGNIFICANT_RESEARCH_SIGNAL"
    elif iid_significant and not stationary_significant:
        comparison = "IID_ONLY_DIVERGENCE_SERIAL_DEPENDENCE_WARNING"
    elif stationary_significant and not iid_significant:
        comparison = "STATIONARY_ONLY_DIVERGENCE_REVIEW"
    else:
        comparison = "NOT_SIGNIFICANT"

    return {
        "schema": "resource-hub-statistical-crosscheck-report-v0.1",
        "status": "RESEARCH_ONLY",
        "input_class": input_class,
        "observation_count": len(normalized),
        "sample_mean": float(statistics.fmean(normalized)),
        "sample_standard_deviation": float(statistics.stdev(normalized)),
        "alpha": alpha,
        "iid_centered_bootstrap": iid,
        "stationary_bootstrap": stationary,
        "comparison": comparison,
        "decision": "DESCRIPTIVE_CROSSCHECK_ONLY",
        "limitations": [
            "The IID bootstrap does not preserve serial dependence between observations.",
            "The stationary bootstrap is a Crypto Autopilot research primitive, not an upstream implementation.",
            "This report does not claim source-code equivalence with the upstream candidate.",
            "This report is not a formal strategy edge gate and cannot authorize promotion or trading.",
        ],
        "authority": dict(authority),
    }
