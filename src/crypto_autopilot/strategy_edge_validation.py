from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import statistics
from dataclasses import dataclass
from enum import Enum
from statistics import NormalDist
from typing import Any, Sequence


class EdgeValidationError(ValueError):
    """Raised when evidence cannot satisfy the frozen validation contract."""


class EdgeVerdict(str, Enum):
    PASS = "PASS"
    REJECT = "REJECT"


@dataclass(frozen=True, slots=True)
class EdgeValidationPolicy:
    alpha: float = 0.05
    maximum_pbo: float = 0.20
    minimum_update_observations: int = 120
    minimum_validation_observations: int = 60
    minimum_trials: int = 5
    cscv_partitions: int = 8
    bootstrap_samples: int = 999
    stationary_bootstrap_mean_block_length: float = 10.0
    minimum_validation_sharpe: float = 0.0
    minimum_oos_sharpe_retention: float = 0.25
    permutation_samples: int = 999
    deterministic_seed: int = 20260828

    def __post_init__(self) -> None:
        if not 0 < self.alpha < 0.5:
            raise ValueError("alpha must be between zero and 0.5")
        if not 0 <= self.maximum_pbo <= 1:
            raise ValueError("maximum_pbo must be between zero and one")
        if self.minimum_update_observations < 8:
            raise ValueError("minimum_update_observations must be at least 8")
        if self.minimum_validation_observations < 8:
            raise ValueError("minimum_validation_observations must be at least 8")
        if self.minimum_trials < 2:
            raise ValueError("minimum_trials must be at least 2")
        if self.cscv_partitions < 4 or self.cscv_partitions % 2:
            raise ValueError("cscv_partitions must be even and at least 4")
        if self.bootstrap_samples < 99:
            raise ValueError("bootstrap_samples must be at least 99")
        if self.stationary_bootstrap_mean_block_length <= 1:
            raise ValueError("stationary bootstrap mean block length must exceed one")
        if self.minimum_oos_sharpe_retention < 0:
            raise ValueError("minimum_oos_sharpe_retention cannot be negative")
        if self.permutation_samples < 99:
            raise ValueError("permutation_samples must be at least 99")


@dataclass(frozen=True, slots=True)
class TrialRegistryEvidence:
    complete: bool
    experiment_ids: tuple[str, ...]
    registry_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.complete, bool):
            raise EdgeValidationError("trial registry completeness must be boolean")
        if not self.experiment_ids:
            raise EdgeValidationError("trial registry must contain experiments")
        if len(set(self.experiment_ids)) != len(self.experiment_ids):
            raise EdgeValidationError("trial registry experiment ids must be unique")
        if any(not item.strip() for item in self.experiment_ids):
            raise EdgeValidationError("trial registry experiment ids must be non-empty")
        _require_sha256(self.registry_sha256, "trial registry SHA-256")


