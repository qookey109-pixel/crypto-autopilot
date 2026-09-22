from __future__ import annotations

from typing import Any, Mapping, Sequence, TypedDict

from crypto_autopilot.training.detailed import IntradayExample, _signal_diagnostics


DEFAULT_THRESHOLDS = (0.50, 0.51, 0.52, 0.53, 0.54, 0.55)


class _FoldResult(TypedDict):
    fold: str
    signal_count: int
    selection_rate: float
    average_net_return: float
    maximum_drawdown: float
    maximum_symbol_concentration: float


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
        "mean": sum(values) / len(values),
        "p50": _quantile(values, 0.50),
        "p75": _quantile(values, 0.75),
        "p90": _quantile(values, 0.90),
        "p95": _quantile(values, 0.95),
        "p99": _quantile(values, 0.99),
        "maximum": max(values),
    }


def probability_quality(
    items: Sequence[IntradayExample], probabilities: Sequence[float]
) -> dict[str, float | int | None]:
    if not items or len(items) != len(probabilities):
        raise ValueError("probability quality requires aligned non-empty inputs")
    values = [float(value) for value in probabilities]
    labels = [int(item.label) for item in items]
    positives = [value for value, label in zip(values, labels) if label == 1]
    negatives = [value for value, label in zip(values, labels) if label == 0]
    mean_probability = sum(values) / len(values)
    positive_rate = sum(labels) / len(labels)
    positive_mean = sum(positives) / len(positives) if positives else None
    negative_mean = sum(negatives) / len(negatives) if negatives else None
    separation = (
        positive_mean - negative_mean
        if positive_mean is not None and negative_mean is not None
        else None
    )
    above_0_50_count = sum(value >= 0.50 for value in values)
    return {
        "samples": len(items),
        "label_positive_rate": positive_rate,
        "mean_predicted_probability": mean_probability,
        "calibration_gap": mean_probability - positive_rate,
        "positive_label_mean_probability": positive_mean,
        "negative_label_mean_probability": negative_mean,
        "mean_probability_separation": separation,
        "above_0_50_count": above_0_50_count,
        "above_0_50_rate": above_0_50_count / len(values),
    }


def _scenario_outcome(signal_count: int, average_net_return: float) -> str:
    if signal_count == 0:
        return "ZERO_SIGNAL"
    if average_net_return > 0.0:
        return "POSITIVE_NET_RETURN"
    return "NON_POSITIVE_NET_RETURN"


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
            diagnostics = dict(
                _signal_diagnostics(
                    items,
                    probabilities,
                    threshold=threshold,
                    fee_bps_per_side=float(scenario["fee_bps_per_side"]),
                    slippage_bps_per_side=float(scenario["slippage_bps_per_side"]),
                )
            )
            signal_count = int(diagnostics["signal_count"])
            average_net_return = float(diagnostics["average_net_return"])
            diagnostics["selection_rate"] = signal_count / len(items)
            diagnostics["outcome"] = _scenario_outcome(
                signal_count, average_net_return
            )
            scenario_rows[name] = diagnostics
        rows.append({"threshold": threshold, "cost_scenarios": scenario_rows})

    return {
        "configured_threshold": configured,
        "candidate_thresholds": candidates,
        "probability_distribution": probability_distribution(probabilities),
        "probability_quality": probability_quality(items, probabilities),
        "rows": rows,
        "diagnostic_only": True,
        "quality_gate_changed": False,
    }


def summarize_thresholds_across_folds(
    folds: Sequence[Mapping[str, Any]], *, scenario_name: str = "base"
) -> dict[str, Any]:
    if not folds:
        raise ValueError("cross-fold threshold summary requires at least one fold")

    candidate_sets = [
        {float(value) for value in fold["candidate_thresholds"]} for fold in folds
    ]
    candidates = sorted(set.intersection(*candidate_sets))
    if not candidates:
        raise ValueError("threshold folds do not share any candidate thresholds")

    rows = []
    supported = []
    for threshold in candidates:
        fold_results: list[_FoldResult] = []
        for fold in folds:
            threshold_row = next(
                (
                    row
                    for row in fold["rows"]
                    if float(row["threshold"]) == threshold
                ),
                None,
            )
            if threshold_row is None:
                raise ValueError(
                    f"fold {fold.get('name')!r} is missing threshold {threshold}"
                )
            scenarios = threshold_row["cost_scenarios"]
            if scenario_name not in scenarios:
                raise ValueError(
                    f"fold {fold.get('name')!r} is missing scenario {scenario_name!r}"
                )
            scenario = scenarios[scenario_name]
            signal_count = int(scenario["signal_count"])
            average_net_return = float(scenario["average_net_return"])
            sample_count = int(fold["probability_distribution"]["count"])
            selection_rate = float(
                scenario.get("selection_rate", signal_count / sample_count)
            )
            fold_results.append(
                {
                    "fold": str(fold.get("name") or ""),
                    "signal_count": signal_count,
                    "selection_rate": selection_rate,
                    "average_net_return": average_net_return,
                    "maximum_drawdown": float(scenario["maximum_drawdown"]),
                    "maximum_symbol_concentration": float(
                        scenario["maximum_symbol_concentration"]
                    ),
                }
            )

        zero_signal_folds = [
            row["fold"] for row in fold_results if row["signal_count"] == 0
        ]
        non_positive_return_folds = [
            row["fold"]
            for row in fold_results
            if row["signal_count"] > 0 and row["average_net_return"] <= 0.0
        ]
        positive_return_folds = [
            row["fold"]
            for row in fold_results
            if row["signal_count"] > 0 and row["average_net_return"] > 0.0
        ]
        viable = not zero_signal_folds and not non_positive_return_folds
        if zero_signal_folds and non_positive_return_folds:
            status = "REJECT_ZERO_SIGNAL_AND_NON_POSITIVE_RETURN"
        elif zero_signal_folds:
            status = "REJECT_ZERO_SIGNAL"
        elif non_positive_return_folds:
            status = "REJECT_NON_POSITIVE_RETURN"
        else:
            status = "VIABLE_DIAGNOSTIC_ONLY"
            supported.append(threshold)
        rows.append(
            {
                "threshold": threshold,
                "scenario": scenario_name,
                "status": status,
                "viable_across_all_folds": viable,
                "total_signal_count": sum(
                    row["signal_count"] for row in fold_results
                ),
                "zero_signal_folds": zero_signal_folds,
                "non_positive_return_folds": non_positive_return_folds,
                "positive_return_folds": positive_return_folds,
                "folds": fold_results,
            }
        )

    return {
        "scenario": scenario_name,
        "candidate_thresholds": candidates,
        "supported_thresholds": supported,
        "threshold_change_supported": bool(supported),
        "recommended_action": (
            "EVALUATE_SUPPORTED_THRESHOLDS_WITH_SEPARATE_AUTHORITY"
            if supported
            else "DO_NOT_CHANGE_THRESHOLD_FROM_THIS_SWEEP"
        ),
        "rows": rows,
        "diagnostic_only": True,
        "quality_gate_changed": False,
    }
