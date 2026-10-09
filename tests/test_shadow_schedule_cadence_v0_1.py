"""Pure bounded nominal Shadow cadence diagnostics, no GitHub/provider runtime."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from crypto_autopilot.research.shadow_schedule_cadence_v0_1 import (
    ShadowCadenceReviewRequired,
    inspect_shadow_run_arrival_cadence,
)

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / (
    "research/status/"
    "prospective_shadow_schedule_arrival_snapshot_2026_10_09_v0_1.json"
)


def verified_source() -> dict[str, object]:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


class ShadowNominalCadenceTests(unittest.TestCase):
    def test_nine_original_runs_offer_only_candidate_arrival_windows(self) -> None:
        source = verified_source()
        self.assertTrue(source["source_query_may_be_incomplete"])
        self.assertFalse(source["original_nominal_trigger_time_known"])
        report = inspect_shadow_run_arrival_cadence(
            source["runs"], cron_utc=source["known_nominal_cron_utc"]
        )
        self.assertEqual(report["status"], "REVIEW_REQUIRED_UNKNOWN_CAUSE")
        self.assertEqual(report["unique_natural_successful_runs"], 9)
        self.assertEqual(report["candidate_four_hour_windows"], 16)
        self.assertEqual(report["windows_with_created_run"], 9)
        self.assertEqual(report["windows_without_created_run"], 7)
        self.assertEqual(report["arrival_phase_minutes_minimum"], 61)
        self.assertEqual(report["arrival_phase_minutes_maximum"], 212)
        self.assertEqual(report["bounded_first_candidate_utc"], "2026-10-06T16:17:00Z")
        self.assertEqual(report["bounded_last_candidate_utc"], "2026-10-09T04:17:00Z")
        self.assertEqual(report["unoccupied_candidate_window_utc"], [
            "2026-10-07T00:17:00Z",
            "2026-10-07T08:17:00Z",
            "2026-10-07T16:17:00Z",
            "2026-10-08T00:17:00Z",
            "2026-10-08T08:17:00Z",
            "2026-10-08T16:17:00Z",
            "2026-10-09T00:17:00Z",
        ])
        self.assertEqual(
            [row["minutes"] for row in report["observed_interarrival_over_6h"]],
            [372, 571, 527, 571, 529],
        )
        self.assertEqual(report["observed_interarrival_over_6h_count"], 5)
        for boundary in (
            "run_metadata_independently_authenticated",
            "nominal_trigger_timestamp_available",
            "candidate_arrival_bucket_is_trigger_attribution",
            "actual_queue_delay_measured",
            "missed_trigger_count_proven",
            "missing_workflow_run_proven",
            "source_collector_failure_proven",
            "full_collection_continuity_proven",
            "github_schedule_changes_authorized",
            "retry_or_backfill_authorized",
            "execution_authority",
        ):
            with self.subTest(boundary=boundary):
                self.assertFalse(report[boundary])
        nine = json.loads(
            (ROOT / "research/status/current-operations-v0-3.json").read_text(
                encoding="utf-8"
            )
        )["vnext_delivery_checkpoint"]["prospective_shadow"]["nine_batch_audit"]
        self.assertEqual(
            [item["run_id"] for item in source["runs"]], nine["natural_run_ids"]
        )
        self.assertEqual(nine["observed_gap_minutes"], [
            row["minutes"] for row in report["observed_interarrival_over_6h"]
        ])

    def test_invalid_source_claims_fail_closed(self) -> None:
        source = verified_source()["runs"]
        cases = [
            ("workflow_id", 123),
            ("workflow_path", ".github/workflows/other.yml"),
            ("workflow_name", "Other workflow"),
            ("event", "workflow_dispatch"),
            ("head_branch", "not-main"),
            ("run_attempt", 2),
            ("status", "in_progress"),
            ("conclusion", "failure"),
            ("job_name", "paper"),
            ("job_conclusion", "skipped"),
            ("head_sha", "bad"),
            ("created_at", "2026-10-06T18:23:26+08:00"),
            ("run_started_at", "invalid"),
            ("run_id", True),
        ]
        for field, value in cases:
            with self.subTest(field=field):
                broken = copy.deepcopy(source)
                broken[0][field] = value
                with self.assertRaises(ShadowCadenceReviewRequired):
                    inspect_shadow_run_arrival_cadence(broken)

    def test_duplicate_or_reverse_time_and_wrong_cron_fail_closed(self) -> None:
        source = verified_source()["runs"]
        with self.assertRaisesRegex(ShadowCadenceReviewRequired, "UNREVIEWED_CRON"):
            inspect_shadow_run_arrival_cadence(source, cron_utc="17 */2 * * *")
        for variant in ("id", "timestamp", "reverse", "empty", "too_many"):
            with self.subTest(variant=variant):
                data = copy.deepcopy(source)
                if variant == "id":
                    data[1]["run_id"] = data[0]["run_id"]
                if variant == "timestamp":
                    data[1]["created_at"] = data[0]["created_at"]
                    data[1]["run_started_at"] = data[0]["run_started_at"]
                if variant == "reverse":
                    data[0]["run_started_at"] = "2026-10-06T18:00:00Z"
                if variant == "empty":
                    data = []
                if variant == "too_many":
                    data = data * 12
                with self.assertRaises(ShadowCadenceReviewRequired):
                    inspect_shadow_run_arrival_cadence(data)

    def test_two_runs_in_one_bucket_are_not_two_proven_cron_slots(self) -> None:
        source = verified_source()["runs"][:2]
        source[1]["created_at"] = "2026-10-06T18:40:00Z"
        source[1]["run_started_at"] = source[1]["created_at"]
        result = inspect_shadow_run_arrival_cadence(source)
        self.assertEqual(result["unique_natural_successful_runs"], 2)
        self.assertEqual(result["candidate_four_hour_windows"], 1)
        self.assertEqual(result["windows_with_created_run"], 1)
        self.assertEqual(result["windows_without_created_run"], 0)
        self.assertFalse(result["candidate_arrival_bucket_is_trigger_attribution"])
        self.assertFalse(result["missed_trigger_count_proven"])


if __name__ == "__main__":
    unittest.main()