@dataclass(frozen=True, slots=True)
class StrategyEdgeInput:
    provider: str
    selected_candidate_id: str
    candidate_ids: tuple[str, ...]
    update_returns_matrix: tuple[tuple[float, ...], ...]
    update_benchmark_returns: tuple[float, ...]
    validation_returns: tuple[float, ...]
    validation_benchmark_returns: tuple[float, ...]
    validation_market_returns: tuple[float, ...]
    validation_positions: tuple[float, ...]
    periods_per_year: int
    trial_registry: TrialRegistryEvidence
    partition_integrity_passed: bool
    evaluation_integrity_sha256: str
    holdout_accessed: bool = False
    provider_data_fetched: bool = False
    r2_accessed: bool = False
    trade_plan_authorized: bool = False
    live_trading_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise EdgeValidationError("provider is required")
        if not self.selected_candidate_id.strip():
            raise EdgeValidationError("selected_candidate_id is required")
        if not self.candidate_ids:
            raise EdgeValidationError("candidate_ids cannot be empty")
        if len(set(self.candidate_ids)) != len(self.candidate_ids):
            raise EdgeValidationError("candidate_ids must be unique")
        if self.selected_candidate_id not in self.candidate_ids:
            raise EdgeValidationError("selected candidate is absent from candidate_ids")
        if self.periods_per_year < 1:
            raise EdgeValidationError("periods_per_year must be positive")
        authority_flags = (
            self.holdout_accessed,
            self.provider_data_fetched,
            self.r2_accessed,
            self.trade_plan_authorized,
            self.live_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in authority_flags):
            raise EdgeValidationError("edge authority flags must be boolean")
        if self.partition_integrity_passed is not True:
            raise EdgeValidationError("disjoint partition-integrity evidence must pass")
        _require_sha256(self.evaluation_integrity_sha256, "evaluation integrity SHA-256")
        if any(authority_flags):
            raise EdgeValidationError("edge validation has zero data/trading authority")
        if not self.update_returns_matrix:
            raise EdgeValidationError("update return matrix cannot be empty")
        width = len(self.candidate_ids)
        if any(len(row) != width for row in self.update_returns_matrix):
            raise EdgeValidationError("update return matrix width does not match candidates")
        if len(self.update_benchmark_returns) != len(self.update_returns_matrix):
            raise EdgeValidationError("update benchmark is not aligned to the candidate matrix")
        validation_length = len(self.validation_returns)
        aligned_validation = (
            self.validation_benchmark_returns,
            self.validation_market_returns,
            self.validation_positions,
        )
        if any(len(values) != validation_length for values in aligned_validation):
            raise EdgeValidationError("validation returns, benchmark, market and positions must align")
        _finite_matrix(self.update_returns_matrix, "update_returns_matrix")
        for name, values in (
            ("update_benchmark_returns", self.update_benchmark_returns),
            ("validation_returns", self.validation_returns),
            ("validation_benchmark_returns", self.validation_benchmark_returns),
            ("validation_market_returns", self.validation_market_returns),
            ("validation_positions", self.validation_positions),
        ):
            _finite_series(values, name)
        if self.trial_registry.experiment_ids != self.candidate_ids:
            raise EdgeValidationError(
                "trial registry experiment order must exactly match candidate_ids"
            )


