from datetime import datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import unittest
from urllib.request import Request
import zipfile

from test_simulation_funding_v0_1 import encoded_kline_sample, funding_report

SPEC = importlib.util.spec_from_file_location(
    "btc_execution", Path(__file__).resolve().parents[1] / "scripts/run_simulation_btc_v0_1.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class BtcExecutionTests(unittest.TestCase):
    def setUp(self):
        self.config, self.receipt = module.load_authority()
        self.env = {"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": module.REPOSITORY,
                    "GITHUB_REF": "refs/heads/main", "GITHUB_RUN_ATTEMPT": "1",
                    "GITHUB_EVENT_NAME": "workflow_run", "GITHUB_SHA": "a" * 40,
                    "GITHUB_RUN_NUMBER": "1", "GITHUB_RUN_ID": "123"}
        self.event = {"workflow_run": {"name": "CI", "event": "push",
                      "status": "completed", "conclusion": "success", "head_branch": "main",
                      "head_repository": {"full_name": module.REPOSITORY}, "head_sha": "a" * 40}}
        self.now = datetime(2026, 9, 12, tzinfo=timezone.utc)

    def test_context_requires_fresh_current_main_ci_within_budget_and_window(self):
        module.require_context(self.config, self.env, self.event, self.now)
        for key, value in [("GITHUB_RUN_ATTEMPT", "2"), ("GITHUB_RUN_NUMBER", "21"),
                           ("GITHUB_REF", "refs/heads/feature"), ("GITHUB_SHA", "b" * 40)]:
            with self.assertRaises(ValueError):
                module.require_context(self.config, {**self.env, key: value}, self.event, self.now)
        with self.assertRaises(ValueError):
            module.require_context(self.config, self.env, self.event,
                                   datetime(2026, 9, 16, tzinfo=timezone.utc))
        self.event["workflow_run"]["event"] = "pull_request"
        with self.assertRaises(ValueError):
            module.require_context(self.config, self.env, self.event, self.now)

    def test_funding_archive_hash_and_run_identity_are_verified(self):
        report = funding_report()
        report["observations"] = report["observations"][::32]
        report["observation_count"] = len(report["observations"])
        report["last_time_ms"] = report["observations"][-1]["funding_time_ms"]
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("report.json", json.dumps(report))
        payload = stream.getvalue()
        config = {**self.config, "funding_zip_sha256": module.digest(payload),
                  "funding_run_id": report["run_id"]}
        self.assertEqual(module.funding_from_zip(payload, config), report)
        with self.assertRaises(ValueError):
            module.funding_from_zip(payload + b"changed", config)
        with self.assertRaises(ValueError):
            module.funding_from_zip(payload, {**config, "funding_run_id": "wrong"})

    def test_redirect_drops_token_and_rejects_plain_http(self):
        redirect = module.ArtifactRedirect()
        request = Request("https://api.github.com/archive", headers={"Authorization": "Bearer TEST"})
        result = redirect.redirect_request(request, None, 302, "", {}, "https://storage.example/archive")
        self.assertIsNone(result.get_header("Authorization"))
        with self.assertRaises(ValueError):
            redirect.redirect_request(request, None, 302, "", {}, "http://storage.example/archive")

    def test_exact_three_reads_then_canonical_simulation_never_claims_full_universe(self):
        payloads, receipt = encoded_kline_sample()
        by_key = {row["key"]: payloads[row["interval"]] for row in receipt["intervals"]}
        calls = []
        def read(key, size):
            calls.append(key)
            return by_key[key]
        result = module.simulate(self.config, receipt, funding_report(), read)
        self.assertEqual(len(calls), 3)
        self.assertEqual(result["status"], "READY")
        self.assertFalse(result["full_universe_ready"])
        self.assertGreater(result["executed_trade_count"], 0)
        self.assertNotIn("production_simulation_data_admission_not_authorized", result["blockers"])

    def test_corrupt_sample_stops_before_later_objects(self):
        calls = []
        def read(key, size):
            calls.append(key)
            return b"wrong"
        with self.assertRaises(ValueError):
            module.simulate(self.config, self.receipt, funding_report(), read)
        self.assertEqual(len(calls), 1)
