from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "package.json"
CONFIG = ROOT / "playwright.config.cjs"
SPEC = ROOT / "tests/browser/dashboard.spec.cjs"
WORKFLOW = ROOT / ".github/workflows/dashboard-github-pages.yml"


class DashboardPlaywrightWorkflowTests(unittest.TestCase):
    def test_playwright_dependency_and_runtime_are_pinned(self) -> None:
        package = json.loads(PACKAGE.read_text(encoding="utf-8"))
        self.assertTrue(package["private"])
        self.assertEqual(package["devDependencies"]["@playwright/test"], "1.63.0")

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
        self.assertIn("npm install --ignore-scripts --no-audit --no-fund --package-lock=false", text)
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


if __name__ == "__main__":
    unittest.main()
