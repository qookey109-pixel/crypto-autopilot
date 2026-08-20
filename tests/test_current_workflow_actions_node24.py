from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

CURRENT = (
    "ci.yml",
    "provider-equivalence-v0-10-render-metadata-capture.yml",
    "validate-v0-11-metadata-stability-evaluator.yml",
    "provider-equivalence-v0-8-render-metadata-capture.yml",
    "validate-v0-7-render-metadata-capture-protocol.yml",
    "dashboard-authority-snapshot.yml",
    "dashboard-github-pages.yml",
    "dashboard-static-smoke.yml",
)


class CurrentWorkflowActionsNode24Tests(unittest.TestCase):
    def test_all_workflows_use_checkout_v6_with_nonpersistent_credentials(self) -> None:
        for path in sorted(WORKFLOWS.glob("*.yml")):
            with self.subTest(workflow=path.name):
                text = path.read_text(encoding="utf-8")
                checkout_lines = [
                    line.strip()
                    for line in text.splitlines()
                    if line.strip().startswith("- uses: actions/checkout@")
                ]
                if not checkout_lines:
                    continue
                self.assertTrue(
                    all(line == "- uses: actions/checkout@v6" for line in checkout_lines),
                    f"{path.name}: checkout actions must use v6: {checkout_lines}",
                )
                self.assertEqual(
                    text.count("persist-credentials: false"),
                    len(checkout_lines),
                    f"{path.name}: every checkout must explicitly avoid persisted git credentials",
                )

    def test_all_setup_python_users_are_on_v6(self) -> None:
        for path in sorted(WORKFLOWS.glob("*.yml")):
            with self.subTest(workflow=path.name):
                setup_lines = [
                    line.strip()
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if line.strip().startswith("- uses: actions/setup-python@")
                ]
                self.assertTrue(
                    all(line == "- uses: actions/setup-python@v6" for line in setup_lines),
                    f"{path.name}: setup-python actions must use v6: {setup_lines}",
                )

    def test_current_workflows_remain_in_global_node24_scope(self) -> None:
        for name in CURRENT:
            with self.subTest(workflow=name):
                text = (WORKFLOWS / name).read_text(encoding="utf-8")
                self.assertIn("uses: actions/checkout@v6", text)
                self.assertNotIn("actions/checkout@v4", text)
                self.assertNotIn("actions/setup-python@v5", text)

    def test_v0_10_capture_schedule_and_authority_markers_are_unchanged(self) -> None:
        text = (WORKFLOWS / "provider-equivalence-v0-10-render-metadata-capture.yml").read_text(
            encoding="utf-8"
        )
        self.assertEqual(text.count("uses: actions/checkout@v6"), 3)
        self.assertEqual(text.count("persist-credentials: false"), 3)
        self.assertIn('    - cron: "17,47 * 27-31 8 *"', text)
        self.assertIn('    - cron: "17,47 * 1-3 9 *"', text)
        self.assertIn('    - cron: "17,47 0-1 4 9 *"', text)
        self.assertIn("METADATA_RELAY_TOKEN: ${{ secrets.METADATA_RELAY_TOKEN }}", text)
        self.assertIn("--mode capture", text)
        self.assertIn("holdout_candles_accessed", text)
        self.assertIn("source_switch_authorized", text)
        self.assertIn("live_trading_authorized", text)

    def test_dashboard_static_smoke_name_no_longer_claims_d1_runtime(self) -> None:
        text = (WORKFLOWS / "dashboard-static-smoke.yml").read_text(encoding="utf-8")
        self.assertIn("name: Dashboard Static Smoke", text)
        self.assertNotIn("Dashboard D1 Static Smoke", text)


if __name__ == "__main__":
    unittest.main()
