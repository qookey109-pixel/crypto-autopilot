from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/dashboard-github-pages.yml"
SCRIPT = ROOT / "scripts/check_dashboard_deploy_freshness.py"
SPEC = importlib.util.spec_from_file_location("dashboard_deploy_freshness", SCRIPT)
assert SPEC and SPEC.loader
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class DashboardPagesQueueGuardTests(unittest.TestCase):
    def test_schedule_and_event_runs_queue_without_cancelling_each_other(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        workflow_concurrency = text.split("\nconcurrency:\n", 1)[1].split("\njobs:\n", 1)[0]
        self.assertIn("|| 'production'", workflow_concurrency)
        self.assertIn("queue: max", workflow_concurrency)
        self.assertIn("cancel-in-progress: false", workflow_concurrency)
        self.assertNotIn("github.event_name == 'schedule'", workflow_concurrency)
        self.assertIn('cron: "43 4 * * *"', text)
        for trigger in ("  workflow_run:", "  push:", "  workflow_dispatch:"):
            with self.subTest(trigger=trigger):
                self.assertIn(trigger, text)

    def test_one_production_group_covers_build_deploy_and_browser_check(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(text.count("\nconcurrency:\n"), 1)
        self.assertIn("  build:\n", text)
        self.assertIn("  deploy:\n", text)
        self.assertIn("  browser-production:\n", text)
        self.assertIn("steps.freshness.outputs.deploy_required == 'true'", text)
        self.assertIn("if: needs.deploy.outputs.deployed == 'true'", text)
        self.assertIn("--expected-sha", text)
        self.assertIn("--content-hash", text)

    def test_queued_old_main_never_deploys(self) -> None:
        self.assertEqual(
            guard.deployment_decision(
                expected_sha="a" * 40,
                current_main_sha="b" * 40,
                content_hash="c" * 64,
                published_hash="",
            ),
            "STALE_MAIN",
        )

    def test_current_main_deploys_only_changed_content(self) -> None:
        for published_hash, expected in (("c" * 64, "UNCHANGED_CONTENT"), ("d" * 64, "DEPLOY")):
            with self.subTest(expected=expected):
                self.assertEqual(
                    guard.deployment_decision(
                        expected_sha="a" * 40,
                        current_main_sha="a" * 40,
                        content_hash="c" * 64,
                        published_hash=published_hash,
                    ),
                    expected,
                )

    def test_invalid_identity_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid main commit SHA"):
            guard.deployment_decision(
                expected_sha="bad",
                current_main_sha="a" * 40,
                content_hash="c" * 64,
                published_hash="",
            )
        with self.assertRaisesRegex(ValueError, "invalid dashboard content hash"):
            guard.deployment_decision(
                expected_sha="a" * 40,
                current_main_sha="a" * 40,
                content_hash="bad",
                published_hash="",
            )

    def test_published_hash_404_allows_initial_deploy_but_other_errors_fail(self) -> None:
        with patch.object(guard, "urlopen", side_effect=HTTPError("url", 404, "missing", {}, None)):
            self.assertEqual(guard.read_published_hash(), "")
        with patch.object(guard, "urlopen", side_effect=HTTPError("url", 503, "unavailable", {}, None)):
            with self.assertRaises(HTTPError):
                guard.read_published_hash()


if __name__ == "__main__":
    unittest.main()
