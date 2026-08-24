"""Local-only V0.6 Shadow Model ablation diagnostics.

This module deliberately does not import the online publisher or any R2 client.
It consumes an already-materialized, provider-separated Spot dataset and
returns comparable research evidence for feature groups.  It is not a model
promotion or trading path.
"""

from __future__ import annotations

import math
import platform
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Sequence

from .advanced_technical import AdvancedTechnicalSnapshot, build_advanced_technical_series
from .experiment_registry import build_experiment_registry_entry
from .models import Candle

DAY_MS = 86_400_000
BASELINE_FEATURES = (
    "return_1d",
    "return_3d",
    "return_7d",
    "close_vs_ma7",
    "quote_volume_vs_ma7",
)
FEATURE_GROUPS: dict[str, tuple[str, ...]] = {
    "baseline": BASELINE_FEATURES,
    "trend": BASELINE_FEATURES + ("adx14", "plus_di14", "minus_di14"),
    "price_volume": BASELINE_FEATURES
    + ("vwap_distance_fraction", "volume_zscore20", "donchian_position20"),
    "volatility": BASELINE_FEATURES
    + (
        "atr_percentile100",
        "bollinger_bandwidth_percentile100",
        "realized_volatility20",
        "parkinson_volatility20",
    ),
}


@dataclass(frozen=True, slots=True)
class ShadowExample:
    symbol: str
    asset_class: str
    time_ms: int
    features: tuple[float, ...]
    label: int
    forward_return: float
    regimes: tuple[tuple[str, str], ...]


def _finite(value: Any) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("shadow dataset contains a non-finite numeric value")
    return result


def _ratio(current: float, reference: float) -> float:
    if not math.isfinite(current) or not math.isfinite(reference) or reference <= 0:
        return 0.0
    return current / reference - 1.0


def _candle(row: dict[str, Any]) -> Candle:
    open_price = _finite(row["open"])
    high = _finite(row["high"])
    low = _finite(row["low"])
    close = _finite(row["close"])
    volume = _finite(row.get("quote_volume", row.get("base_volume", 0.0)))
    if min(open_price, high, low, close) <= 0 or volume < 0 or high < low:
        raise ValueError("shadow dataset contains invalid OHLCV values")
    if high < max(open_price, close) or low > min(open_price, close):
        raise ValueError("shadow dataset violates OHLC bounds")
    return Candle(
        time_ms=int(row["open_time_ms"]),
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def _segments(rows: Sequence[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    ordered = sorted(rows, key=lambda row: int(row["open_time_ms"]))
    output: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for row in ordered:
        if current and int(row["open_time_ms"]) - int(current[-1]["open_time_ms"]) != DAY_MS:
            output.append(current)
            current = []
        current.append(row)
    if current:
        output.append(current)
    return output


def _feature_values(
    items: Sequence[dict[str, Any]], index: int, advanced: AdvancedTechnicalSnapshot
) -> dict[str, float]:
    closes = [_finite(items[offset]["close"]) for offset in range(index - 6, index + 1)]
    volumes = [_finite(items[offset].get("quote_volume", items[offset].get("base_volume", 0.0))) for offset in range(index - 6, index + 1)]
    values: dict[str, float] = {
        "return_1d": _ratio(closes[-1], _finite(items[index - 1]["close"])),
        "return_3d": _ratio(closes[-1], _finite(items[index - 3]["close"])),
        "return_7d": _ratio(closes[-1], _finite(items[index - 7]["close"])),
        "close_vs_ma7": _ratio(closes[-1], sum(closes) / len(closes)),
        "quote_volume_vs_ma7": _ratio(volumes[-1], sum(volumes) / len(volumes)),
    }
    for name, value in advanced.normalized_features.items():
        if value is not None:
            values[name] = float(value)
    return values


def _regimes(values: dict[str, float]) -> tuple[tuple[str, str], ...]:
    regimes: list[tuple[str, str]] = []
    if "adx14" in values:
        regimes.append(("trend", "strong" if values["adx14"] >= 25.0 else "weak"))
    if "volume_zscore20" in values:
        regimes.append(("volume", "high" if values["volume_zscore20"] >= 1.0 else "normal"))
    if "atr_percentile100" in values:
        regimes.append(("volatility", "high" if values["atr_percentile100"] >= 0.7 else "normal"))
    return tuple(regimes)


def build_shadow_examples(
    rows: Sequence[dict[str, Any]],
    *,
    end_exclusive_ms: int,
    warmup_bars: int = 100,
    groups: dict[str, tuple[str, ...]] | None = None,
) -> dict[str, list[ShadowExample]]:
    """Build causal examples for each ablation group from audited daily rows."""

    selected_groups = groups or FEATURE_GROUPS
    for group, names in selected_groups.items():
        if not names or tuple(names[: len(BASELINE_FEATURES)]) != BASELINE_FEATURES:
            raise ValueError(f"shadow group {group!r} must begin with the baseline contract")

    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("audit_ok") is True and int(row["open_time_ms"]) < end_exclusive_ms:
            by_symbol[str(row["symbol"])].append(dict(row))

    result: dict[str, list[ShadowExample]] = {group: [] for group in selected_groups}
    for symbol, symbol_rows in sorted(by_symbol.items()):
        for segment in _segments(symbol_rows):
            if len(segment) <= warmup_bars + 1:
                continue
            candles = tuple(_candle(row) for row in segment)
            advanced = build_advanced_technical_series(candles, "1D")
            asset_class = str(segment[0]["asset_class"])
            for index in range(warmup_bars, len(segment) - 1):
                current = segment[index]
                next_row = segment[index + 1]
                values = _feature_values(segment, index, advanced[index])
                if any(name not in values for names in selected_groups.values() for name in names):
                    continue
                regimes = _regimes(values)
                base = dict(
                    symbol=symbol,
                    asset_class=asset_class,
                    time_ms=int(current["open_time_ms"]),
                    label=int(_finite(next_row["close"]) > _finite(current["close"])),
                    forward_return=_ratio(_finite(next_row["close"]), _finite(current["close"])),
                    regimes=regimes,
                )
                for group, names in selected_groups.items():
                    result[group].append(
                        ShadowExample(features=tuple(values[name] for name in names), **base)
                    )
    for items in result.values():
        items.sort(key=lambda item: (item.time_ms, item.symbol))
    return result


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, value))))


