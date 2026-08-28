from __future__ import annotations

import hashlib
import json
import math
import random
import unittest
from pathlib import Path

from crypto_autopilot.strategy_edge_validation import (
    EdgeValidationError,
    EdgeValidationPolicy,
    StrategyEdgeInput,
    TrialRegistryEvidence,
    circular_shift_signal_permutation,
    deflated_sharpe_test,
    input_fingerprint,
    policy_from_dict,
    probability_of_backtest_overfitting,
    romano_wolf_stepdown,
    stationary_bootstrap_mean_test,
    validate_strategy_edge,
)


DIGEST = "a" * 64


def _policy() -> EdgeValidationPolicy:
    return EdgeValidationPolicy(
        alpha=0.05,
        maximum_pbo=0.20,
        minimum_update_observations=120,
        minimum_validation_observations=60,
        minimum_trials=5,
        cscv_partitions=8,
        bootstrap_samples=199,
        stationary_bootstrap_mean_block_length=8.0,
        minimum_validation_sharpe=0.0,
        minimum_oos_sharpe_retention=0.20,
        permutation_samples=199,
        deterministic_seed=77,
    )


def _strong_evidence(*, registry_complete: bool = True) -> StrategyEdgeInput:
    candidate_ids = tuple(f"candidate-{index}" for index in range(5))
    update_rows = []
    for index in range(160):
        update_rows.append(
            (
                0.0030 + 0.0010 * math.sin(index * 0.37),
                0.0010 + 0.0018 * math.sin(index * 0.23 + 0.2),
                0.0002 + 0.0025 * math.cos(index * 0.19),
                -0.0002 + 0.0027 * math.sin(index * 0.31),
                -0.0010 + 0.0020 * math.cos(index * 0.13),
            )
        )
    rng = random.Random(20260828)
    market = tuple(rng.normalvariate(0.0, 0.01) for _ in range(80))
    positions = tuple(1.0 if value >= 0 else -1.0 for value in market)
    validation = tuple(position * value - 0.0003 for position, value in zip(positions, market))
    return StrategyEdgeInput(
        provider="synthetic_fixture",
        selected_candidate_id="candidate-0",
        candidate_ids=candidate_ids,
        update_returns_matrix=tuple(update_rows),
        update_benchmark_returns=(0.0,) * len(update_rows),
        validation_returns=validation,
        validation_benchmark_returns=(0.0,) * len(validation),
        validation_market_returns=market,
        validation_positions=positions,
        periods_per_year=365,
        trial_registry=TrialRegistryEvidence(
            complete=registry_complete,
            experiment_ids=candidate_ids,
            registry_sha256=DIGEST,
        ),
        partition_integrity_passed=True,
        evaluation_integrity_sha256="b" * 64,
    )


class StrategyEdgePrimitiveTests(unittest.TestCase):
    def test_stationary_bootstrap_is_deterministic_and_detects_positive_mean(self) -> None:
        values = tuple(0.002 + 0.001 * math.sin(index * 0.3) for index in range(120))
        first = stationary_bootstrap_mean_test(
            values, samples=199, mean_block_length=8.0, seed=5
        )
        second = stationary_bootstrap_mean_test(
            values, samples=199, mean_block_length=8.0, seed=5
        )
        self.assertEqual(first, second)
        self.assertLessEqual(first["p_value"], 0.05)

    def test_deflated_sharpe_penalizes_the_complete_trial_family(self) -> None:
        trials = tuple(
            tuple(
                mean + 0.001 * math.sin(index * frequency)
                for index in range(160)
            )
            for mean, frequency in (
                (0.0030, 0.37),
                (0.0010, 0.23),
                (0.0002, 0.19),
                (-0.0002, 0.31),
                (-0.0010, 0.13),
            )
        )
        result = deflated_sharpe_test(trials[0], trials, periods_per_year=365)
        self.assertEqual(result["trial_count"], 5)
        self.assertGreaterEqual(result["probability"], 0.95)

    def test_pbo_uses_all_symmetric_splits(self) -> None:
        evidence = _strong_evidence()
        result = probability_of_backtest_overfitting(
            evidence.update_returns_matrix, partitions=8
        )
        self.assertEqual(result["split_count"], 70)
        self.assertEqual(result["pbo"], 0.0)

    def test_romano_wolf_controls_the_trial_family(self) -> None:
        evidence = _strong_evidence()
        matrix = tuple(
            tuple(value - baseline for value in row)
            for row, baseline in zip(
                evidence.update_returns_matrix, evidence.update_benchmark_returns
            )
        )
        result = romano_wolf_stepdown(
            matrix,
            samples=199,
            mean_block_length=8.0,
            alpha=0.05,
            seed=8,
        )
        self.assertLessEqual(result["adjusted_p_values"][0], 0.05)
        self.assertIn(0, result["surviving_candidate_indices"])

    def test_signal_permutation_breaks_time_alignment(self) -> None:
        evidence = _strong_evidence()
        result = circular_shift_signal_permutation(
            evidence.validation_market_returns,
            evidence.validation_positions,
            samples=199,
            seed=9,
        )
        self.assertLessEqual(result["p_value"], 0.05)
        self.assertIn("path-dependent", result["limitation"])


