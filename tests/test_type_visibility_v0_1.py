from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "type_visibility.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("type_visibility", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load type_visibility.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TypeVisibilityV01Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_module()

    def test_report_is_nonblocking_and_authority_free(self) -> None:
        report = self.module.build_report(run_tool=False)
        self.assertEqual(report["schema"], "qookey-type-visibility-v0.1")
        self.assertEqual(report["scan_targets"], ["src/crypto_autopilot"])
        self.assertEqual(report["python_version_target"], "3.13")
        self.assertTrue(report["policy"]["informational_only"])
        self.assertFalse(report["policy"]["blocking_gate"])
        self.assertFalse(report["policy"]["thresholds_enforced"])
        self.assertFalse(report["policy"]["promotion_authority"])
        self.assertFalse(report["policy"]["validation_authority"])
        self.assertFalse(report["policy"]["holdout_authority"])
        self.assertFalse(report["policy"]["source_switch_authority"])
        self.assertFalse(report["policy"]["trading_authority"])
        self.assertFalse(report["result"]["ran"])
        self.assertTrue(report["result"]["skipped_for_test"])

    def test_parser_counts_errors_by_code_without_treating_notes_as_errors(self) -> None:
        parsed = self.module.parse_mypy_output(
            "\n".join(
                [
                    "src/crypto_autopilot/a.py:10:5: error: Bad assignment [assignment]",
                    "src/crypto_autopilot/a.py:10:5: note: Consider widening the type",
                    "src/crypto_autopilot/b.py:20: error: Missing annotation [no-untyped-def]",
                ]
            )
        )
        self.assertEqual(parsed["diagnostic_count"], 3)
        self.assertEqual(parsed["error_count"], 2)
        self.assertEqual(parsed["note_count"], 1)
        self.assertEqual(
            parsed["by_error_code"],
            {"assignment": 1, "no-untyped-def": 1},
        )
        self.assertFalse(parsed["diagnostics_truncated"])
        self.assertEqual(parsed["unparsable_lines"], [])

    def test_parser_classifies_receipt_bound_without_hiding_errors(self) -> None:
        parsed = self.module.parse_mypy_output(
            "\n".join(
                [
                    "src/crypto_autopilot/frozen.py:10:5: error: Frozen issue [arg-type]",
                    "src/crypto_autopilot/live.py:20:7: error: Live issue [assignment]",
                ]
            ),
            receipt_bindings={
                "src/crypto_autopilot/frozen.py": (
                    "research/receipts/example-prepared.json",
                )
            },
        )
        self.assertEqual(parsed["error_count"], 2)
        self.assertEqual(parsed["receipt_bound_error_count"], 1)
        self.assertEqual(parsed["unbound_error_count"], 1)
        self.assertEqual(
            parsed["by_error_file"],
            {
                "src/crypto_autopilot/frozen.py": 1,
                "src/crypto_autopilot/live.py": 1,
            },
        )
        diagnostics = {row["path"]: row for row in parsed["diagnostics"]}
        self.assertTrue(diagnostics["src/crypto_autopilot/frozen.py"]["receipt_bound"])
        self.assertEqual(
            diagnostics["src/crypto_autopilot/frozen.py"]["receipt_paths"],
            ["research/receipts/example-prepared.json"],
        )
        self.assertFalse(diagnostics["src/crypto_autopilot/live.py"]["receipt_bound"])

    def test_parser_classifies_freeze_bound_without_hiding_errors(self) -> None:
        parsed = self.module.parse_mypy_output(
            "\n".join(
                [
                    "src/crypto_autopilot/receipt.py:10:5: error: Receipt issue [arg-type]",
                    "src/crypto_autopilot/freeze.py:20:7: error: Freeze issue [assignment]",
                    "src/crypto_autopilot/live.py:30:9: error: Live issue [attr-defined]",
                ]
            ),
            receipt_bindings={
                "src/crypto_autopilot/receipt.py": (
                    "research/receipts/example-prepared.json",
                )
            },
            freeze_bindings={
                "src/crypto_autopilot/freeze.py": (
                    "config/v0_10_critical_path_freeze_v0_1.json",
                )
            },
        )
        self.assertEqual(parsed["error_count"], 3)
        self.assertEqual(parsed["receipt_bound_error_count"], 1)
        self.assertEqual(parsed["unbound_error_count"], 2)
        self.assertEqual(parsed["freeze_bound_error_count"], 1)
        self.assertEqual(parsed["protected_error_count"], 2)
        self.assertEqual(parsed["cleanup_candidate_error_count"], 1)
        diagnostics = {row["path"]: row for row in parsed["diagnostics"]}
        self.assertTrue(diagnostics["src/crypto_autopilot/receipt.py"]["receipt_bound"])
        self.assertFalse(diagnostics["src/crypto_autopilot/receipt.py"]["freeze_bound"])
        self.assertTrue(diagnostics["src/crypto_autopilot/freeze.py"]["freeze_bound"])
        self.assertEqual(
            diagnostics["src/crypto_autopilot/freeze.py"]["freeze_manifests"],
            ["config/v0_10_critical_path_freeze_v0_1.json"],
        )
        self.assertFalse(diagnostics["src/crypto_autopilot/live.py"]["receipt_bound"])
        self.assertFalse(diagnostics["src/crypto_autopilot/live.py"]["freeze_bound"])

    def test_repository_receipt_bindings_include_git_blob_bound_files(self) -> None:
        bindings = self.module._receipt_bindings()
        path = "src/crypto_autopilot/paper/run_recovery_v0_1.py"
        self.assertIn(path, bindings)
        self.assertIn(
            "research/receipts/2026-09-22-live-paper-run-slot-claim-v0-1-prepared.json",
            bindings[path],
        )

    def test_parser_preserves_unrecognized_lines_as_visibility_metadata(self) -> None:
        parsed = self.module.parse_mypy_output("unexpected mypy output")
        self.assertEqual(parsed["diagnostic_count"], 0)
        self.assertEqual(parsed["error_count"], 0)
        self.assertEqual(parsed["unparsable_lines"], ["unexpected mypy output"])


if __name__ == "__main__":
    unittest.main()