def _require_sha256(value: str, label: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise EdgeValidationError(f"{label} must be lowercase hexadecimal")


def _strict_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise EdgeValidationError(f"{label} must be a JSON boolean")
    return value


def _finite_series(values: Sequence[float], label: str) -> None:
    if not values:
        raise EdgeValidationError(f"{label} cannot be empty")
    if any(isinstance(value, bool) or not math.isfinite(float(value)) for value in values):
        raise EdgeValidationError(f"{label} must contain finite numeric values")


def _finite_matrix(matrix: Sequence[Sequence[float]], label: str) -> None:
    for index, row in enumerate(matrix):
        _finite_series(row, f"{label}[{index}]")


def _sample_standard_deviation(values: Sequence[float]) -> float:
    if len(values) < 2:
        raise EdgeValidationError("at least two observations are required")
    return float(statistics.stdev(values))


def _periodic_sharpe(values: Sequence[float]) -> float:
    deviation = _sample_standard_deviation(values)
    if deviation <= 0:
        raise EdgeValidationError("Sharpe ratio is undefined for zero-variance returns")
    return float(statistics.fmean(values) / deviation)


def _annualized_sharpe(values: Sequence[float], periods_per_year: int) -> float:
    return _periodic_sharpe(values) * math.sqrt(periods_per_year)


def _skewness(values: Sequence[float]) -> float:
    mean = statistics.fmean(values)
    second = statistics.fmean((value - mean) ** 2 for value in values)
    if second <= 0:
        raise EdgeValidationError("skewness is undefined for zero-variance returns")
    third = statistics.fmean((value - mean) ** 3 for value in values)
    return third / (second**1.5)


def _kurtosis(values: Sequence[float]) -> float:
    mean = statistics.fmean(values)
    second = statistics.fmean((value - mean) ** 2 for value in values)
    if second <= 0:
        raise EdgeValidationError("kurtosis is undefined for zero-variance returns")
    fourth = statistics.fmean((value - mean) ** 4 for value in values)
    return fourth / (second**2)


def _columns(matrix: Sequence[Sequence[float]]) -> tuple[tuple[float, ...], ...]:
    return tuple(tuple(row[index] for row in matrix) for index in range(len(matrix[0])))


def _excess(values: Sequence[float], benchmark: Sequence[float]) -> tuple[float, ...]:
    return tuple(float(value - baseline) for value, baseline in zip(values, benchmark))


def _stationary_indices(
    length: int,
    *,
    mean_block_length: float,
    rng: random.Random,
) -> tuple[int, ...]:
    restart_probability = 1.0 / mean_block_length
    current = rng.randrange(length)
    indices = [current]
    for _ in range(1, length):
        if rng.random() < restart_probability:
            current = rng.randrange(length)
        else:
            current = (current + 1) % length
        indices.append(current)
    return tuple(indices)


def stationary_bootstrap_mean_test(
    values: Sequence[float],
    *,
    samples: int,
    mean_block_length: float,
    seed: int,
) -> dict[str, Any]:
    _finite_series(values, "stationary bootstrap values")
    observed = float(statistics.fmean(values))
    centered = tuple(value - observed for value in values)
    rng = random.Random(seed)
    greater_or_equal = 0
    for _ in range(samples):
        indices = _stationary_indices(
            len(centered), mean_block_length=mean_block_length, rng=rng
        )
        boot_mean = statistics.fmean(centered[index] for index in indices)
        greater_or_equal += boot_mean >= observed
    p_value = (greater_or_equal + 1) / (samples + 1)
    return {
        "method": "stationary_bootstrap_one_sided_mean",
        "observed_mean_excess_return": observed,
        "p_value": p_value,
        "samples": samples,
        "mean_block_length": mean_block_length,
    }


def deflated_sharpe_test(
    selected_returns: Sequence[float],
    trial_returns: Sequence[Sequence[float]],
    *,
    periods_per_year: int,
) -> dict[str, Any]:
    selected_sharpe = _periodic_sharpe(selected_returns)
    trial_sharpes = tuple(_periodic_sharpe(values) for values in trial_returns)
    trial_count = len(trial_sharpes)
    if trial_count < 2:
        raise EdgeValidationError("deflated Sharpe requires at least two trials")
    trial_variance = statistics.variance(trial_sharpes)
    gamma = 0.5772156649015329
    normal = NormalDist()
    first_quantile = normal.inv_cdf(1.0 - (1.0 / trial_count))
    second_quantile = normal.inv_cdf(1.0 - (1.0 / (trial_count * math.e)))
    expected_maximum = math.sqrt(trial_variance) * (
        (1.0 - gamma) * first_quantile + gamma * second_quantile
    )
    skew = _skewness(selected_returns)
    kurtosis = _kurtosis(selected_returns)
    denominator_term = (
        1.0
        - skew * selected_sharpe
        + ((kurtosis - 1.0) / 4.0) * (selected_sharpe**2)
    )
    if denominator_term <= 0:
        raise EdgeValidationError("deflated Sharpe denominator is not positive")
    z_score = (
        (selected_sharpe - expected_maximum)
        * math.sqrt(len(selected_returns) - 1)
        / math.sqrt(denominator_term)
    )
    probability = normal.cdf(z_score)
    return {
        "method": "deflated_sharpe_ratio",
        "probability": probability,
        "z_score": z_score,
        "selected_periodic_sharpe": selected_sharpe,
        "selected_annualized_sharpe": selected_sharpe * math.sqrt(periods_per_year),
        "expected_maximum_periodic_sharpe": expected_maximum,
        "trial_count": trial_count,
        "selected_skewness": skew,
        "selected_kurtosis": kurtosis,
    }


def probability_of_backtest_overfitting(
    matrix: Sequence[Sequence[float]],
    *,
    partitions: int,
) -> dict[str, Any]:
    _finite_matrix(matrix, "PBO matrix")
    observation_count = len(matrix)
    candidate_count = len(matrix[0])
    if candidate_count < 2:
        raise EdgeValidationError("PBO requires at least two candidates")
    if observation_count < partitions or partitions % 2:
        raise EdgeValidationError("PBO requires an even feasible partition count")
    if observation_count % partitions:
        raise EdgeValidationError("PBO observations must divide evenly across partitions")
    group_size = observation_count // partitions
    groups = tuple(
        tuple(range(start, start + group_size))
        for start in range(0, observation_count, group_size)
    )
    if len(groups) != partitions or any(not group for group in groups):
        raise EdgeValidationError("PBO observations cannot form the frozen partitions")
    combinations = tuple(itertools.combinations(range(partitions), partitions // 2))
    if len(combinations) > 5000:
        raise EdgeValidationError("PBO combination count exceeds the deterministic safety cap")
    logits: list[float] = []
    selected_ids: list[int] = []
    for in_sample_groups in combinations:
        in_sample_group_set = set(in_sample_groups)
        in_indices = tuple(
            index for group in in_sample_groups for index in groups[group]
        )
        out_indices = tuple(
            index
            for group in range(partitions)
            if group not in in_sample_group_set
            for index in groups[group]
        )
        in_scores = []
        out_scores = []
        for candidate in range(candidate_count):
            in_scores.append(_periodic_sharpe(tuple(matrix[index][candidate] for index in in_indices)))
            out_scores.append(
                _periodic_sharpe(tuple(matrix[index][candidate] for index in out_indices))
            )
        selected = max(range(candidate_count), key=lambda item: (in_scores[item], -item))
        selected_ids.append(selected)
        ordered = sorted(range(candidate_count), key=lambda item: (out_scores[item], -item))
        rank = ordered.index(selected) + 1
        relative_rank = rank / (candidate_count + 1.0)
        logits.append(math.log(relative_rank / (1.0 - relative_rank)))
    pbo = sum(value <= 0 for value in logits) / len(logits)
    return {
        "method": "combinatorially_symmetric_cross_validation",
        "pbo": pbo,
        "partitions": partitions,
        "split_count": len(combinations),
        "median_oos_rank_logit": float(statistics.median(logits)),
        "distinct_is_winners": len(set(selected_ids)),
    }


def romano_wolf_stepdown(
    candidate_excess_returns: Sequence[Sequence[float]],
    *,
    samples: int,
    mean_block_length: float,
    alpha: float,
    seed: int,
) -> dict[str, Any]:
    columns = _columns(candidate_excess_returns)
    observed_t = tuple(
        math.sqrt(len(values)) * statistics.fmean(values) / _sample_standard_deviation(values)
        for values in columns
    )
    centered = tuple(
        tuple(value - statistics.fmean(values) for value in values) for values in columns
    )
    rng = random.Random(seed)
    bootstrap_t: list[tuple[float, ...]] = []
    for _ in range(samples):
        indices = _stationary_indices(
            len(candidate_excess_returns), mean_block_length=mean_block_length, rng=rng
        )
        row = []
        for values in centered:
            sample_values = tuple(values[index] for index in indices)
            deviation = _sample_standard_deviation(sample_values)
            row.append(
                0.0
                if deviation <= 0
                else math.sqrt(len(sample_values))
                * statistics.fmean(sample_values)
                / deviation
            )
        bootstrap_t.append(tuple(row))
    order = tuple(sorted(range(len(observed_t)), key=lambda item: (-observed_t[item], item)))
    adjusted = [1.0] * len(observed_t)
    previous = 0.0
    for position, candidate in enumerate(order):
        remaining = order[position:]
        exceedances = sum(
            max(draw[item] for item in remaining) >= observed_t[candidate]
            for draw in bootstrap_t
        )
        raw_adjusted = (exceedances + 1) / (samples + 1)
        previous = max(previous, raw_adjusted)
        adjusted[candidate] = previous
    global_statistic = max(0.0, max(observed_t))
    global_exceedances = sum(max(0.0, max(draw)) >= global_statistic for draw in bootstrap_t)
    return {
        "method": "romano_wolf_stationary_bootstrap_stepdown",
        "observed_t_statistics": list(observed_t),
        "adjusted_p_values": adjusted,
        "global_max_t_p_value": (global_exceedances + 1) / (samples + 1),
        "surviving_candidate_indices": [
            index for index, p_value in enumerate(adjusted) if p_value <= alpha
        ],
        "samples": samples,
    }


def circular_shift_signal_permutation(
    market_returns: Sequence[float],
    positions: Sequence[float],
    *,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    if len(market_returns) != len(positions):
        raise EdgeValidationError("market returns and positions must align")
    if len(market_returns) < 3:
        raise EdgeValidationError("signal permutation requires at least three observations")
    observed = float(sum(position * value for position, value in zip(positions, market_returns)))
    possible_shifts = list(range(1, len(positions)))
    rng = random.Random(seed)
    if len(possible_shifts) <= samples:
        shifts = possible_shifts
    else:
        shifts = rng.sample(possible_shifts, samples)
    greater_or_equal = 0
    for shift in shifts:
        shifted = positions[-shift:] + positions[:-shift]
        statistic = sum(position * value for position, value in zip(shifted, market_returns))
        greater_or_equal += statistic >= observed
    p_value = (greater_or_equal + 1) / (len(shifts) + 1)
    return {
        "method": "circular_shift_signal_alignment_permutation",
        "observed_gross_alignment_return": observed,
        "p_value": p_value,
        "permutation_count": len(shifts),
        "limitation": "Tests signal timing, not path-dependent stop/target execution.",
    }


def _canonical_input_payload(value: StrategyEdgeInput) -> dict[str, Any]:
    return {
        "schema": "qookey-strategy-edge-input-v0.1",
        "provider": value.provider,
        "selected_candidate_id": value.selected_candidate_id,
        "candidate_ids": list(value.candidate_ids),
        "update_returns_matrix": [list(row) for row in value.update_returns_matrix],
        "update_benchmark_returns": list(value.update_benchmark_returns),
        "validation_returns": list(value.validation_returns),
        "validation_benchmark_returns": list(value.validation_benchmark_returns),
        "validation_market_returns": list(value.validation_market_returns),
        "validation_positions": list(value.validation_positions),
        "periods_per_year": value.periods_per_year,
        "trial_registry": {
            "complete": value.trial_registry.complete,
            "experiment_ids": list(value.trial_registry.experiment_ids),
            "registry_sha256": value.trial_registry.registry_sha256,
        },
        "partition_integrity": {
            "passed": value.partition_integrity_passed,
            "evaluation_integrity_sha256": value.evaluation_integrity_sha256,
        },
        "authority": {
            "holdout_accessed": value.holdout_accessed,
            "provider_data_fetched": value.provider_data_fetched,
            "r2_accessed": value.r2_accessed,
            "trade_plan_authorized": value.trade_plan_authorized,
            "live_trading_authorized": value.live_trading_authorized,
        },
    }


def input_fingerprint(value: StrategyEdgeInput) -> str:
    encoded = json.dumps(
        _canonical_input_payload(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def validate_strategy_edge(
    evidence: StrategyEdgeInput,
    policy: EdgeValidationPolicy | None = None,
) -> dict[str, Any]:
    active_policy = policy or EdgeValidationPolicy()
    reasons: list[str] = []
    if len(evidence.update_returns_matrix) < active_policy.minimum_update_observations:
        reasons.append("update_observations_below_minimum")
    if len(evidence.validation_returns) < active_policy.minimum_validation_observations:
        reasons.append("validation_observations_below_minimum")
    if len(evidence.candidate_ids) < active_policy.minimum_trials:
        reasons.append("trial_count_below_minimum")
    if not evidence.trial_registry.complete:
        reasons.append("trial_registry_not_complete")
    if reasons:
        return _report(evidence, active_policy, {}, reasons)

    selected_index = evidence.candidate_ids.index(evidence.selected_candidate_id)
    update_excess_matrix = tuple(
        tuple(value - baseline for value in row)
        for row, baseline in zip(
            evidence.update_returns_matrix, evidence.update_benchmark_returns
        )
    )
    update_excess_columns = _columns(update_excess_matrix)
    selected_validation_excess = _excess(
        evidence.validation_returns, evidence.validation_benchmark_returns
    )
    seed = active_policy.deterministic_seed
    methods: dict[str, Any] = {}
    try:
        methods["stationary_bootstrap"] = stationary_bootstrap_mean_test(
            selected_validation_excess,
            samples=active_policy.bootstrap_samples,
            mean_block_length=active_policy.stationary_bootstrap_mean_block_length,
            seed=seed + 1,
        )
        methods["deflated_sharpe"] = deflated_sharpe_test(
            update_excess_columns[selected_index],
            update_excess_columns,
            periods_per_year=evidence.periods_per_year,
        )
        methods["pbo_cscv"] = probability_of_backtest_overfitting(
            evidence.update_returns_matrix,
            partitions=active_policy.cscv_partitions,
        )
        methods["romano_wolf"] = romano_wolf_stepdown(
            update_excess_matrix,
            samples=active_policy.bootstrap_samples,
            mean_block_length=active_policy.stationary_bootstrap_mean_block_length,
            alpha=active_policy.alpha,
            seed=seed + 2,
        )
        update_sharpe = _annualized_sharpe(
            update_excess_columns[selected_index], evidence.periods_per_year
        )
        validation_sharpe = _annualized_sharpe(
            selected_validation_excess, evidence.periods_per_year
        )
        retention = validation_sharpe / update_sharpe if update_sharpe > 0 else -math.inf
        methods["oos_retention"] = {
            "method": "disjoint_validation_sharpe_retention",
            "update_annualized_sharpe": update_sharpe,
            "validation_annualized_excess_sharpe": validation_sharpe,
            "retention_fraction": retention,
        }
        methods["signal_permutation"] = circular_shift_signal_permutation(
            evidence.validation_market_returns,
            evidence.validation_positions,
            samples=active_policy.permutation_samples,
            seed=seed + 3,
        )
    except EdgeValidationError as error:
        reasons.append(f"method_input_invalid:{error}")
        return _report(evidence, active_policy, methods, reasons)

    if methods["stationary_bootstrap"]["p_value"] > active_policy.alpha:
        reasons.append("stationary_bootstrap_not_significant")
    if methods["deflated_sharpe"]["probability"] < 1.0 - active_policy.alpha:
        reasons.append("deflated_sharpe_below_probability_gate")
    if methods["pbo_cscv"]["pbo"] > active_policy.maximum_pbo:
        reasons.append("pbo_above_maximum")
    adjusted_p = methods["romano_wolf"]["adjusted_p_values"][selected_index]
    if adjusted_p > active_policy.alpha:
        reasons.append("selected_candidate_fails_romano_wolf")
    if methods["romano_wolf"]["global_max_t_p_value"] > active_policy.alpha:
        reasons.append("global_superior_predictive_ability_not_significant")
    if methods["oos_retention"]["validation_annualized_excess_sharpe"] < (
        active_policy.minimum_validation_sharpe
    ):
        reasons.append("validation_sharpe_below_minimum")
    if methods["oos_retention"]["retention_fraction"] < (
        active_policy.minimum_oos_sharpe_retention
    ):
        reasons.append("oos_sharpe_retention_below_minimum")
    if methods["signal_permutation"]["p_value"] > active_policy.alpha:
        reasons.append("signal_alignment_permutation_not_significant")
    return _report(evidence, active_policy, methods, reasons)


def _report(
    evidence: StrategyEdgeInput,
    policy: EdgeValidationPolicy,
    methods: dict[str, Any],
    reasons: list[str],
) -> dict[str, Any]:
    verdict = EdgeVerdict.REJECT if reasons else EdgeVerdict.PASS
    return {
        "schema": "qookey-strategy-edge-validation-report-v0.1",
        "verdict": verdict.value,
        "input_fingerprint": input_fingerprint(evidence),
        "provider": evidence.provider,
        "selected_candidate_id": evidence.selected_candidate_id,
        "reasons": reasons or ["all_frozen_edge_gates_pass"],
        "policy": {
            "alpha": policy.alpha,
            "maximum_pbo": policy.maximum_pbo,
            "minimum_update_observations": policy.minimum_update_observations,
            "minimum_validation_observations": policy.minimum_validation_observations,
            "minimum_trials": policy.minimum_trials,
            "cscv_partitions": policy.cscv_partitions,
            "bootstrap_samples": policy.bootstrap_samples,
            "stationary_bootstrap_mean_block_length": (
                policy.stationary_bootstrap_mean_block_length
            ),
            "minimum_validation_sharpe": policy.minimum_validation_sharpe,
            "minimum_oos_sharpe_retention": policy.minimum_oos_sharpe_retention,
            "permutation_samples": policy.permutation_samples,
            "deterministic_seed": policy.deterministic_seed,
        },
        "methods": methods,
        "authority": {
            "research_evidence_only": True,
            "provider_requests_performed": False,
            "r2_accessed": False,
            "holdout_accessed": False,
            "promotion_authority": 0,
            "trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
            "v0_10_production_critical_path_mutated": False,
        },
        "limitations": [
            "Statistical PASS is historical evidence, not proof of future profitability.",
            "Cost, slippage, capacity, drawdown and exposure remain separate upstream gates.",
            "Signal permutation does not reproduce path-dependent stop/target execution.",
            "This report never opens or substitutes for the frozen replacement holdout.",
        ],
    }


def edge_input_from_dict(payload: dict[str, Any]) -> StrategyEdgeInput:
    if payload.get("schema") != "qookey-strategy-edge-input-v0.1":
        raise EdgeValidationError("unsupported strategy edge input schema")
    trial = payload.get("trial_registry")
    partition_integrity = payload.get("partition_integrity")
    authority = payload.get("authority")
    if (
        not isinstance(trial, dict)
        or not isinstance(partition_integrity, dict)
        or not isinstance(authority, dict)
    ):
        raise EdgeValidationError(
            "trial_registry, partition_integrity and authority objects are required"
        )
    try:
        return StrategyEdgeInput(
            provider=str(payload["provider"]),
            selected_candidate_id=str(payload["selected_candidate_id"]),
            candidate_ids=tuple(str(value) for value in payload["candidate_ids"]),
            update_returns_matrix=tuple(
                tuple(float(value) for value in row)
                for row in payload["update_returns_matrix"]
            ),
            update_benchmark_returns=tuple(
                float(value) for value in payload["update_benchmark_returns"]
            ),
            validation_returns=tuple(float(value) for value in payload["validation_returns"]),
            validation_benchmark_returns=tuple(
                float(value) for value in payload["validation_benchmark_returns"]
            ),
            validation_market_returns=tuple(
                float(value) for value in payload["validation_market_returns"]
            ),
            validation_positions=tuple(
                float(value) for value in payload["validation_positions"]
            ),
            periods_per_year=int(payload["periods_per_year"]),
            trial_registry=TrialRegistryEvidence(
                complete=_strict_bool(trial["complete"], "trial_registry.complete"),
                experiment_ids=tuple(str(value) for value in trial["experiment_ids"]),
                registry_sha256=str(trial["registry_sha256"]),
            ),
            partition_integrity_passed=_strict_bool(
                partition_integrity["passed"], "partition_integrity.passed"
            ),
            evaluation_integrity_sha256=str(
                partition_integrity["evaluation_integrity_sha256"]
            ),
            holdout_accessed=_strict_bool(
                authority.get("holdout_accessed", False), "authority.holdout_accessed"
            ),
            provider_data_fetched=_strict_bool(
                authority.get("provider_data_fetched", False),
                "authority.provider_data_fetched",
            ),
            r2_accessed=_strict_bool(
                authority.get("r2_accessed", False), "authority.r2_accessed"
            ),
            trade_plan_authorized=_strict_bool(
                authority.get("trade_plan_authorized", False),
                "authority.trade_plan_authorized",
            ),
            live_trading_authorized=_strict_bool(
                authority.get("live_trading_authorized", False),
                "authority.live_trading_authorized",
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, EdgeValidationError):
            raise
        raise EdgeValidationError(f"invalid strategy edge input: {error}") from error


def policy_from_dict(payload: dict[str, Any]) -> EdgeValidationPolicy:
    policy = payload.get("policy")
    if payload.get("schema_version") != "strategy_edge_validation_v0_1" or not isinstance(
        policy, dict
    ):
        raise EdgeValidationError("unsupported strategy edge validation policy")
    try:
        return EdgeValidationPolicy(
            alpha=float(policy["alpha"]),
            maximum_pbo=float(policy["maximum_pbo"]),
            minimum_update_observations=int(policy["minimum_update_observations"]),
            minimum_validation_observations=int(policy["minimum_validation_observations"]),
            minimum_trials=int(policy["minimum_trials"]),
            cscv_partitions=int(policy["cscv_partitions"]),
            bootstrap_samples=int(policy["bootstrap_samples"]),
            stationary_bootstrap_mean_block_length=float(
                policy["stationary_bootstrap_mean_block_length"]
            ),
            minimum_validation_sharpe=float(policy["minimum_validation_sharpe"]),
            minimum_oos_sharpe_retention=float(policy["minimum_oos_sharpe_retention"]),
            permutation_samples=int(policy["permutation_samples"]),
            deterministic_seed=int(policy["deterministic_seed"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, EdgeValidationError):
            raise
        raise EdgeValidationError(f"invalid strategy edge policy: {error}") from error
