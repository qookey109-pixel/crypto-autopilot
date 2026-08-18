from __future__ import annotations

import hashlib
import itertools
import json
import math
import statistics
from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias


ParameterValue: TypeAlias = str | int | float | bool
MAX_SWEEP_CANDIDATES = 4096


class SweepPhase(str, Enum):
    UPDATE = "UPDATE"
    VALIDATION = "VALIDATION"


class PrimaryMetric(str, Enum):
    MEAN_R = "mean_r"
    RETURN_PCT = "return_pct"


class ValidationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class SweepProtocolError(RuntimeError):
    pass


def _value_key(value: ParameterValue) -> tuple[str, str]:
    if isinstance(value, bool):
        return ("bool", "true" if value else "false")
    if isinstance(value, int):
        return ("int", str(value))
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("parameter float values must be finite")
        return ("float", repr(value))
    if isinstance(value, str):
        if not value.strip():
            raise ValueError("parameter string values must be non-empty")
        return ("str", value)
    raise TypeError(f"unsupported parameter value type: {type(value)!r}")


def _canonical_value(value: ParameterValue) -> dict[str, object]:
    kind, encoded = _value_key(value)
    if kind == "bool":
        parsed: object = encoded == "true"
    elif kind == "int":
        parsed = int(encoded)
    elif kind == "float":
        parsed = float(encoded)
    else:
        parsed = encoded
    return {"type": kind, "value": parsed}


@dataclass(frozen=True, slots=True)
class ParameterAxis:
    name: str
    values: tuple[ParameterValue, ...]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("parameter axis name is required")
        if not self.values:
            raise ValueError(f"parameter axis {self.name} must contain at least one value")
        keys = tuple(_value_key(value) for value in self.values)
        if len(set(keys)) != len(keys):
            raise ValueError(f"parameter axis {self.name} contains duplicate values")


@dataclass(frozen=True, slots=True)
class SweepPolicy:
    primary_metric: PrimaryMetric
    min_update_trades_per_fold: int
    min_validation_trades: int
    min_update_primary_metric: float
    min_validation_primary_metric: float
    max_update_drawdown_pct: float
    max_validation_drawdown_pct: float
    min_stable_neighbors: int
    max_neighbor_primary_drop: float

    def __post_init__(self) -> None:
        if self.min_update_trades_per_fold < 1 or self.min_validation_trades < 1:
            raise ValueError("trade-count gates must be positive")
        numeric = (
            self.min_update_primary_metric,
            self.min_validation_primary_metric,
            self.max_update_drawdown_pct,
            self.max_validation_drawdown_pct,
            self.max_neighbor_primary_drop,
        )
        if not all(math.isfinite(value) for value in numeric):
            raise ValueError("sweep policy metrics must be finite")
        if self.max_update_drawdown_pct < 0 or self.max_validation_drawdown_pct < 0:
            raise ValueError("drawdown gates cannot be negative")
        if self.min_stable_neighbors < 0:
            raise ValueError("min_stable_neighbors cannot be negative")
        if self.max_neighbor_primary_drop < 0:
            raise ValueError("max_neighbor_primary_drop cannot be negative")


@dataclass(frozen=True, slots=True)
class SweepPlan:
    plan_id: str
    axes: tuple[ParameterAxis, ...]
    update_fold_ids: tuple[str, ...]
    validation_fold_id: str
    policy: SweepPolicy

    def __post_init__(self) -> None:
        if not self.plan_id.strip():
            raise ValueError("plan_id is required")
        if not self.axes:
            raise ValueError("at least one parameter axis is required")
        names = tuple(axis.name for axis in self.axes)
        if len(set(names)) != len(names):
            raise ValueError("parameter axis names must be unique")
        if not self.update_fold_ids or any(not fold.strip() for fold in self.update_fold_ids):
            raise ValueError("update_fold_ids must contain non-empty values")
        if len(set(self.update_fold_ids)) != len(self.update_fold_ids):
            raise ValueError("update_fold_ids must be unique")
        if not self.validation_fold_id.strip():
            raise ValueError("validation_fold_id is required")
        if self.validation_fold_id in self.update_fold_ids:
            raise ValueError("validation fold must be disjoint from update folds")
        candidate_count = math.prod(len(axis.values) for axis in self.axes)
        if candidate_count > MAX_SWEEP_CANDIDATES:
            raise ValueError(
                f"candidate grid too large: {candidate_count} > {MAX_SWEEP_CANDIDATES}"
            )


@dataclass(frozen=True, slots=True)
class ParameterCandidate:
    candidate_id: str
    values: tuple[tuple[str, ParameterValue], ...]


