from __future__ import annotations

from typing import Any, Mapping, Sequence

from crypto_autopilot.training.detailed import IntradayExample, _signal_diagnostics


DEFAULT_THRESHOLDS = (0.50, 0.51, 0.52, 0.53, 0.54, 0.55)


def _quantile(values: Sequence[float], fraction: float) -> float:
    if not values:
        raise ValueError("probability quantiles require non-empty values")
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("quantile fraction must be between 0 and 1")
    ordered = sorted(float(value) for value in values)
    index = int(round(fraction * (len(ordered) - 1)))
    return ordered[index]


def probability_distribution(probabilities: Sequence[float]) -> dict[str, float | int]:
    if not probabilities:
        raise ValueError("probability distribution requires non-empty values")
    values = [float(value) for value in probabilities]
    return {
        "count": len(values),
        "minimum": min(values),
        "p50": _quantile(values, 0.50),
        "p75": _quantile(values, 0.75),
        "p90": _quantile(values, 0.90),
        "p95": _quantile(values, 0.95),
        "p99": _quantile(values, 0.99),
        "maximum": max(values),
    }


def threshold_sweep(
    items: Sequence[IntradayExample],
    probabilities: Sequence[float],
    *,
    training: Mapping[str, Any],
    thresholds: Sequence[float] = DEFAULT_THRESHOLDS,
) -> dict[str, Any]:
    if not items or len(items) != len(probabilities):
        raise ValueError("threshold sweep requires aligned non-empty items and probabilities")

    configured = float(training["probability_threshold"])
    candidates = sorted({configured, *(float(value) for value in thresholds)})
    if any(not 0.0 < value < 1.0 for value in candidates):
        raise ValueError("threshold candidates must be between 0 and 1")

    scenarios = training["cost_scenarios"]
    rows = []
    for threshold in candidates:
        scenario_rows = {}
        for scenario in scenarios:
            name = str(scenario["name"])
            scenario_rows[name] = _signal_diagnostics(
                items,
                probabilities,
                threshold=threshold,
                fee_bps_per_side=float(scenario["fee_bps_per_side"]),
                slippage_bps_per_side=float(scenario["slippage_bps_per_side"]),
            )
        rows.append({"threshold": threshold, "cost_scenarios": scenario_rows})

    return {
        "configured_threshold": configured,
        "candidate_thresholds": candidates,
        "probability_distribution": probability_distribution(probabilities),
        "rows": rows,
        "diagnostic_only": True,
        "quality_gate_changed": False,
    }
