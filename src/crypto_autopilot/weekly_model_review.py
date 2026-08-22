from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

from .lineage import sha256_json
from .online_training import (
    Example,
    bound_daily_direction_examples,
    build_daily_direction_examples,
    daily_direction_metrics,
    fit_daily_direction_examples,
    predict_daily_direction_probability,
    require_daily_direction_feature_contract,
)


def _drawdown(returns: list[float], initial_equity: float) -> tuple[float, float]:
    equity = initial_equity
    peak = equity
    maximum = 0.0
    for value in returns:
        equity *= max(0.0, 1.0 + value)
        peak = max(peak, equity)
        if peak > 0:
            maximum = max(maximum, (peak - equity) / peak)
    return round(equity, 8), round(maximum * 100.0, 8)


def _cost_scenarios(
    predictions: list[dict[str, Any]], *, review_config: dict[str, Any]
) -> list[dict[str, Any]]:
    threshold = float(review_config["long_probability_threshold"])
    selected = [item for item in predictions if float(item["probability"]) >= threshold]
    output = []
    for scenario in review_config["cost_scenarios"]:
        fee = float(scenario["taker_fee_bps_each_side"])
        slippage = float(scenario["slippage_bps_each_fill"])
        round_trip_cost = 2.0 * (fee + slippage) / 10_000.0
        by_day: dict[int, list[float]] = defaultdict(list)
        for item in selected:
            by_day[int(item["time_ms"])].append(
                float(item["forward_return"]) - round_trip_cost
            )
        daily_returns = [
            sum(values) / len(values) for _, values in sorted(by_day.items()) if values
        ]
        final_equity, max_drawdown_pct = _drawdown(
            daily_returns,
            float(review_config["diagnostic_initial_equity_usd"]),
        )
        output.append(
            {
                "name": str(scenario["name"]),
                "taker_fee_bps_each_side": fee,
                "slippage_bps_each_fill": slippage,
                "signal_count": len(selected),
                "active_days": len(daily_returns),
                "mean_net_signal_return": (
                    round(
                        sum(
                            float(item["forward_return"]) - round_trip_cost
                            for item in selected
                        )
                        / len(selected),
                        12,
                    )
                    if selected
                    else 0.0
                ),
                "diagnostic_final_equity_usd": final_equity,
                "diagnostic_net_growth_pct": round(
                    (final_equity / float(review_config["diagnostic_initial_equity_usd"]) - 1.0)
                    * 100.0,
                    8,
                ),
                "diagnostic_max_drawdown_pct": max_drawdown_pct,
            }
        )
    return output


def _constant_probability_metrics(
    items: list[Example], probability: float
) -> dict[str, float | int]:
    probability = max(1e-9, min(1.0 - 1e-9, probability))
    positives = sum(item.label for item in items)
    log_loss = sum(
        -item.label * math.log(probability)
        - (1 - item.label) * math.log(1.0 - probability)
        for item in items
    )
    brier = sum((probability - item.label) ** 2 for item in items)
    predicted_positive = probability >= 0.5
    correct = sum(int(predicted_positive == bool(item.label)) for item in items)
    count = len(items)
    return {
        "samples": count,
        "train_positive_rate_probability": probability,
        "positive_rate": positives / count,
        "accuracy": correct / count,
        "log_loss": log_loss / count,
        "brier_score": brier / count,
    }


