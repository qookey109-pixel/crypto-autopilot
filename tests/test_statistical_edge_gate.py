import unittest

from crypto_autopilot.research.statistical_edge_gate import (
    StatisticalEdgePolicy,
    centered_bootstrap_one_sided_p_value,
    evaluate_selected_candidate_edge,
    holm_step_down,
)


class StatisticalEdgeGateTests(unittest.TestCase):
    def test_centered_bootstrap_is_deterministic_for_fixed_seed(self) -> None:
        values = [1.0] * 40
        first = centered_bootstrap_one_sided_p_value(
            values, resamples=1000, seed=17
        )
        second = centered_bootstrap_one_sided_p_value(
            values, resamples=1000, seed=17
        )
        self.assertEqual(first, second)
        self.assertLess(first, 0.05)

    def test_non_positive_mean_fails_closed(self) -> None:
        policy = StatisticalEdgePolicy(
            minimum_samples=30,
            bootstrap_resamples=1000,
            bootstrap_seed=7,
        )
        evidence = evaluate_selected_candidate_edge(
            [-1.0, 0.5] * 20,
            policy=policy,
        )
        self.assertFalse(evidence.passed)
        self.assertEqual(evidence.centered_bootstrap_p_value, 1.0)
        self.assertIn("mean_net_pnl_not_positive", evidence.reasons)
        self.assertFalse(evidence.formal_holdout_accessed)
        self.assertFalse(evidence.strategy_mutation_authorized)
        self.assertFalse(evidence.live_trading_authorized)

    def test_strong_positive_sample_can_pass_research_gate(self) -> None:
        policy = StatisticalEdgePolicy(
            minimum_samples=30,
            bootstrap_resamples=1000,
            bootstrap_seed=11,
        )
        evidence = evaluate_selected_candidate_edge(
            [1.0] * 40,
            development_mean_net_pnl=1.2,
            policy=policy,
        )
        self.assertTrue(evidence.passed)
        self.assertTrue(evidence.bootstrap_significant)
        self.assertTrue(evidence.decay_gate_passed)
        self.assertAlmostEqual(evidence.decay_fraction_vs_development, 1.0 - 1.0 / 1.2)

    def test_edge_decay_can_reject_otherwise_positive_validation(self) -> None:
        policy = StatisticalEdgePolicy(
            minimum_samples=30,
            bootstrap_resamples=1000,
            bootstrap_seed=13,
            maximum_edge_decay_fraction=0.50,
        )
        evidence = evaluate_selected_candidate_edge(
            [0.4] * 40,
            development_mean_net_pnl=1.0,
            policy=policy,
        )
        self.assertFalse(evidence.passed)
        self.assertTrue(evidence.bootstrap_significant)
        self.assertFalse(evidence.decay_gate_passed)
        self.assertIn("edge_decay_above_maximum", evidence.reasons)

    def test_holm_step_down_controls_family(self) -> None:
        result = holm_step_down(
            {
                "hypothesis-a": 0.001,
                "hypothesis-b": 0.02,
                "hypothesis-c": 0.03,
            },
            alpha=0.05,
        )
        self.assertTrue(result["hypothesis-a"])
        self.assertTrue(result["hypothesis-b"])
        self.assertTrue(result["hypothesis-c"])

        stopped = holm_step_down(
            {
                "hypothesis-a": 0.02,
                "hypothesis-b": 0.021,
                "hypothesis-c": 0.022,
            },
            alpha=0.05,
        )
        self.assertFalse(any(stopped.values()))

    def test_small_sample_cannot_pass(self) -> None:
        policy = StatisticalEdgePolicy(
            minimum_samples=30,
            bootstrap_resamples=1000,
            bootstrap_seed=19,
        )
        evidence = evaluate_selected_candidate_edge([1.0] * 20, policy=policy)
        self.assertFalse(evidence.passed)
        self.assertIn("sample_count_below_minimum", evidence.reasons)


if __name__ == "__main__":
    unittest.main()
