from __future__ import annotations

import math
from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence

from crypto_autopilot.features.advanced import AdvancedTechnicalSnapshot, build_advanced_technical_series
from crypto_autopilot.historical import INTERVAL_MS
from crypto_autopilot.models import Candle
from crypto_autopilot.technical import TechnicalSnapshot, build_technical_series


FEATURE_NAMES = (
    "return_15m",
    "return_1h",
    "return_4h",
    "close_vs_ema20_15m",
    "ema20_vs_ema50_15m",
    "rsi14_15m",
    "macd_histogram_fraction_15m",
    "adx14_15m",
    "di_spread_15m",
    "vwap_distance_15m",
    "volume_zscore_15m",
    "donchian_position_15m",
    "atr_percentile_15m",
    "bollinger_bandwidth_percentile_15m",
    "realized_volatility_15m",
    "parkinson_volatility_15m",
    "efficiency_ratio_15m",
    "choppiness_15m",
    "volatility_adjusted_momentum_15m",
    "close_vs_ema20_1h",
    "ema20_vs_ema50_1h",
    "rsi14_1h",
    "adx14_1h",
    "di_spread_1h",
    "atr_percentile_1h",
    "close_vs_ema20_4h",
    "ema20_vs_ema50_4h",
    "rsi14_4h",
    "adx14_4h",
    "di_spread_4h",
    "atr_percentile_4h",
)


@dataclass(frozen=True, slots=True)
class IntradayExample:
    symbol: str
    asset_class: str
    time_ms: int
    features: tuple[float, ...]
    label: int
    forward_return: float


def _ratio(current: float, reference: float) -> float:
    if not math.isfinite(current) or not math.isfinite(reference) or reference <= 0:
        return 0.0
    return current / reference - 1.0


def _technical_features(
    technical: TechnicalSnapshot,
    advanced: AdvancedTechnicalSnapshot,
    *,
    suffix: str,
) -> dict[str, float]:
    if (
        not technical.ready_v0_2
        or not advanced.ready
        or technical.ema20 is None
        or technical.ema50 is None
        or technical.rsi14 is None
        or technical.macd_histogram is None
        or advanced.adx14 is None
        or advanced.plus_di14 is None
        or advanced.minus_di14 is None
        or advanced.atr_percentile100 is None
    ):
        return {}
    output = {
        f"close_vs_ema20_{suffix}": _ratio(technical.close, technical.ema20),
        f"ema20_vs_ema50_{suffix}": _ratio(technical.ema20, technical.ema50),
        f"rsi14_{suffix}": technical.rsi14 / 100.0,
        f"adx14_{suffix}": advanced.adx14 / 100.0,
        f"di_spread_{suffix}": (advanced.plus_di14 - advanced.minus_di14) / 100.0,
        f"atr_percentile_{suffix}": advanced.atr_percentile100,
    }
    if suffix == "15m":
        normalized = advanced.normalized_features
        required = (
            "vwap_distance_fraction",
            "volume_zscore20",
            "donchian_position20",
            "atr_percentile100",
            "bollinger_bandwidth_percentile100",
            "realized_volatility20",
            "parkinson_volatility20",
            "kaufman_efficiency_ratio10",
            "choppiness_index14",
            "volatility_adjusted_momentum20",
        )
        if any(normalized.get(name) is None for name in required):
            return {}
        output.update(
            {
                "rsi14_15m": technical.rsi14 / 100.0,
                "macd_histogram_fraction_15m": technical.macd_histogram / technical.close,
                "adx14_15m": advanced.adx14 / 100.0,
                "di_spread_15m": (advanced.plus_di14 - advanced.minus_di14) / 100.0,
                "vwap_distance_15m": float(normalized["vwap_distance_fraction"]),
                "volume_zscore_15m": float(normalized["volume_zscore20"]),
                "donchian_position_15m": float(normalized["donchian_position20"]),
                "atr_percentile_15m": float(normalized["atr_percentile100"]),
                "bollinger_bandwidth_percentile_15m": float(
                    normalized["bollinger_bandwidth_percentile100"]
                ),
                "realized_volatility_15m": float(normalized["realized_volatility20"]),
                "parkinson_volatility_15m": float(normalized["parkinson_volatility20"]),
                "efficiency_ratio_15m": float(normalized["kaufman_efficiency_ratio10"]),
                "choppiness_15m": float(normalized["choppiness_index14"]) / 100.0,
                "volatility_adjusted_momentum_15m": float(
                    normalized["volatility_adjusted_momentum20"]
                ),
            }
        )
    return output


