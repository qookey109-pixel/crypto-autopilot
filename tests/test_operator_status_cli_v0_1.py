from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "operator_status_v0_1.py"


class OperatorStatusCliV01Tests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_status_json_uses_existing_offline_resolver(self) -> None:
        result = self.run_cli("status", "--format", "json")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["schema"],
            "qookey-operator-status-response-v0.1",
        )
        self.assertEqual(payload["command"], "STATUS")
        self.assertFalse(payload["snapshot_is_latest_main_claim"])
        self.assertFalse(payload["execution_authorized"])
        self.assertEqual(payload["data"]["real_money_orders"], "CLOSED")
        self.assertEqual(payload["data"]["live_trading"], "CLOSED")

    def test_paper_status_text_is_operator_friendly(self) -> None:
        result = self.run_cli("paper_status")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Paper status:", result.stdout)
        self.assertIn("real-money orders: False", result.stdout)
        self.assertIn("real live trading: False", result.stdout)

    def test_help_does_not_advertise_write_commands(self) -> None:
        result = self.run_cli("help", "--format", "json")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["data"]["commands"],
            ["help", "status", "paper_status"],
        )
        self.assertFalse(payload["data"]["write_commands_available"])

    def test_unrecognized_command_fails_closed(self) -> None:
        result = self.run_cli("buy btc", "--format", "json")

        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "REJECTED")
        self.assertTrue(payload["read_only"])
        self.assertFalse(payload["execution_authorized"])
        self.assertFalse(payload["network_access_performed"])
        self.assertFalse(payload["state_mutation_performed"])

    def test_missing_status_file_fails_closed(self) -> None:
        result = self.run_cli(
            "status",
            "--status-file",
            "research/status/does-not-exist.json",
            "--format",
            "json",
        )

        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "REJECTED")
        self.assertFalse(payload["execution_authorized"])


if __name__ == "__main__":
    unittest.main()
