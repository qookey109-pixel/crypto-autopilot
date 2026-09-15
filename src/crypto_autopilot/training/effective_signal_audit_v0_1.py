from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Mapping, Sequence

from crypto_autopilot.training.detailed import FEATURE_NAMES, IntradayExample


class EffectiveSignalAuditError(ValueError):
    """Raised when the aggregate-only Core100 audit contract is violated."""


def _utc_ms(value: str) -> int:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise EffectiveSignalAuditError("audit timestamps must be timezone-aware")
    return int(parsed.timestamp() * 1000)


def _safe_rate(positive: int, count: int) -> float | None:
    return positive / count if count else None


def _label_summary(items: Sequence[IntradayExample]) -> dict[str, Any]:
    positives = sum(int(item.label) for item in items)
    return {
        "count": len(items),
        "positives": positives,
        "negatives": len(items) - positives,
        "positive_rate": _safe_rate(positives, len(items)),
    }


def _quantile(sorted_values: Sequence[float], fraction: float) -> float | None:
    if not sorted_values:
        return None
    if not 0.0 <= fraction <= 1.0:
        raise EffectiveSignalAuditError("quantile fraction must be between zero and one")
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    position = fraction * (len(sorted_values) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return float(sorted_values[lower])
    weight = position - lower
    return float(sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight)


def dependence_diagnostics(
    items: Sequence[IntradayExample], *, label_horizon_ms: int
) -> dict[str, Any]:
    if label_horizon_ms <= 0:
        raise EffectiveSignalAuditError("label horizon must be positive")
    by_symbol: dict[str, list[int]] = defaultdict(list)
    timestamp_counts: Counter[int] = Counter()
    for item in items:
        by_symbol[item.symbol].append(int(item.time_ms))
        timestamp_counts[int(item.time_ms)] += 1

    gaps_hours: list[float] = []
    overlapping_pairs = 0
    adjacent_pairs = 0
    per_symbol_overlap: list[dict[str, Any]] = []
    for symbol in sorted(by_symbol):
        times = sorted(by_symbol[symbol])
        local_pairs = max(0, len(times) - 1)
        local_overlap = 0
        for previous, current in zip(times, times[1:]):
            gap = current - previous
            if gap < 0:
                raise EffectiveSignalAuditError("example timestamps must sort monotonically")
            gaps_hours.append(gap / 3_600_000.0)
            adjacent_pairs += 1
            if gap < label_horizon_ms:
                overlapping_pairs += 1
                local_overlap += 1
        per_symbol_overlap.append(
            {
                "symbol": symbol,
                "count": len(times),
                "adjacent_pairs": local_pairs,
                "overlap_pairs": local_overlap,
                "overlap_fraction": local_overlap / local_pairs if local_pairs else 0.0,
            }
        )

    gaps_hours.sort()
    cluster_sizes = sorted(timestamp_counts.values())
    return {
        "label_horizon_hours": label_horizon_ms / 3_600_000.0,
        "symbol_count": len(by_symbol),
        "same_symbol_adjacent_pairs": adjacent_pairs,
        "same_symbol_overlap_pairs": overlapping_pairs,
        "same_symbol_overlap_fraction": (
            overlapping_pairs / adjacent_pairs if adjacent_pairs else 0.0
        ),
        "adjacent_gap_hours": {
            "minimum": gaps_hours[0] if gaps_hours else None,
            "p50": _quantile(gaps_hours, 0.50),
            "p90": _quantile(gaps_hours, 0.90),
            "maximum": gaps_hours[-1] if gaps_hours else None,
        },
        "timestamp_clusters": {
            "example_count": len(items),
            "unique_timestamp_count": len(timestamp_counts),
            "unique_timestamp_fraction": (
                len(timestamp_counts) / len(items) if items else 0.0
            ),
            "mean_examples_per_timestamp": (
                len(items) / len(timestamp_counts) if timestamp_counts else 0.0
            ),
            "maximum_examples_at_one_timestamp": max(cluster_sizes) if cluster_sizes else 0,
        },
        "highest_same_symbol_overlap": sorted(
            per_symbol_overlap,
            key=lambda row: (
                -float(row["overlap_fraction"]),
                -int(row["count"]),
                str(row["symbol"]),
            ),
        )[:15],
        "interpretation": (
            "Descriptive dependence diagnostics only; these counts are not a formal effective "
            "sample-size estimate or an IID confidence adjustment."
        ),
    }


def _group_label_stats(items: Sequence[IntradayExample], key_fn) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[IntradayExample]] = defaultdict(list)
    for item in items:
        grouped[str(key_fn(item))].append(item)
    return {key: _label_summary(grouped[key]) for key in sorted(grouped)}


