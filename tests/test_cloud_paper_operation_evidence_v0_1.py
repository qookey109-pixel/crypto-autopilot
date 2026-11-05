"""Evidence regression for a conditional-create collision during a Paper slot."""
import unittest

from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.cloud_run_store_v0_1 import CloudPaperRunStore
from scripts.measure_cloud_paper_r2_protocol_profile_v0_1 import _MemoryS3Client
from test_cloud_paper_composition_v0_1 import (
    NOW, FakeClient, composition, make_budget_guard,
)


class CollisionS3(_MemoryS3Client):
    def __init__(self):
        super().__init__()
        self.collision_injected = False

    def put_object(self, **kwargs):
        key = kwargs["Key"]
        if (not self.collision_injected and "/live-state/" in key
                and kwargs.get("IfNoneMatch") == "*"):
            # Another writer commits exactly the same object after the first
            # GET and before this writer's conditional PUT is processed.
            self.collision_injected = True
            self.objects[key] = (kwargs["Body"], dict(kwargs["Metadata"]))
        return super().put_object(**kwargs)


class PaperOperationEvidenceTests(unittest.TestCase):
    def test_conditional_conflict_is_not_reported_as_known_zero_replays(self):
        client = CollisionS3()
        guard = make_budget_guard()
        adapter = BudgetedR2Store(client=client, bucket="synthetic-only", budget_guard=guard)
        store = CloudPaperRunStore(adapter, prefix="synthetic")
        result = composition(FakeClient(), store, guard=guard).run_slot(
            tick_ms=NOW, previous_slot=None, activation_enabled=True, run_id="fixture",
        )
        self.assertTrue(client.collision_injected)
        self.assertEqual(result["state"], "NO_TRADE")
        puts = sum(call["operation"] == "PUT" for call in client.calls)
        observed = result["operation_counts"]
        # Until a trusted attempt meter is carried into the immutable report,
        # UNKNOWN is acceptable; a fabricated KNOWN value is not.
        if observed["status"] == "KNOWN":
            self.assertEqual(observed["r2_write_attempts"], puts)
            self.assertGreater(observed["r2_write_replays"], 0)
        else:
            self.assertIsNone(observed["r2_write_attempts"])
            self.assertIsNone(observed["r2_write_replays"])


class PaperOperationReaderTests(unittest.TestCase):
    def test_old_then_new_reports_recover_and_chain(self):
        from crypto_autopilot.paper.cloud_loop_v0_2 import run_cloud_step as old_step
        from crypto_autopilot.paper.cloud_loop_v0_3 import run_cloud_step as new_step
        from crypto_autopilot.paper.cloud_report_reader_v0_3 import committed_report
        from test_cloud_paper_loop_v0_1 import MemoryStore, NeverCalledFeed, REGISTRY

        store = MemoryStore()
        def run(fn, tick, previous):
            return fn(
                tick_ms=tick, previous_slot=previous, store=store,
                feed=NeverCalledFeed(),
                market_supplier=lambda: {"provider_requests_performed": 0},
                candidate_supplier=lambda market, state: (),
                strategy_registry=REGISTRY, before_external=lambda: None,
            )

        first = run(old_step, 420000, None)
        second = run(new_step, 1320000, "0")
        third = run(new_step, 2220000, "1")
        self.assertEqual(first["schema"], "qookey-cloud-paper-loop-report-v0.2")
        self.assertEqual(second["schema"], "qookey-cloud-paper-loop-report-v0.3")
        self.assertEqual(third["coordinator"]["sequence"], 3)
        self.assertEqual(committed_report(store, "0"), first)
        self.assertEqual(committed_report(store, "1"), second)
        self.assertEqual(second["operation_counts"]["status"], "PARTIAL")
        self.assertIsNone(second["operation_counts"]["r2_write_attempts"])
        self.assertIsNone(second["operation_counts"]["r2_write_replays"])

    def test_tampered_new_report_fails_digest_validation(self):
        from crypto_autopilot.paper.cloud_loop_v0_1 import CloudLoopReviewRequired
        from crypto_autopilot.paper.cloud_loop_v0_3 import run_cloud_step
        from crypto_autopilot.paper.cloud_report_reader_v0_3 import committed_report
        from test_cloud_paper_loop_v0_1 import MemoryStore, NeverCalledFeed, REGISTRY

        store = MemoryStore()
        run_cloud_step(
            tick_ms=420000, previous_slot=None, store=store, feed=NeverCalledFeed(),
            market_supplier=lambda: {"provider_requests_performed": 0},
            candidate_supplier=lambda market, state: (), strategy_registry=REGISTRY,
            before_external=lambda: None,
        )
        pointer = store.objects[("cloud-result", "0")]
        report = store.objects[("cloud-report", pointer["report_id"])]
        report["operation_counts"]["r2_write_attempts"] = 0
        with self.assertRaisesRegex(CloudLoopReviewRequired, "RESULT_REPORT_MISMATCH"):
            committed_report(store, "0")
