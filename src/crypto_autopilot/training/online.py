from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any


DAY_MS = 86_400_000
DAILY_DIRECTION_FEATURE_NAMES = (
    "return_1d",
    "return_3d",
    "return_7d",
    "close_vs_ma7",
    "quote_volume_vs_ma7",
)


def require_daily_direction_feature_contract(
    training_config: dict[str, Any],
) -> tuple[str, ...]:
    """Fail closed if configured labels drift from the implemented feature order."""

    configured = tuple(str(value) for value in training_config.get("feature_names", ()))
    if configured != DAILY_DIRECTION_FEATURE_NAMES:
        raise ValueError(
            "daily-direction feature contract mismatch: expected exact ordered names "
            f"{list(DAILY_DIRECTION_FEATURE_NAMES)}, received {list(configured)}"
        )
    return configured


@dataclass(frozen=True, slots=True)
class Example:
    symbol: str
    time_ms: int
    features: tuple[float, ...]
    label: int
    forward_return: float


def _ratio(current: float, reference: float) -> float:
    if not math.isfinite(current) or not math.isfinite(reference) or reference <= 0:
        return 0.0
    return current / reference - 1.0


def build_daily_direction_examples(
    rows: list[dict[str, Any]], *, end_exclusive_ms: int
) -> dict[str, list[Example]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("audit_ok") is not True:
            continue
        timestamp = int(row["open_time_ms"])
        if timestamp >= end_exclusive_ms:
            continue
        grouped[str(row["symbol"])].append(row)

    result: dict[str, list[Example]] = defaultdict(list)
    for symbol, items in grouped.items():
        items.sort(key=lambda row: int(row["open_time_ms"]))
        asset_class = str(items[0]["asset_class"])
        for index in range(7, len(items) - 1):
            current = items[index]
            next_row = items[index + 1]
            if int(next_row["open_time_ms"]) - int(current["open_time_ms"]) != DAY_MS:
                continue
            closes = [float(items[offset]["close"]) for offset in range(index - 6, index + 1)]
            volumes = [
                float(items[offset]["quote_volume"]) for offset in range(index - 6, index + 1)
            ]
            close = closes[-1]
            features = (
                _ratio(close, float(items[index - 1]["close"])),
                _ratio(close, float(items[index - 3]["close"])),
                _ratio(close, float(items[index - 7]["close"])),
                _ratio(close, sum(closes) / len(closes)),
                _ratio(volumes[-1], sum(volumes) / len(volumes)),
            )
            if not all(math.isfinite(value) for value in features):
                continue
            result[asset_class].append(
                Example(
                    symbol=symbol,
                    time_ms=int(current["open_time_ms"]),
                    features=features,
                    label=int(float(next_row["close"]) > close),
                    forward_return=_ratio(float(next_row["close"]), close),
                )
            )
    return result


def bound_daily_direction_examples(items: list[Example], limit: int) -> list[Example]:
    ordered = sorted(items, key=lambda item: (item.time_ms, item.symbol))
    if len(ordered) <= limit:
        return ordered
    return [ordered[(index * len(ordered)) // limit] for index in range(limit)]


def _sigmoid(value: float) -> float:
    value = max(-30.0, min(30.0, value))
    return 1.0 / (1.0 + math.exp(-value))


def _normalization(items: list[Example]) -> tuple[list[float], list[float]]:
    width = len(items[0].features)
    means = [sum(item.features[index] for item in items) / len(items) for index in range(width)]
    standard_deviations = []
    for index, mean in enumerate(means):
        variance = sum((item.features[index] - mean) ** 2 for item in items) / len(items)
        standard_deviations.append(max(math.sqrt(variance), 1e-12))
    return means, standard_deviations


def _normalized(item: Example, means: list[float], stds: list[float]) -> tuple[float, ...]:
    return tuple(
        max(-8.0, min(8.0, (value - means[index]) / stds[index]))
        for index, value in enumerate(item.features)
    )


def _metrics(
    items: list[Example], weights: list[float], bias: float, means: list[float], stds: list[float]
) -> dict[str, float | int]:
    correct = 0
    log_loss = 0.0
    brier = 0.0
    positives = 0
    for item in items:
        features = _normalized(item, means, stds)
        probability = _sigmoid(bias + sum(weight * value for weight, value in zip(weights, features)))
        probability = max(1e-9, min(1.0 - 1e-9, probability))
        positives += item.label
        correct += int((probability >= 0.5) == bool(item.label))
        log_loss -= item.label * math.log(probability) + (1 - item.label) * math.log(1 - probability)
        brier += (probability - item.label) ** 2
    count = len(items)
    return {
        "samples": count,
        "positive_rate": positives / count,
        "accuracy": correct / count,
        "log_loss": log_loss / count,
        "brier_score": brier / count,
    }


def fit_daily_direction_examples(
    items: list[Example], *, training_config: dict[str, Any], feature_names: list[str]
) -> dict[str, Any]:
    if not items:
        raise ValueError("cannot fit a model without examples")
    configured_names = require_daily_direction_feature_contract(training_config)
    if tuple(feature_names) != configured_names:
        raise ValueError("feature_names must match the validated training feature contract")
    means, stds = _normalization(items)
    weights = [0.0] * len(feature_names)
    positive_rate = sum(item.label for item in items) / len(items)
    bias = math.log(max(1e-6, positive_rate) / max(1e-6, 1.0 - positive_rate))
    learning_rate = float(training_config["learning_rate"])
    l2 = float(training_config["l2"])
    epochs = int(training_config["epochs"])
    for epoch in range(epochs):
        gradients = [0.0] * len(weights)
        bias_gradient = 0.0
        for item in items:
            features = _normalized(item, means, stds)
            prediction = _sigmoid(
                bias + sum(weight * value for weight, value in zip(weights, features))
            )
            error = prediction - item.label
            bias_gradient += error
            for index, value in enumerate(features):
                gradients[index] += error * value
        rate = learning_rate / (1.0 + epoch * 0.25)
        bias -= rate * bias_gradient / len(items)
        for index in range(len(weights)):
            weights[index] -= rate * (
                gradients[index] / len(items) + l2 * weights[index]
            )
    return {
        "feature_names": feature_names,
        "feature_means": means,
        "feature_standard_deviations": stds,
        "weights": weights,
        "bias": bias,
    }


def predict_daily_direction_probability(item: Example, model: dict[str, Any]) -> float:
    features = _normalized(
        item,
        list(model["feature_means"]),
        list(model["feature_standard_deviations"]),
    )
    return _sigmoid(
        float(model["bias"])
        + sum(
            float(weight) * value
            for weight, value in zip(model["weights"], features)
        )
    )


def daily_direction_metrics(items: list[Example], model: dict[str, Any]) -> dict[str, float | int]:
    return _metrics(
        items,
        list(model["weights"]),
        float(model["bias"]),
        list(model["feature_means"]),
        list(model["feature_standard_deviations"]),
    )


def train_daily_direction_models(
    rows: list[dict[str, Any]],
    *,
    training_config: dict[str, Any],
    data_sha256: str,
    end_exclusive_ms: int,
    generated_at_utc: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    feature_names = list(require_daily_direction_feature_contract(training_config))
    output_schema_version = str(training_config.get("output_schema_version", "v0.3"))
    if output_schema_version not in {"v0.3", "v0.5"}:
        raise ValueError("unsupported daily-direction output schema version")
    examples = build_daily_direction_examples(rows, end_exclusive_ms=end_exclusive_ms)
    models: dict[str, Any] = {}
    class_metrics: dict[str, Any] = {}

    minimum_train = int(training_config["minimum_train_samples"])
    minimum_test = int(training_config["minimum_test_samples"])
    for asset_class in training_config["asset_classes"]:
        items = examples.get(str(asset_class), [])
        if not items:
            models[str(asset_class)] = {"status": "NOT_READY", "reason": "NO_EXAMPLES"}
            class_metrics[str(asset_class)] = {"status": "NOT_READY", "examples": 0}
            continue
        timestamps = sorted(item.time_ms for item in items)
        split_time_ms = timestamps[min(len(timestamps) - 1, int(len(timestamps) * 0.8))]
        train = bound_daily_direction_examples(
            [item for item in items if item.time_ms < split_time_ms],
            int(training_config["max_train_samples_per_class"]),
        )
        test = bound_daily_direction_examples(
            [item for item in items if item.time_ms >= split_time_ms],
            int(training_config["max_test_samples_per_class"]),
        )
        if len(train) < minimum_train or len(test) < minimum_test:
            reason = f"INSUFFICIENT_SAMPLES train={len(train)} test={len(test)}"
            models[str(asset_class)] = {"status": "NOT_READY", "reason": reason}
            class_metrics[str(asset_class)] = {
                "status": "NOT_READY",
                "examples": len(items),
                "train_samples": len(train),
                "test_samples": len(test),
            }
            continue

        fitted = fit_daily_direction_examples(
            train,
            training_config=training_config,
            feature_names=feature_names,
        )

        models[str(asset_class)] = {
            "status": "PASS",
            "split_time_ms": split_time_ms,
            **fitted,
        }
        class_metrics[str(asset_class)] = {
            "status": "PASS",
            "examples": len(items),
            "train": daily_direction_metrics(train, fitted),
            "test": daily_direction_metrics(test, fitted),
        }

    status = "PASS" if models.get("crypto", {}).get("status") == "PASS" else "NOT_READY"
    model = {
        "schema": f"binance-spot-daily-direction-model-{output_schema_version}",
        "status": status,
        "mode": "RESEARCH_TRAINING_ONLY",
        "generated_at_utc": generated_at_utc,
        "provider": "binance_spot",
        "data_sha256": data_sha256,
        "target": training_config["target"],
        "feature_contract": {
            "schema": "binance-spot-daily-direction-features-v0.3",
            "ordered_names": feature_names,
        },
        "models": models,
        "authority": {
            "source_switch_authorized": False,
            "holdout_accessed": False,
            "automatic_model_promotion_authorized": False,
            "automatic_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }
    model_canonical_sha256 = hashlib.sha256(
        (json.dumps(model, sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()
    metrics = {
        "schema": f"binance-spot-daily-direction-training-metrics-{output_schema_version}",
        "status": status,
        "mode": "RESEARCH_DIAGNOSTICS_ONLY",
        "generated_at_utc": generated_at_utc,
        "provider": "binance_spot",
        "data_sha256": data_sha256,
        "model_canonical_sha256": model_canonical_sha256,
        "classes": class_metrics,
        "interpretation": "Research diagnostics only; no strategy promotion or trading authority.",
        "authority": {
            "source_switch_authorized": False,
            "holdout_accessed": False,
            "automatic_model_promotion_authorized": False,
            "automatic_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }
    return model, metrics