def _normalization(items: Sequence[ShadowExample]) -> tuple[list[float], list[float]]:
    width = len(items[0].features)
    means = [sum(item.features[index] for item in items) / len(items) for index in range(width)]
    stds = []
    for index, mean in enumerate(means):
        variance = sum((item.features[index] - mean) ** 2 for item in items) / len(items)
        stds.append(max(math.sqrt(variance), 1e-12))
    return means, stds


def _predict(item: ShadowExample, model: dict[str, Any]) -> float:
    normalized = [
        max(-8.0, min(8.0, (value - mean) / std))
        for value, mean, std in zip(item.features, model["means"], model["stds"])
    ]
    return _sigmoid(float(model["bias"]) + sum(weight * value for weight, value in zip(model["weights"], normalized)))


def _fit(items: Sequence[ShadowExample], *, epochs: int, learning_rate: float, l2: float) -> dict[str, Any]:
    means, stds = _normalization(items)
    weights = [0.0] * len(items[0].features)
    positive_rate = sum(item.label for item in items) / len(items)
    bias = math.log(max(1e-6, positive_rate) / max(1e-6, 1.0 - positive_rate))
    for epoch in range(epochs):
        gradients = [0.0] * len(weights)
        bias_gradient = 0.0
        for item in items:
            normalized = [
                max(-8.0, min(8.0, (value - mean) / std))
                for value, mean, std in zip(item.features, means, stds)
            ]
            error = _sigmoid(bias + sum(weight * value for weight, value in zip(weights, normalized))) - item.label
            bias_gradient += error
            for index, value in enumerate(normalized):
                gradients[index] += error * value
        rate = learning_rate / (1.0 + epoch * 0.25)
        bias -= rate * bias_gradient / len(items)
        for index in range(len(weights)):
            weights[index] -= rate * (gradients[index] / len(items) + l2 * weights[index])
    return {"means": means, "stds": stds, "weights": weights, "bias": bias}


def _metrics(items: Sequence[ShadowExample], model: dict[str, Any], *, bins: int) -> dict[str, Any]:
    if not items:
        raise ValueError("cannot score an empty shadow split")
    probabilities = [_predict(item, model) for item in items]
    labels = [item.label for item in items]
    log_loss = 0.0
    brier = 0.0
    correct = 0
    for probability, label in zip(probabilities, labels):
        probability = max(1e-9, min(1.0 - 1e-9, probability))
        log_loss -= label * math.log(probability) + (1 - label) * math.log(1 - probability)
        brier += (probability - label) ** 2
        correct += int((probability >= 0.5) == bool(label))
    calibration_bins = []
    ece = 0.0
    mce = 0.0
    for bucket in range(bins):
        members = [index for index, probability in enumerate(probabilities) if int(probability * bins) == bucket]
        if not members:
            continue
        confidence = sum(probabilities[index] for index in members) / len(members)
        outcome = sum(labels[index] for index in members) / len(members)
        gap = abs(confidence - outcome)
        ece += gap * len(members) / len(items)
        mce = max(mce, gap)
        calibration_bins.append({"bin": bucket, "samples": len(members), "confidence": confidence, "outcome_rate": outcome})
    return {
        "samples": len(items),
        "positive_rate": sum(labels) / len(labels),
        "accuracy": correct / len(items),
        "log_loss": log_loss / len(items),
        "brier_score": brier / len(items),
        "ece": ece,
        "mce": mce,
        "calibration_bins": calibration_bins,
    }


