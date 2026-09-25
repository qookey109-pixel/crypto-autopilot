from __future__ import annotations

import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from crypto_autopilot.research.cloud_maintenance import (
    BEGIN, END, HEALTH, MESSAGE, POLICY, PREFIX, RECEIPT, REPOSITORY, SCHEMA,
    TARGETS, GitHub, Stop, classify_checks, collect, digest, existing_record,
    project_documents, publish, render, validate_branch_documents,
    validate_contract, validate_trigger,
)

A, B = "a" * 40, "b" * 40
NOW = datetime(2026, 9, 25, tzinfo=timezone.utc)


def run(**updates):
    data = {"id": 10, "run_attempt": 1, "repository": {"full_name": REPOSITORY},
            "head_repository": {"full_name": REPOSITORY}, "head_branch": "main",
            "path": HEALTH, "event": "schedule", "status": "completed",
            "conclusion": "success", "head_sha": A,
            "created_at": "2026-09-24T23:57:00Z",
            "run_started_at": "2026-09-24T23:58:00Z"}
    return {**data, **updates}


def event():
    return {"action": "completed", "repository": {"full_name": REPOSITORY, "private": False},
            "workflow_run": run()}


def record():
    return {"schema": SCHEMA, "semantic": {
        "workflows": [{"workflow": HEALTH.split("/")[-1], "health": "HEALTHY",
                       "conclusion": "success", "registration": "active", "jobs": []}],
        "prs": [], "next_action": "CLOUD-01"},
        "evidence": {"main_sha": A, "workflows": {HEALTH.split("/")[-1]: run()},
                     "observed_at_utc": NOW.isoformat(), "coverage": [], "prs": {},
                     "source": run()}}


def documents():
    return {p: "human preface\n" + BEGIN + "\nPENDING_FIRST_CLOUD_OBSERVATION\n"
            + END + "\nhuman appendix\n" for p in TARGETS}


class PublishAPI:
    def __init__(self):
        self.docs = documents()
        self.head_docs = self.docs
        self.pr = None
        self.ref = None
        self.writes = []
        self.main_sha = A
        self.drift_after_commit = False
        self.files = list(TARGETS)
        self.commits = [{"author": {"login": "github-actions[bot]"},
                         "commit": {"message": MESSAGE}}]
        self.fail_pr = False
        self.closed_prs = []

    def main(self):
        return self.main_sha

    def file(self, path, ref):
        return self.docs[path] if ref == A else self.head_docs[path]

    def pages(self, path, key=None, params=None):
        if params.get("state") == "closed":
            return self.closed_prs
        return [self.pr] if self.pr else []

    def request(self, method, path, payload=None, **kwargs):
        if method != "GET":
            self.writes.append((method, path, payload))
        if path.startswith("/git/ref/"):
            return self.ref
        if path.startswith("/compare/"):
            return {"status": "ahead", "behind_by": 0, "merge_base_commit": {"sha": A},
                    "files": [{"filename": p} for p in self.files],
                    "total_commits": len(self.commits), "commits": self.commits}
        if method == "GET" and path.startswith("/git/commits/"):
            return {"tree": {"sha": A}}
        if path == "/git/trees":
            return {"sha": B}
        if path == "/git/commits":
            if self.drift_after_commit:
                self.main_sha = B
            return {"sha": B}
        if path == "/git/refs" or path.startswith("/git/refs/"):
            self.ref = {"object": {"sha": B}}
            return self.ref
        if path == "/pulls":
            if self.fail_pr:
                raise Stop("BLOCKED_PERMISSION")
            self.pr = {"number": 500, "draft": True,
                       "user": {"login": "github-actions[bot]"},
                       "head": {"ref": PREFIX + A[:12], "sha": B,
                                "repo": {"full_name": REPOSITORY}}}
            return self.pr
        raise AssertionError((method, path))


