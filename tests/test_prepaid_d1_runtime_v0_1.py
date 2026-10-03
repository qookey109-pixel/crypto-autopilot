from __future__ import annotations

import json
import sqlite3
import unittest
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch

from crypto_autopilot.paper.cloud_budget_ledger_v0_1 import (
    D1_SHARED_ROWS_RESERVATION_SQL,
    READ_SLOT_RESERVATION_SQL,
    D1CloudBudgetLedger,
    D1LedgerUnavailable,
    D1UsageGuard,
    D1UsageSnapshot,
)
from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked, R2UsageSnapshot
from crypto_autopilot.paper.cloud_loop_v0_1 import SLOT_MS, SLOT_OFFSET_MS
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.cloud_runtime_v0_2 import (
    PrepaidCloudPaperBudgetLedger,
    build_runtime_composition,
)
from crypto_autopilot.paper.prepaid_d1_client_v0_1 import (
    DatabaseSizeEvidence,
    PrepaidCloudflareD1QueryClient,
)
from crypto_autopilot.paper.prepaid_query_controller_v0_1 import (
    AllocationEvidence,
    claim_prepaid_query_meter,
)
from scripts.measure_cloud_paper_r2_protocol_profile_v0_1 import _MemoryS3Client
from test_prepaid_query_controller_v0_1 import FakeGitHub, authority_fixture

ROOT = Path(__file__).parents[1]
NOW = int(datetime(2026, 10, 3, 2, 7, tzinfo=UTC).timestamp() * 1000)
DB_ID = "00000000-0000-0000-0000-000000000001"
CLIENT_MODULE = "crypto_autopilot.paper.prepaid_d1_client_v0_1"
RUNTIME_MODULE = "crypto_autopilot.paper.cloud_runtime_v0_2"
WRITER = "project-a:writer"


class Response:
    def __init__(self, body):
        self.body = body
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, limit):
        return self.body[:limit]


def body(*, rows=(), reads=1, writes=0, size=1024):
    return json.dumps({
        "success": True, "result": [{"success": True, "results": list(rows),
            "meta": {"rows_read": reads, "rows_written": writes, "size_after": size}}],
    }).encode()


