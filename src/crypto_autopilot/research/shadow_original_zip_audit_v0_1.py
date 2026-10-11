"""Offline validation for previously created Shadow GitHub Actions ZIPs.

This library accepts archive bytes and GitHub API metadata from a caller.
It never fetches, dispatches, collects, backfills, writes or trades.
Integrity against caller-supplied metadata is NOT independent GitHub
attestation; an external authorized caller must establish source provenance.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from zipfile import BadZipFile, ZipFile

from crypto_autopilot.research.prospective_shadow_continuity_v0_1 import (
    ContinuityReviewRequired, inspect_shadow_batch_continuity,
)

MAX_ARCHIVE_BYTES = 2_097_152
MAX_REPORT_BYTES = 2_097_152
CAPTURE_CLOCK_TOLERANCE_MS = 180_000
WORKFLOW_PATH = ".github/workflows/prospective-shadow-collection-v0-1.yml"
WORKFLOW_NAME = "Prospective Shadow Collection V0.1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_SHA = re.compile(r"[0-9a-f]{40}\Z")


class OriginalZipReviewRequired(ValueError):
    """Fail-closed status code; source content is not included in errors."""


def _require(ok: bool, code: str) -> None:
    if not ok:
        raise OriginalZipReviewRequired(code)


def _utc_ms(timestamp: object) -> int:
    _require(isinstance(timestamp, str) and timestamp.endswith("Z"), "RUN_TIME")
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        raise OriginalZipReviewRequired("RUN_TIME") from None
    _require(parsed.tzinfo == timezone.utc, "RUN_TIME")
    return int(parsed.timestamp() * 1_000)


def verify_existing_original_zip(
    raw_zip: bytes,
    expected: Mapping[str, object],
    run: Mapping[str, object],
    artifact: Mapping[str, object],
    jobs: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Validate ONE original ZIP plus caller-supplied GitHub REST identities.

    expected: run_id, run_number, artifact_id, created_at_utc,
    head_sha and zip_sha256. Never infer original cron scheduled-for slots.
    """
    _require(type(raw_zip) is bytes and 0 < len(raw_zip) <= MAX_ARCHIVE_BYTES, "ZIP_SIZE")
    _require(all(isinstance(x, Mapping) for x in (expected, run, artifact)), "METADATA_SHAPE")
    run_id = expected.get("run_id")
    artifact_id = expected.get("artifact_id")
    run_number = expected.get("run_number")
    sha = expected.get("head_sha")
    digest = expected.get("zip_sha256")
    created = expected.get("created_at_utc")
    _require(all(type(v) is int and v > 0 for v in (run_id, artifact_id, run_number)),
             "EXPECTED_IDENTITIES")
    _require(isinstance(sha, str) and bool(_SHA.fullmatch(sha)), "EXPECTED_SHA")
    _require(isinstance(digest, str) and bool(_SHA256.fullmatch(digest)), "EXPECTED_DIGEST")
    created_ms = _utc_ms(created)
    _require(
        run.get("id") == run_id and type(run.get("id")) is int
        and run.get("run_number") == run_number
        and run.get("run_attempt") == 1
        and run.get("event") == "schedule"
        and run.get("name") == WORKFLOW_NAME
        and run.get("path") == WORKFLOW_PATH
        and run.get("head_branch") == "main"
        and run.get("head_sha") == sha
        and run.get("created_at") == created
        and run.get("status") == "completed"
        and run.get("conclusion") == "success",
        "GITHUB_RUN_IDENTITY",
    )
    _require(
        artifact.get("id") == artifact_id and type(artifact.get("id")) is int
        and artifact.get("name") == f"prospective-shadow-v0-1-{run_id}-1"
        and artifact.get("digest") == "sha256:" + digest
        and artifact.get("expired") is False,
        "GITHUB_ARTIFACT_IDENTITY",
    )
    origin = artifact.get("workflow_run")
    _require(isinstance(origin, Mapping) and origin.get("id") == run_id,
             "GITHUB_ARTIFACT_RUN_LINEAGE")
    _require(isinstance(jobs, (list, tuple)) and 0 < len(jobs) <= 32, "JOB_LIST")
    collection = [x for x in jobs if isinstance(x, Mapping) and x.get("name") == "collect"]
    _require(
        len(collection) == 1
        and collection[0].get("status") == "completed"
        and collection[0].get("conclusion") == "success"
        and collection[0].get("run_id") == run_id
        and collection[0].get("run_attempt") == 1,
        "COLLECT_JOB",
    )
    _require(hashlib.sha256(raw_zip).hexdigest() == digest, "ORIGINAL_ZIP_DIGEST")
    try:
        with ZipFile(io.BytesIO(raw_zip)) as zipped:
            _require(zipped.namelist() == ["report.json"], "ZIP_LAYOUT")
            info = zipped.getinfo("report.json")
            _require(info.file_size <= MAX_REPORT_BYTES and not info.flag_bits & 1,
                     "ZIP_CONTENT_BOUND")
            _require(not info.is_dir(), "ZIP_LAYOUT")
            report = json.loads(zipped.read("report.json").decode("utf-8"))
    except (BadZipFile, UnicodeError, json.JSONDecodeError, RuntimeError,
            OSError, OverflowError, ValueError, EOFError):
        raise OriginalZipReviewRequired("ZIP_REPORT_UNREADABLE") from None
    _require(isinstance(report, dict), "REPORT_SHAPE")
    embedded = report.get("github")
    _require(
        isinstance(embedded, Mapping)
        and embedded.get("run_id") == str(run_id)
        and embedded.get("run_attempt") == "1"
        and embedded.get("event_name") == "schedule"
        and embedded.get("ref") == "refs/heads/main"
        and embedded.get("sha") == sha,
        "EMBEDDED_RUN_PROVENANCE",
    )
    record = report.get("collection")
    _require(isinstance(record, Mapping), "COLLECTION_MISSING")
    capture = record.get("capture_timestamp_ms")
    _require(
        type(capture) is int
        and created_ms - CAPTURE_CLOCK_TOLERANCE_MS <= capture
        <= created_ms + CAPTURE_CLOCK_TOLERANCE_MS,
        "CAPTURE_VS_RUN_CLOCK",
    )
    try:
        diagnostic = inspect_shadow_batch_continuity([report])
    except ContinuityReviewRequired as exc:
        raise OriginalZipReviewRequired("REPORT_" + str(exc)) from None
    _require(diagnostic["report_count"] == 1
             and diagnostic["execution_authority"] is False
             and diagnostic["production_eligibility_proven"] is False,
             "SINGLETON_UNSAFE")
    return report


