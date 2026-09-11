import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "btc_completion_guard", ROOT / "scripts/check_simulation_btc_completion_v0_1.py"
)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class BtcCompletionGuardV01Tests(unittest.TestCase):
    def test_formal_pass_receipt_stops_duplicate_execution(self):
        self.assertTrue(module.completion_is_frozen(module.DEFAULT_RECEIPT))

    def test_missing_receipt_allows_first_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertFalse(module.completion_is_frozen(Path(directory) / "missing.json"))

    def test_present_tampered_receipt_fails_closed(self):
        receipt = json.loads(module.DEFAULT_RECEIPT.read_text(encoding="utf-8"))
        receipt["report_status"] = "NOT_READY"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            path.write_text(json.dumps(receipt), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "report_status"):
                module.completion_is_frozen(path)

    def test_workflow_checks_receipt_before_runtime_or_r2_execution(self):
        workflow = (ROOT / ".github/workflows/simulation-btc-v0-1.yml").read_text(
            encoding="utf-8"
        )
        guard = workflow.index("Check frozen fixed-sample completion receipt")
        install = workflow.index("Install constrained runtime")
        execute = workflow.index("Execute exact admitted BTC simulation")
        self.assertLess(guard, install)
        self.assertLess(guard, execute)
        self.assertGreaterEqual(
            workflow.count("steps.completion.outputs.complete != 'true'"), 3
        )
        self.assertIn("steps.completion.outcome == 'success'", workflow)


if __name__ == "__main__":
    unittest.main()