class PrepaidD1RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.now = NOW
        self.authority = authority_fixture()
        for writer in self.authority["writers"]:
            writer["queries_per_ticket"] = 12
        self.authority["statement_costs"] = {
            "RESERVATION": {"queries": 1, "rows_read": 4000, "rows_written": 10, "storage_bytes": 16384},
            "REPLAY_READ": {"queries": 1, "rows_read": 4000, "rows_written": 0, "storage_bytes": 0},
        }
        self.github = FakeGitHub(self.authority)
        self._set_run(101)
        self.meter = self.claim()
        self.guard = self.make_guard()
        self.evidence = self.database_evidence()
        self.slot = str((NOW - SLOT_OFFSET_MS) // SLOT_MS)
        self.sdk = _MemoryS3Client()

    def _set_run(self, run):
        stamp = datetime.fromtimestamp(self.now / 1000, UTC).isoformat()
        self.github.runs[run]["created_at"] = stamp
        self.github.runs[run]["run_started_at"] = stamp

    def claim(self, run=101, *, path=None):
        kwargs = {} if path is None else {"authority_path": path}
        return claim_prepaid_query_meter(
            authority_document=self.authority, writer_id=WRITER,
            slot_id=f"slot:{self.now}", run_id=run, transport=self.github,
            evidence=AllocationEvidence(
                account_coverage_complete=True, zero_cost_verified=True,
                observed_at_ms=self.now, measured_through_ms=self.now,
                available={"queries": 1000, "rows_read": 1_000_000,
                    "rows_written": 10_000, "storage_bytes": 10_000_000},
            ),
            clock_ms=lambda: self.now, **kwargs,
        )

    def make_guard(self, size=1024):
        return D1UsageGuard(
            snapshot=D1UsageSnapshot(
                account_wide=True, reservation_coverage_complete=True,
                observed_at_ms=self.now, measured_through_ms=self.now,
                rows_read_day=0, rows_written_day=0, storage_bytes=size,
            ),
            clock_ms=lambda: self.now,
        )

    def database_evidence(self, size=1024):
        return DatabaseSizeEvidence(DB_ID, True, self.now, self.now, size)

    def client(self, **changes):
        kwargs = dict(
            api_token="synthetic-only-token", account_id="a" * 32, database_id=DB_ID,
            usage_guard=self.guard, query_meter=self.meter,
            writer_id=WRITER, slot_id=f"slot:{self.now}", database_evidence=self.evidence,
        )
        kwargs.update(changes)
        return PrepaidCloudflareD1QueryClient(**kwargs)

    def test_meter_readonly_checks_never_debit_or_refresh(self):
        before = self.meter.report()
        self.meter.validate_binding(writer_id=WRITER, slot_id=f"slot:{NOW}")
        cost = self.meter.statement_cost("RESERVATION")
        self.assertEqual(cost.rows_written, 10)
        self.assertEqual(self.meter.report(), before)
        self.now += 60_001
        with self.assertRaisesRegex(BudgetBlocked, "STALE"):
            self.meter.validate_binding(writer_id=WRITER, slot_id=f"slot:{NOW}")

    def test_successor_authority_path_is_read_from_exact_main(self):
        self._set_run(102)
        path = "config/cloudflare_prepaid_query_controller_execution_v0_1.json"
        self.claim(102, path=path)
        self.assertTrue(any("/contents/" + path + "?ref=" in p for _, p in self.github.calls))
        for invalid in ("../secret", "config/other.json", path + "?ref=x", "https://example.test"):
            with self.subTest(path=invalid):
                before = len(self.github.calls)
                with self.assertRaisesRegex(BudgetBlocked, "AUTHORITY_PATH"):
                    self.claim(102, path=invalid)
                self.assertEqual(len(self.github.calls), before)

    def test_client_missing_meter_stops_before_credentials(self):
        with patch(f"{CLIENT_MODULE}.os.environ.get") as environment:
            with self.assertRaisesRegex(BudgetBlocked, "METER_REQUIRED"):
                PrepaidCloudflareD1QueryClient.from_environment(
                    usage_guard=self.guard, query_meter=None, writer_id=WRITER,
                    slot_id=f"slot:{NOW}", database_evidence=self.evidence,
                )
        environment.assert_not_called()

    def test_database_scope_completeness_freshness_and_size_are_required(self):
        for changes in (
            {"database_id": "other"}, {"coverage_complete": False},
            {"size_bytes": True}, {"size_bytes": 1025},
            {"observed_at_ms": NOW - 50_001}, {"measured_through_ms": NOW + 1},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(BudgetBlocked):
                    self.client(database_evidence=replace(self.evidence, **changes))
        self.assertEqual(self.meter.report()["query_attempts_charged"], 0)

    def test_single_prepaid_http_attempt_with_redacted_repr(self):
        client = self.client()
        opener = Mock()
        def send(request, timeout):
            self.assertEqual(self.meter.report()["query_attempts_charged"], 1)
            self.assertEqual(timeout, 10)
            self.assertEqual(json.loads(request.data)["sql"], READ_SLOT_RESERVATION_SQL)
            return Response(body())
        opener.open.side_effect = send
        with patch(f"{CLIENT_MODULE}.build_opener", return_value=opener):
            result = client.query(READ_SLOT_RESERVATION_SQL, (self.slot,))
        self.assertEqual(result.rows, ())
        self.assertEqual(opener.open.call_count, 1)
        self.assertNotIn("synthetic-only-token", repr(client))

    def test_unapproved_sql_and_cross_slot_rejected_without_debit_or_network(self):
        client = self.client()
        with patch(f"{CLIENT_MODULE}.build_opener") as network:
            for sql, params in (
                ("SELECT 1", ()), (D1_SHARED_ROWS_RESERVATION_SQL, ()),
                (READ_SLOT_RESERVATION_SQL, ("other",)),
                (READ_SLOT_RESERVATION_SQL, [self.slot]),
                (READ_SLOT_RESERVATION_SQL, (self.slot, "extra")),
            ):
                with self.subTest(sql=sql):
                    with self.assertRaises((BudgetBlocked, D1LedgerUnavailable)):
                        client.query(sql, params)
        network.assert_not_called()
        self.assertEqual(self.meter.report()["query_attempts_charged"], 0)

    def test_missing_invalid_overlimit_and_ambiguous_metadata_poison_client(self):
        payloads = [
            body(reads=True), body(writes=-1), body(size=None),
            body(reads=4001), body(writes=1), body(size=1025),
            b"{}", b"not-json", b"x" * 256001,
        ]
        for raw in payloads:
            with self.subTest(raw=raw[:80]):
                client = self.client()
                opener = Mock()
                opener.open.return_value = Response(raw)
                with patch(f"{CLIENT_MODULE}.build_opener", return_value=opener):
                    with self.assertRaisesRegex(D1LedgerUnavailable, "REVIEW_REQUIRED"):
                        client.query(READ_SLOT_RESERVATION_SQL, (self.slot,))
                    with self.assertRaisesRegex(D1LedgerUnavailable, "REVIEW_REQUIRED"):
                        client.query(READ_SLOT_RESERVATION_SQL, (self.slot,))
                self.assertEqual(opener.open.call_count, 1)
        self.assertEqual(self.meter.report()["query_attempts_charged"], len(payloads))

    def test_transport_failure_keeps_debit_blocks_retry_and_redacts_error(self):
        client = self.client()
        opener = Mock()
        opener.open.side_effect = OSError("synthetic-secret-content")
        with patch(f"{CLIENT_MODULE}.build_opener", return_value=opener):
            with self.assertRaisesRegex(D1LedgerUnavailable, "REVIEW_REQUIRED") as error:
                client.query(READ_SLOT_RESERVATION_SQL, (self.slot,))
            with self.assertRaises(D1LedgerUnavailable):
                client.query(READ_SLOT_RESERVATION_SQL, (self.slot,))
        self.assertNotIn("synthetic-secret", str(error.exception))
        self.assertEqual(opener.open.call_count, 1)
        self.assertEqual(self.meter.report()["query_attempts_charged"], 1)

    def test_expired_or_exhausted_ticket_stops_before_http(self):
        client = self.client()
        for _ in range(12):
            self.meter.charge_before_query(writer_id=WRITER, slot_id=f"slot:{NOW}", operation="REPLAY_READ")
        with patch(f"{CLIENT_MODULE}.build_opener") as network:
            with self.assertRaisesRegex(BudgetBlocked, "EXHAUSTED"):
                client.query(READ_SLOT_RESERVATION_SQL, (self.slot,))
        network.assert_not_called()

    def runtime(self, *, meter=None, database_size=1024, enabled=True):
        def r2_factory(**kwargs):
            return BudgetedR2Store(
                client=self.sdk, bucket="synthetic-only",
                budget_guard=kwargs["budget_guard"], freshness_check=kwargs["freshness_check"],
            )
        size = sum(len(value[0]) for value in self.sdk.objects.values())
        a = sum(call["operation"] in {"PUT", "LIST"} for call in self.sdk.calls)
        b = sum(call["operation"] == "GET" for call in self.sdk.calls)
        snapshot = R2UsageSnapshot(
            account_wide=True, reservation_coverage_complete=True,
            observed_at_ms=self.now, measured_through_ms=self.now, storage_bytes=size,
            class_a_month=a, class_b_month=b, class_a_31_days=a, class_b_31_days=b,
            class_a_day=a, class_b_day=b, provider_requests_day=0, new_bytes_day=size,
        )
        env = {
            "CLOUDFLARE_D1_API_TOKEN": "synthetic-only-token",
            "CLOUDFLARE_ACCOUNT_ID": "a" * 32, "CLOUDFLARE_D1_DATABASE_ID": DB_ID,
        }
        with patch.dict("os.environ", env), patch(
            f"{RUNTIME_MODULE}.BudgetedR2Store.from_credentials", side_effect=r2_factory,
        ):
            return build_runtime_composition(
                r2_snapshot=snapshot, d1_snapshot=self.make_guard(database_size).snapshot,
                strategy_registry=json.loads((ROOT / "config/cloud_paper_strategy_registry_v0_1.json").read_text()),
                allowed_base_assets=frozenset({"BTC"}), clock_ms=lambda: self.now,
                query_meter=self.meter if meter is None else meter, writer_id=WRITER,
                slot_at_ms=self.now, database_evidence=self.database_evidence(database_size),
                construction_enabled=enabled,
            )

    def sqlite(self):
        db = sqlite3.connect(":memory:")
        self.addCleanup(db.close)
        for migration in (
            "cloud_paper_budget_ledger_v0_1.sql",
            "cloud_paper_settlement_recovery_v0_1.sql",
            "cloudflare_shared_writer_admission_v0_3.sql",
            "cloudflare_shared_writer_budget_policy_v0_4.sql",
        ):
            db.executescript((ROOT / "migrations" / migration).read_text())
        db.execute("""UPDATE cloudflare_shared_writer_lifecycle_policy_v0_3
            SET max_active_reservations=20, max_lifetime_writer_identities=10""")
        db.execute("INSERT INTO cloudflare_shared_writer_identities_v0_3 VALUES (?, 'ACTIVE', ?, ?)",
            (WRITER, "a" * 64, NOW))
        names = [row[1] for row in db.execute("PRAGMA table_info(cloudflare_shared_writer_budget_policy_v0_4)")]
        db.execute("UPDATE cloudflare_shared_writer_budget_policy_v0_4 SET " +
            ", ".join(name + "=100000000" for name in names if name != "policy_id"))
        return db

    def test_runtime_default_disabled_and_invalid_meter_before_environment(self):
        self.assertIsNone(self.runtime(enabled=False))
        with patch(f"{CLIENT_MODULE}.os.environ.get") as environment:
            with self.assertRaisesRegex(BudgetBlocked, "METER_REQUIRED"):
                self.runtime(meter=object())
        environment.assert_not_called()
        self.assertEqual(self.sdk.calls, [])

    def test_full_no_trade_shared_admission_settlement_restart_and_duplicate(self):
        db = self.sqlite()
        size = [1024]
        statements = []
        def send(request, timeout):
            payload = json.loads(request.data)
            sql = payload["sql"]
            statements.append(sql)
            self.assertNotEqual(sql, D1_SHARED_ROWS_RESERVATION_SQL)
            cursor = db.execute(sql, tuple(payload["params"]))
            columns = tuple(item[0] for item in cursor.description or ())
            rows = tuple(dict(zip(columns, row, strict=True)) for row in cursor.fetchall())
            db.commit()
            size[0] += 64
            return Response(body(rows=rows, reads=1, writes=7, size=size[0]))
        opener = Mock()
        opener.open.side_effect = send
        with patch(f"{CLIENT_MODULE}.build_opener", return_value=opener):
            first = self.runtime()
            result = first.run_slot(tick_ms=self.now, previous_slot=None,
                activation_enabled=True, run_id="synthetic-main-101")
            self.assertEqual(result["state"], "NO_TRADE")
            self.assertEqual(result["account"]["initial_equity_usd"], 10000)
            self.assertEqual(result["account"]["open_position_count"], 0)
            self.assertEqual(len(statements), 3)
            self.assertEqual(self.meter.report()["query_attempts_charged"], 4)
            calls = len(self.sdk.calls)
            with self.assertRaisesRegex(BudgetBlocked, "ALREADY_USED"):
                first.run_slot(tick_ms=self.now, previous_slot=None,
                    activation_enabled=True, run_id="duplicate")
            self.assertEqual(len(statements), 3)
            self.assertEqual(len(self.sdk.calls), calls)
            self.now += SLOT_MS
            self._set_run(102)
            self.meter = self.claim(102)
            second = self.runtime(database_size=size[0])
            resumed = second.run_slot(tick_ms=self.now, previous_slot=result["slot_id"],
                activation_enabled=True, run_id="synthetic-main-102")
        self.assertEqual(resumed["state"], "NO_TRADE")
        self.assertEqual(resumed["account"]["initial_equity_usd"], 10000)
        self.assertEqual(resumed["account"]["open_position_count"], 0)
        self.assertEqual(len(statements), 6)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3").fetchone()[0], 2)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM cloud_paper_budget_reservations WHERE state='SETTLED'").fetchone()[0], 2)
        self.assertEqual(second.budget_guard.attempted_usage().provider_requests, 0)

    def test_failure_after_admission_retains_shared_reservation_before_r2(self):
        db = self.sqlite()
        attempts = []
        def send(request, timeout):
            payload = json.loads(request.data)
            attempts.append(payload["sql"])
            cursor = db.execute(payload["sql"], tuple(payload["params"]))
            cursor.fetchall()
            db.commit()
            # Lost first response after central SQL committed.
            raise OSError("synthetic lost response")
        opener = Mock()
        opener.open.side_effect = send
        runtime = self.runtime()
        with patch(f"{CLIENT_MODULE}.build_opener", return_value=opener):
            with self.assertRaisesRegex(BudgetBlocked, "UNVERIFIED"):
                runtime.run_slot(tick_ms=NOW, previous_slot=None,
                    activation_enabled=True, run_id="synthetic")
        self.assertEqual(len(attempts), 1)
        self.assertEqual(self.meter.report()["query_attempts_charged"], 2)
        self.assertEqual(self.sdk.calls, [])
        self.assertEqual(db.execute("SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3").fetchone()[0], 1)

    def test_historical_recovery_requires_fresh_separate_admission(self):
        runtime = self.runtime()
        with patch(f"{CLIENT_MODULE}.build_opener") as network:
            with self.assertRaisesRegex(BudgetBlocked, "FRESH_WORKLOAD"):
                runtime.recover_completed_slot(slot=self.slot, recovery_enabled=True)
        network.assert_not_called()
        self.assertEqual(self.sdk.calls, [])

    def test_runtime_rejects_different_client_meter_binding(self):
        self._set_run(102)
        other = self.claim(102)
        with self.assertRaisesRegex(BudgetBlocked, "BINDING_MISMATCH"):
            PrepaidCloudPaperBudgetLedger(
                client=self.client(), meter=other, writer_id=WRITER, slot_at_ms=NOW,
            )

    def test_legacy_budget_ledger_uses_prepaid_adapter(self):
        ledger = D1CloudBudgetLedger(self.client())
        opener = Mock()
        opener.open.return_value = Response(body())
        with patch(f"{CLIENT_MODULE}.build_opener", return_value=opener):
            self.assertIsNone(ledger.get_slot_reservation(slot_id=self.slot))
        self.assertEqual(self.meter.report()["query_attempts_charged"], 1)


if __name__ == "__main__":
    unittest.main()
