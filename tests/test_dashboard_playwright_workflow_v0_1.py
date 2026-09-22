from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "package.json"
LOCKFILE = ROOT / "package-lock.json"
CONFIG = ROOT / "playwright.config.cjs"
SPEC = ROOT / "tests/browser/dashboard.spec.cjs"
WORKFLOW = ROOT / ".github/workflows/dashboard-github-pages.yml"


class DashboardPlaywrightWorkflowTests(unittest.TestCase):
    def test_lockfile_only_changes_trigger_pr_and_main_browser_validation(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        push = text.split("  push:\n", 1)[1].split("  pull_request:\n", 1)[0]
        pull_request = text.split("  pull_request:\n", 1)[1].split("\npermissions:", 1)[0]
        for event, paths in (("push", push), ("pull_request", pull_request)):
            with self.subTest(event=event):
                self.assertIn('      - "package-lock.json"', paths)

    def test_playwright_dependency_and_runtime_are_pinned(self) -> None:
        package = json.loads(PACKAGE.read_text(encoding="utf-8"))
        self.assertTrue(package["private"])
        self.assertEqual(package["devDependencies"]["@playwright/test"], "1.63.0")

        lock = json.loads(LOCKFILE.read_text(encoding="utf-8"))
        self.assertEqual(lock["lockfileVersion"], 3)
        self.assertEqual(
            lock["packages"][""]["devDependencies"]["@playwright/test"],
            "1.63.0",
        )
        self.assertEqual(lock["packages"]["node_modules/@playwright/test"]["version"], "1.63.0")
        self.assertEqual(lock["packages"]["node_modules/playwright"]["version"], "1.63.0")
        self.assertEqual(lock["packages"]["node_modules/playwright-core"]["version"], "1.63.0")

        config = CONFIG.read_text(encoding="utf-8")
        self.assertIn("workers: 1", config)
        self.assertIn('screenshot: "only-on-failure"', config)
        self.assertIn('trace: "retain-on-failure"', config)
        self.assertIn('video: "off"', config)
        self.assertIn('name: "desktop-chromium"', config)
        self.assertIn('name: "mobile-chromium"', config)
        self.assertIn('browserName: "chromium"', config)

    def test_browser_spec_covers_primary_views_and_fail_closed_contracts(self) -> None:
        spec = SPEC.read_text(encoding="utf-8")
        for view in (
            "overview",
            "data-health",
            "signals",
            "strategy",
            "positions",
            "trades",
            "performance",
            "backtests",
            "gates",
        ):
            self.assertIn(f'["{view}",', spec)
        self.assertIn("狀態快照暫時無法讀取", spec)
        self.assertIn("較舊快照", spec)
        self.assertIn("cloud-run-links", spec)
        self.assertIn("paper-equity-chart", spec)
        self.assertIn("data/content-hash.txt", spec)
        self.assertIn("PLAYWRIGHT_EXPECTED_CONTENT_HASH", spec)
        self.assertIn('page.route("**/data/dashboard.json"', spec)
        self.assertIn('page.route("**/data/cloud-runs.json"', spec)
        self.assertIn('page.route("**/data/paper-training.json"', spec)
        self.assertIn("pageErrors", spec)
        self.assertIn("badResponses", spec)

    def test_pages_workflow_runs_pr_build_and_post_deploy_browser_checks(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("actions/setup-node@249970729cb0ef3589644e2896645e5dc5ba9c38", text)
        self.assertEqual(text.count("npm ci --ignore-scripts --no-audit --no-fund"), 2)
        self.assertNotIn("npm install --ignore-scripts --no-audit --no-fund --package-lock=false", text)
        self.assertIn("npx playwright install --with-deps chromium", text)
        self.assertIn("python -m http.server 4173 -d _site", text)
        self.assertIn("PLAYWRIGHT_BASE_URL: http://127.0.0.1:4173/", text)
        self.assertIn(
            "PLAYWRIGHT_EXPECTED_CONTENT_HASH: ${{ steps.content-hash.outputs.content_hash }}",
            text,
        )
        self.assertIn("content_hash: ${{ steps.content-hash.outputs.content_hash }}", text)
        self.assertIn('echo "content_hash=${local_hash}" >> "${GITHUB_OUTPUT}"', text)
        self.assertIn("workers=1", text)
        self.assertIn("retention-days: 7", text)
        self.assertIn("browser-production:", text)
        self.assertIn("needs: [build, deploy]", text)
        self.assertIn("page_url: ${{ steps.deployment.outputs.page_url }}", text)
        self.assertIn("PLAYWRIGHT_BASE_URL: ${{ needs.deploy.outputs.page_url }}", text)
        self.assertIn(
            "PLAYWRIGHT_EXPECTED_CONTENT_HASH: ${{ needs.build.outputs.content_hash }}",
            text,
        )

        for workflow_name in (
            "Binance USD-M Crypto Core 100 Training V0.1.2",
            "Pionex Alternative Assets Observability V0.2",
            "Research Signal Quality V0.1",
            "Live Paper Run Coordinator V0.1",
        ):
            self.assertIn(f'- "{workflow_name}"', text)

        self.assertNotIn(
            '- "Binance USD-M Crypto Core 100 History V0.1.2"',
            text,
        )
        self.assertNotIn('- "BTC Fixed Sample Simulation V0.1"', text)
        self.assertIn(
            "github.event.workflow_run.name == 'Research Signal Quality V0.1'",
            text,
        )
        self.assertNotIn(
            "github.event.workflow_run.name == 'BTC Fixed Sample Simulation V0.1'",
            text,
        )


if __name__ == "__main__":
    unittest.main()