def _partition_integrity(
    train: list[Example], validation: list[Example]
) -> dict[str, Any]:
    train_keys = [(item.symbol, item.time_ms) for item in train]
    validation_keys = [(item.symbol, item.time_ms) for item in validation]
    train_set = set(train_keys)
    validation_set = set(validation_keys)
    overlap = train_set & validation_set
    chronological = bool(train and validation) and max(item.time_ms for item in train) < min(
        item.time_ms for item in validation
    )
    failures = []
    if len(train_keys) != len(train_set):
        failures.append("DUPLICATE_TRAIN_RECORD_KEYS")
    if len(validation_keys) != len(validation_set):
        failures.append("DUPLICATE_VALIDATION_RECORD_KEYS")
    if overlap:
        failures.append("TRAIN_VALIDATION_RECORD_OVERLAP")
    if not chronological:
        failures.append("TRAIN_VALIDATION_NOT_STRICTLY_CHRONOLOGICAL")
    return {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "train_record_count": len(train_keys),
        "validation_record_count": len(validation_keys),
        "record_overlap_count": len(overlap),
        "strictly_chronological": chronological,
        "train_records_sha256": sha256_json(sorted(train_set)),
        "validation_records_sha256": sha256_json(sorted(validation_set)),
        "provider_source_overlap_expected": True,
        "holdout_status": "FROZEN_UNOPENED_NOT_ACCESSED",
        "holdout_accessed": False,
    }


def _baseline_comparison(
    train: list[Example],
    validation: list[Example],
    candidate: dict[str, float | int],
    *,
    required_metrics: tuple[str, ...],
) -> dict[str, Any]:
    train_positive_rate = sum(item.label for item in train) / len(train)
    baseline = _constant_probability_metrics(validation, train_positive_rate)
    supported = {"accuracy", "log_loss", "brier_score"}
    if not required_metrics or any(metric not in supported for metric in required_metrics):
        raise ValueError("unsupported or empty baseline quality-gate metric set")
    improvements = {
        "accuracy": float(candidate["accuracy"]) - float(baseline["accuracy"]),
        "log_loss": float(baseline["log_loss"]) - float(candidate["log_loss"]),
        "brier_score": float(baseline["brier_score"])
        - float(candidate["brier_score"]),
    }
    passed = all(improvements[metric] > 0.0 for metric in required_metrics)
    baseline_brier = float(baseline["brier_score"])
    return {
        "status": "PASS" if passed else "REJECT",
        "baseline": "train_prevalence_constant_probability",
        "required_positive_improvements": list(required_metrics),
        "candidate_metrics": candidate,
        "baseline_metrics": baseline,
        "improvements": improvements,
        "brier_skill_score": (
            1.0 - float(candidate["brier_score"]) / baseline_brier
            if baseline_brier > 0.0
            else 0.0
        ),
    }


def _model_quality_gate(
    *,
    pipeline_status: str,
    class_results: dict[str, Any],
    cost_scenarios: list[dict[str, Any]],
    exposure: dict[str, Any],
    review_config: dict[str, Any],
) -> dict[str, Any]:
    policy = dict(review_config["quality_gate"])
    failures: list[str] = []
    if pipeline_status != "PASS":
        return {
            "status": "NOT_READY",
            "failures": ["CRYPTO_WALK_FORWARD_NOT_READY"],
            "policy": policy,
            "promotion_eligible": False,
        }
    baseline_rejected_classes = sorted(
        asset_class
        for asset_class, result in class_results.items()
        if result.get("status") == "PASS"
        and result.get("baseline_quality_status") != "PASS"
    )
    if baseline_rejected_classes:
        failures.append("READY_CLASSES_DID_NOT_BEAT_NAIVE_BASELINE_IN_EVERY_FOLD")
    integrity_failed_classes = sorted(
        asset_class
        for asset_class, result in class_results.items()
        if result.get("status") == "FAIL"
    )
    if integrity_failed_classes:
        failures.append("CLASS_PARTITION_INTEGRITY_FAILED")

    scenario_name = str(policy["cost_scenario_name"])
    scenario = next((item for item in cost_scenarios if item["name"] == scenario_name), None)
    if scenario is None:
        failures.append("CONFIGURED_COST_SCENARIO_MISSING")
    else:
        if int(scenario["signal_count"]) <= 0:
            failures.append("NO_OUT_OF_FOLD_LONG_SIGNALS")
        if float(scenario["diagnostic_net_growth_pct"]) <= float(
            policy["minimum_net_growth_pct"]
        ):
            failures.append("NET_GROWTH_BELOW_POLICY")
        if float(scenario["diagnostic_max_drawdown_pct"]) > float(
            policy["maximum_diagnostic_drawdown_pct"]
        ):
            failures.append("DRAWDOWN_ABOVE_POLICY")
    if float(exposure["maximum_symbol_signal_share"]) > float(
        policy["maximum_symbol_signal_share"]
    ):
        failures.append("SYMBOL_SIGNAL_CONCENTRATION_ABOVE_POLICY")
    return {
        "status": "PASS" if not failures else "REJECT",
        "failures": failures,
        "baseline_rejected_asset_classes": baseline_rejected_classes,
        "integrity_failed_asset_classes": integrity_failed_classes,
        "policy": policy,
        "evaluated_cost_scenario": scenario,
        "promotion_eligible": False,
        "interpretation": (
            "Research evidence gate only. PASS does not authorize model promotion, "
            "backtest admission or trading."
        ),
    }


