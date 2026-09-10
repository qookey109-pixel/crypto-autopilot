"""Promotion evidence V0.2 with preregistration and multiplicity control.

The evaluator extends V0.1 quantitative gates.  It validates externally
computed time-series block-bootstrap evidence and applies Holm-Bonferroni to a
locked challenger family.  Passing still means human review only.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from .challenger_promotion_v0_1 import (
    ChallengerPromotionEvidenceError,
    evaluate_challenger_promotion,
)


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ChallengerPromotionEvidenceError(f"{name} must be an object")
    return value


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ChallengerPromotionEvidenceError(f"{name} must be an array")
    return value


def _finite(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ChallengerPromotionEvidenceError(f"{name} must be numeric") from exc
    if not math.isfinite(result):
        raise ChallengerPromotionEvidenceError(f"{name} must be finite")
    return result


def _integer(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise ChallengerPromotionEvidenceError(f"{name} must be an integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ChallengerPromotionEvidenceError(f"{name} must be an integer") from exc
    if result < 0 or result != _finite(value, name):
        raise ChallengerPromotionEvidenceError(f"{name} must be a non-negative integer")
    return result


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ChallengerPromotionEvidenceError(f"{name} must be a non-empty string")
    return value.strip()


def _holm_bonferroni(
    p_values: Mapping[str, float],
    *,
    alpha: float,
) -> tuple[set[str], dict[str, float]]:
    ordered = sorted(p_values.items(), key=lambda item: (item[1], item[0]))
    count = len(ordered)
    rejected: set[str] = set()
    adjusted: dict[str, float] = {}
    running_adjusted = 0.0
    stepdown_open = True
    for rank, (challenger_id, p_value) in enumerate(ordered):
        remaining = count - rank
        running_adjusted = max(running_adjusted, min(1.0, p_value * remaining))
        adjusted[challenger_id] = running_adjusted
        if stepdown_open and p_value <= alpha / remaining:
            rejected.add(challenger_id)
        else:
            stepdown_open = False
    return rejected, adjusted


def evaluate_challenger_promotion_v0_2(
    *,
    track: str,
    evidence: Mapping[str, Any],
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply V0.1 gates plus locked-family statistical evidence gates."""

    base = evaluate_challenger_promotion(
        track=track,
        evidence=evidence,
        protocol=protocol,
    )
    failures = list(base["failures"])
    common = _mapping(protocol.get("common_integrity_gates"), "common_integrity_gates")
    track_rules = _mapping(_mapping(protocol.get("tracks"), "tracks")[track], f"tracks.{track}")
    integrity = _mapping(evidence.get("integrity"), "evidence.integrity")
    for name in ("experiment_preregistered", "family_registry_locked", "primary_metric_frozen"):
        if integrity.get(name) is not common.get(name):
            failures.append(f"INTEGRITY_{name.upper()}_FAILED")

    calendar_days = _integer(
        evidence.get("out_of_sample_calendar_days"), "out_of_sample_calendar_days"
    )
    if calendar_days < _integer(
        common["minimum_out_of_sample_calendar_days"],
        "minimum_out_of_sample_calendar_days",
    ):
        failures.append("OUT_OF_SAMPLE_CALENDAR_DAYS_BELOW_GATE")
    prospective_days = _integer(
        evidence.get("prospective_paper_days"), "prospective_paper_days"
    )
    if prospective_days < _integer(
        common["minimum_prospective_paper_days"], "minimum_prospective_paper_days"
    ):
        failures.append("PROSPECTIVE_PAPER_DAYS_BELOW_GATE")

    statistical = _mapping(protocol.get("statistical_evidence"), "statistical_evidence")
    primary_metric = _nonempty(evidence.get("primary_metric"), "primary_metric")
    if primary_metric != statistical["primary_metric"]:
        failures.append("PRIMARY_METRIC_MISMATCH")
    bootstrap = _mapping(evidence.get("block_bootstrap"), "block_bootstrap")
    if bootstrap.get("method") != statistical["bootstrap_method"]:
        failures.append("BLOCK_BOOTSTRAP_METHOD_MISMATCH")
    confidence_level = _finite(
        bootstrap.get("confidence_level"), "block_bootstrap.confidence_level"
    )
    if not math.isclose(
        confidence_level,
        _finite(statistical["confidence_level"], "statistical confidence_level"),
        abs_tol=1e-12,
    ):
        failures.append("BLOCK_BOOTSTRAP_CONFIDENCE_LEVEL_MISMATCH")
    replicates = _integer(bootstrap.get("replicates"), "block_bootstrap.replicates")
    if replicates < _integer(
        statistical["minimum_bootstrap_replicates"], "minimum_bootstrap_replicates"
    ):
        failures.append("BLOCK_BOOTSTRAP_REPLICATES_BELOW_GATE")
    if bootstrap.get("serial_dependence_preserved") is not bool(
        statistical["serial_dependence_must_be_preserved"]
    ):
        failures.append("BLOCK_BOOTSTRAP_SERIAL_DEPENDENCE_NOT_PRESERVED")
    lower_bound = _finite(
        bootstrap.get("primary_metric_lower_confidence_bound_r"),
        "block_bootstrap.primary_metric_lower_confidence_bound_r",
    )
    minimum_lower_bound = _finite(
        statistical["minimum_primary_metric_lower_confidence_bound_r"],
        "minimum_primary_metric_lower_confidence_bound_r",
    )
    if lower_bound <= minimum_lower_bound:
        failures.append("PRIMARY_METRIC_LOWER_CONFIDENCE_BOUND_BELOW_GATE")
    raw_p_value = _finite(bootstrap.get("p_value"), "block_bootstrap.p_value")
    if not 0 <= raw_p_value <= 1:
        raise ChallengerPromotionEvidenceError("block_bootstrap.p_value must be in [0, 1]")

    multiple = _mapping(
        protocol.get("multiple_comparison_control"), "multiple_comparison_control"
    )
    family = _mapping(evidence.get("experiment_family"), "experiment_family")
    family_id = _nonempty(family.get("family_id"), "experiment_family.family_id")
    registry_sha256 = _nonempty(
        family.get("registry_sha256"), "experiment_family.registry_sha256"
    )
    if multiple.get("registry_sha256_required") is True and (
        len(registry_sha256) != 64
        or any(character not in "0123456789abcdef" for character in registry_sha256.lower())
    ):
        failures.append("FAMILY_REGISTRY_SHA256_INVALID")
    if registry_sha256 != multiple.get("approved_registry_sha256"):
        failures.append("FAMILY_REGISTRY_SHA256_NOT_APPROVED")
    challenger_id = _nonempty(
        family.get("challenger_id"), "experiment_family.challenger_id"
    )
    registered_raw = _sequence(
        family.get("registered_challenger_ids"),
        "experiment_family.registered_challenger_ids",
    )
    registered = [
        _nonempty(value, "registered_challenger_ids item") for value in registered_raw
    ]
    if len(registered) != len(set(registered)):
        raise ChallengerPromotionEvidenceError("registered challenger ids must be unique")
    if challenger_id not in registered:
        failures.append("CHALLENGER_NOT_IN_LOCKED_FAMILY")
    if family_id != track_rules.get("experiment_family_id"):
        failures.append("EXPERIMENT_FAMILY_TRACK_MISMATCH")
    approved_families = _mapping(
        multiple.get("approved_families"), "approved_families"
    )
    approved_registered = approved_families.get(family_id)
    if not isinstance(approved_registered, list) or registered != approved_registered:
        failures.append("REGISTERED_FAMILY_DOES_NOT_MATCH_APPROVED_REGISTRY")
    if len(registered) > _integer(
        multiple["maximum_registered_challengers_per_family"],
        "maximum_registered_challengers_per_family",
    ):
        failures.append("REGISTERED_CHALLENGER_COUNT_ABOVE_GATE")
    look_index = _integer(family.get("evaluation_look_index"), "evaluation_look_index")
    if look_index < 1 or look_index > _integer(
        multiple["maximum_evaluation_looks"], "maximum_evaluation_looks"
    ):
        failures.append("EVALUATION_LOOK_OUTSIDE_GATE")

    p_values_raw = _mapping(family.get("p_values"), "experiment_family.p_values")
    if set(p_values_raw) != set(registered):
        failures.append("FAMILY_P_VALUES_INCOMPLETE")
    p_values: dict[str, float] = {}
    for identifier, value in p_values_raw.items():
        numeric = _finite(value, f"p_values.{identifier}")
        if not 0 <= numeric <= 1:
            raise ChallengerPromotionEvidenceError("family p-values must be in [0, 1]")
        p_values[str(identifier)] = numeric
    if challenger_id in p_values and not math.isclose(
        p_values[challenger_id], raw_p_value, abs_tol=1e-12
    ):
        failures.append("CHALLENGER_P_VALUE_MISMATCH")
    if multiple["method"] != "HOLM_BONFERRONI":
        raise ChallengerPromotionEvidenceError("unsupported multiple-comparison method")
    rejected, adjusted = _holm_bonferroni(
        p_values,
        alpha=_finite(multiple["family_wise_alpha"], "family_wise_alpha"),
    )
    if challenger_id not in rejected:
        failures.append("HOLM_BONFERRONI_GATE_FAILED")

    if track_rules.get("sstate_gate_calibration_required") is True:
        calibration = _mapping(
            evidence.get("sstate_gate_calibration"), "sstate_gate_calibration"
        )
        if calibration.get("ready") is not True:
            failures.append("SSTATE_GATE_CALIBRATION_NOT_READY")
        if calibration.get("holm_adjusted_pass") is not True:
            failures.append("SSTATE_GATE_MULTIPLE_COMPARISON_FAILED")
        if calibration.get("holdout_untouched") is not True:
            failures.append("SSTATE_CALIBRATION_HOLDOUT_BOUNDARY_FAILED")
        if _integer(
            calibration.get("selected_effective_samples"),
            "sstate_gate_calibration.selected_effective_samples",
        ) < _integer(
            track_rules["minimum_sstate_selected_effective_samples"],
            "minimum_sstate_selected_effective_samples",
        ):
            failures.append("SSTATE_EFFECTIVE_SAMPLES_BELOW_GATE")
        if _integer(
            calibration.get("outer_fold_count"),
            "sstate_gate_calibration.outer_fold_count",
        ) < _integer(
            track_rules["minimum_sstate_outer_folds"],
            "minimum_sstate_outer_folds",
        ):
            failures.append("SSTATE_OUTER_FOLDS_BELOW_GATE")
        if _finite(
            calibration.get("wilson_lower_bound"),
            "sstate_gate_calibration.wilson_lower_bound",
        ) < _finite(
            track_rules["minimum_sstate_wilson_lower_bound"],
            "minimum_sstate_wilson_lower_bound",
        ):
            failures.append("SSTATE_WILSON_LOWER_BOUND_BELOW_GATE")
    if track == "CORE_LONG_SHORT":
        short_calibration = _mapping(
            evidence.get("short_score_calibration"), "short_score_calibration"
        )
        if track_rules.get("short_score_independently_calibrated_required") is True:
            if short_calibration.get("ready") is not True or short_calibration.get(
                "independent_from_formal_long_weights"
            ) is not True:
                failures.append("SHORT_SCORE_NOT_INDEPENDENTLY_CALIBRATED")
        if _integer(
            short_calibration.get("out_of_sample_trades"),
            "short_score_calibration.out_of_sample_trades",
        ) < _integer(
            track_rules["minimum_short_calibration_trades"],
            "minimum_short_calibration_trades",
        ):
            failures.append("SHORT_CALIBRATION_TRADES_BELOW_GATE")
        if (
            track_rules.get("short_funding_stress_pass_required") is True
            and short_calibration.get("funding_stress_pass") is not True
        ):
            failures.append("SHORT_FUNDING_STRESS_FAILED")
        if (
            track_rules.get("short_squeeze_regime_evaluated_required") is True
            and short_calibration.get("squeeze_regime_evaluated") is not True
        ):
            failures.append("SHORT_SQUEEZE_REGIME_NOT_EVALUATED")

    failures = sorted(set(failures))
    semantics = _mapping(protocol.get("result_semantics"), "result_semantics")
    base["schema"] = "challenger-promotion-evaluation-v0.2"
    base["status"] = semantics["failing_status"] if failures else semantics["passing_status"]
    base["failures"] = failures
    base["metrics"].update(
        {
            "out_of_sample_calendar_days": calendar_days,
            "prospective_paper_days": prospective_days,
            "primary_metric_lower_confidence_bound_r": lower_bound,
            "bootstrap_replicates": replicates,
            "bootstrap_confidence_level": confidence_level,
            "raw_p_value": raw_p_value,
            "holm_adjusted_p_value": adjusted.get(challenger_id),
            "experiment_family_id": family_id,
            "experiment_registry_sha256": registry_sha256,
            "registered_challenger_count": len(registered),
            "evaluation_look_index": look_index,
        }
    )
    base["interpretation"] = (
        "Passing V0.2 means preregistered, multiplicity-adjusted evidence is ready "
        "for human review only; it is not a strategy promotion or trading authority."
    )
    return base