class PureMaintenanceTests(unittest.TestCase):
    def test_contract_and_receipt_exact_binding(self):
        config = json.loads(Path(POLICY).read_text())
        receipt = json.loads(Path(RECEIPT).read_text())
        validate_contract(config, receipt)
        for field in ("r2", "provider", "training", "local_user_files", "merge"):
            changed = copy.deepcopy(config)
            changed["authority"][field] = True
            with self.subTest(field=field), self.assertRaises(Stop):
                validate_contract(changed, receipt)
        changed = copy.deepcopy(receipt)
        changed["policy_contract"]["runtime"]["model_required"] = True
        with self.assertRaisesRegex(Stop, "RECEIPT"):
            validate_contract(config, changed)

    def test_natural_failed_health_is_valid_source(self):
        source = run(conclusion="failure")
        trigger = event()
        trigger["workflow_run"] = source
        validate_trigger(trigger, source, A)

    def test_reject_wrong_event_repo_branch_attempt_and_sha(self):
        changes = [{"event": "workflow_dispatch"}, {"event": "pull_request"},
                   {"head_branch": "evil"}, {"head_sha": B}, {"path": "evil.yml"},
                   {"repository": {"full_name": "other/repo"}},
                   {"head_repository": {"full_name": "other/repo"}},
                   {"status": "in_progress"}, {"run_attempt": 2}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(Stop):
                validate_trigger(event(), run(**change), A)

    def test_no_check_is_not_success_and_skips_remain_distinct(self):
        self.assertEqual(classify_checks([]), "UNKNOWN_NO_CHECKS")
        self.assertEqual(classify_checks([{"status": "waiting"}]),
                         "WAITING_CI_APPROVAL_OR_START")
        self.assertEqual(classify_checks([{"status": "queued"}]), "PENDING")
        self.assertEqual(classify_checks([{"status": "completed", "conclusion": "failure"}]),
                         "FAILURE")
        self.assertEqual(classify_checks([{"status": "completed", "conclusion": "skipped"}]),
                         "COMPLETED_WITH_SKIPS")

    def test_roundtrip_and_timestamp_run_id_only_dedupe(self):
        rec = record()
        first = project_documents(documents(), rec)
        self.assertEqual(existing_record(first[TARGETS[0]]), rec)
        later = copy.deepcopy(rec)
        later["evidence"]["observed_at_utc"] = "2026-09-26T00:00:00Z"
        later["evidence"]["source"]["id"] = 20
        later["evidence"]["main_sha"] = B
        self.assertEqual(project_documents(first, later), first)
        self.assertEqual(render(rec), render(rec))

    def test_real_failure_and_recovery_change_projection(self):
        first = project_documents(documents(), record())
        failed = record()
        failed["semantic"]["workflows"][0]["health"] = "FAILED"
        changed = project_documents(first, failed)
        self.assertNotEqual(changed, first)
        self.assertEqual(project_documents(changed, record()), first)

    def test_allowlist_and_frozen_paths(self):
        for path in ("AGENTS.md", ".github/workflows/ci.yml",
                     "config/provider_equivalence_v0_10_final_atomic_cutover_v0_1.json"):
            with self.subTest(path=path), self.assertRaisesRegex(Stop, "ALLOWLIST"):
                project_documents({**documents(), path: "unsafe"}, record())

    def test_manual_edit_inside_or_outside_generated_block(self):
        original = documents()
        head = project_documents(original, record())
        for text in (head[TARGETS[0]].replace("非執行權限", "human edit"),
                     head[TARGETS[0]].replace("human preface", "changed preface")):
            changed = {**head, TARGETS[0]: text}
            with self.assertRaises(Stop):
                validate_branch_documents(original, changed)
        validate_branch_documents(original, head)

    def test_duplicate_missing_markers_and_record_tampering(self):
        for value in ("no block", BEGIN + BEGIN + END, END + BEGIN):
            with self.subTest(value=value), self.assertRaises(Stop):
                existing_record(value)
        changed = render(record()).replace("CLOUD-01", "CLOUD-99")
        with self.assertRaises(Stop):
            existing_record(BEGIN + changed + END)

    def test_first_publication_is_draft_only_and_no_force(self):
        api = PublishAPI()
        result = publish(api, record())
        self.assertEqual(result["status"], "DRAFT_UPDATED")
        self.assertTrue(api.pr["draft"])
        self.assertEqual([p for _, p, _ in api.writes],
                         ["/git/trees", "/git/commits", "/git/refs", "/pulls"])
        written_paths = {e["path"] for e in api.writes[0][2]["tree"]}
        self.assertEqual(written_paths, set(TARGETS))

    def test_repeated_observation_does_not_commit(self):
        api = PublishAPI()
        publish(api, record())
        api.head_docs = project_documents(documents(), record())
        api.writes.clear()
        self.assertEqual(publish(api, record())["status"], "NO_CHANGE")
        self.assertEqual(api.writes, [])

    def test_missing_pr_permission_recovers_without_duplicate_commit(self):
        api = PublishAPI()
        api.fail_pr = True
        with self.assertRaisesRegex(Stop, "BLOCKED_PERMISSION"):
            publish(api, record())
        api.head_docs = project_documents(documents(), record())
        api.fail_pr = False
        api.writes.clear()
        self.assertEqual(publish(api, record())["status"], "DRAFT_RECOVERED")
        self.assertEqual([p for _, p, _ in api.writes], ["/pulls"])

    def test_closed_draft_is_not_silently_reopened(self):
        api = PublishAPI()
        publish(api, record())
        api.head_docs = project_documents(documents(), record())
        api.closed_prs = [api.pr]
        api.pr = None
        api.writes.clear()
        with self.assertRaisesRegex(Stop, "CLOSED_BRANCH_REVIEW_REQUIRED"):
            publish(api, record())
        self.assertEqual(api.writes, [])

    def test_closed_draft_cannot_be_reopened_implicitly(self):
        api = PublishAPI()
        publish(api, record())
        api.head_docs = project_documents(documents(), record())
        api.closed_prs = [api.pr]
        api.pr = None
        api.writes.clear()
        with self.assertRaisesRegex(Stop, "CLOSED_BRANCH_REVIEW_REQUIRED"):
            publish(api, record())
        self.assertEqual(api.writes, [])

    def test_main_race_before_ref_write_stops(self):
        api = PublishAPI()
        api.drift_after_commit = True
        with self.assertRaisesRegex(Stop, "MAIN_CHANGED"):
            publish(api, record())
        self.assertFalse(any(path.startswith("/git/refs") or path == "/pulls"
                             for _, path, _ in api.writes))

    def test_human_commit_and_outside_scope_are_rejected(self):
        for malicious in ("author", "path"):
            api = PublishAPI()
            publish(api, record())
            api.head_docs = project_documents(documents(), record())
            api.writes.clear()
            if malicious == "author":
                api.commits[0]["author"]["login"] = "human"
            else:
                api.files.append("src/trade.py")
            with self.assertRaises(Stop):
                publish(api, record())
            self.assertEqual(api.writes, [])

    def test_workflow_has_no_cron_dispatch_artifacts_or_untrusted_checkout(self):
        text = Path(".github/workflows/cloud-project-maintenance-v0-1.yml").read_text()
        self.assertIn('workflows: ["Research Automation Health V0.2"]', text)
        self.assertEqual(text.count("ref: ${{ github.sha }}"), 2)
        for forbidden in ("  schedule:", "workflow_dispatch:", "pull_request_target:",
                          "secrets.", "upload-artifact", "download-artifact", "self-hosted",
                          "ref: ${{ github.event.workflow_run.head_sha }}"):
            self.assertNotIn(forbidden, text)
        self.assertIn("persist-credentials: false", text)
        self.assertIn("checks: read", text)

    def test_read_adapter_cannot_write_or_escape_github(self):
        api = GitHub("synthetic-test-token")
        for method, path in (("POST", "/pulls"), ("GET", "https://evil.invalid"),
                             ("GET", "/../secrets")):
            with self.assertRaises(Stop):
                api.request(method, path)

    def test_pagination_complete_missing_duplicate_limit(self):
        api = GitHub("synthetic-test-token")
        full = [{"id": n} for n in range(100)]
        with patch.object(api, "request", side_effect=[
            {"total_count": 101, "workflow_runs": full},
            {"total_count": 101, "workflow_runs": [{"id": 100}]}]):
            self.assertEqual(len(api.pages("/runs", "workflow_runs")), 101)
        for replies in (
            [{"total_count": 2, "workflow_runs": [{"id": 1}]}],
            [{"total_count": 101, "workflow_runs": full},
             {"total_count": 101, "workflow_runs": [{"id": 1}]}],
            [{"total_count": 101, "workflow_runs": full},
             {"total_count": 102, "workflow_runs": [{"id": 100}]}],
        ):
            with patch.object(api, "request", side_effect=replies), self.assertRaises(Stop):
                api.pages("/runs", "workflow_runs")
        with patch.object(api, "request", return_value=full), self.assertRaises(Stop):
            api.pages("/pulls")

    def test_http_errors_are_sanitized(self):
        from urllib.error import HTTPError, URLError
        for error, code in ((403, "BLOCKED_PERMISSION"), (429, "UNKNOWN_RATE_LIMIT"),
                            (500, "UNKNOWN_HTTP")):
            opener = unittest.mock.Mock()
            opener.open.side_effect = HTTPError("https://api.github.com", error,
                                                "secret-response", {}, None)
            with patch("crypto_autopilot.research.cloud_maintenance.build_opener",
                       return_value=opener):
                with self.assertRaisesRegex(Stop, code):
                    GitHub("synthetic-test-token").request("GET", "/pulls")
        opener.open.side_effect = URLError("do-not-print")
        with patch("crypto_autopilot.research.cloud_maintenance.build_opener",
                   return_value=opener), self.assertRaisesRegex(Stop, "TRANSPORT"):
            GitHub("synthetic-test-token").request("GET", "/pulls")


class CollectAPI:
    def __init__(self):
        self.coverage = []
        self.latest = run()
        self.state = "active"
        self.fail_pages = False
        self.now = NOW

    def main(self):
        return A

    def file(self, path, ref):
        if path in (POLICY, RECEIPT):
            return Path(path).read_text()
        if path == HEALTH:
            return '  schedule:\n  --config config/research_automation_health_v0_2.json'
        if path == "research/status/current-operations-v0-3.json":
            return '{"gates":{"source_switch_authorized":false}}'
        return json.dumps({"schema": "research-automation-health-v0.2", "workflows": [{
            "workflow": HEALTH.split("/")[-1], "label": "Health", "mode": "bounded",
            "active_from_utc": "2026-09-01T00:00:00Z",
            "active_until_utc": "2026-10-01T00:00:00Z",
            "max_age_seconds": 14400, "allowed_events": ["schedule"],
            "allowed_conclusions": ["success"]}]})

    def request(self, method, path, payload=None, **kwargs):
        if path == "/actions/runs/10":
            return run()
        if path.startswith("/git/trees/"):
            return {"truncated": False, "tree": [{"path": HEALTH}] +
                    [{"path": p, "mode": "100644"} for p in TARGETS]}
        if path.startswith("/actions/workflows/"):
            return {"state": self.state}
        if path.startswith("/pulls/"):
            return {"number": int(path.split("/")[-1]), "state": "open",
                    "draft": False, "merged": False,
                    "head": {"sha": B}, "base": {"sha": A}}
        raise AssertionError(path)

    def pages(self, path, key=None, params=None):
        if self.fail_pages:
            raise Stop("UNKNOWN_MISSING_PAGE")
        if path == "/pulls":
            return [{"number": 999, "head": {"ref": PREFIX + A[:12]}}]
        if path.startswith("/commits/"):
            return [{"id": 1, "name": "test", "status": "completed", "conclusion": "success"}]
        return [self.latest]


class CollectionTests(unittest.TestCase):
    def test_normal_failure_pending_skipped_stale_expired(self):
        api = CollectAPI()
        for updates, expected in (({}, "HEALTHY"), ({"conclusion": "failure"}, "FAILED"),
                                  ({"status": "queued", "conclusion": None}, "IN_PROGRESS"),
                                  ({"conclusion": "skipped"}, "FAILED"),
                                  ({"run_started_at": "2026-09-20T00:00:00Z"}, "STALE")):
            api.latest = run(**updates)
            result = collect(api, event(), A, NOW)
            self.assertEqual(result["semantic"]["workflows"][0]["health"], expected)
            self.assertEqual([p["number"] for p in result["semantic"]["prs"]], [496, 497])
        expired = collect(api, event(), A, datetime(2026, 10, 2, tzinfo=timezone.utc))
        self.assertEqual(expired["semantic"]["workflows"][0]["health"], "EXPECTED_STOP")
        api.state = "disabled_manually"
        active = collect(api, event(), A, NOW)
        self.assertEqual(active["semantic"]["workflows"][0]["health"], "DISABLED")

    def test_missing_source_or_page_never_becomes_healthy(self):
        api = CollectAPI()
        api.fail_pages = True
        with self.assertRaisesRegex(Stop, "MISSING_PAGE"):
            collect(api, event(), A, NOW)
        api.fail_pages = False
        api.latest = run(event="push")
        with self.assertRaisesRegex(Stop, "LINEAGE"):
            collect(api, event(), A, NOW)
        with self.assertRaisesRegex(Stop, "MAIN_CHANGED"):
            collect(api, event(), B, NOW)

    def test_semantic_digest_ignores_evidence_timestamp(self):
        api = CollectAPI()
        a = collect(api, event(), A, NOW)
        b = collect(api, event(), A, NOW.replace(minute=1))
        self.assertEqual(digest(a["semantic"]), digest(b["semantic"]))
        self.assertNotEqual(a["evidence"], b["evidence"])


if __name__ == "__main__":
    unittest.main()
