from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import check_history_cadence_authority as gate

ENV = {
    "GITHUB_REPOSITORY": "qookey109-pixel/crypto-autopilot",
    "GITHUB_REF": "refs/heads/main",
    "GITHUB_EVENT_NAME": "schedule",
    "GITHUB_RUN_ATTEMPT": "1",
}
NOW = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)


class HistoryCadenceTests(unittest.TestCase):
    def test_valid_contract_and_no_external_access(self):
        with patch("socket.socket", side_effect=AssertionError("network forbidden")):
            result = gate.validate(env=ENV, now=NOW)
        self.assertEqual(result["cron"], "23 */2 9-30 9 *")
        self.assertEqual(result["provider_requests_performed"], 0)
        self.assertFalse(result["r2_access_performed"])

    def test_execution_origin_and_rerun_rejected(self):
        for key, value in (
            ("GITHUB_REF", "refs/heads/branch"),
            ("GITHUB_EVENT_NAME", "pull_request"),
            ("GITHUB_EVENT_NAME", "push"),
            ("GITHUB_RUN_ATTEMPT", "2"),
            ("GITHUB_REPOSITORY", "other/repo"),
        ):
            with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, "FRESH_MAIN"):
                gate.validate(env=dict(ENV, **{key: value}), now=NOW)
        with self.assertRaises(ValueError):
            gate.validate(env={}, now=NOW)

    def test_real_clock_default_and_exclusive_expiry(self):
        for now in (
            datetime(2026, 9, 8, tzinfo=timezone.utc),
            datetime(2026, 10, 1, tzinfo=timezone.utc),
        ):
            with self.assertRaisesRegex(ValueError, "WINDOW_CLOSED"):
                gate.validate(env=ENV, now=now)
        with patch.object(gate, "datetime") as clock:
            clock.now.return_value = datetime(2026, 10, 1, tzinfo=timezone.utc)
            clock.fromisoformat.side_effect = datetime.fromisoformat
            with self.assertRaisesRegex(ValueError, "WINDOW_CLOSED"):
                gate.validate(env=ENV)

    def test_changed_config_base_workflow_and_receipt_fail_closed(self):
        receipt = json.loads((gate.ROOT / gate.RECEIPT).read_text())
        files = {gate.RECEIPT, *gate.BASE_BINDINGS,
                 *(row["path"] for row in receipt["bound_files"])}
        for changed in (gate.CONFIG, gate.RECEIPT, *gate.BASE_BINDINGS,
                        ".github/workflows/binance-usdm-detailed-history-v0-1.yml"):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for name in files:
                    target = root / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes((gate.ROOT / name).read_bytes())
                if changed == gate.RECEIPT:
                    bad = dict(receipt, bound_files=[])
                    (root / changed).write_text(json.dumps(bad))
                else:
                    with (root / changed).open("ab") as output:
                        output.write(b" ")
                with self.assertRaises(ValueError):
                    gate.validate(root, env=ENV, now=NOW)

    def test_schedule_and_single_writer_match_appendix(self):
        config = json.loads((gate.ROOT / gate.CONFIG).read_text())
        workflow = (gate.ROOT / ".github/workflows" / config["workflow"]).read_text()
        self.assertEqual(workflow.count("cron:"), 1)
        self.assertIn('cron: "' + config["cron"] + '"', workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("timeout-minutes: 330", workflow)
        self.assertLess(workflow.index("python scripts/check_history_cadence_authority.py"),
                        workflow.index("R2_SECRET_ACCESS_KEY"))
        policy = json.loads((gate.ROOT / "config/github_automatic_research_operations_v0_2.json").read_text())
        history = next(row for row in policy["scheduled_workflows"]
                       if row["workflow"] == config["workflow"])
        self.assertEqual(history["cron_utc"], [config["cron"]])