class StrategyEdgeContractTests(unittest.TestCase):
    def test_complete_strong_fixture_passes_all_frozen_gates(self) -> None:
        report = validate_strategy_edge(_strong_evidence(), _policy())
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["reasons"], ["all_frozen_edge_gates_pass"])
        self.assertEqual(
            set(report["methods"]),
            {
                "stationary_bootstrap",
                "deflated_sharpe",
                "pbo_cscv",
                "romano_wolf",
                "oos_retention",
                "signal_permutation",
            },
        )
        self.assertEqual(report["authority"]["promotion_authority"], 0)
        self.assertFalse(report["authority"]["holdout_accessed"])
        self.assertFalse(report["authority"]["live_trading_authorized"])

    def test_incomplete_trial_registry_rejects_before_methods(self) -> None:
        report = validate_strategy_edge(
            _strong_evidence(registry_complete=False), _policy()
        )
        self.assertEqual(report["verdict"], "REJECT")
        self.assertIn("trial_registry_not_complete", report["reasons"])
        self.assertEqual(report["methods"], {})

    def test_holdout_or_data_authority_claim_fails_closed(self) -> None:
        evidence = _strong_evidence()
        with self.assertRaisesRegex(EdgeValidationError, "zero data/trading authority"):
            StrategyEdgeInput(
                provider=evidence.provider,
                selected_candidate_id=evidence.selected_candidate_id,
                candidate_ids=evidence.candidate_ids,
                update_returns_matrix=evidence.update_returns_matrix,
                update_benchmark_returns=evidence.update_benchmark_returns,
                validation_returns=evidence.validation_returns,
                validation_benchmark_returns=evidence.validation_benchmark_returns,
                validation_market_returns=evidence.validation_market_returns,
                validation_positions=evidence.validation_positions,
                periods_per_year=evidence.periods_per_year,
                trial_registry=evidence.trial_registry,
                partition_integrity_passed=True,
                evaluation_integrity_sha256=evidence.evaluation_integrity_sha256,
                holdout_accessed=True,
            )

    def test_input_fingerprint_is_deterministic(self) -> None:
        first = _strong_evidence()
        second = _strong_evidence()
        self.assertEqual(input_fingerprint(first), input_fingerprint(second))

    def test_versioned_policy_is_research_only_and_loads_exactly(self) -> None:
        root = Path(__file__).parents[1]
        payload = json.loads(
            root.joinpath("config/strategy_edge_validation_v0_1.json").read_text(
                encoding="utf-8"
            )
        )
        policy = policy_from_dict(payload)
        self.assertEqual(policy, EdgeValidationPolicy())
        self.assertEqual(payload["status"], "PREPARED_RESEARCH_ONLY")
        self.assertFalse(payload["execution"]["production_dataset_execution_authorized"])
        self.assertFalse(payload["authority"]["replacement_holdout_access_authorized"])
        self.assertEqual(payload["authority"]["model_promotion_authority"], 0)
        self.assertFalse(payload["authority"]["live_trading_authorized"])

    def test_preparation_receipt_binds_exact_artifact_bytes(self) -> None:
        root = Path(__file__).parents[1]
        receipt = json.loads(
            root.joinpath(
                "research/receipts/2026-08-28-strategy-edge-validation-v0-1-prepared.json"
            ).read_text(encoding="utf-8")
        )
        for artifact in receipt["artifacts"].values():
            actual = hashlib.sha256(root.joinpath(artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(actual, artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
