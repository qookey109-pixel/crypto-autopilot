from __future__ import annotations

import copy
import unittest

from crypto_autopilot.paper.cloud_loop_v0_1 import CloudLoopReviewRequired
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

    def test_absent_result_remains_absent(self):
        self.assertIsNone(committed_report_with_seal_validation(MemoryStore(), "0"))


if __name__ == "__main__":
    unittest.main()
