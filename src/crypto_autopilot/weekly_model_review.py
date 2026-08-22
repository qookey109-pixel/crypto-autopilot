from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .online_training import (
    bound_daily_direction_examples,
    build_daily_direction_examples,
    daily_direction_metrics,
    fit_daily_direction_examples,
    predict_daily_direction_probability,
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
                "diagnostic_max_drawdown_pct": max_drawdown_pct,
            }
        )
    return output


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
    feature_names = list(training_config["feature_names"])
    fold_fractions = [float(value) for value in review_config["walk_forward_train_fractions"]]
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
            model = fit_daily_direction_examples(
                train,
                training_config=training_config,
                feature_names=feature_names,
            )
            metrics = daily_direction_metrics(validation, model)
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
                }
            )
        class_results[str(asset_class)] = {
            "status": "PASS" if any(item.get("status") == "PASS" for item in folds) else "NOT_READY",
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
    return {
        "schema": "binance-spot-weekly-model-review-v0.4",
        "status": status,
        "mode": "RESEARCH_DIAGNOSTICS_ONLY",
        "provider": "binance_spot",
        "generated_at_utc": generated_at_utc,
        "data_sha256": data_sha256,
        "walk_forward": {
            "method": "expanding_train_non_overlapping_forward_validation",
            "classes": class_results,
        },
        "cost_and_drawdown_sensitivity": _cost_scenarios(
            predictions,
            review_config=review_config,
        ),
        "asset_exposure": exposure,
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
