from __future__ import annotations

import copy
import hashlib
import io
import json
import unittest
from datetime import datetime, timezone
from zipfile import ZIP_DEFLATED, ZipFile

from crypto_autopilot.research.shadow_original_zip_audit_v0_1 import (
    OriginalZipReviewRequired,
    audit_existing_original_zip_batch,
    verify_existing_original_zip,
)
from test_prospective_shadow_continuity_v0_1 import report_fixture


def canonical_digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()


def zip_report(report, *, extra=False):
    data = json.dumps(report, separators=(",", ":")).encode()
    output = io.BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as zipped:
        zipped.writestr("report.json", data)
        if extra:
            zipped.writestr("surprise.txt", "not part of the original contract")
    return output.getvalue()


def fixture(index):
    report = report_fixture(index)
    run_id = int(report["github"]["run_id"])
    artifact_id = 999000 + index
    run_number = index + 1
    created = datetime.fromtimestamp(
        report["collection"]["capture_timestamp_ms"] / 1000, tz=timezone.utc
    ).isoformat().replace("+00:00", "Z")
    raw = zip_report(report)
    digest = hashlib.sha256(raw).hexdigest()
    expected = {
        "run_id": run_id, "run_number": run_number,
        "artifact_id": artifact_id, "created_at_utc": created,
        "head_sha": report["github"]["sha"], "zip_sha256": digest,
    }
    run = {
        "id": run_id, "run_number": run_number, "run_attempt": 1,
        "event": "schedule", "name": "Prospective Shadow Collection V0.1",
        "path": ".github/workflows/prospective-shadow-collection-v0-1.yml",
        "head_branch": "main", "head_sha": report["github"]["sha"],
        "created_at": created, "status": "completed", "conclusion": "success",
    }
    artifact = {
        "id": artifact_id,
        "name": f"prospective-shadow-v0-1-{run_id}-1",
        "digest": "sha256:" + digest, "expired": False,
        "workflow_run": {"id": run_id},
    }
    jobs = [{
        "name": "collect", "status": "completed", "conclusion": "success",
        "run_id": run_id, "run_attempt": 1,
    }]
    return (raw, expected, run, artifact, jobs)


def replace_zip(item, report, **kw):
    raw, expected, run, artifact, jobs = copy.deepcopy(item)
    raw = zip_report(report, **kw)
    digest = hashlib.sha256(raw).hexdigest()
    expected["zip_sha256"] = digest
    artifact["digest"] = "sha256:" + digest
    return raw, expected, run, artifact, jobs


