import importlib.util
from datetime import datetime, timezone
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "cloud_run_status", ROOT / "scripts/build_cloud_run_status.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class CloudRunStatusTests(unittest.TestCase):
    def run_fixture(self, **updates):
        base = {
            "id": 123,
            "head_branch": "main",
            "head_sha": "a" * 40,
            "path": ".github/workflows/example.yml",
            "event": "schedule",
            "head_repository": {"full_name": module.REPOSITORY},
            "status": "completed",
            "conclusion": "success",
            "run_started_at": "2026-09-21T04:00:00Z",
            "created_at": "2026-09-21T03:59:00Z",
        }
        base.update(updates)
        return base

    def test_success_is_execution_only_not_business_result(self):
        result = module.project_run([self.run_fixture()], "example.yml")
        self.assertEqual(result["state"], "WORKFLOW_SUCCESS")
        self.assertEqual(result["runId"], 123)
        self.assertEqual(result["headSha"], "a" * 40)
        self.assertEqual(result["evidenceTimeUtc"], "2026-09-21T04:00:00Z")
        self.assertNotIn("datasetComplete", result)

    def test_only_main_schedule_run_counts_as_automatic_evidence(self):
        invalid = [
            {"head_branch": "feature"},
            {"event": "workflow_dispatch"},
            {"event": "pull_request"},
            {"head_repository": {"full_name": "fork/repo"}},
            {"path": ".github/workflows/other.yml"},
            {"head_sha": "invalid"},
        ]
        for update in invalid:
            result = module.project_run([self.run_fixture(**update)], "example.yml")
            self.assertEqual(result["state"], "UNVERIFIED")
            self.assertIsNone(result["runId"])

    def test_latest_failure_supersedes_old_success(self):
        result = module.project_run([
            self.run_fixture(),
            self.run_fixture(id=124, conclusion="failure"),
        ], "example.yml")
        self.assertEqual(result["state"], "WORKFLOW_FAILED")
        self.assertEqual(result["runId"], 124)

    def test_monitor_definitions_match_v0_5_health_and_effective_split(self):
        definitions = module.load_monitor_definitions()
        self.assertEqual(len(definitions), 8)
        self.assertEqual(
            sum(row["lifecycleState"] == "CURRENT_EFFECTIVE" for row in definitions),
            7,
        )
        expired = [
            row for row in definitions
            if row["lifecycleState"] == "EXPIRED_BOUNDED_FROZEN_CRON_DECLARATION"
        ]
        self.assertEqual(len(expired), 1)
        self.assertEqual(
            expired[0]["workflow"],
            "provider-equivalence-v0-12-successor-metadata-capture.yml",
        )
        self.assertEqual(expired[0]["authorityState"], "HISTORICAL_WINDOW_ENDED")

    def test_collect_separates_execution_freshness_and_business_result(self):
        now = datetime(2026, 9, 21, 5, 0, tzinfo=timezone.utc)

        def fetch(url):
            workflow = url.split("/actions/workflows/", 1)[1].split("/runs", 1)[0]
            return {
                "workflow_runs": [
                    self.run_fixture(
                        id=200,
                        path=f".github/workflows/{workflow}",
                        run_started_at="2026-09-21T04:30:00Z",
                    )
                ]
            }

        result = module.collect(fetch, now=now)
        self.assertEqual(result["schema"], "qookey-cloud-run-status-v0.2")
        self.assertFalse(result["authority"])
        self.assertEqual(result["mode"], "GITHUB_ACTIONS_METADATA_ONLY")
        self.assertEqual(result["summary"]["repositoryCronDeclarationCount"], 8)
        self.assertEqual(result["summary"]["monitoredCronDeclarationCount"], 8)
        self.assertEqual(result["summary"]["currentEffectiveScheduleCount"], 7)
        self.assertEqual(result["summary"]["expiredFrozenCronDeclarationCount"], 1)
        self.assertEqual(len(result["items"]), 8)
        current = next(
            row for row in result["items"]
            if row["lifecycleState"] == "CURRENT_EFFECTIVE"
        )
        self.assertEqual(current["latestAutomaticRun"]["state"], "WORKFLOW_SUCCESS")
        self.assertEqual(current["freshnessState"], "FRESH")
        self.assertEqual(
            current["businessResult"]["status"],
            "UNKNOWN_FROM_GITHUB_RUN_METADATA",
        )
        expired = next(
            row for row in result["items"]
            if row["lifecycleState"] == "EXPIRED_BOUNDED_FROZEN_CRON_DECLARATION"
        )
        self.assertEqual(expired["freshnessState"], "EXPIRED_WINDOW")
        self.assertTrue(all(value is False for value in result["safetyBoundary"].values()))

    def test_network_failure_is_secret_free_and_does_not_preserve_success(self):
        calls = []

        def fetch(url):
            calls.append(url)
            raise RuntimeError("SECRET_RESPONSE")

        result = module.collect(
            fetch,
            now=datetime(2026, 9, 21, 5, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(len(calls), 8)
        self.assertTrue(all(
            row["latestAutomaticRun"]["state"] == "QUERY_FAILED"
            for row in result["items"]
        ))
        self.assertNotIn("SECRET_RESPONSE", str(result))
        self.assertEqual(
            next(
                row for row in result["items"]
                if row["workflow"] == "resource-hub-supply-chain-v0-2.yml"
            )["freshnessState"],
            "QUERY_FAILED",
        )

    def test_active_until_marks_current_schedule_expired(self):
        definition = {
            "lifecycleState": "CURRENT_EFFECTIVE",
            "maxAgeSeconds": 7200,
            "activeFromUtc": "2026-09-20T00:00:00Z",
            "activeUntilUtc": "2026-09-21T04:30:00Z",
        }
        latest = {
            "state": "WORKFLOW_SUCCESS",
            "evidenceTimeUtc": "2026-09-21T04:20:00Z",
        }
        self.assertEqual(
            module.freshness_state(
                definition,
                latest,
                now=datetime(2026, 9, 21, 5, 0, tzinfo=timezone.utc),
            ),
            "EXPIRED_WINDOW",
        )

    def test_running_schedule_becomes_stalled_after_max_age(self):
        definition = {
            "lifecycleState": "CURRENT_EFFECTIVE",
            "maxAgeSeconds": 1800,
            "activeFromUtc": "2026-09-20T00:00:00Z",
            "activeUntilUtc": None,
        }
        latest = {
            "state": "RUNNING",
            "evidenceTimeUtc": "2026-09-21T04:00:00Z",
        }
        self.assertEqual(
            module.freshness_state(
                definition,
                latest,
                now=datetime(2026, 9, 21, 5, 0, tzinfo=timezone.utc),
            ),
            "STALLED",
        )

    def test_completed_btc_workflow_remains_retired_and_not_in_monitor_inventory(self):
        workflow = (ROOT / ".github/workflows/simulation-btc-v0-1.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("BTC Fixed Sample Simulation V0.1 — RETIRED", workflow)
        self.assertIn("pull_request:", workflow)
        self.assertNotIn("workflow_run:", workflow)
        self.assertNotIn(
            "simulation-btc-v0-1.yml",
            {row["workflow"] for row in module.load_monitor_definitions()},
        )


if __name__ == "__main__":
    unittest.main()
