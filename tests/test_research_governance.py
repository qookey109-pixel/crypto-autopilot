from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from crypto_autopilot.evaluation_integrity import (
    EvaluationIntegrityPolicy,
    EvaluationUsage,
    PartitionAccessGuard,
    PartitionRole,
    build_partition_evidence,
    evaluate_partition_integrity,
)
from crypto_autopilot.experiment_registry import (
    ExperimentComparisonKey,
    ExperimentCost,
    ExperimentRecord,
    ExperimentRegistryError,
    JsonExperimentRegistry,
)
from crypto_autopilot.lineage import (
    LineageProtocolError,
    build_lineage_manifest,
    sha256_json,
)
from crypto_autopilot.resource_planning import (
    ResourceEstimate,
    ResourcePlanningError,
    ResourcePlanningPolicy,
    ResearchProposal,
    rank_research_proposals,
)


DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64


def _partitions():
    return (
        build_partition_evidence(
            name="update",
            role=PartitionRole.UPDATE,
            record_fingerprints=(DIGEST_A,),
            source_fingerprints=(DIGEST_B,),
            seeds=(1, 2),
        ),
        build_partition_evidence(
            name="validation",
            role=PartitionRole.VALIDATION,
            record_fingerprints=(DIGEST_C,),
            source_fingerprints=("d" * 64,),
            seeds=(3, 4),
        ),
        build_partition_evidence(
            name="holdout",
            role=PartitionRole.HOLDOUT,
            record_fingerprints=("e" * 64,),
            source_fingerprints=("f" * 64,),
            seeds=(5, 6),
            frozen=True,
        ),
    )


class LineageTests(unittest.TestCase):
    def test_manifest_is_stable_and_has_zero_execution_authority(self) -> None:
        first = build_lineage_manifest(
            run_id="run-1",
            provider="pionex",
            symbol_universe=("BTC_USDT_PERP",),
            intervals=("15M", "1H"),
            datasets={"train": {"rows": 3}},
            feature_config={"technical": "v0.2"},
            strategy_config={"mode": "research"},
            environment={"python": "3.13"},
            seed=7,
        )
        second = build_lineage_manifest(
            run_id="run-1",
            provider="pionex",
            symbol_universe=("BTC_USDT_PERP",),
            intervals=("15M", "1H"),
            datasets={"train": {"rows": 3}},
            feature_config={"technical": "v0.2"},
            strategy_config={"mode": "research"},
            environment={"python": "3.13"},
            seed=7,
        )
        self.assertEqual(first.fingerprint, second.fingerprint)
        self.assertFalse(first.evidence()["holdoutAccessed"])
        self.assertFalse(first.evidence()["tradePlanAuthorized"])

    def test_secret_like_metadata_and_authority_flags_fail_closed(self) -> None:
        with self.assertRaisesRegex(LineageProtocolError, "secret-like"):
            build_lineage_manifest(
                run_id="run-1",
                provider="pionex",
                symbol_universe=("BTC_USDT_PERP",),
                intervals=("15M",),
                datasets={"train": {"rows": 3}},
                feature_config={},
                strategy_config={"api_key": "never"},
                environment={},
                seed=1,
            )
        with self.assertRaisesRegex(LineageProtocolError, "holdout"):
            from crypto_autopilot.lineage import ResearchLineageManifest

            ResearchLineageManifest(
                run_id="run-1",
                provider="pionex",
                symbol_universe_sha256=DIGEST_A,
                interval_set=("15M",),
                dataset_fingerprints=(("train", DIGEST_B),),
                feature_config_sha256=DIGEST_C,
                strategy_config_sha256=DIGEST_A,
                environment={},
                seed=1,
                holdout_accessed=True,
            )


class EvaluationIntegrityTests(unittest.TestCase):
    def test_update_and_validation_are_accessible_but_holdout_is_denied(self) -> None:
        guard = PartitionAccessGuard(_partitions())
        self.assertEqual(guard.access("update", stage=PartitionRole.UPDATE).name, "update")
        self.assertEqual(guard.access("validation", stage=PartitionRole.VALIDATION).name, "validation")
        with self.assertRaisesRegex(PermissionError, "holdout"):
            guard.access("holdout", stage=PartitionRole.HOLDOUT)

    def test_integrity_passes_only_for_disjoint_frozen_partitions(self) -> None:
        result = evaluate_partition_integrity(_partitions())
        self.assertTrue(result.passed)
        self.assertEqual(result.failures, ())

        bad = list(_partitions())
        bad[1] = build_partition_evidence(
            name="validation",
            role=PartitionRole.VALIDATION,
            record_fingerprints=(DIGEST_A,),
            source_fingerprints=(DIGEST_B,),
            seeds=(1,),
        )
        failed = evaluate_partition_integrity(bad)
        self.assertFalse(failed.passed)
        self.assertIn("record-overlap:update:validation", failed.failures)
        self.assertIn("seed-overlap:update:validation", failed.failures)

    def test_usage_receipt_cannot_claim_holdout_before_authority(self) -> None:
        result = evaluate_partition_integrity(
            _partitions(), usage=EvaluationUsage(holdout=("holdout",))
        )
        self.assertFalse(result.passed)
        self.assertIn("holdout-usage-recorded-before-separate-authority", result.failures)