def symbol_drift(
    train: Sequence[IntradayExample],
    test: Sequence[IntradayExample],
    *,
    minimum_count: int,
    top_n: int,
) -> dict[str, Any]:
    if minimum_count < 1 or top_n < 1:
        raise EffectiveSignalAuditError("symbol drift bounds must be positive")
    train_stats = _group_label_stats(train, lambda item: item.symbol)
    test_stats = _group_label_stats(test, lambda item: item.symbol)
    rows = []
    for symbol in sorted(set(train_stats) | set(test_stats)):
        left = train_stats.get(symbol, {"count": 0, "positives": 0, "positive_rate": None})
        right = test_stats.get(symbol, {"count": 0, "positives": 0, "positive_rate": None})
        if int(left["count"]) < minimum_count or int(right["count"]) < minimum_count:
            continue
        train_rate = float(left["positive_rate"])
        test_rate = float(right["positive_rate"])
        rows.append(
            {
                "symbol": symbol,
                "train_count": int(left["count"]),
                "test_count": int(right["count"]),
                "train_positive_rate": train_rate,
                "test_positive_rate": test_rate,
                "positive_rate_delta": test_rate - train_rate,
                "absolute_positive_rate_delta": abs(test_rate - train_rate),
            }
        )
    rows.sort(
        key=lambda row: (
            -float(row["absolute_positive_rate_delta"]),
            str(row["symbol"]),
        )
    )
    return {
        "minimum_count_per_side": minimum_count,
        "eligible_symbol_count": len(rows),
        "top_absolute_positive_rate_drifts": rows[:top_n],
    }


_FEATURE_INDEX = {name: index for index, name in enumerate(FEATURE_NAMES)}


def _regime_name(item: IntradayExample) -> str:
    trend_value = item.features[_FEATURE_INDEX["ema20_vs_ema50_1h"]]
    volatility_value = item.features[_FEATURE_INDEX["atr_percentile_1h"]]
    trend = "bull" if trend_value >= 0.0 else "bear"
    if volatility_value < 1.0 / 3.0:
        volatility = "low"
    elif volatility_value < 2.0 / 3.0:
        volatility = "mid"
    else:
        volatility = "high"
    return f"{trend}_{volatility}"


def regime_drift(
    train: Sequence[IntradayExample], test: Sequence[IntradayExample]
) -> dict[str, Any]:
    train_stats = _group_label_stats(train, _regime_name)
    test_stats = _group_label_stats(test, _regime_name)
    rows = []
    for regime in sorted(set(train_stats) | set(test_stats)):
        left = train_stats.get(regime, {"count": 0, "positives": 0, "positive_rate": None})
        right = test_stats.get(regime, {"count": 0, "positives": 0, "positive_rate": None})
        train_count = int(left["count"])
        test_count = int(right["count"])
        train_share = train_count / len(train) if train else 0.0
        test_share = test_count / len(test) if test else 0.0
        train_rate = left["positive_rate"]
        test_rate = right["positive_rate"]
        rows.append(
            {
                "regime": regime,
                "train_count": train_count,
                "test_count": test_count,
                "train_share": train_share,
                "test_share": test_share,
                "share_delta": test_share - train_share,
                "train_positive_rate": train_rate,
                "test_positive_rate": test_rate,
                "positive_rate_delta": (
                    float(test_rate) - float(train_rate)
                    if train_rate is not None and test_rate is not None
                    else None
                ),
            }
        )
    return {
        "definition": {
            "trend_feature": "ema20_vs_ema50_1h",
            "trend_rule": "bull >= 0; bear < 0",
            "volatility_feature": "atr_percentile_1h",
            "volatility_rule": "low < 1/3; mid < 2/3; high otherwise",
        },
        "regimes": rows,
    }


