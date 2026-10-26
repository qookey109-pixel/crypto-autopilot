from __future__ import annotations

import copy
import unittest

from crypto_autopilot.training.fingerprint_v0_2 import FingerprintValidationError
from crypto_autopilot.training.runtime_manifest_field_review_v0_1 import (
    inspect_runtime_manifest_fields,
)


def runtime(*, version: str = "20260920.314.1") -> dict[str, object]:
    return {
        "implementation": "cpython",
        "version": "3.13.15 (test-build)",
        "cache_tag": "cpython-313",
        "platform": "linux-x86_64",
        "system": "Linux",
        "release": "6.11.0",
        "machine": "x86_64",
        "libc": ["glibc", "2.39"],
        "distributions": [
            {"name": "pip", "version": "25.2"},
            {"name": "setuptools", "version": "80.9.0"},
            {"name": "qookey-crypto-autopilot", "version": "0.1.0"},
        ],
        "install_tools": [
            {"name": "pip", "version": "25.2"},
            {"name": "setuptools", "version": "80.9.0"},
        ],
        "project_version": "0.1.0",
        "runner_image": {"os": "ubuntu24", "version": version},
        "isolated_environment": True,
        "distribution_inventory_complete": True,
        "install_tools_complete": True,
    }


class Core100RuntimeManifestFieldReviewTests(unittest.TestCase):
    def test_runner_version_is_reported_without_an_unearned_root_cause(self) -> None:
        before = runtime()
        after = runtime(version="20260927.320.1")
        original = copy.deepcopy(before)
        current = copy.deepcopy(after)
        result = inspect_runtime_manifest_fields(baseline=before, observed=after)
        self.assertEqual(result["status"], "DIFFERENCE_OBSERVED")
        self.assertEqual(result["changed_top_level_fields"], ["runner_image"])
        self.assertTrue(result["runner_image_version_changed"])
        self.assertEqual(result["changed_distribution_names"], [])
        self.assertFalse(result["runtime_changed_root_cause_proven"])
        self.assertFalse(result["complete_source_manifests_authenticated"])
        self.assertFalse(result["authority"]["new_training"])
        self.assertFalse(result["authority"]["r2_access"])
        self.assertEqual(before, original)
        self.assertEqual(after, current)

    def test_updated_runner_and_python_are_two_distinct_changes_not_root_cause(self) -> None:
        baseline = runtime(version="20260920.314.1")
        observed = runtime(version="20261012.334.1")
        observed["version"] = "3.13.16 (test-build)"
        result = inspect_runtime_manifest_fields(baseline=baseline, observed=observed)
        self.assertEqual(result["changed_top_level_fields"], ["runner_image", "version"])
        self.assertEqual(result["changed_distribution_names"], [])
        self.assertTrue(result["runner_image_version_changed"])
        self.assertFalse(result["runtime_changed_root_cause_proven"])
        self.assertFalse(result["complete_source_manifests_authenticated"])

    def test_distribution_and_kernel_changes_are_named_without_value_leaks(self) -> None:
        before = runtime()
        after = runtime()
        after["release"] = "6.12.0"
        # A changed installed package must remain self-consistent with the tool subset.
        after["distributions"][1]["version"] = "80.9.1"
        after["install_tools"][1]["version"] = "80.9.1"
        result = inspect_runtime_manifest_fields(baseline=before, observed=after)
        self.assertEqual(
            result["changed_top_level_fields"], ["distributions", "install_tools", "release"]
        )
        self.assertEqual(result["changed_distribution_names"], ["setuptools"])
        self.assertEqual(result["changed_install_tool_names"], ["setuptools"])
        self.assertNotIn("80.9.1", str(result))
        self.assertFalse(result["runner_image_version_changed"])

    def test_same_caller_values_do_not_claim_production_no_change(self) -> None:
        row = runtime()
        got = inspect_runtime_manifest_fields(baseline=row, observed=copy.deepcopy(row))
        self.assertEqual(got["status"], "NO_DIFFERENCE_IN_CALLER_DATA")
        self.assertEqual(got["changed_top_level_fields"], [])
        self.assertFalse(got["governed_comparator_replaced"])

    def test_incomplete_or_invalid_manifests_fail_closed(self) -> None:
        before = runtime()
        cases = []
        bad = runtime()
        del bad["runner_image"]
        cases.append(bad)
        bad = runtime()
        bad["distribution_inventory_complete"] = False
        cases.append(bad)
        bad = runtime()
        bad["distributions"][0]["version"] = "12.0"
        cases.append(bad)
        bad = runtime()
        bad["runner_image"] = {"os": "ubuntu", "extra": "unsafe"}
        cases.append(bad)
        for candidate in cases:
            with self.subTest(candidate=candidate), self.assertRaises(FingerprintValidationError):
                inspect_runtime_manifest_fields(baseline=before, observed=candidate)


if __name__ == "__main__":
    unittest.main()
