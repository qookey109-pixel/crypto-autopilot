from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "quality_visibility.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("quality_visibility", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load quality_visibility.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class QualityVisibilityV02Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_module()
        cls.report = cls.module.build_report(include_broad_ruff=False)

    def test_report_remains_informational_only(self) -> None:
        report = self.report
        self.assertEqual(report["schema"], "qookey-quality-visibility-v0.2")
        self.assertTrue(report["policy"]["informational_only"])
        self.assertFalse(report["policy"]["blocking_gate"])
        self.assertFalse(report["policy"]["thresholds_enforced"])
        self.assertFalse(report["policy"]["semantic_type_checker_run"])
        self.assertFalse(report["policy"]["promotion_authority"])
        self.assertFalse(report["policy"]["trading_authority"])

    def test_annotation_visibility_is_descriptive(self) -> None:
        visibility = self.report["annotation_visibility"]
        self.assertGreater(visibility["callables"], 0)
        self.assertGreaterEqual(visibility["fully_annotated_callable_fraction"], 0.0)
        self.assertLessEqual(visibility["fully_annotated_callable_fraction"], 1.0)
        self.assertGreaterEqual(visibility["parameter_annotation_fraction"], 0.0)
        self.assertLessEqual(visibility["parameter_annotation_fraction"], 1.0)
        self.assertGreaterEqual(visibility["return_annotation_fraction"], 0.0)
        self.assertLessEqual(visibility["return_annotation_fraction"], 1.0)

    def test_dead_code_visibility_is_explicitly_heuristic(self) -> None:
        visibility = self.report["dead_code_visibility"]
        self.assertTrue(visibility["heuristic_only"])
        self.assertEqual(
            visibility["scope"],
            "unreferenced_private_module_level_definitions_only",
        )
        for row in visibility["candidates"]:
            self.assertTrue(row["name"].startswith("_"))
            self.assertFalse(row["name"].startswith("__"))
            self.assertEqual(row["observed_static_reference_count"], 0)
            self.assertTrue(row["heuristic_only"])

    def test_test_mode_does_not_require_external_ruff_process(self) -> None:
        broad = self.report["broad_ruff_visibility"]
        self.assertTrue(broad["skipped_for_test"])
        self.assertEqual(broad["rules"], ["F", "I", "UP", "B", "C90"])

    def test_inventory_has_no_syntax_issue(self) -> None:
        self.assertEqual(self.report["inventory"]["syntax_issue_count"], 0)
        self.assertEqual(self.report["syntax_issues"], [])


if __name__ == "__main__":
    unittest.main()
