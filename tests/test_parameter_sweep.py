from __future__ import annotations

import unittest

from crypto_autopilot.research.parameter_sweep import (
    ParameterAxis,
    PrimaryMetric,
    SweepObservation,
    SweepPhase,
    SweepPlan,
    SweepPolicy,
    SweepProtocolError,
    SweepScore,
    ValidationStatus,
    build_candidate_grid,
    freeze_validated_parameters,
    plan_fingerprint,
    select_update_candidate,
    validate_selected_candidate,
)


def _policy(*, neighbor_drop: float = 0.12, stable_neighbors: int = 2) -> SweepPolicy:
    return SweepPolicy(
        primary_metric=PrimaryMetric.MEAN_R,
        min_update_trades_per_fold=20,
        min_validation_trades=20,
        min_update_primary_metric=0.0,
        min_validation_primary_metric=0.0,
        max_update_drawdown_pct=25.0,
        max_validation_drawdown_pct=25.0,
        min_stable_neighbors=stable_neighbors,
        max_neighbor_primary_drop=neighbor_drop,
    )


def _plan(*, neighbor_drop: float = 0.12, stable_neighbors: int = 2) -> SweepPlan:
    return SweepPlan(
        plan_id="fixture-plan-v0-1",
        axes=(ParameterAxis("example_threshold", (0.5, 1.0, 1.5)),),
        update_fold_ids=("update-a", "update-b"),
        validation_fold_id="validation-a",
        policy=_policy(neighbor_drop=neighbor_drop, stable_neighbors=stable_neighbors),
    )


def _obs(
    candidate_id: str,
    fold_id: str,
    mean_r: float,
    *,
    phase: SweepPhase = SweepPhase.UPDATE,
    trades: int = 30,
    drawdown: float = 10.0,
) -> SweepObservation:
    return SweepObservation(
        candidate_id=candidate_id,
        fold_id=fold_id,
        phase=phase,
        score=SweepScore(
            trade_count=trades,
            mean_r=mean_r,
            return_pct=mean_r * 10.0,
            max_drawdown_pct=drawdown,
        ),
        evidence_ref=f"fixture:{phase.value}:{fold_id}:{candidate_id}:{mean_r}",
    )


def _complete_update_matrix(plan: SweepPlan) -> list[SweepObservation]:
    values = {
        "candidate-0001": (0.20, 0.21),
        "candidate-0002": (0.30, 0.31),
        "candidate-0003": (0.27, 0.28),
    }
    rows: list[SweepObservation] = []
    for candidate_id, scores in values.items():
        for fold_id, score in zip(plan.update_fold_ids, scores):
            rows.append(_obs(candidate_id, fold_id, score))
    return rows


