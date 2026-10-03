from __future__ import annotations

import base64
import copy
import json
import sqlite3
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.prepaid_query_controller_v0_1 import (
    CONFIG_PATH,
    AllocationEvidence,
    GitHubJSONClient,
    GitHubResponse,
    PoolAuthority,
    PrepaidQueryMeter,
    claim_and_reserve_shared_writer_envelope,
    claim_prepaid_query_meter,
)
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import (
    SharedWriterReservation,
    reserve_shared_writer_envelope,
)

ROOT = Path(__file__).parents[1]
NOW_MS = int(datetime(2026, 10, 3, 2, 20, tzinfo=UTC).timestamp() * 1000)
SHA = "a" * 40
SLOT = f"slot:{NOW_MS}"
PREFIX = "/repos/qookey109-pixel/crypto-autopilot"


def authority_fixture() -> dict[str, object]:
    return {
        "schema": "qookey-cloudflare-prepaid-query-controller-v0.1",
        "activation_enabled": True,
        "github_claims_authorized": True,
        "account_allocation_verified": True,
        "scope_id": "synthetic-epoch-1",
        "repository": "qookey109-pixel/crypto-autopilot",
        "starts_on": "2026-10-03",
        "ends_on": "2026-10-04",
        "ruleset_id": 101,
        "max_evidence_age_ms": 60000,
        "max_run_age_ms": 600000,
        "statement_costs": {
            "RESERVATION": {"queries": 1, "rows_read": 10, "rows_written": 7, "storage_bytes": 100},
            "REPLAY_READ": {"queries": 1, "rows_read": 3, "rows_written": 0, "storage_bytes": 0},
        },
        "writers": [
            {
                "writer_id": "project-a:writer", "alias": "project-a",
                "workflow_id": 7, "workflow_path": ".github/workflows/synthetic-a.yml",
                "daily_tickets": 2, "queries_per_ticket": 2,
            },
            {
                "writer_id": "project-b:writer", "alias": "project-b",
                "workflow_id": 8, "workflow_path": ".github/workflows/synthetic-b.yml",
                "daily_tickets": 2, "queries_per_ticket": 2,
            },
        ],
    }


class FakeGitHub:
    """Shared remote-reference fixture. A new caller cannot reset its claims."""

    def __init__(self, authority: dict[str, object]) -> None:
        self.authority = copy.deepcopy(authority)
        self.refs: dict[str, dict[str, object]] = {}
        self.calls: list[tuple[str, str]] = []
        self.lock = threading.Lock()
        self.lose_post_response = False
        self.bad_readback = False
        self.main_moved = False
        self.ruleset = {
            "target": "tag", "enforcement": "active", "bypass_actors": [],
            "conditions": {"ref_name": {
                "include": ["refs/tags/cloud-budget-query-v0-1/synthetic-epoch-1/**"],
                "exclude": [],
            }},
            "rules": [{"type": "update"}, {"type": "deletion"}],
        }
        self.runs = {
            101: self.run(101, 1, 7, "a"),
            102: self.run(102, 2, 7, "a"),
            103: self.run(103, 3, 7, "a"),
            201: self.run(201, 1, 8, "b"),
        }

    @staticmethod
    def run(run_id: int, number: int, workflow: int, suffix: str) -> dict[str, object]:
        return {
            "id": run_id, "run_number": number, "workflow_id": workflow,
            "path": f".github/workflows/synthetic-{suffix}.yml",
            "head_sha": SHA, "head_branch": "main", "event": "schedule",
            "status": "in_progress", "run_attempt": 1,
            "run_started_at": "2026-10-03T02:20:00Z",
            "created_at": "2026-10-03T02:19:50Z",
        }

    def __call__(
        self, method: str, path: str, body: dict[str, object] | None = None,
    ) -> GitHubResponse:
        with self.lock:
            self.calls.append((method, path))
            subpath = path.removeprefix(PREFIX)
            if subpath == "/git/ref/heads/main":
                return GitHubResponse(200, {"object": {"sha": "b" * 40 if self.main_moved and self.refs else SHA}})
            if subpath.startswith("/contents/"):
                return GitHubResponse(200, {
                    "encoding": "base64",
                    "content": base64.b64encode(json.dumps(self.authority).encode()).decode(),
                })
            if subpath.startswith("/actions/runs/"):
                return GitHubResponse(200, copy.deepcopy(self.runs[int(subpath.rsplit("/", 1)[1])]))
            if subpath == "/rulesets/101":
                return GitHubResponse(200, copy.deepcopy(self.ruleset))
            if method == "POST" and subpath == "/git/refs":
                assert body is not None
                ref = str(body["ref"])
                if ref in self.refs:
                    return GitHubResponse(422, {})
                result = {"ref": ref, "object": {"sha": body["sha"], "type": "commit"}}
                self.refs[ref] = result
                if self.lose_post_response:
                    raise TimeoutError("synthetic response lost after remote commit")
                return GitHubResponse(201, copy.deepcopy(result))
            if subpath.startswith("/git/ref/tags/"):
                ref = "refs/" + subpath.removeprefix("/git/ref/")
                if self.bad_readback:
                    return GitHubResponse(200, {"ref": ref, "object": {"sha": "c" * 40, "type": "commit"}})
                return GitHubResponse(200, copy.deepcopy(self.refs[ref]))
            raise AssertionError("unexpected synthetic GitHub endpoint")


