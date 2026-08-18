from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from crypto_autopilot.pilot_evidence import aggregate_pilot_evidence


class PilotEvidenceTest(unittest.TestCase):
    def test_aggregate_requires_all_passing_shards(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for shard in range(3):
                (root / f"final-shard-{shard}.json").write_text(
                    json.dumps(
                        {
                            "status": "PASS",
                            "shard_index": shard,
                            "work_items_total": 70,
                            "finalized_new": 10,
                            "skipped_finalized": 60,
                            "resumed_from_staged": 1 if shard == 0 else 0,
                            "pages_fetched": 5,
                            "rows_fetched": 100,
                        }
                    ),
                    encoding="utf-8",
                )
            (root / "planned-stop-shard-0.json").write_text(
                json.dumps({"status": "PLANNED_STOP", "shard_index": 0}),
                encoding="utf-8",
            )

            aggregate = aggregate_pilot_evidence(root, year=2025, shard_count=3)
            self.assertEqual(aggregate["status"], "PASS")
            self.assertTrue(aggregate["planned_stop_observed"])
            self.assertEqual(aggregate["totals"]["work_items_total"], 210)
            self.assertEqual(aggregate["totals"]["resumed_from_staged"], 1)
            self.assertEqual(aggregate["missing_shards"], [])

    def test_aggregate_marks_missing_or_failed_shards_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "final-shard-0.json").write_text(
                json.dumps({"status": "FAIL", "shard_index": 0}),
                encoding="utf-8",
            )
            aggregate = aggregate_pilot_evidence(root, year=2025, shard_count=3)
            self.assertEqual(aggregate["status"], "INCOMPLETE")
            self.assertEqual(aggregate["failed_shards"], [0])
            self.assertEqual(aggregate["missing_shards"], [1, 2])


if __name__ == "__main__":
    unittest.main()
