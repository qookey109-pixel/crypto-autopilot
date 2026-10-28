from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from crypto_autopilot.paper.cloud_loop_v0_1 import CloudLoopReviewRequired, digest
from crypto_autopilot.paper.run_coordinator_v0_3 import LivePaperRunCoordinatorPolicy
from crypto_autopilot.paper.cloud_result_seal_validation_v0_1 import (
    committed_report_with_seal_validation,
)
from test_cloud_paper_loop_v0_1 import MemoryStore, step


class CloudResultSealValidationTests(unittest.TestCase):
    def test_valid_compact_result_is_read_without_mutation(self):
        store = MemoryStore()
        original = step(store, 420000, None)
        before = copy.deepcopy(store.objects)
        actual = committed_report_with_seal_validation(store, "0")
        self.assertEqual(actual["state"], "NO_TRADE")
        self.assertEqual(actual["coordinator"]["step_id"], original["coordinator"]["step_id"])
        self.assertEqual(store.objects, before)

    def test_rejects_tampered_or_unbound_result_seal(self):
        source = MemoryStore()
        first = step(source, 420000, None)
        run_step = source.objects[("live-run-step", first["coordinator"]["step_id"])]
        key = ("live-run-result", run_step["request_id"])
        for case in ("schema", "state", "request", "run", "sequence", "authority"):
            with self.subTest(case=case):
                store = MemoryStore()
                store.objects = copy.deepcopy(source.objects)
                seal = store.objects[key]
                if case == "schema":
                    seal["schema"] = "unexpected"
                elif case == "state":
                    seal["state"] = "REVIEW_REQUIRED"
                elif case == "request":
                    seal["request_id"] = "another-request"
                elif case == "run":
                    seal["run_id"] = "another-run"
                elif case == "sequence":
                    seal["sequence"] = 2
                else:
                    seal["authority"]["execution_authority"] = True
                with self.assertRaisesRegex(CloudLoopReviewRequired, "COORDINATOR_SEAL_INVALID"):
                    committed_report_with_seal_validation(store, "0")

    def test_legacy_embedded_step_seal_is_checked(self):
        store = MemoryStore()
        with patch(
            "crypto_autopilot.paper.cloud_loop_v0_1.LivePaperRunCoordinatorPolicy",
            return_value=LivePaperRunCoordinatorPolicy(run_slot_claim_required=True),
        ):
            step(store, 420000, None)
        pointer = store.objects[("cloud-result", "0")]
        old_id = pointer["report_id"]
        compact = store.objects[("cloud-report", old_id)]
        step_id = compact["coordinator"]["step_id"]
        legacy = dict(compact)
        legacy["schema"] = "qookey-cloud-paper-loop-report-v0.1"
        legacy["coordinator"] = {
            **compact["coordinator"], "run_step": store.objects[("live-run-step", step_id)],
        }
        new_id = digest(legacy)
        del store.objects[("cloud-report", old_id)]
        store.objects[("cloud-report", new_id)] = legacy
        pointer["report_id"] = new_id
        self.assertEqual(committed_report_with_seal_validation(store, "0"), legacy)
        request_id = store.objects[("live-run-step", step_id)]["request_id"]
        store.objects[("live-run-result", request_id)]["run_id"] = "another-run"
        with self.assertRaisesRegex(CloudLoopReviewRequired, "COORDINATOR_SEAL_INVALID"):
            committed_report_with_seal_validation(store, "0")

    def test_every_read_is_guarded_including_successor_reads(self):
        class TracedStore(MemoryStore):
            def __init__(self):
                super().__init__()
                self.events = []

            def get_json(self, kind, object_id):
                self.events.append(("get", kind))
                return super().get_json(kind, object_id)

        store = TracedStore()
        step(store, 420000, None)
        store.events.clear()
        committed_report_with_seal_validation(
            store, "0", before_external=lambda: store.events.append(("guard", None)),
        )
        self.assertEqual(
            store.events[-6:],
            [("guard", None), ("get", "live-run-step"),
             ("guard", None), ("get", "live-tick"),
             ("guard", None), ("get", "live-run-result")],
        )
        for index in range(0, len(store.events), 2):
            self.assertEqual(store.events[index], ("guard", None))
            self.assertEqual(store.events[index + 1][0], "get")

    def test_absent_result_remains_absent(self):
        self.assertIsNone(committed_report_with_seal_validation(MemoryStore(), "0"))


if __name__ == "__main__":
    unittest.main()
