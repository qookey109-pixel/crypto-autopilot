from __future__ import annotations

import unittest

from crypto_autopilot.agent_arena import (
    AgentArenaError,
    AgentArenaPolicy,
    ArenaCandidate,
    rank_candidates,
)
from crypto_autopilot.experiment_registry import ExperimentComparisonKey, ExperimentCost, ExperimentRecord


DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64


def _record(experiment_id: str, score: float, *, provider: str = "binance_usdm", outcome: str = "completed", metrics: dict[str, object] | None = None) -> ExperimentRecord:
    return ExperimentRecord(
        experiment_id=experiment_id,
        run_id=f"run-{experiment_id}",
        comparison=ExperimentComparisonKey(
            provider=provider,
            symbol_universe_sha256=DIGEST_A,
            interval_set=("15M", "1H", "4H"),
            feature_config_sha256=DIGEST_B,
            evaluation_fingerprint=DIGEST_C,
            primary_metric="net_return_after_cost",
        ),
        strategy_config_sha256=DIGEST_A,
        lineage_fingerprint=DIGEST_B,
        candidate_score=score,
        baseline_score=0.1,
        outcome=outcome,
        cost=ExperimentCost(decisions=12),
        metrics=metrics or {"foldCount": 4, "tradeCount": 12, "maxDrawdownPct": 20.0},
        artifact_refs=(f"r2://research/{experiment_id}/receipt.json",),
    )


class AgentArenaTests(unittest.TestCase):
    def test_ranks_only_comparable_completed_candidates(self) -> None:
        result = rank_candidates(
            [
                ArenaCandidate("technical", _record("exp-technical", 0.3)),
                ArenaCandidate("momentum", _record("exp-momentum", 0.5)),
                ArenaCandidate(
                    "weak",
                    _record("exp-weak", 0.9, metrics={"foldCount": 2, "tradeCount": 12, "maxDrawdownPct": 20.0}),
                ),
            ]
        )
        self.assertEqual([item.agent_id for item in result.rankings], ["momentum", "technical"])
        rejected = next(item for item in result.decisions if item.agent_id == "weak")
        self.assertFalse(rejected.eligible)
        self.assertIn("insufficient-folds", rejected.reasons)
        self.assertFalse(result.holdout_accessed)
        self.assertEqual(result.promotion_authority, 0)
        self.assertFalse(result.trade_plan_authorized)

    def test_mixed_provider_fails_closed(self) -> None:
        left = ArenaCandidate("pionex", _record("exp-pionex", 0.2, provider="pionex"))
        right = ArenaCandidate("binance", _record("exp-binance", 0.3))
        with self.assertRaisesRegex(AgentArenaError, "comparison-key-mismatch"):
            rank_candidates([left, right])

    def test_missing_drawdown_is_not_eligible_when_capped(self) -> None:
        candidate = ArenaCandidate(
            "missing-dd",
            _record("exp-missing-dd", 0.4, metrics={"foldCount": 4, "tradeCount": 8}),
        )
        result = rank_candidates([candidate], policy=AgentArenaPolicy(maximum_drawdown_pct=50.0))
        self.assertFalse(result.decisions[0].eligible)
        self.assertIn("missing-max-drawdown", result.decisions[0].reasons)


if __name__ == "__main__":
    unittest.main()
