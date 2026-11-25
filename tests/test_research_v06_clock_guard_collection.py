"""Synthetic V0.6 bridge in the disabled research collection successor."""
import unittest
from unittest.mock import patch

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import RESERVE_SHARED_WRITER_SQL
from crypto_autopilot.research.shared_signal_collection_v0_3 import run_shared_signal_collection
import test_research_v05_collection_integration as fixtures


class ResearchV06CollectionTests(unittest.TestCase):
    def setUp(self):
        for target in ("socket.getaddrinfo", "socket.socket.connect", "socket.socket.connect_ex"):
            blocker = patch(target, side_effect=AssertionError("unexpected network access"))
            blocker.start()
            self.addCleanup(blocker.stop)
        self.f = fixtures.ResearchV05CollectionTests(
            "test_existing_github_run_identity_survives_shared_collection"
        )
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def test_disabled_does_not_access_sources_or_storage(self):
        result = run_shared_signal_collection(
            sources=[], run_id="", reservation=None, guard=None, execute=None,
            query_meter=None, validate_binding=None, credentials={}, execution_enabled=False,
        )
        self.assertEqual(result["status"], "SKIPPED_DISABLED")
        self.assertEqual(self.f.sdk.events, [])

    def test_normal_publication_preserves_existing_run_identity(self):
        with patch.object(fixtures, "run_shared_signal_collection", run_shared_signal_collection):
            self.f.test_existing_github_run_identity_survives_shared_collection()

    def test_post_commit_clock_rollback_stops_before_source_or_storage(self):
        fixture = self.f
        start = fixture.f.f.now
        fixture.f.f.now = start + 100
        original = fixture.sqlite_request
        def committed_then_rollback(sql, params):
            result = original(sql, params)
            if sql == RESERVE_SHARED_WRITER_SQL:
                fixture.f.f.now = start + 50
            return result
        with patch.object(fixtures, "run_shared_signal_collection", run_shared_signal_collection), patch.dict(
            "os.environ", {"CLOUDFLARE_ACCOUNT_ID": "a" * 32, "R2_BUCKET_NAME": "fixture"}
        ), patch(
            "crypto_autopilot.paper.prepaid_d1_client_v0_1.PrepaidCloudflareD1QueryClient._request",
            side_effect=committed_then_rollback,
        ), patch.object(BudgetedR2Store, "from_credentials") as store_factory:
            with self.assertRaises(BudgetBlocked):
                fixture.run_collection()
        store_factory.assert_not_called()
        self.assertEqual(fixture.sources_called, [])
        self.assertEqual(fixture.sdk.events, [])
        self.assertEqual(fixture.db.execute(
            "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3 WHERE writer_id=?",
            (fixtures.research_fixture.WRITER,),
        ).fetchone()[0], 1)
        self.assertGreater(fixture.f.meter.report()["query_attempts_charged"], 0)
