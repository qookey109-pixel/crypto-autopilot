import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    "cloud_run_status", Path(__file__).resolve().parents[1] / "scripts/build_cloud_run_status.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class CloudRunStatusTests(unittest.TestCase):
    def run_fixture(self, **updates):
        return {"id": 123, "head_branch": "main", "head_sha": "a" * 40,
                "path": ".github/workflows/example.yml", "event": "schedule",
                "head_repository": {"full_name": module.REPOSITORY},
                "status": "completed", "conclusion": "success", **updates}

    def test_success_does_not_mean_dataset_complete(self):
        result = module.project_run([self.run_fixture()], "example.yml")
        self.assertEqual(result["state"], "WORKFLOW_SUCCESS")
        self.assertIsNone(result["datasetComplete"])

    def test_fork_branch_pr_and_wrong_workflow_are_not_production_evidence(self):
        for update in [{"head_branch": "feature"}, {"event": "pull_request"},
                       {"head_repository": {"full_name": "fork/repo"}},
                       {"path": ".github/workflows/other.yml"}, {"head_sha": "invalid"}]:
            result = module.project_run([self.run_fixture(**update)], "example.yml")
            self.assertEqual(result["state"], "UNVERIFIED")

    def test_latest_failure_supersedes_old_success(self):
        result = module.project_run([self.run_fixture(), self.run_fixture(
            id=124, conclusion="failure")], "example.yml")
        self.assertEqual(result["state"], "WORKFLOW_FAILED")

    def test_network_failure_neither_leaks_exception_nor_claims_ready(self):
        calls = []
        def fetch(url):
            calls.append(url)
            raise RuntimeError("SECRET_RESPONSE")
        result = module.collect(fetch)
        self.assertEqual(len(calls), 6)
        self.assertFalse(result["simulationReady"])
        self.assertTrue(all(row["state"] == "UNVERIFIED" for row in result["runs"].values()))
        self.assertNotIn("SECRET_RESPONSE", str(result))