def _record(experiment_id: str, score: float, *, provider: str = "pionex") -> ExperimentRecord:
    return ExperimentRecord(
        experiment_id=experiment_id,
        run_id=f"run-{experiment_id}",
        comparison=ExperimentComparisonKey(
            provider=provider,
            symbol_universe_sha256=DIGEST_A,
            interval_set=("15M", "1H"),
            feature_config_sha256=DIGEST_B,
            evaluation_fingerprint=DIGEST_C,
            primary_metric="mean_r",
        ),
        strategy_config_sha256=DIGEST_A,
        lineage_fingerprint=DIGEST_B,
        candidate_score=score,
        baseline_score=0.1,
        outcome="completed",
        cost=ExperimentCost(wall_clock_seconds=2.0, decisions=10),
        metrics={"tradeCount": 10},
        artifact_refs=(f"r2://research/{experiment_id}/receipt.json",),
    )


class ExperimentRegistryTests(unittest.TestCase):
    def test_registry_is_immutable_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = JsonExperimentRegistry(Path(directory) / "experiments.json")
            record = _record("exp-1", 0.4)
            registry.register(record)
            registry.register(record)
            self.assertEqual(len(registry.list()), 1)
            with self.assertRaisesRegex(ExperimentRegistryError, "immutable"):
                registry.register(_record("exp-1", 0.5))

    def test_comparison_fails_closed_for_different_provider(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = JsonExperimentRegistry(Path(directory) / "experiments.json")
            registry.register(_record("exp-1", 0.4))
            registry.register(_record("exp-2", 0.5, provider="binance_usdm"))
            comparison = registry.compare("exp-1", "exp-2")
            self.assertFalse(comparison.comparable)
            self.assertEqual(comparison.reason, "comparison-key-mismatch")

    def test_comparison_selects_winner_only_with_same_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = JsonExperimentRegistry(Path(directory) / "experiments.json")
            registry.register(_record("exp-1", 0.4))
            registry.register(_record("exp-2", 0.5))
            comparison = registry.compare("exp-1", "exp-2")
            self.assertTrue(comparison.comparable)
            self.assertEqual(comparison.winner_experiment_id, "exp-2")


class ResourcePlanningTests(unittest.TestCase):
    def test_versioned_config_keeps_research_only_authority(self) -> None:
        config = json.loads(
            Path(__file__).parents[1].joinpath("config/research_governance_v0_1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(config["status"], "RESEARCH_ONLY")
        self.assertFalse(config["authority"]["holdout_access_authorized"])
        self.assertFalse(config["authority"]["trade_plan_authorized"])
        self.assertEqual(config["authority"]["promotion_authority"], 0)
        self.assertFalse(config["authority"]["v0_10_production_critical_path_mutation"])

    def test_utility_remains_dominant_and_missing_estimate_is_neutral(self) -> None:
        proposals = (
            ResearchProposal("cheap-low-utility", {"threshold": 1}, 0.70, 1),
            ResearchProposal("expensive-high-utility", {"threshold": 2}, 0.90, 2),
            ResearchProposal("very-expensive-low-utility", {"threshold": 4}, 0.60, 4),
            ResearchProposal("missing", {"threshold": 3}, 0.80, 3),
        )
        estimates = (
            ResourceEstimate("cheap-low-utility", DIGEST_A, 1.0, 100),
            ResourceEstimate("expensive-high-utility", DIGEST_A, 2.0, 200),
            ResourceEstimate("very-expensive-low-utility", DIGEST_A, 100.0, 10_000_000),
        )
        receipt = rank_research_proposals(proposals, estimates)
        self.assertEqual(receipt.rankings[0].proposal_id, "expensive-high-utility")
        self.assertEqual(receipt.estimate_coverage_fraction, 3 / 4)
        self.assertFalse(receipt.holdout_accessed)
        self.assertEqual(receipt.promotion_authority, 0)

    def test_planner_rejects_mixed_resource_profiles_and_authority(self) -> None:
        proposal = ResearchProposal("p", {"threshold": 1}, 0.8, 1)
        other = ResearchProposal("other", {"threshold": 2}, 0.7, 2)
        with self.assertRaisesRegex(ResourcePlanningError, "one profile"):
            rank_research_proposals(
                (proposal, other),
                (
                    ResourceEstimate("p", DIGEST_A, 1.0, 1),
                    ResourceEstimate("other", DIGEST_B, 2.0, 2),
                ),
            )
        with self.assertRaisesRegex(ResourcePlanningError, "no promotion"):
            ResourcePlanningPolicy(promotion_authority=1)


if __name__ == "__main__":
    unittest.main()