@dataclass(frozen=True)
class Result:
    rows: tuple[dict[str, object], ...]


class PrepaidControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.authority = authority_fixture()
        self.github = FakeGitHub(self.authority)
        self.now = NOW_MS
        self.evidence = AllocationEvidence(
            account_coverage_complete=True, zero_cost_verified=True,
            observed_at_ms=NOW_MS, measured_through_ms=NOW_MS,
            available={"queries": 100, "rows_read": 1000, "rows_written": 1000, "storage_bytes": 10000},
        )

    def claim(self, *, run_id: int = 101, writer_id: str = "project-a:writer") -> PrepaidQueryMeter:
        return claim_prepaid_query_meter(
            authority_document=self.authority, writer_id=writer_id, slot_id=SLOT,
            run_id=run_id, transport=self.github, evidence=self.evidence,
            clock_ms=lambda: self.now,
        )

    def charge(self, meter: PrepaidQueryMeter) -> None:
        meter.charge_before_query(writer_id="project-a:writer", slot_id=SLOT, operation="RESERVATION")

    def test_success_claims_reads_back_then_allows_exactly_prepaid_queries(self) -> None:
        meter = self.claim()
        self.assertEqual(len(self.github.calls), 8)
        self.assertEqual(sum(method == "POST" for method, _ in self.github.calls), 1)
        self.charge(meter)
        self.charge(meter)
        with self.assertRaisesRegex(BudgetBlocked, "QUERY_POOL_EXHAUSTED"):
            self.charge(meter)
        self.assertEqual(meter.report()["query_attempts_charged"], 2)
        self.assertEqual(meter.report()["ticket_envelope_charged_in_full"],
                         {"queries": 2, "rows_read": 20, "rows_written": 14, "storage_bytes": 200})

    def test_fresh_process_cannot_reclaim_even_unused_ticket(self) -> None:
        self.claim()
        with self.assertRaisesRegex(BudgetBlocked, "GITHUB_RESULT_UNVERIFIED"):
            self.claim()
        self.assertEqual(len(self.github.refs), 1)

    def test_daily_ring_does_not_search_another_ticket_or_replenish(self) -> None:
        self.claim(run_id=101)
        self.claim(run_id=102)
        with self.assertRaisesRegex(BudgetBlocked, "GITHUB_RESULT_UNVERIFIED"):
            self.claim(run_id=103)
        self.assertEqual(len(self.github.refs), 2)

    def test_lost_post_response_retains_charge_and_restart_blocks(self) -> None:
        self.github.lose_post_response = True
        with self.assertRaisesRegex(BudgetBlocked, "GITHUB_TRANSPORT_UNVERIFIED"):
            self.claim()
        self.assertEqual(len(self.github.refs), 1)
        self.github.lose_post_response = False
        with self.assertRaisesRegex(BudgetBlocked, "GITHUB_RESULT_UNVERIFIED"):
            self.claim()

    def test_readback_failure_and_changed_main_do_not_release_claim(self) -> None:
        for field, reason in (("bad_readback", "CLAIM_READBACK"), ("main_moved", "MAIN_CHANGED")):
            with self.subTest(field=field):
                self.github = FakeGitHub(self.authority)
                setattr(self.github, field, True)
                with self.assertRaisesRegex(BudgetBlocked, reason):
                    self.claim()
                self.assertEqual(len(self.github.refs), 1)

    def test_two_concurrent_claimants_only_one_gets_a_meter(self) -> None:
        def attempt() -> str:
            try:
                self.claim()
                return "CLAIMED"
            except BudgetBlocked:
                return "BLOCKED"

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(lambda _: attempt(), range(2)))
        self.assertCountEqual(outcomes, ["CLAIMED", "BLOCKED"])
        self.assertEqual(len(self.github.refs), 1)

    def test_same_meter_concurrent_debits_cannot_exceed_ticket(self) -> None:
        meter = self.claim()

        def attempt() -> str:
            try:
                self.charge(meter)
                return "CHARGED"
            except BudgetBlocked:
                return "BLOCKED"

        with ThreadPoolExecutor(max_workers=8) as executor:
            outcomes = list(executor.map(lambda _: attempt(), range(8)))
        self.assertEqual(outcomes.count("CHARGED"), 2)

    def test_distinct_writers_have_disjoint_prepaid_tickets_and_shared_cap(self) -> None:
        self.claim()
        self.claim(run_id=201, writer_id="project-b:writer")
        self.assertEqual(len(self.github.refs), 2)
        self.assertEqual(PoolAuthority.parse(self.authority).daily_envelope(),
                         {"queries": 8, "rows_read": 80, "rows_written": 56, "storage_bytes": 800})

    def test_every_dimension_and_entire_scope_storage_must_fit_headroom(self) -> None:
        for metric, limit in (("queries", 7), ("rows_read", 79), ("rows_written", 55), ("storage_bytes", 1599)):
            with self.subTest(metric=metric):
                self.evidence = replace(self.evidence, available={**self.evidence.available, metric: limit})
                with self.assertRaisesRegex(BudgetBlocked, "ACCOUNT_ALLOCATION_EXCEEDED"):
                    self.claim()
                self.assertEqual(self.github.calls, [])
                self.setUp()

    def test_default_merged_config_cannot_make_any_github_claim(self) -> None:
        self.authority = json.loads((ROOT / CONFIG_PATH).read_text())
        with self.assertRaisesRegex(BudgetBlocked, "CONTROLLER_DISABLED"):
            self.claim()
        self.assertEqual(self.github.calls, [])

    def test_unregistered_writer_or_rerun_branch_sha_workflow_event_block(self) -> None:
        with self.assertRaisesRegex(BudgetBlocked, "WRITER_UNREGISTERED"):
            self.claim(writer_id="unknown:writer")
        for field, value in (
            ("run_attempt", 2), ("head_branch", "feature"), ("head_sha", "d" * 40),
            ("workflow_id", 9), ("path", ".github/workflows/other.yml"),
            ("event", "pull_request"), ("status", "completed"), ("id", 999),
        ):
            with self.subTest(field=field):
                self.github = FakeGitHub(self.authority)
                self.github.runs[101][field] = value
                with self.assertRaisesRegex(BudgetBlocked, "RUN_UNVERIFIED"):
                    self.claim()
                self.assertEqual(len(self.github.refs), 0)

    def test_inactive_bypass_missing_rule_or_bad_scope_protection_blocks_claim(self) -> None:
        for field, value in (
            ("enforcement", "evaluate"), ("bypass_actors", [{"actor_id": 1}]),
            ("target", "branch"), ("rules", [{"type": "deletion"}]),
            ("conditions", {"ref_name": {"include": ["refs/tags/**"], "exclude": []}}),
        ):
            with self.subTest(field=field):
                self.github = FakeGitHub(self.authority)
                self.github.ruleset[field] = value
                with self.assertRaisesRegex(BudgetBlocked, "CLAIM_PROTECTION_UNVERIFIED"):
                    self.claim()
                self.assertEqual(len(self.github.refs), 0)

    def test_authority_mismatch_blocks_before_claim(self) -> None:
        self.github.authority["scope_id"] = "different-scope"
        with self.assertRaisesRegex(BudgetBlocked, "AUTHORITY_NOT_CURRENT_MAIN"):
            self.claim()
        self.assertEqual(len(self.github.refs), 0)

    def test_stale_missing_incomplete_or_nonzero_cost_evidence_blocks(self) -> None:
        for changes in (
            {"account_coverage_complete": False}, {"zero_cost_verified": False},
            {"observed_at_ms": NOW_MS - 60001}, {"measured_through_ms": NOW_MS - 60001},
            {"measured_through_ms": NOW_MS + 1},
        ):
            with self.subTest(changes=changes):
                self.evidence = replace(self.evidence, **changes)
                with self.assertRaises(BudgetBlocked):
                    self.claim()
                self.assertEqual(self.github.calls, [])
                self.setUp()

    def test_scope_expired_and_delayed_run_block(self) -> None:
        self.authority["ends_on"] = "2026-10-02"
        with self.assertRaises(BudgetBlocked):
            self.claim()
        self.setUp()
        self.github.runs[101]["created_at"] = "2026-10-03T01:00:00Z"
        with self.assertRaisesRegex(BudgetBlocked, "RUN_STALE"):
            self.claim()
        self.assertEqual(len(self.github.refs), 0)

    def test_ticket_day_and_evidence_expiry_stop_before_query(self) -> None:
        for advance, reason in ((60001, "ACCOUNT_EVIDENCE_STALE"), (86400000, "TICKET_EXPIRED")):
            with self.subTest(advance=advance):
                self.setUp()
                meter = self.claim()
                self.now += advance
                with self.assertRaisesRegex(BudgetBlocked, reason):
                    self.charge(meter)
                self.assertEqual(meter.report()["query_attempts_charged"], 0)

    def test_old_slot_replay_is_charged_to_current_meter_day(self) -> None:
        old_slot = f"slot:{NOW_MS - 86400000}"
        meter = claim_prepaid_query_meter(
            authority_document=self.authority, writer_id="project-a:writer", slot_id=old_slot,
            run_id=101, transport=self.github, evidence=self.evidence, clock_ms=lambda: self.now,
        )
        meter.charge_before_query(writer_id="project-a:writer", slot_id=old_slot, operation="REPLAY_READ")
        self.assertEqual(meter.report()["utc_day"], "2026-10-03")

    def test_identity_mismatch_does_not_consume_query_and_direct_meter_creation_blocks(self) -> None:
        meter = self.claim()
        with self.assertRaisesRegex(BudgetBlocked, "TICKET_IDENTITY_MISMATCH"):
            meter.charge_before_query(writer_id="project-b:writer", slot_id=SLOT, operation="RESERVATION")
        authority = PoolAuthority.parse(self.authority)
        with self.assertRaisesRegex(BudgetBlocked, "CLAIM_REQUIRED"):
            PrepaidQueryMeter(
                authority=authority, writer=authority.writers[0], ticket_ref="fake", slot_id=SLOT,
                charged_day=datetime.fromtimestamp(NOW_MS / 1000, UTC).date(),
                claim_confirmation=object(), evidence=self.evidence, clock_ms=lambda: self.now,
            )
        self.assertEqual(meter.report()["query_attempts_charged"], 0)

    def test_invalid_policy_shapes_fail_before_network(self) -> None:
        for field, value in (
            ("ruleset_id", None), ("max_evidence_age_ms", True),
            ("repository", "https://other"), ("scope_id", "../escape"),
            ("max_run_age_ms", 600001), ("writers", []),
        ):
            with self.subTest(field=field):
                self.authority = authority_fixture()
                self.authority[field] = value
                with self.assertRaises(BudgetBlocked):
                    self.claim()
                self.assertEqual(self.github.calls, [])

    def test_failed_d1_attempt_spends_ticket_and_does_not_retry(self) -> None:
        meter = self.claim()
        calls = []

        def execute(sql: str, params: tuple[object, ...]) -> Result:
            calls.append(sql)
            raise OSError("synthetic failure")

        reservation = self.reservation()
        with self.assertRaisesRegex(BudgetBlocked, "RESERVATION_UNVERIFIED"):
            reserve_shared_writer_envelope(execute=execute, reservation=reservation, query_meter=meter)
        self.assertEqual(len(calls), 1)
        self.assertEqual(meter.report()["query_attempts_charged"], 1)
        self.assertFalse(meter.report()["unused_allowance_refunded"])
        with self.assertRaises(BudgetBlocked):
            self.claim()

    @staticmethod
    def reservation() -> SharedWriterReservation:
        return SharedWriterReservation(
            writer_id="project-a:writer", slot_id=SLOT, idempotency_key=SLOT,
            slot_at_ms=NOW_MS, reserved_at_ms=NOW_MS,
            provider_requests=1, r2_class_a=1, r2_class_b=1, r2_new_bytes=100,
            d1_queries=2, d1_rows_read=20, d1_rows_written=7, d1_storage_growth_bytes=100,
        )

    def test_composition_claims_before_real_sqlite_admission_and_blocks_restart(self) -> None:
        db = sqlite3.connect(":memory:")
        self.addCleanup(db.close)
        db.executescript((ROOT / "migrations/cloudflare_shared_writer_admission_v0_3.sql").read_text())
        db.executescript((ROOT / "migrations/cloudflare_shared_writer_budget_policy_v0_4.sql").read_text())
        db.execute("""UPDATE cloudflare_shared_writer_lifecycle_policy_v0_3
                      SET max_active_reservations=20, max_lifetime_writer_identities=10""")
        db.execute("""INSERT INTO cloudflare_shared_writer_identities_v0_3
                      VALUES (?, 'ACTIVE', ?, ?)""", ("project-a:writer", "a" * 64, NOW_MS))
        db.execute("""UPDATE cloudflare_shared_writer_budget_policy_v0_4 SET
            max_reservations_per_utc_day=10, provider_requests_per_utc_day=10,
            r2_class_a_per_utc_day=10, r2_class_b_per_utc_day=10, r2_new_bytes_per_utc_day=10000,
            d1_queries_per_utc_day=100, d1_rows_read_per_utc_day=1000,
            d1_rows_written_per_utc_day=1000, d1_storage_growth_bytes_per_utc_day=100000,
            r2_class_a_per_rolling_31_days=100, r2_class_b_per_rolling_31_days=100,
            r2_new_bytes_per_rolling_31_days=100000""")
        calls = []

        def execute(sql: str, params: tuple[object, ...]) -> Result:
            self.assertEqual(len(self.github.refs), 1)
            calls.append(sql)
            cursor = db.execute(sql, params)
            columns = tuple(column[0] for column in cursor.description or ())
            return Result(tuple(dict(zip(columns, row, strict=True)) for row in cursor.fetchall()))

        args = dict(
            authority_document=self.authority, run_id=101, transport=self.github,
            evidence=self.evidence, clock_ms=lambda: self.now,
            execute=execute, reservation=self.reservation(),
        )
        result, report = claim_and_reserve_shared_writer_envelope(**args)
        self.assertEqual(result, "RESERVED")
        self.assertEqual(report["query_attempts_charged"], 1)
        with self.assertRaises(BudgetBlocked):
            claim_and_reserve_shared_writer_envelope(**args)
        self.assertEqual(len(calls), 1)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3").fetchone()[0], 1)

    def test_transport_http_rejection_has_no_body_and_no_retry(self) -> None:
        opener = Mock()
        opener.open.side_effect = HTTPError("https://api.github.com", 422, "synthetic", None, None)
        with patch("crypto_autopilot.paper.prepaid_query_controller_v0_1.build_opener", return_value=opener):
            response = GitHubJSONClient(token="synthetic-not-secret")("POST", PREFIX + "/git/refs", {})
        self.assertEqual(response, GitHubResponse(422, {}))
        opener.open.assert_called_once()

    def test_transport_timeout_is_redacted_and_not_retried(self) -> None:
        opener = Mock()
        opener.open.side_effect = TimeoutError("synthetic sensitive body should never be forwarded")
        with patch("crypto_autopilot.paper.prepaid_query_controller_v0_1.build_opener", return_value=opener):
            with self.assertRaisesRegex(BudgetBlocked, "^BLOCKED_PREPAID_GITHUB_TRANSPORT_UNVERIFIED$"):
                GitHubJSONClient(token="synthetic-not-secret")("GET", PREFIX + "/git/ref/heads/main")
        opener.open.assert_called_once()


if __name__ == "__main__":
    unittest.main()