def build_intraday_examples(
    *,
    symbol: str,
    asset_class: str,
    candles_by_interval: Mapping[str, Sequence[Candle]],
    sample_stride_15m_bars: int,
    forward_horizon_15m_bars: int,
    label_cost_bps_round_trip: float,
) -> list[IntradayExample]:
    """Build causal 15m examples joined to already-closed 1h/4h context."""

    if sample_stride_15m_bars < 1 or forward_horizon_15m_bars < 1:
        raise ValueError("intraday stride and horizon must be positive")
    required = ("15m", "1h", "4h")
    if any(interval not in candles_by_interval for interval in required):
        raise ValueError("intraday training requires 15m, 1h and 4h candles")
    project = {"15m": "15M", "1h": "60M", "4h": "4H"}
    candles = {interval: tuple(candles_by_interval[interval]) for interval in required}
    technical = {
        interval: build_technical_series(candles[interval], project[interval])
        for interval in required
    }
    advanced = {
        interval: build_advanced_technical_series(
            candles[interval], project[interval], technical_series=technical[interval]
        )
        for interval in required
    }
    available = {
        interval: tuple(item.available_at_ms for item in technical[interval])
        for interval in required
    }
    source = candles["15m"]
    horizon_ms = forward_horizon_15m_bars * INTERVAL_MS["15M"]
    label_cost = label_cost_bps_round_trip / 10_000.0
    output: list[IntradayExample] = []
    start = 200
    for index in range(start, len(source) - forward_horizon_15m_bars, sample_stride_15m_bars):
        future_index = index + forward_horizon_15m_bars
        if source[future_index].time_ms - source[index].time_ms != horizon_ms:
            continue
        current_technical = technical["15m"][index]
        current_advanced = advanced["15m"][index]
        values = _technical_features(current_technical, current_advanced, suffix="15m")
        if not values:
            continue
        values["return_15m"] = _ratio(source[index].close, source[index - 1].close)
        values["return_1h"] = _ratio(source[index].close, source[index - 4].close)
        values["return_4h"] = _ratio(source[index].close, source[index - 16].close)
        for interval in ("1h", "4h"):
            context_index = bisect_right(
                available[interval], current_technical.available_at_ms
            ) - 1
            if context_index < 0:
                values = {}
                break
            values.update(
                _technical_features(
                    technical[interval][context_index],
                    advanced[interval][context_index],
                    suffix=interval,
                )
            )
        if set(values) != set(FEATURE_NAMES):
            continue
        feature_values = tuple(float(values[name]) for name in FEATURE_NAMES)
        if not all(math.isfinite(value) for value in feature_values):
            continue
        forward_return = _ratio(source[future_index].close, source[index].close)
        output.append(
            IntradayExample(
                symbol=symbol,
                asset_class=asset_class,
                time_ms=current_technical.available_at_ms,
                features=feature_values,
                label=int(forward_return > label_cost),
                forward_return=forward_return,
            )
        )
    return output


def bound_examples(
    items: Sequence[IntradayExample], limit: int
) -> list[IntradayExample]:
    if limit < 1:
        raise ValueError("example limit must be positive")
    ordered = sorted(items, key=lambda item: (item.time_ms, item.symbol))
    if len(ordered) <= limit:
        return ordered
    return [ordered[(index * len(ordered)) // limit] for index in range(limit)]


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, value))))