class PureExistingShadowZipAuditTests(unittest.TestCase):
    def test_valid_archive_and_two_consistent_natural_runs(self):
        item = fixture(0)
        report = verify_existing_original_zip(*item)
        self.assertEqual(report["github"]["run_id"], "10000")
        result = audit_existing_original_zip_batch([fixture(1), fixture(0)])
        self.assertEqual(result["report_count"], 2)
        self.assertEqual(result["status"], "PARTIAL_OBSERVATION_ONLY")
        self.assertEqual(result["continuity"]["shared_overlapping_candles_consistent"], 1180)
        self.assertFalse(result["github_source_metadata_independently_authenticated"])
        self.assertFalse(result["production_eligibility_proven"])
        self.assertFalse(result["execution_authority"])
        self.assertFalse(result["continuity"]["source_archive_digests_authenticated"])

    def test_actual_bytes_and_artifact_digest_must_match(self):
        raw, expected, run, artifact, jobs = fixture(0)
        cases = [
            (raw + b"extra", expected, run, artifact, jobs),
            (raw, {**expected, "zip_sha256": "a" * 64}, run, artifact, jobs),
            (raw, expected, run, {**artifact, "digest": "sha256:" + "a" * 64}, jobs),
        ]
        for row in cases:
            with self.subTest(case=len(row[0])), self.assertRaises(OriginalZipReviewRequired):
                verify_existing_original_zip(*row)

    def test_source_run_identity_and_collector_job_fail_closed(self):
        base = fixture(0)
        for group, field, bad in (
            (1, "head_sha", "b" * 40),
            (1, "created_at_utc", "2026-10-10T00:00:00Z"),
            (2, "event", "workflow_dispatch"),
            (2, "run_attempt", 2),
            (2, "head_branch", "research"),
            (2, "conclusion", "failure"),
            (2, "path", "other.yml"),
            (3, "expired", True),
            (3, "workflow_run", {"id": 0}),
        ):
            values = copy.deepcopy(base)
            values[group][field] = bad
            with self.subTest(group=group, field=field), self.assertRaises(
                OriginalZipReviewRequired
            ):
                verify_existing_original_zip(*values)

        values = copy.deepcopy(base)
        values[4][0]["conclusion"] = "failure"
        with self.assertRaisesRegex(OriginalZipReviewRequired, "COLLECT_JOB"):
            verify_existing_original_zip(*values)

    def test_zip_layout_bombs_and_embedded_provenance_rejected(self):
        original = fixture(0)
        report = verify_existing_original_zip(*original)
        for changed in (
            replace_zip(original, report, extra=True),
            replace_zip(original, {**report, "github": {
                **report["github"], "event_name": "workflow_dispatch",
            }}),
        ):
            with self.assertRaises(OriginalZipReviewRequired):
                verify_existing_original_zip(*changed)
        giant_zip = io.BytesIO()
        with ZipFile(giant_zip, "w", compression=ZIP_DEFLATED) as z:
            z.writestr("report.json", " " * (2_097_152 + 1))
        raw, expected, run, artifact, jobs = copy.deepcopy(original)
        raw = giant_zip.getvalue()
        expected["zip_sha256"] = hashlib.sha256(raw).hexdigest()
        artifact["digest"] = "sha256:" + expected["zip_sha256"]
        with self.assertRaisesRegex(OriginalZipReviewRequired, "ZIP_CONTENT_BOUND"):
            verify_existing_original_zip(raw, expected, run, artifact, jobs)

    def test_capture_time_cannot_be_backdated_or_future_leaked(self):
        original = fixture(0)
        report = copy.deepcopy(verify_existing_original_zip(*original))
        report["collection"]["capture_timestamp_ms"] += 180_001
        record = report["collection"]
        record["record_id"] = canonical_digest({
            k: v for k, v in record.items() if k != "record_id"
        })
        with self.assertRaisesRegex(OriginalZipReviewRequired, "CAPTURE_VS_RUN_CLOCK"):
            verify_existing_original_zip(*replace_zip(original, report))

    def test_cross_batch_revision_detected_even_if_rehashed(self):
        original = fixture(1)
        changed = copy.deepcopy(verify_existing_original_zip(*original))
        # Later window has four newly closed hours; -8 is in the shared history.
        candle = changed["collection"]["market_evidence"][0]["candles_60m"][-8]
        candle["close"] += 1
        market = changed["collection"]["market_evidence"][0]
        market["candles_sha256"] = canonical_digest(market["candles_60m"])
        record = changed["collection"]
        record["record_id"] = canonical_digest({
            k: v for k, v in record.items() if k != "record_id"
        })
        changed_zip = replace_zip(original, changed)
        self.assertEqual(
            verify_existing_original_zip(*changed_zip)["github"]["run_id"], "10001"
        )
        with self.assertRaisesRegex(OriginalZipReviewRequired, "REVISED_OVERLAPPING_CANDLE"):
            audit_existing_original_zip_batch([fixture(0), changed_zip])

    def test_duplication_and_unsupported_batch_shape_are_rejected(self):
        item = fixture(0)
        with self.assertRaisesRegex(OriginalZipReviewRequired, "DUPLICATE_SOURCE"):
            audit_existing_original_zip_batch([item, item])
        with self.assertRaisesRegex(OriginalZipReviewRequired, "BATCH_COUNT"):
            audit_existing_original_zip_batch([])
        with self.assertRaisesRegex(OriginalZipReviewRequired, "BATCH_ROW"):
            audit_existing_original_zip_batch([(1, 2)])

    def test_research_context_count_cannot_become_production_authority(self):
        items = [fixture(i) for i in range(21)]
        result = audit_existing_original_zip_batch(items)
        self.assertEqual(result["report_count"], 21)
        self.assertEqual(result["continuity"]["context_warmup_state"], "COUNT_REACHED_NOT_VALIDATED")
        self.assertFalse(result["production_eligibility_proven"])
        self.assertFalse(result["execution_authority"])
        self.assertFalse(result["github_source_metadata_independently_authenticated"])


if __name__ == "__main__":
    unittest.main()
