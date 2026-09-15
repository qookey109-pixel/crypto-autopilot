"""Fail-closed evidence gate for paper-strategy challenger graduation.

Passing this gate means only that a bounded evidence package is ready for
human review.  The module exposes no model-promotion, trade-plan or execution
capability.
"""

from __future__ import annotations

import math
from statistics import median
from typing import Any, Mapping, Sequence


class ChallengerPromotionEvidenceError(ValueError):
    """Raised when evidence is malformed instead of merely insufficient."""


def _finite(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ChallengerPromotionEvidenceError(f"{name} must be numeric") from exc
    if not math.isfinite(result):
        raise ChallengerPromotionEvidenceError(f"{name} must be finite")
    return result


def _count(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise ChallengerPromotionEvidenceError(f"{name} must be an integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ChallengerPromotionEvidenceError(f"{name} must be an integer") from exc
    if result < 0 or result != _finite(value, name):
        raise ChallengerPromotionEvidenceError(f"{name} must be a non-negative integer")
    return result


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ChallengerPromotionEvidenceError(f"{name} must be an object")
    return value


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ChallengerPromotionEvidenceError(f"{name} must be an array")
    return value


def evaluate_challenger_promotion(
    *,
    track: str,
    evidence: Mapping[str, Any],
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate frozen quantitative evidence without granting promotion.

    ``evidence`` is expected to be built from chronological out-of-sample
    folds.  Malformed evidence raises; valid but weak evidence returns REJECT.
    """

    tracks = _mapping(protocol.get("tracks"), "protocol.tracks")
    if track not in tracks:
        raise ChallengerPromotionEvidenceError(f"unknown promotion track: {track}")
    common = _mapping(protocol.get("common_integrity_gates"), "common_integrity_gates")
    track_rules = _mapping(tracks[track], f"tracks.{track}")
    failures: list[str] = []

    integrity = _mapping(evidence.get("integrity"), "evidence.integrity")
    for name in (
        "lineage_complete",
        "no_lookahead",
        "provider_separated",
        "holdout_untouched",
        "formal_baseline_unchanged",
    ):
        if integrity.get(name) is not common.get(name):
            failures.append(f"INTEGRITY_{name.upper()}_FAILED")

    folds = _sequence(evidence.get("walk_forward_folds"), "walk_forward_folds")
    minimum_folds = _count(common["minimum_walk_forward_folds"], "minimum_walk_forward_folds")
    if len(folds) < minimum_folds:
        failures.append("INSUFFICIENT_WALK_FORWARD_FOLDS")
    fold_expectancies: list[float] = []
    positive_folds = 0
    fold_trade_count = 0
    for index, raw_fold in enumerate(folds):
        fold = _mapping(raw_fold, f"walk_forward_folds[{index}]")
        if fold.get("ready") is not True:
            failures.append("WALK_FORWARD_FOLD_NOT_READY")
            continue
        expectancy = _finite(fold.get("net_expectancy_r"), "fold.net_expectancy_r")
        trades = _count(fold.get("out_of_sample_trades"), "fold.out_of_sample_trades")
        fold_expectancies.append(expectancy)
        fold_trade_count += trades
        positive_folds += int(expectancy > 0.0)

    positive_fraction = positive_folds / len(fold_expectancies) if fold_expectancies else 0.0
    if positive_fraction < _finite(
        common["minimum_positive_fold_fraction"], "minimum_positive_fold_fraction"
    ):
        failures.append("POSITIVE_FOLD_FRACTION_BELOW_GATE")

    total_trades = _count(evidence.get("total_out_of_sample_trades"), "total trades")
    minimum_total = _count(
        track_rules.get(
            "minimum_total_out_of_sample_trades",
            common["minimum_total_out_of_sample_trades"],
        ),
        "minimum_total_out_of_sample_trades",
    )
    if total_trades < minimum_total:
        failures.append("OUT_OF_SAMPLE_TRADES_BELOW_GATE")
    if fold_trade_count != total_trades:
        failures.append("WALK_FORWARD_TRADE_COUNT_MISMATCH")

    median_expectancy = median(fold_expectancies) if fold_expectancies else 0.0
    if median_expectancy < _finite(
        common["minimum_median_net_expectancy_r"], "minimum_median_net_expectancy_r"
    ):
        failures.append("MEDIAN_EXPECTANCY_BELOW_GATE")
    cost_stress = _finite(
        evidence.get("cost_stress_net_expectancy_r"), "cost_stress_net_expectancy_r"
    )
    if cost_stress < _finite(
        common["minimum_cost_stress_net_expectancy_r"],
        "minimum_cost_stress_net_expectancy_r",
    ):
        failures.append("COST_STRESS_EXPECTANCY_BELOW_GATE")

    maximum_drawdown = _finite(evidence.get("maximum_drawdown_pct"), "maximum_drawdown_pct")
    if maximum_drawdown < 0 or maximum_drawdown > _finite(
        common["maximum_drawdown_pct"], "protocol.maximum_drawdown_pct"
    ):
        failures.append("MAXIMUM_DRAWDOWN_ABOVE_GATE")
    concentration = _finite(
        evidence.get("maximum_single_symbol_fraction"), "maximum_single_symbol_fraction"
    )
    if not 0 <= concentration <= 1 or concentration > _finite(
        common["maximum_single_symbol_fraction"], "protocol.maximum_single_symbol_fraction"
    ):
        failures.append("SYMBOL_CONCENTRATION_ABOVE_GATE")
    leverage_rejections = _finite(
        evidence.get("leverage_rejection_fraction"), "leverage_rejection_fraction"
    )
    if not 0 <= leverage_rejections <= 1 or leverage_rejections > _finite(
        common["maximum_leverage_rejection_fraction"],
        "protocol.maximum_leverage_rejection_fraction",
    ):
        failures.append("LEVERAGE_REJECTION_FRACTION_ABOVE_GATE")

    baseline = _finite(evidence.get("baseline_expectancy_r"), "baseline_expectancy_r")
    challenger = _finite(evidence.get("challenger_expectancy_r"), "challenger_expectancy_r")
    expectancy_lift = challenger - baseline
    if expectancy_lift < _finite(
        common["minimum_expectancy_lift_vs_baseline_r"],
        "minimum_expectancy_lift_vs_baseline_r",
    ):
        failures.append("EXPECTANCY_LIFT_BELOW_GATE")

    if track == "CORE_LONG_SHORT":
        side_counts = _mapping(evidence.get("side_trade_counts"), "side_trade_counts")
        for side, minimum in _mapping(
            track_rules.get("minimum_side_trades"), "minimum_side_trades"
        ).items():
            if _count(side_counts.get(side, 0), f"side_trade_counts.{side}") < _count(
                minimum, f"minimum_side_trades.{side}"
            ):
                failures.append(f"{side}_TRADES_BELOW_GATE")
        regime_counts = _mapping(evidence.get("regime_trade_counts"), "regime_trade_counts")
        for regime, minimum in _mapping(
            track_rules.get("minimum_regime_trades"), "minimum_regime_trades"
        ).items():
            if _count(regime_counts.get(regime, 0), f"regime_trade_counts.{regime}") < _count(
                minimum, f"minimum_regime_trades.{regime}"
            ):
                failures.append(f"{regime}_TRADES_BELOW_GATE")
    else:
        distinct_symbols = _count(evidence.get("distinct_symbols"), "distinct_symbols")
        if distinct_symbols < _count(
            track_rules["minimum_distinct_symbols"], "minimum_distinct_symbols"
        ):
            failures.append("DISTINCT_TOKENIZED_SYMBOLS_BELOW_GATE")
        session_coverage = _finite(
            evidence.get("session_policy_coverage"), "session_policy_coverage"
        )
        if session_coverage < _finite(
            track_rules["minimum_session_policy_coverage"],
            "minimum_session_policy_coverage",
        ):
            failures.append("SESSION_POLICY_COVERAGE_BELOW_GATE")
        corporate_coverage = _finite(
            evidence.get("corporate_action_policy_coverage"),
            "corporate_action_policy_coverage",
        )
        if corporate_coverage < _finite(
            track_rules["minimum_corporate_action_policy_coverage"],
            "minimum_corporate_action_policy_coverage",
        ):
            failures.append("CORPORATE_ACTION_POLICY_COVERAGE_BELOW_GATE")
        if (
            track_rules.get("spread_stress_must_pass") is True
            and evidence.get("spread_stress_pass") is not True
        ):
            failures.append("SPREAD_STRESS_FAILED")

    failures = sorted(set(failures))
    semantics = _mapping(protocol.get("result_semantics"), "result_semantics")
    status = semantics["failing_status"] if failures else semantics["passing_status"]
    return {
        "schema": "challenger-promotion-evaluation-v0.1",
        "status": status,
        "track": track,
        "failures": failures,
        "metrics": {
            "walk_forward_fold_count": len(folds),
            "positive_fold_fraction": positive_fraction,
            "total_out_of_sample_trades": total_trades,
            "median_net_expectancy_r": median_expectancy,
            "cost_stress_net_expectancy_r": cost_stress,
            "maximum_drawdown_pct": maximum_drawdown,
            "maximum_single_symbol_fraction": concentration,
            "leverage_rejection_fraction": leverage_rejections,
            "expectancy_lift_vs_baseline_r": expectancy_lift,
        },
        "authority": {
            "human_review_required": True,
            "automatic_model_promotion_authorized": False,
            "formal_strategy_change_authorized": False,
            "automatic_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
        "interpretation": (
            "Passing means evidence is ready for human review only; it is not a "
            "strategy promotion or trading authorization."
        ),
    }