def _mean_variance(values: Sequence[float]) -> tuple[float, float]:
    if not values:
        raise EffectiveSignalAuditError("mean/variance requires observations")
    mean = statistics.fmean(values)
    variance = statistics.fmean((value - mean) ** 2 for value in values)
    return float(mean), float(variance)


def feature_separation(
    items: Sequence[IntradayExample], *, top_n: int
) -> dict[str, Any]:
    if top_n < 1:
        raise EffectiveSignalAuditError("feature separation top_n must be positive")
    positive = [item for item in items if item.label == 1]
    negative = [item for item in items if item.label == 0]
    rows = []
    if not positive or not negative:
        return {
            "positive_count": len(positive),
            "negative_count": len(negative),
            "top_absolute_standardized_mean_differences": [],
        }
    for index, name in enumerate(FEATURE_NAMES):
        positive_values = [item.features[index] for item in positive]
        negative_values = [item.features[index] for item in negative]
        positive_mean, positive_variance = _mean_variance(positive_values)
        negative_mean, negative_variance = _mean_variance(negative_values)
        scale = math.sqrt((positive_variance + negative_variance) / 2.0)
        standardized = (
            (positive_mean - negative_mean) / scale if scale > 1e-12 else 0.0
        )
        rows.append(
            {
                "feature": name,
                "positive_mean": positive_mean,
                "negative_mean": negative_mean,
                "standardized_mean_difference": standardized,
                "absolute_standardized_mean_difference": abs(standardized),
            }
        )
    rows.sort(
        key=lambda row: (
            -float(row["absolute_standardized_mean_difference"]),
            str(row["feature"]),
        )
    )
    return {
        "positive_count": len(positive),
        "negative_count": len(negative),
        "top_absolute_standardized_mean_differences": rows[:top_n],
    }


def feature_drift(
    train: Sequence[IntradayExample],
    test: Sequence[IntradayExample],
    *,
    top_n: int,
) -> dict[str, Any]:
    if not train or not test:
        return {"top_absolute_standardized_mean_drifts": []}
    rows = []
    for index, name in enumerate(FEATURE_NAMES):
        train_values = [item.features[index] for item in train]
        test_values = [item.features[index] for item in test]
        train_mean, train_variance = _mean_variance(train_values)
        test_mean, test_variance = _mean_variance(test_values)
        scale = math.sqrt((train_variance + test_variance) / 2.0)
        standardized = (test_mean - train_mean) / scale if scale > 1e-12 else 0.0
        rows.append(
            {
                "feature": name,
                "train_mean": train_mean,
                "test_mean": test_mean,
                "standardized_mean_drift": standardized,
                "absolute_standardized_mean_drift": abs(standardized),
            }
        )
    rows.sort(
        key=lambda row: (
            -float(row["absolute_standardized_mean_drift"]),
            str(row["feature"]),
        )
    )
    return {"top_absolute_standardized_mean_drifts": rows[:top_n]}