@dataclass(frozen=True, slots=True)
class SweepScore:
    trade_count: int
    mean_r: float
    return_pct: float
    max_drawdown_pct: float

    def __post_init__(self) -> None:
        if self.trade_count < 0:
            raise ValueError("trade_count cannot be negative")
        if not all(
            math.isfinite(value)
            for value in (self.mean_r, self.return_pct, self.max_drawdown_pct)
        ):
            raise ValueError("sweep scores must be finite")
        if self.max_drawdown_pct < 0:
            raise ValueError("max_drawdown_pct cannot be negative")


@dataclass(frozen=True, slots=True)
class SweepObservation:
    candidate_id: str
    fold_id: str
    phase: SweepPhase
    score: SweepScore
    evidence_ref: str

    def __post_init__(self) -> None:
        if not self.candidate_id.strip() or not self.fold_id.strip():
            raise ValueError("candidate_id and fold_id are required")
        if not self.evidence_ref.strip():
            raise ValueError("evidence_ref is required")


@dataclass(frozen=True, slots=True)
class UpdateCandidateSummary:
    candidate_id: str
    worst_primary_metric: float
    median_primary_metric: float
    worst_drawdown_pct: float
    eligible: bool


@dataclass(frozen=True, slots=True)
class UpdateSelection:
    plan_id: str
    plan_fingerprint: str
    selected_candidate_id: str
    selected_worst_primary_metric: float
    selected_median_primary_metric: float
    stable_neighbor_ids: tuple[str, ...]
    ranked_eligible_candidate_ids: tuple[str, ...]
    update_observation_digest: str


@dataclass(frozen=True, slots=True)
class ValidationDecision:
    status: ValidationStatus
    plan_id: str
    plan_fingerprint: str
    selected_candidate_id: str
    primary_metric_value: float
    trade_count: int
    max_drawdown_pct: float
    evidence_ref: str
    reasons: tuple[str, ...]
    validation_consumed: bool = True


@dataclass(frozen=True, slots=True)
class FrozenParameterSet:
    plan_id: str
    plan_fingerprint: str
    candidate_id: str
    values: tuple[tuple[str, ParameterValue], ...]
    update_observation_digest: str
    validation_fold_id: str
    validation_evidence_ref: str
    validation_primary_metric_value: float
    validation_trade_count: int
    validation_max_drawdown_pct: float


def build_candidate_grid(plan: SweepPlan) -> tuple[ParameterCandidate, ...]:
    candidates: list[ParameterCandidate] = []
    for index, combination in enumerate(
        itertools.product(*(axis.values for axis in plan.axes)),
        start=1,
    ):
        values = tuple((axis.name, value) for axis, value in zip(plan.axes, combination))
        candidates.append(ParameterCandidate(f"candidate-{index:04d}", values))
    return tuple(candidates)


