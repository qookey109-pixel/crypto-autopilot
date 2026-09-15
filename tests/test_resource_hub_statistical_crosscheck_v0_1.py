from __future__ import annotations

import json
import math
import random
import unittest
from copy import deepcopy
from pathlib import Path

from crypto_autopilot.toolkit.statistical_crosscheck_v0_1 import (
    StatisticalCrosscheckError,
    run_statistical_crosscheck,
)


POLICY_PATH = Path("config/resource_hub_statistical_crosscheck_v0_1.json")


def _positive_fixture() -> tuple[float, ...]:
    return tuple(0.002 + 0.001 * math.sin(index * 0.3) for index in range(120))


def _serial_fixture() -> tuple[float, ...]:
    rng = random.Random(1)
    state = 0.0
    values = []
    for _ in range(120):
        state = 0.7 * state + rng.normalvariate(0.0, 0.003)
        values.append(0.002 + state)
    return tuple(values)


def _zero_fixture() -> tuple[float, ...]:
    return tuple(0.002 if index % 2 == 0 else -0.002 for index in range(120))


class ResourceHubStatisticalCrosscheckV01Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def test_positive_synthetic_fixture_is_significant_under_both_methods(self) -> None:
        report = run_statistical_crosscheck(
            _positive_fixture(),
            self.policy,
            input_class="synthetic_fixture",
        )
        self.assertEqual(report["status"], "RESEARCH_ONLY")
        self.assertEqual(report["decision"], "DESCRIPTIVE_CROSSCHECK_ONLY")
        self.assertEqual(report["comparison"], "BOTH_SIGNIFICANT_RESEARCH_SIGNAL")
        self.assertLess(report["iid_centered_bootstrap"]["p_value"], 0.05)
        self.assertLess(report["stationary_bootstrap"]["p_value"], 0.05)
        self.assertTrue(all(value is False for value in report["authority"].values()))

    def test_serial_dependence_fixture_exposes_iid_only_divergence(self) -> None:
        report = run_statistical_crosscheck(
            _serial_fixture(),
            self.policy,
            input_class="synthetic_fixture",
        )
        self.assertEqual(
            report["comparison"],
            "IID_ONLY_DIVERGENCE_SERIAL_DEPENDENCE_WARNING",
        )
        self.assertLess(report["iid_centered_bootstrap"]["p_value"], 0.05)
        self.assertGreaterEqual(report["stationary_bootstrap"]["p_value"], 0.05)
        self.assertGreater(report["sample_mean"], 0.0)

    def test_zero_mean_fixture_is_not_significant(self) -> None:
        report = run_statistical_crosscheck(
            _zero_fixture(),
            self.policy,
            input_class="existing_non_holdout_fixture",
        )
        self.assertEqual(report["comparison"], "NOT_SIGNIFICANT")
        self.assertGreaterEqual(report["iid_centered_bootstrap"]["p_value"], 0.05)
        self.assertGreaterEqual(report["stationary_bootstrap"]["p_value"], 0.05)

    def test_holdout_or_unknown_input_class_fails_closed(self) -> None:
        for input_class in ("holdout", "provider_data", "r2_fixture", "unknown"):
            with self.subTest(input_class=input_class):
                with self.assertRaisesRegex(StatisticalCrosscheckError, "input class"):
                    run_statistical_crosscheck(
                        _positive_fixture(),
                        self.policy,
                        input_class=input_class,
                    )

    def test_any_authority_expansion_fails_closed(self) -> None:
        unsafe = deepcopy(self.policy)
        unsafe["authority"]["holdout_access_authorized"] = True
        with self.assertRaisesRegex(StatisticalCrosscheckError, "authority flags"):
            run_statistical_crosscheck(
                _positive_fixture(),
                unsafe,
                input_class="synthetic_fixture",
            )

    def test_crosscheck_cannot_become_edge_gate_or_promotion_signal(self) -> None:
        for field in ("formal_edge_gate", "promotion_signal", "upstream_code_equivalence_claimed"):
            unsafe = deepcopy(self.policy)
            unsafe["interpretation"][field] = True
            with self.subTest(field=field):
                with self.assertRaises(StatisticalCrosscheckError):
                    run_statistical_crosscheck(
                        _positive_fixture(),
                        unsafe,
                        input_class="synthetic_fixture",
                    )


if __name__ == "__main__":
    unittest.main()
