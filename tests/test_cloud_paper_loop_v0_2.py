from __future__ import annotations

import copy
import json
import unittest

import test_cloud_paper_loop_v0_1 as legacy_tests
from crypto_autopilot.paper.cloud_loop_v0_1 import CloudLoopReviewRequired
from crypto_autopilot.paper.cloud_loop_v0_2 import run_cloud_step


class CloudPaperLoopV02Tests(unittest.TestCase):
    def test_json_roundtrip_report_replays_and_rejects_changed_content(self):
        class JsonStore(legacy_tests.MemoryStore):
            def get_json(self, kind, object_id):
                value = super().get_json(kind, object_id)
                return None if value is None else json.loads(json.dumps(value))

        def execute(store):
            return run_cloud_step(
                tick_ms=420000, previous_slot=None, store=store,
                feed=legacy_tests.NeverCalledFeed(),
                market_supplier=lambda: {
                    "context_status": "REGIME_UNAVAILABLE",
                    "provider_requests_performed": 0,
                    "nested_evidence": {"levels": ((1, 2), (3, 4))},
                },
                candidate_supplier=lambda market, state: (),
                strategy_registry=legacy_tests.REGISTRY, before_external=lambda: None,
            )

        store = JsonStore()
        first = execute(store)
        self.assertEqual(first["market"]["nested_evidence"]["levels"], [[1, 2], [3, 4]])
        before = copy.deepcopy(store.objects)
        replay = execute(store)
        self.assertEqual(replay["report"], first)
        self.assertEqual(store.objects, before)

        class ChangedReportStore(JsonStore):
            def get_json(self, kind, object_id):
                value = super().get_json(kind, object_id)
                if kind == "cloud-report" and value is not None:
                    value["market"]["nested_evidence"]["levels"][0][0] = 9
                return value

        changed = ChangedReportStore()
        with self.assertRaisesRegex(CloudLoopReviewRequired, "REPORT_READBACK_MISMATCH"):
            execute(changed)
        self.assertEqual(changed.list_json_ids("cloud-result"), ())

    def test_successor_continues_from_frozen_predecessor_report(self):
        store = legacy_tests.MemoryStore()
        first = legacy_tests.step(store, 420000, None)
        second = run_cloud_step(
            tick_ms=1320000, previous_slot=first["slot_id"], store=store,
            feed=legacy_tests.NeverCalledFeed(),
            market_supplier=lambda: {"provider_requests_performed": 0},
            candidate_supplier=lambda market, state: (),
            strategy_registry=legacy_tests.REGISTRY, before_external=lambda: None,
        )
        self.assertEqual(second["state"], "NO_TRADE")
        self.assertEqual(second["coordinator"]["sequence"], 2)
        self.assertEqual(second["account"]["initial_equity_usd"], 10000.0)


if __name__ == "__main__":
    unittest.main()