def build_weekly_model_review(
    rows: list[dict[str, Any]],
    *,
    training_config: dict[str, Any],
    review_config: dict[str, Any],
    data_sha256: str,
    end_exclusive_ms: int,
    generated_at_utc: str,
) -> dict[str, Any]:
    examples = build_daily_direction_examples(rows, end_exclusive_ms=end_exclusive_ms)
    schema_version = str(review_config.get("schema_version", "v0.5"))
    if schema_version != "v0.5":
        raise ValueError("weekly model review requires the V0.5 evidence contract")
    feature_names = list(require_daily_direction_feature_contract(training_config))
    fold_fractions = [float(value) for value in review_config["walk_forward_train_fractions"]]
    baseline_required_metrics = tuple(
        str(value)
        for value in review_config["quality_gate"]["required_baseline_improvements"]
    )
    predictions: list[dict[str, Any]] = []
    class_results: dict[str, Any] = {}

    for asset_class in training_config["asset_classes"]:
        items = sorted(
            examples.get(str(asset_class), []),
            key=lambda item: (item.time_ms, item.symbol),
        )
        timestamps = sorted({item.time_ms for item in items})
        folds = []
        for fold_index, train_fraction in enumerate(fold_fractions):
            if not timestamps:
                break
            start_index = min(len(timestamps) - 1, int(len(timestamps) * train_fraction))
            end_fraction = (
                fold_fractions[fold_index + 1]
                if fold_index + 1 < len(fold_fractions)
                else 1.0
            )
            end_index = min(len(timestamps), max(start_index + 1, int(len(timestamps) * end_fraction)))
            start_time = timestamps[start_index]
            end_time = timestamps[end_index] if end_index < len(timestamps) else end_exclusive_ms
            train = bound_daily_direction_examples(
                [item for item in items if item.time_ms < start_time],
                int(training_config["max_train_samples_per_class"]),
            )
            validation = bound_daily_direction_examples(
                [item for item in items if start_time <= item.time_ms < end_time],
                int(training_config["max_test_samples_per_class"]),
            )
            if (
                len(train) < int(review_config["minimum_fold_train_samples"])
                or len(validation) < int(review_config["minimum_fold_validation_samples"])
            ):
                folds.append(
                    {
                        "status": "NOT_READY",
                        "train_samples": len(train),
                        "validation_samples": len(validation),
                    }
                )
                continue
            integrity = _partition_integrity(train, validation)
            if integrity["status"] != "PASS":
                folds.append(
                    {
                        "status": "INTEGRITY_FAIL",
                        "train_samples": len(train),
                        "validation_samples": len(validation),
                        "partition_integrity": integrity,
                    }
                )
                continue
            model = fit_daily_direction_examples(
                train,
                training_config=training_config,
                feature_names=feature_names,
            )
            metrics = daily_direction_metrics(validation, model)
            baseline_comparison = _baseline_comparison(
                train,
                validation,
                metrics,
                required_metrics=baseline_required_metrics,
            )
            for item in validation:
                predictions.append(
                    {
                        "asset_class": str(asset_class),
                        "symbol": item.symbol,
                        "time_ms": item.time_ms,
                        "probability": predict_daily_direction_probability(item, model),
                        "forward_return": item.forward_return,
                    }
                )
            folds.append(
                {
                    "status": "PASS",
                    "train_end_exclusive_ms": start_time,
                    "validation_end_exclusive_ms": end_time,
                    "train_samples": len(train),
                    "validation": metrics,
                    "partition_integrity": integrity,
                    "baseline_comparison": baseline_comparison,
                }
            )
        ready_folds = [item for item in folds if item.get("status") == "PASS"]
        baseline_quality_status = (
            "PASS"
            if len(ready_folds) == len(fold_fractions)
            and all(
                item["baseline_comparison"]["status"] == "PASS"
                for item in ready_folds
            )
            else "REJECT"
            if ready_folds
            else "NOT_READY"
        )
        class_results[str(asset_class)] = {
            "status": (
                "FAIL"
                if any(item.get("status") == "INTEGRITY_FAIL" for item in folds)
                else "PASS"
                if ready_folds
                else "NOT_READY"
            ),
            "baseline_quality_status": baseline_quality_status,
            "example_count": len(items),
            "folds": folds,
        }

    threshold = float(review_config["long_probability_threshold"])
    selected = [item for item in predictions if float(item["probability"]) >= threshold]
    symbol_counts = Counter(str(item["symbol"]) for item in selected)
    class_counts = Counter(str(item["asset_class"]) for item in selected)
    concurrent = Counter(int(item["time_ms"]) for item in selected)
    total = len(selected)
    exposure = {
        "signal_count": total,
        "maximum_concurrent_symbols": max(concurrent.values(), default=0),
        "maximum_symbol_signal_share": (
            round(max(symbol_counts.values(), default=0) / total, 12) if total else 0.0
        ),
        "symbol_signal_shares": {
            key: round(value / total, 12) for key, value in sorted(symbol_counts.items())
        }
        if total
        else {},
        "asset_class_signal_shares": {
            key: round(value / total, 12) for key, value in sorted(class_counts.items())
        }
        if total
        else {},
        "interpretation": "Signal concentration proxy only; not an executed portfolio position ledger.",
    }
    status = "PASS" if class_results.get("crypto", {}).get("status") == "PASS" else "NOT_READY"
    cost_scenarios = _cost_scenarios(predictions, review_config=review_config)
    quality_gate = _model_quality_gate(
        pipeline_status=status,
        class_results=class_results,
        cost_scenarios=cost_scenarios,
        exposure=exposure,
        review_config=review_config,
    )
    return {
        "schema": f"binance-spot-weekly-model-review-{schema_version}",
        "status": status,
        "status_semantics": "PIPELINE_EVIDENCE_COMPLETED_NOT_MODEL_APPROVAL",
        "mode": "RESEARCH_DIAGNOSTICS_ONLY",
        "provider": "binance_spot",
        "generated_at_utc": generated_at_utc,
        "data_sha256": data_sha256,
        "walk_forward": {
            "method": "expanding_train_non_overlapping_forward_validation",
            "classes": class_results,
        },
        "cost_and_drawdown_sensitivity": cost_scenarios,
        "asset_exposure": exposure,
        "model_quality_gate": quality_gate,
        "lineage": {
            "schema": f"binance-spot-weekly-training-lineage-{schema_version}",
            "provider": "binance_spot",
            "dataset_sha256": data_sha256,
            "feature_contract_sha256": sha256_json(feature_names),
            "training_config_sha256": sha256_json(training_config),
            "review_config_sha256": sha256_json(review_config),
            "holdout_status": "FROZEN_UNOPENED_NOT_ACCESSED",
            "holdout_accessed": False,
            "source_switch_authorized": False,
        },
        "authority": {
            "formal_backtest_admission_authorized": False,
            "automatic_model_promotion_authorized": False,
            "automatic_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
        "interpretation": (
            "Out-of-fold research diagnostics only; returns, drawdown and exposure are "
            "model-signal proxies and not a strategy profitability claim."
        ),
    }