def fit_logistic(
    items: Sequence[IntradayExample],
    *,
    epochs: int,
    learning_rate: float,
    l2: float,
) -> dict[str, Any]:
    if not items:
        raise ValueError("cannot fit an empty intraday model")
    width = len(FEATURE_NAMES)
    if any(len(item.features) != width for item in items):
        raise ValueError("intraday feature width mismatch")
    means = [sum(item.features[index] for item in items) / len(items) for index in range(width)]
    stds = []
    for index, mean in enumerate(means):
        variance = sum((item.features[index] - mean) ** 2 for item in items) / len(items)
        stds.append(max(math.sqrt(variance), 1e-12))
    weights = [0.0] * width
    positive_rate = sum(item.label for item in items) / len(items)
    bias = math.log(max(1e-6, positive_rate) / max(1e-6, 1.0 - positive_rate))
    for epoch in range(epochs):
        gradients = [0.0] * width
        bias_gradient = 0.0
        for item in items:
            normalized = [
                max(-8.0, min(8.0, (value - mean) / std))
                for value, mean, std in zip(item.features, means, stds)
            ]
            error = _sigmoid(
                bias + sum(weight * value for weight, value in zip(weights, normalized))
            ) - item.label
            bias_gradient += error
            for index, value in enumerate(normalized):
                gradients[index] += error * value
        rate = learning_rate / (1.0 + epoch * 0.25)
        bias -= rate * bias_gradient / len(items)
        for index in range(width):
            weights[index] -= rate * (gradients[index] / len(items) + l2 * weights[index])
    return {
        "feature_names": list(FEATURE_NAMES),
        "means": means,
        "standard_deviations": stds,
        "weights": weights,
        "bias": bias,
    }


def predict(item: IntradayExample, model: Mapping[str, Any]) -> float:
    normalized = [
        max(-8.0, min(8.0, (value - float(mean)) / float(std)))
        for value, mean, std in zip(
            item.features, model["means"], model["standard_deviations"]
        )
    ]
    return _sigmoid(
        float(model["bias"])
        + sum(float(weight) * value for weight, value in zip(model["weights"], normalized))
    )


def probability_metrics(
    items: Sequence[IntradayExample], probabilities: Sequence[float]
) -> dict[str, float | int]:
    if not items or len(items) != len(probabilities):
        raise ValueError("probability metrics require aligned non-empty inputs")
    loss = 0.0
    brier = 0.0
    correct = 0
    for item, raw_probability in zip(items, probabilities):
        probability = max(1e-9, min(1.0 - 1e-9, raw_probability))
        loss -= item.label * math.log(probability) + (1 - item.label) * math.log(
            1.0 - probability
        )
        brier += (probability - item.label) ** 2
        correct += int((probability >= 0.5) == bool(item.label))
    return {
        "samples": len(items),
        "positive_rate": sum(item.label for item in items) / len(items),
        "accuracy": correct / len(items),
        "log_loss": loss / len(items),
        "brier_score": brier / len(items),
    }


def _signal_diagnostics(
    items: Sequence[IntradayExample],
    probabilities: Sequence[float],
    *,
    threshold: float,
    fee_bps_per_side: float,
    slippage_bps_per_side: float,
) -> dict[str, Any]:
    selected = [
        (item, probability)
        for item, probability in zip(items, probabilities)
        if probability >= threshold
    ]
    if not selected:
        return {
            "signal_count": 0,
            "average_net_return": 0.0,
            "diagnostic_growth": 0.0,
            "maximum_drawdown": 0.0,
            "maximum_symbol_concentration": 0.0,
        }
    cost = 2.0 * (fee_bps_per_side + slippage_bps_per_side) / 10_000.0
    equity = 1.0
    peak = 1.0
    maximum_drawdown = 0.0
    symbol_counts: dict[str, int] = {}
    net_returns = []
    for item, _probability in sorted(selected, key=lambda value: (value[0].time_ms, value[0].symbol)):
        net = max(-0.99, item.forward_return - cost)
        net_returns.append(net)
        equity *= 1.0 + net
        peak = max(peak, equity)
        maximum_drawdown = max(maximum_drawdown, 1.0 - equity / peak)
        symbol_counts[item.symbol] = symbol_counts.get(item.symbol, 0) + 1
    return {
        "signal_count": len(selected),
        "average_net_return": sum(net_returns) / len(net_returns),
        "diagnostic_growth": equity - 1.0,
        "maximum_drawdown": maximum_drawdown,
        "maximum_symbol_concentration": max(symbol_counts.values()) / len(selected),
    }