def _regime_metrics(items: Sequence[ShadowExample], model: dict[str, Any], *, minimum_samples: int) -> dict[str, Any]:
    groups: dict[str, list[ShadowExample]] = defaultdict(list)
    for item in items:
        for dimension, state in item.regimes:
            groups[f"{dimension}:{state}"].append(item)
    output: dict[str, Any] = {}
    for name, members in sorted(groups.items()):
        if len(members) < minimum_samples:
            output[name] = {"status": "DESCRIPTIVE_ONLY_MIN_N_NOT_MET", "samples": len(members)}
        else:
            output[name] = {"status": "DESCRIPTIVE_ONLY", **_metrics(members, model, bins=10)}
    return output


def _validate_config(config: dict[str, Any]) -> None:
    if config.get("status") != "PREPARED_NOT_ACTIVE":
        raise ValueError("shadow config must remain PREPARED_NOT_ACTIVE")
    execution = config.get("authority", {})
    if any(execution.get(key) is not False for key in ("provider_reads_authorized", "r2_writes_authorized", "automatic_model_promotion_authorized", "live_trading_authorized")):
        raise ValueError("shadow config crosses an execution or trading authority boundary")
    training = config.get("training", {})
    if tuple(training.get("groups", {})) != tuple(FEATURE_GROUPS):
        raise ValueError("shadow feature groups are not the canonical ordered set")


def run_shadow_ablation(
    rows: Sequence[dict[str, Any]],
    *,
    config: dict[str, Any],
    data_sha256: str,
    config_sha256: str,
    end_exclusive_ms: int,
) -> dict[str, Any]:
    """Run bounded, deterministic, research-only feature-group comparisons."""

    _validate_config(config)
    training = config["training"]
    groups = {name: tuple(values) for name, values in training["groups"].items()}
    examples = build_shadow_examples(
        rows,
        end_exclusive_ms=end_exclusive_ms,
        warmup_bars=int(training["warmup_bars"]),
        groups=groups,
    )
    results: dict[str, Any] = {}
    for group, items in examples.items():
        by_class: dict[str, list[ShadowExample]] = defaultdict(list)
        for item in items:
            by_class[item.asset_class].append(item)
        class_results: dict[str, Any] = {}
        for asset_class, class_items in sorted(by_class.items()):
            split = int(len(class_items) * float(training["train_fraction"]))
            train = class_items[:split]
            test = class_items[split:]
            minimum = int(training["minimum_samples_per_split"])
            if len(train) < minimum or len(test) < minimum:
                class_results[asset_class] = {
                    "status": "NOT_READY",
                    "reason": "MINIMUM_SPLIT_SAMPLES_NOT_MET",
                    "train_samples": len(train),
                    "test_samples": len(test),
                }
                continue
            model = _fit(
                train,
                epochs=int(training["epochs"]),
                learning_rate=float(training["learning_rate"]),
                l2=float(training["l2"]),
            )
            class_results[asset_class] = {
                "status": "PASS",
                "train": _metrics(train, model, bins=int(training["calibration_bins"])),
                "test": _metrics(test, model, bins=int(training["calibration_bins"])),
                "regimes": _regime_metrics(test, model, minimum_samples=int(training["regime_minimum_samples"])),
            }
        results[group] = {
            "feature_names": list(groups[group]),
            "examples": len(items),
            "classes": class_results,
        }

    registry_entry = build_experiment_registry_entry(
        comparison_key="binance_spot/1d/next_complete_daily_close_up",
        dataset_sha256=data_sha256,
        config_sha256=config_sha256,
        trainer={"name": "shadow_logistic_regression", "version": "v0.6.0"},
        environment={"python": platform.python_version(), "feature_engine": "advanced_technical_v0.2"},
        evaluation={
            "groups": {name: list(values) for name, values in groups.items()},
            "end_exclusive_ms": end_exclusive_ms,
            "train_fraction": training["train_fraction"],
        },
    )
    return {
        "schema": "binance-spot-shadow-ablation-v0.6",
        "status": "PASS",
        "mode": "RESEARCH_SHADOW_ONLY",
        "generated_at_utc": str(config.get("generated_at_utc", "")),
        "provider": "binance_spot",
        "data_sha256": data_sha256,
        "config_sha256": config_sha256,
        "experiment_id": registry_entry["experiment_id"],
        "experiment_registry": registry_entry,
        "groups": results,
        "calibration": {"method": "equal_width_10_bins", "interpretation": "DESCRIPTIVE_ONLY"},
        "bounded_search": {
            "max_groups": len(groups),
            "max_retries": 0,
            "automatic_promotion": False,
        },
        "authority": {
            "provider_reads_authorized": False,
            "r2_writes_authorized": False,
            "holdout_accessed": False,
            "automatic_model_promotion_authorized": False,
            "automatic_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }
