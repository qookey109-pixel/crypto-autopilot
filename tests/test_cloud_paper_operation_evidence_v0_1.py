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