def _utc_ms(value: str) -> int:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("walk-forward timestamp must be timezone-aware")
    return int(parsed.timestamp() * 1000)


def run_intraday_training(
    examples: Sequence[IntradayExample],
    *,
    config: Mapping[str, Any],
    dataset_fingerprint: str,
    generated_at_utc: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    training = config["training"]
    items = bound_examples(examples, int(training["maximum_total_examples"]))
    folds = []
    all_ready = True
    all_better_than_baseline = True
    for fold in training["walk_forward_folds"]:
        train_end = _utc_ms(str(fold["train_end_exclusive"]))
        test_end = _utc_ms(str(fold["test_end_exclusive"]))
        train = [item for item in items if item.time_ms < train_end]
        test = [item for item in items if train_end <= item.time_ms < test_end]
        if (
            len(train) < int(training["minimum_train_examples"])
            or len(test) < int(training["minimum_test_examples"])
        ):
            folds.append(
                {
                    "name": fold["name"],
                    "status": "NOT_READY",
                    "train_samples": len(train),
                    "test_samples": len(test),
                }
            )
            all_ready = False
            all_better_than_baseline = False
            continue
        model = fit_logistic(
            train,
            epochs=int(training["epochs"]),
            learning_rate=float(training["learning_rate"]),
            l2=float(training["l2"]),
        )
        probabilities = [predict(item, model) for item in test]
        metrics = probability_metrics(test, probabilities)
        prevalence = sum(item.label for item in train) / len(train)
        baseline = probability_metrics(test, [prevalence] * len(test))
        better = float(metrics["log_loss"]) < float(baseline["log_loss"])
        all_better_than_baseline = all_better_than_baseline and better
        scenarios = {
            str(scenario["name"]): _signal_diagnostics(
                test,
                probabilities,
                threshold=float(training["probability_threshold"]),
                fee_bps_per_side=float(scenario["fee_bps_per_side"]),
                slippage_bps_per_side=float(scenario["slippage_bps_per_side"]),
            )
            for scenario in training["cost_scenarios"]
        }
        folds.append(
            {
                "name": fold["name"],
                "status": "PASS",
                "train_samples": len(train),
                "test_samples": len(test),
                "metrics": metrics,
                "naive_train_prevalence_baseline": baseline,
                "beats_naive_log_loss": better,
                "cost_scenarios": scenarios,
            }
        )

    final_model = fit_logistic(
        items,
        epochs=int(training["epochs"]),
        learning_rate=float(training["learning_rate"]),
        l2=float(training["l2"]),
    )
    model_payload = {
        "schema": "binance-usdm-intraday-research-model-v0.1",
        "status": "RESEARCH_ONLY",
        "provider": "binance_usdm",
        "generated_at_utc": generated_at_utc,
        "dataset_fingerprint": dataset_fingerprint,
        "model": final_model,
        "authority": {
            "pionex_native_relabel_authorized": False,
            "source_switch_authorized": False,
            "automatic_model_promotion_authorized": False,
            "formal_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }
    base_scenario_positive = all(
        fold.get("status") == "PASS"
        and float(fold["cost_scenarios"]["base"]["average_net_return"]) > 0.0
        for fold in folds
    )
    quality_status = (
        "PASS"
        if all_ready and all_better_than_baseline and base_scenario_positive
        else "REJECT"
    )
    metrics_payload = {
        "schema": "binance-usdm-intraday-research-metrics-v0.1",
        "status": "PASS",
        "provider": "binance_usdm",
        "generated_at_utc": generated_at_utc,
        "dataset_fingerprint": dataset_fingerprint,
        "example_count": len(items),
        "symbol_count": len({item.symbol for item in items}),
        "feature_names": list(FEATURE_NAMES),
        "walk_forward_folds": folds,
        "model_quality_gate": {
            "status": quality_status,
            "all_folds_ready": all_ready,
            "all_folds_beat_naive_log_loss": all_better_than_baseline,
            "all_base_cost_scenarios_positive_average_return": base_scenario_positive,
            "automatic_promotion": False,
        },
        "interpretation": (
            "Research diagnostics over provider-separated Binance USD-M history; "
            "not Pionex-native evidence or a profitability claim."
        ),
    }
    return model_payload, metrics_payload