def audit_existing_original_zip_batch(
    inputs: Sequence[tuple[bytes, Mapping[str, object], Mapping[str, object],
                           Mapping[str, object], Sequence[Mapping[str, object]]]],
) -> dict[str, object]:
    """Check a bounded collection; provenance comes from the outside caller."""
    _require(isinstance(inputs, (list, tuple)) and 1 <= len(inputs) <= 100, "BATCH_COUNT")
    ids: set[int] = set()
    artifacts: set[int] = set()
    reports = []
    for row in inputs:
        _require(isinstance(row, (list, tuple)) and len(row) == 5, "BATCH_ROW")
        raw, expected, run, artifact, jobs = row
        report = verify_existing_original_zip(raw, expected, run, artifact, jobs)
        run_id = expected["run_id"]
        artifact_id = expected["artifact_id"]
        _require(run_id not in ids and artifact_id not in artifacts, "DUPLICATE_SOURCE")
        ids.add(run_id)
        artifacts.add(artifact_id)
        reports.append(report)
    try:
        continuity = inspect_shadow_batch_continuity(reports)
    except ContinuityReviewRequired as exc:
        raise OriginalZipReviewRequired("BATCH_" + str(exc)) from None
    return {
        "status": continuity["status"],
        "report_count": continuity["report_count"],
        "source_scope": "ZIP_DIGEST_VS_CALLER_SUPPLIED_GITHUB_METADATA",
        "github_source_metadata_independently_authenticated": False,
        "production_eligibility_proven": False,
        "execution_authority": False,
        "continuity": continuity,
    }