def plan_fingerprint(plan: SweepPlan) -> str:
    payload = {
        "plan_id": plan.plan_id,
        "axes": [
            {
                "name": axis.name,
                "values": [_canonical_value(value) for value in axis.values],
            }
            for axis in plan.axes
        ],
        "update_fold_ids": list(plan.update_fold_ids),
        "validation_fold_id": plan.validation_fold_id,
        "policy": {
            "primary_metric": plan.policy.primary_metric.value,
            "min_update_trades_per_fold": plan.policy.min_update_trades_per_fold,
            "min_validation_trades": plan.policy.min_validation_trades,
            "min_update_primary_metric": plan.policy.min_update_primary_metric,
            "min_validation_primary_metric": plan.policy.min_validation_primary_metric,
            "max_update_drawdown_pct": plan.policy.max_update_drawdown_pct,
            "max_validation_drawdown_pct": plan.policy.max_validation_drawdown_pct,
            "min_stable_neighbors": plan.policy.min_stable_neighbors,
            "max_neighbor_primary_drop": plan.policy.max_neighbor_primary_drop,
        },
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _primary(score: SweepScore, metric: PrimaryMetric) -> float:
    if metric is PrimaryMetric.MEAN_R:
        return score.mean_r
    if metric is PrimaryMetric.RETURN_PCT:
        return score.return_pct
    raise AssertionError(f"unhandled primary metric: {metric}")


def _observation_digest(observations: tuple[SweepObservation, ...]) -> str:
    rows = []
    for item in sorted(
        observations,
        key=lambda value: (value.candidate_id, value.fold_id, value.evidence_ref),
    ):
        rows.append(
            {
                "candidate_id": item.candidate_id,
                "fold_id": item.fold_id,
                "phase": item.phase.value,
                "evidence_ref": item.evidence_ref,
                "score": {
                    "trade_count": item.score.trade_count,
                    "mean_r": item.score.mean_r,
                    "return_pct": item.score.return_pct,
                    "max_drawdown_pct": item.score.max_drawdown_pct,
                },
            }
        )
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _candidate_neighbors(
    plan: SweepPlan,
    candidate: ParameterCandidate,
) -> tuple[str, ...]:
    grid = build_candidate_grid(plan)
    by_keys = {
        tuple(_value_key(value) for _, value in item.values): item.candidate_id
        for item in grid
    }
    current_keys = tuple(_value_key(value) for _, value in candidate.values)
    neighbors: list[str] = []
    for axis_index, axis in enumerate(plan.axes):
        axis_keys = tuple(_value_key(value) for value in axis.values)
        position = axis_keys.index(current_keys[axis_index])
        for adjacent in (position - 1, position + 1):
            if adjacent < 0 or adjacent >= len(axis_keys):
                continue
            replaced = list(current_keys)
            replaced[axis_index] = axis_keys[adjacent]
            neighbor = by_keys.get(tuple(replaced))
            if neighbor is not None:
                neighbors.append(neighbor)
    return tuple(sorted(set(neighbors)))


def _summaries(
    plan: SweepPlan,
    observations: tuple[SweepObservation, ...],
) -> dict[str, UpdateCandidateSummary]:
    grid = build_candidate_grid(plan)
    candidate_ids = {candidate.candidate_id for candidate in grid}
    expected = {
        (candidate.candidate_id, fold_id)
        for candidate in grid
        for fold_id in plan.update_fold_ids
    }
    seen: dict[tuple[str, str], SweepObservation] = {}
    for observation in observations:
        if observation.phase is not SweepPhase.UPDATE:
            raise SweepProtocolError("update selection accepts UPDATE observations only")
        if observation.candidate_id not in candidate_ids:
            raise SweepProtocolError(f"unknown candidate: {observation.candidate_id}")
        if observation.fold_id not in plan.update_fold_ids:
            raise SweepProtocolError(f"unknown update fold: {observation.fold_id}")
        key = (observation.candidate_id, observation.fold_id)
        if key in seen:
            raise SweepProtocolError(f"duplicate update observation: {key}")
        seen[key] = observation
    missing = expected - set(seen)
    extra = set(seen) - expected
    if missing or extra:
        raise SweepProtocolError(
            f"update matrix must be complete; missing={len(missing)} extra={len(extra)}"
        )

    summaries: dict[str, UpdateCandidateSummary] = {}
    metric = plan.policy.primary_metric
    for candidate in grid:
        scores = [seen[(candidate.candidate_id, fold_id)].score for fold_id in plan.update_fold_ids]
        primary_values = [_primary(score, metric) for score in scores]
        eligible = all(
            score.trade_count >= plan.policy.min_update_trades_per_fold
            and _primary(score, metric) >= plan.policy.min_update_primary_metric
            and score.max_drawdown_pct <= plan.policy.max_update_drawdown_pct
            for score in scores
        )
        summaries[candidate.candidate_id] = UpdateCandidateSummary(
            candidate_id=candidate.candidate_id,
            worst_primary_metric=min(primary_values),
            median_primary_metric=float(statistics.median(primary_values)),
            worst_drawdown_pct=max(score.max_drawdown_pct for score in scores),
            eligible=eligible,
        )
    return summaries


def select_update_candidate(
    plan: SweepPlan,
    observations: list[SweepObservation] | tuple[SweepObservation, ...],
) -> UpdateSelection:
    """Select exactly one candidate using UPDATE evidence only.

    The full candidate/fold matrix is mandatory, preventing selective omission.
    Ranking is robust-first: worst-fold primary metric, then median metric, then
    lower worst drawdown, followed by deterministic candidate id.
    """

    source = tuple(observations)
    summaries = _summaries(plan, source)
    eligible = [summary for summary in summaries.values() if summary.eligible]
    if not eligible:
        raise SweepProtocolError("no update candidate passed the frozen update gates")
    ranked = sorted(
        eligible,
        key=lambda item: (
            -item.worst_primary_metric,
            -item.median_primary_metric,
            item.worst_drawdown_pct,
            item.candidate_id,
        ),
    )
    selected = ranked[0]
    candidate_by_id = {item.candidate_id: item for item in build_candidate_grid(plan)}
    selected_candidate = candidate_by_id[selected.candidate_id]
    stable_neighbors = []
    for neighbor_id in _candidate_neighbors(plan, selected_candidate):
        neighbor = summaries[neighbor_id]
        if not neighbor.eligible:
            continue
        if (
            neighbor.worst_primary_metric
            >= selected.worst_primary_metric - plan.policy.max_neighbor_primary_drop
        ):
            stable_neighbors.append(neighbor_id)
    if len(stable_neighbors) < plan.policy.min_stable_neighbors:
        raise SweepProtocolError(
            "selected update candidate is an isolated/unstable peak: "
            f"stable_neighbors={len(stable_neighbors)} "
            f"required={plan.policy.min_stable_neighbors}"
        )

    return UpdateSelection(
        plan_id=plan.plan_id,
        plan_fingerprint=plan_fingerprint(plan),
        selected_candidate_id=selected.candidate_id,
        selected_worst_primary_metric=selected.worst_primary_metric,
        selected_median_primary_metric=selected.median_primary_metric,
        stable_neighbor_ids=tuple(sorted(stable_neighbors)),
        ranked_eligible_candidate_ids=tuple(item.candidate_id for item in ranked),
        update_observation_digest=_observation_digest(source),
    )


def validate_selected_candidate(
    plan: SweepPlan,
    selection: UpdateSelection,
    observation: SweepObservation,
) -> ValidationDecision:
    """Consume validation for the already-selected candidate only.

    This function never ranks validation candidates and therefore cannot switch
    to a different candidate after seeing validation results.
    """

    fingerprint = plan_fingerprint(plan)
    if selection.plan_id != plan.plan_id or selection.plan_fingerprint != fingerprint:
        raise SweepProtocolError("selection does not match the frozen sweep plan")
    if observation.phase is not SweepPhase.VALIDATION:
        raise SweepProtocolError("validation requires a VALIDATION observation")
    if observation.fold_id != plan.validation_fold_id:
        raise SweepProtocolError("validation fold does not match the frozen plan")
    if observation.candidate_id != selection.selected_candidate_id:
        raise SweepProtocolError(
            "validation may evaluate only the UPDATE-selected candidate; reselection is forbidden"
        )

    score = observation.score
    primary_value = _primary(score, plan.policy.primary_metric)
    reasons: list[str] = []
    if score.trade_count < plan.policy.min_validation_trades:
        reasons.append("validation_trade_count_below_minimum")
    if primary_value < plan.policy.min_validation_primary_metric:
        reasons.append("validation_primary_metric_below_minimum")
    if score.max_drawdown_pct > plan.policy.max_validation_drawdown_pct:
        reasons.append("validation_drawdown_above_maximum")

    return ValidationDecision(
        status=ValidationStatus.PASS if not reasons else ValidationStatus.FAIL,
        plan_id=plan.plan_id,
        plan_fingerprint=fingerprint,
        selected_candidate_id=selection.selected_candidate_id,
        primary_metric_value=primary_value,
        trade_count=score.trade_count,
        max_drawdown_pct=score.max_drawdown_pct,
        evidence_ref=observation.evidence_ref,
        reasons=tuple(reasons) if reasons else ("frozen_validation_gates_pass",),
    )


def freeze_validated_parameters(
    plan: SweepPlan,
    selection: UpdateSelection,
    decision: ValidationDecision,
) -> FrozenParameterSet:
    if decision.status is not ValidationStatus.PASS:
        raise SweepProtocolError("failed validation cannot freeze parameters")
    fingerprint = plan_fingerprint(plan)
    if selection.plan_fingerprint != fingerprint or decision.plan_fingerprint != fingerprint:
        raise SweepProtocolError("plan fingerprint mismatch")
    if decision.selected_candidate_id != selection.selected_candidate_id:
        raise SweepProtocolError("validation candidate does not match update selection")
    candidate_by_id = {item.candidate_id: item for item in build_candidate_grid(plan)}
    candidate = candidate_by_id.get(selection.selected_candidate_id)
    if candidate is None:
        raise SweepProtocolError("selected candidate is not in the frozen grid")

    return FrozenParameterSet(
        plan_id=plan.plan_id,
        plan_fingerprint=fingerprint,
        candidate_id=candidate.candidate_id,
        values=candidate.values,
        update_observation_digest=selection.update_observation_digest,
        validation_fold_id=plan.validation_fold_id,
        validation_evidence_ref=decision.evidence_ref,
        validation_primary_metric_value=decision.primary_metric_value,
        validation_trade_count=decision.trade_count,
        validation_max_drawdown_pct=decision.max_drawdown_pct,
    )