def _bounded_even_sample(
    items: Sequence[IntradayExample], limit: int
) -> list[IntradayExample]:
    ordered = sorted(items, key=lambda item: (item.time_ms, item.symbol))
    if len(ordered) <= limit:
        return list(ordered)
    return [ordered[(index * len(ordered)) // limit] for index in range(limit)]


def feature_redundancy(
    items: Sequence[IntradayExample],
    *,
    sample_limit: int,
    absolute_correlation_threshold: float,
    top_n: int,
) -> dict[str, Any]:
    if sample_limit < 20 or top_n < 1:
        raise EffectiveSignalAuditError("feature redundancy bounds are too small")
    if not 0.0 < absolute_correlation_threshold <= 1.0:
        raise EffectiveSignalAuditError("correlation threshold must be in (0, 1]")
    sample = _bounded_even_sample(items, sample_limit)
    if len(sample) < 2:
        return {
            "sample_count": len(sample),
            "threshold": absolute_correlation_threshold,
            "top_high_correlation_pairs": [],
        }
    width = len(FEATURE_NAMES)
    columns = [[item.features[index] for item in sample] for index in range(width)]
    means = [statistics.fmean(column) for column in columns]
    centered = [
        [value - means[index] for value in column]
        for index, column in enumerate(columns)
    ]
    sums_sq = [sum(value * value for value in column) for column in centered]
    rows = []
    for left in range(width):
        if sums_sq[left] <= 1e-24:
            continue
        for right in range(left + 1, width):
            if sums_sq[right] <= 1e-24:
                continue
            numerator = sum(x * y for x, y in zip(centered[left], centered[right]))
            correlation = numerator / math.sqrt(sums_sq[left] * sums_sq[right])
            if abs(correlation) >= absolute_correlation_threshold:
                rows.append(
                    {
                        "left_feature": FEATURE_NAMES[left],
                        "right_feature": FEATURE_NAMES[right],
                        "correlation": correlation,
                        "absolute_correlation": abs(correlation),
                    }
                )
    rows.sort(
        key=lambda row: (
            -float(row["absolute_correlation"]),
            str(row["left_feature"]),
            str(row["right_feature"]),
        )
    )
    return {
        "sample_count": len(sample),
        "threshold": absolute_correlation_threshold,
        "top_high_correlation_pairs": rows[:top_n],
    }


def _fold_audit(
    items: Sequence[IntradayExample],
    *,
    fold: Mapping[str, Any],
    minimum_symbol_count: int,
    top_n: int,
) -> dict[str, Any]:
    train_end = _utc_ms(str(fold["train_end_exclusive"]))
    test_end = _utc_ms(str(fold["test_end_exclusive"]))
    train = [item for item in items if item.time_ms < train_end]
    test = [item for item in items if train_end <= item.time_ms < test_end]
    return {
        "name": str(fold["name"]),
        "train_end_exclusive": str(fold["train_end_exclusive"]),
        "test_end_exclusive": str(fold["test_end_exclusive"]),
        "train_label_balance": _label_summary(train),
        "test_label_balance": _label_summary(test),
        "symbol_drift": symbol_drift(
            train,
            test,
            minimum_count=minimum_symbol_count,
            top_n=top_n,
        ),
        "regime_drift": regime_drift(train, test),
        "test_feature_separation": feature_separation(test, top_n=top_n),
        "feature_train_test_drift": feature_drift(train, test, top_n=top_n),
    }


def _recommendations(folds: Sequence[Mapping[str, Any]]) -> list[str]:
    recommendations = ["DO_NOT_CHANGE_THRESHOLD_FROM_THIS_AUDIT_ALONE"]
    max_late_separation = 0.0
    max_late_drift = 0.0
    for fold in folds[-2:]:
        separation = fold["test_feature_separation"][
            "top_absolute_standardized_mean_differences"
        ]
        drift = fold["feature_train_test_drift"]["top_absolute_standardized_mean_drifts"]
        if separation:
            max_late_separation = max(
                max_late_separation,
                max(float(row["absolute_standardized_mean_difference"]) for row in separation),
            )
        if drift:
            max_late_drift = max(
                max_late_drift,
                max(float(row["absolute_standardized_mean_drift"]) for row in drift),
            )
    if max_late_drift >= 0.5:
        recommendations.append("REGIME_OR_FEATURE_DRIFT_REVIEW")
    if max_late_separation < 0.1:
        recommendations.append("FEATURE_INFORMATION_REVIEW_BEFORE_MODEL_CAPACITY")
    elif max_late_separation >= 0.25:
        recommendations.append("NONLINEAR_CAPACITY_BENCHMARK_CANDIDATE")
    recommendations.append("KEEP_HOLDOUT_CLOSED")
    return recommendations


def run_effective_signal_audit(
    examples: Sequence[IntradayExample],
    *,
    training_config: Mapping[str, Any],
    dataset_fingerprint: str,
    expected_dataset_fingerprint: str,
    generated_at_utc: str,
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a deterministic aggregate-only diagnostic report without fitting a model."""

    if dataset_fingerprint != expected_dataset_fingerprint:
        raise EffectiveSignalAuditError("dataset fingerprint does not match frozen audit lineage")
    if not examples:
        raise EffectiveSignalAuditError("effective signal audit requires examples")
    if any(item.label not in (0, 1) for item in examples):
        raise EffectiveSignalAuditError("audit labels must be binary")
    if any(len(item.features) != len(FEATURE_NAMES) for item in examples):
        raise EffectiveSignalAuditError("audit feature width mismatch")
    if any(
        not math.isfinite(value)
        for item in examples
        for value in (*item.features, item.forward_return)
    ):
        raise EffectiveSignalAuditError("audit inputs must be finite")

    authority = policy.get("authority")
    if not isinstance(authority, Mapping) or not authority:
        raise EffectiveSignalAuditError("audit authority must be a non-empty object")
    required_false = (
        "provider_requests_authorized",
        "r2_writes_authorized",
        "holdout_access_authorized",
        "training_authorized",
        "training_publication_authorized",
        "strategy_parameter_change_authorized",
        "source_switch_authorized",
        "automatic_model_promotion_authorized",
        "formal_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    )
    if any(authority.get(name) is not False for name in required_false):
        raise EffectiveSignalAuditError("unsafe audit authority flag changed")
    if authority.get("production_r2_training_reads_authorized") is not True:
        raise EffectiveSignalAuditError("audit requires exact governed R2 training-read authority")

    expected_example_count = int(policy["lineage"]["expected_example_count"])
    expected_symbol_count = int(policy["lineage"]["expected_symbol_count"])
    if len(examples) != expected_example_count:
        raise EffectiveSignalAuditError("example count does not match frozen audit lineage")
    if len({item.symbol for item in examples}) != expected_symbol_count:
        raise EffectiveSignalAuditError("symbol count does not match frozen audit lineage")

    source_end_ms = _utc_ms(str(policy["lineage"]["source_end_exclusive_utc"]))
    holdout_start_ms = _utc_ms(str(policy["lineage"]["replacement_holdout_start_utc"]))
    if any(item.time_ms >= source_end_ms for item in examples):
        raise EffectiveSignalAuditError("example timestamp crosses frozen source end")
    if any(item.time_ms >= holdout_start_ms for item in examples):
        raise EffectiveSignalAuditError("example timestamp reaches replacement holdout")

    horizon_bars = int(training_config["forward_horizon_15m_bars"])
    label_horizon_ms = horizon_bars * 15 * 60 * 1000
    top_n = int(policy["diagnostics"]["top_n"])
    minimum_symbol_count = int(policy["diagnostics"]["minimum_symbol_count_per_fold_side"])
    folds = [
        _fold_audit(
            examples,
            fold=fold,
            minimum_symbol_count=minimum_symbol_count,
            top_n=top_n,
        )
        for fold in training_config["walk_forward_folds"]
    ]
    return {
        "schema": "core100-effective-signal-audit-report-v0.1",
        "status": "PASS",
        "stage": "CORE100_EFFECTIVE_SIGNAL_AUDIT_V0_1",
        "generated_at_utc": generated_at_utc,
        "dataset_fingerprint": dataset_fingerprint,
        "example_count": len(examples),
        "symbol_count": len({item.symbol for item in examples}),
        "feature_count": len(FEATURE_NAMES),
        "feature_names": list(FEATURE_NAMES),
        "global_label_balance": _label_summary(examples),
        "dependence_diagnostics": dependence_diagnostics(
            examples, label_horizon_ms=label_horizon_ms
        ),
        "walk_forward_folds": folds,
        "feature_redundancy": feature_redundancy(
            examples,
            sample_limit=int(policy["diagnostics"]["feature_correlation_sample_limit"]),
            absolute_correlation_threshold=float(
                policy["diagnostics"]["feature_correlation_threshold"]
            ),
            top_n=top_n,
        ),
        "recommendations": _recommendations(folds),
        "interpretation": (
            "Aggregate descriptive diagnosis of the exact governed Core100 training examples. "
            "It does not fit a model, change a threshold, claim profitability, or grant trading "
            "authority."
        ),
        "authority": {
            "diagnostic_only": True,
            "aggregate_only": True,
            "holdout_accessed": False,
            "provider_requests_performed": 0,
            "r2_reads_performed": True,
            "r2_writes_performed": False,
            "training_performed": False,
            "training_published": False,
            "strategy_parameter_changed": False,
            "source_switch_authorized": False,
            "automatic_model_promotion": False,
            "formal_trade_plan": False,
            "real_money_orders": False,
            "live_trading": False,
        },
    }