class ParameterSweepTest(unittest.TestCase):
    def test_candidate_grid_and_plan_fingerprint_are_deterministic(self) -> None:
        plan = SweepPlan(
            plan_id="mixed-axis-plan",
            axes=(
                ParameterAxis("threshold", (0.5, 1.0)),
                ParameterAxis("semantic_variant", ("A", "B")),
            ),
            update_fold_ids=("u1", "u2"),
            validation_fold_id="v1",
            policy=_policy(stable_neighbors=0),
        )

        first = build_candidate_grid(plan)
        second = build_candidate_grid(plan)

        self.assertEqual(first, second)
        self.assertEqual(
            [candidate.candidate_id for candidate in first],
            [
                "candidate-0001",
                "candidate-0002",
                "candidate-0003",
                "candidate-0004",
            ],
        )
        self.assertEqual(plan_fingerprint(plan), plan_fingerprint(plan))

        changed = SweepPlan(
            plan_id=plan.plan_id,
            axes=(
                ParameterAxis("threshold", (0.5, 1.1)),
                ParameterAxis("semantic_variant", ("A", "B")),
            ),
            update_fold_ids=plan.update_fold_ids,
            validation_fold_id=plan.validation_fold_id,
            policy=plan.policy,
        )
        self.assertNotEqual(plan_fingerprint(changed), plan_fingerprint(plan))

    def test_update_selection_requires_complete_frozen_matrix(self) -> None:
        plan = _plan()
        rows = _complete_update_matrix(plan)

        with self.assertRaisesRegex(SweepProtocolError, "update matrix must be complete"):
            select_update_candidate(plan, rows[:-1])

    def test_update_selection_is_robust_first_and_requires_neighbor_stability(self) -> None:
        plan = _plan()
        selection = select_update_candidate(plan, _complete_update_matrix(plan))

        self.assertEqual(selection.selected_candidate_id, "candidate-0002")
        self.assertAlmostEqual(selection.selected_worst_primary_metric, 0.30)
        self.assertEqual(
            selection.stable_neighbor_ids,
            ("candidate-0001", "candidate-0003"),
        )
        self.assertEqual(selection.ranked_eligible_candidate_ids[0], "candidate-0002")
        self.assertEqual(len(selection.update_observation_digest), 64)

    def test_isolated_update_peak_is_rejected_instead_of_cherry_picked(self) -> None:
        plan = _plan(neighbor_drop=0.05, stable_neighbors=1)
        rows: list[SweepObservation] = []
        values = {
            "candidate-0001": (0.10, 0.11),
            "candidate-0002": (0.40, 0.42),
            "candidate-0003": (0.12, 0.13),
        }
        for candidate_id, scores in values.items():
            for fold_id, score in zip(plan.update_fold_ids, scores):
                rows.append(_obs(candidate_id, fold_id, score))

        with self.assertRaisesRegex(SweepProtocolError, "isolated/unstable peak"):
            select_update_candidate(plan, rows)

    def test_validation_cannot_switch_to_an_alternative_candidate(self) -> None:
        plan = _plan()
        selection = select_update_candidate(plan, _complete_update_matrix(plan))
        wrong_candidate = _obs(
            "candidate-0003",
            plan.validation_fold_id,
            0.50,
            phase=SweepPhase.VALIDATION,
        )

        with self.assertRaisesRegex(SweepProtocolError, "reselection is forbidden"):
            validate_selected_candidate(plan, selection, wrong_candidate)

    def test_failed_validation_is_consumed_and_cannot_freeze_parameters(self) -> None:
        plan = _plan()
        selection = select_update_candidate(plan, _complete_update_matrix(plan))
        validation = _obs(
            selection.selected_candidate_id,
            plan.validation_fold_id,
            -0.10,
            phase=SweepPhase.VALIDATION,
        )

        decision = validate_selected_candidate(plan, selection, validation)

        self.assertIs(decision.status, ValidationStatus.FAIL)
        self.assertTrue(decision.validation_consumed)
        self.assertIn("validation_primary_metric_below_minimum", decision.reasons)
        with self.assertRaisesRegex(SweepProtocolError, "failed validation cannot freeze"):
            freeze_validated_parameters(plan, selection, decision)

    def test_passed_validation_freezes_exact_update_selected_candidate(self) -> None:
        plan = _plan()
        selection = select_update_candidate(plan, _complete_update_matrix(plan))
        validation = _obs(
            selection.selected_candidate_id,
            plan.validation_fold_id,
            0.18,
            phase=SweepPhase.VALIDATION,
            trades=40,
            drawdown=12.0,
        )

        decision = validate_selected_candidate(plan, selection, validation)
        frozen = freeze_validated_parameters(plan, selection, decision)

        self.assertIs(decision.status, ValidationStatus.PASS)
        self.assertEqual(frozen.candidate_id, "candidate-0002")
        self.assertEqual(frozen.values, (("example_threshold", 1.0),))
        self.assertEqual(frozen.plan_fingerprint, plan_fingerprint(plan))
        self.assertEqual(
            frozen.update_observation_digest,
            selection.update_observation_digest,
        )
        self.assertEqual(frozen.validation_evidence_ref, validation.evidence_ref)


if __name__ == "__main__":
    unittest.main()
