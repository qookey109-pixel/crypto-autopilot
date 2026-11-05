"""Generate Cloud CI-only Paper receipt evidence with isolated fake services.

No production provider, D1 or R2 request is permitted. This script is a test
harness, never a PAPER execution entrypoint or a source of production authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from unittest.mock import patch

from crypto_autopilot.paper.cloud_paper_usage_observation_v0_1 import (
    PaperObservationError, run_observed_slot,
)
from crypto_autopilot.paper.cloud_paper_usage_receipt_v0_1 import write_usage_receipt

_ROOT = Path(__file__).resolve().parents[1]
_RUN = re.compile(r"github-[1-9][0-9]{0,19}-[1-9][0-9]{0,9}")
_SHA = re.compile(r"[0-9a-f]{40}")


def produce_evidence(output, *, run_id, source_sha):
    """Run success and ambiguous-response fixtures and emit redacted receipts."""
    if (not isinstance(run_id, str) or not _RUN.fullmatch(run_id)
            or not isinstance(source_sha, str) or not _SHA.fullmatch(source_sha)):
        raise ValueError("SYNTHETIC_EVIDENCE_IDENTITY_INVALID")
    if not isinstance(output, (str, Path)):
        raise ValueError("SYNTHETIC_EVIDENCE_OUTPUT_INVALID")
    output = Path(output)
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    success_dir = output / "completed"
    failure_dir = output / "ambiguous"
    success_dir.mkdir(mode=0o700)
    failure_dir.mkdir(mode=0o700)
    test_dir = str(_ROOT / "tests")
    added = test_dir not in sys.path
    if added:
        sys.path.insert(0, test_dir)
    try:
        import test_paper_v05_prepaid_runtime_v0_1 as paper
        import test_prepaid_d1_runtime_v0_1 as fixtures

        success = paper.PaperV05RuntimeTests("test_default_disabled_has_no_requests")
        success.setUp()
        try:
            _, _, statements, opener = success.outer.transport()
            with patch(fixtures.CLIENT_MODULE + ".build_opener", return_value=opener):
                report, observed = run_observed_slot(
                    success.runtime(), tick_ms=success.f.now, previous_slot=None,
                    activation_enabled=True, run_id=run_id,
                )
            calls = success.f.sdk.calls
            actual = {name: sum(call["operation"] == name for call in calls)
                      for name in ("PUT", "GET", "LIST")}
            if (report.get("state") != "NO_TRADE"
                    or observed.get("status") != "OBSERVED_RETURNED"
                    or observed.get("r2_sdk_attempts") != actual
                    or observed.get("d1_transport_attempts") != len(statements)):
                raise ValueError("SYNTHETIC_SUCCESS_VALIDATION_FAILED")
            saved_success = write_usage_receipt(success_dir, observed, report=report)
        finally:
            success.doCleanups()

        failed = paper.PaperV05RuntimeTests("test_default_disabled_has_no_requests")
        failed.setUp()
        try:
            db, _, _, _ = failed.outer.transport()
            def lost(request, timeout):
                payload = json.loads(request.data)
                db.execute(payload["sql"], tuple(payload["params"])).fetchall()
                db.commit()
                raise OSError("synthetic-lost-response")
            with patch(fixtures.CLIENT_MODULE + ".build_opener") as network:
                network.return_value.open.side_effect = lost
                try:
                    run_observed_slot(
                        failed.runtime(), tick_ms=failed.f.now, previous_slot=None,
                        activation_enabled=True, run_id=run_id,
                    )
                except PaperObservationError as error:
                    partial = error.receipt
                else:
                    raise ValueError("SYNTHETIC_FAILURE_NOT_OBSERVED")
            if (partial.get("status") != "REVIEW_REQUIRED"
                    or partial.get("d1_transport_attempts") != 1
                    or partial.get("report_id") is not None
                    or failed.f.sdk.calls
                    or db.execute(
                        "SELECT COUNT(*) FROM cloudflare_shared_writer_reservations_v0_3"
                    ).fetchone()[0] != 1):
                raise ValueError("SYNTHETIC_FAILURE_VALIDATION_FAILED")
            saved_failure = write_usage_receipt(failure_dir, partial)
        finally:
            failed.doCleanups()

        manifest = {
            "schema": "qookey-cloud-paper-synthetic-receipt-evidence-v0.1",
            "evidence_type": "SYNTHETIC_CI_ONLY",
            "run_id_unattested": run_id,
            "source_sha_unattested": source_sha,
            "production_data_service_access": False,
            "provider_access": False, "r2_access": False, "d1_access": False,
            "production_readiness_proven": False,
            "scenarios": {
                "completed": {"state": "NO_TRADE", "receipt_sha256": saved_success["sha256"]},
                "ambiguous": {"state": "REVIEW_REQUIRED", "receipt_sha256": saved_failure["sha256"]},
            },
        }
        with (output / "manifest.json").open("x", encoding="utf-8") as handle:
            json.dump(manifest, handle, sort_keys=True, separators=(",", ":"), allow_nan=False)
            handle.write("\n")
        return manifest
    finally:
        if added:
            sys.path.remove(test_dir)



def verify_downloaded_evidence(expected, downloaded):
    """Require exact artifact file set and byte-for-byte uploaded readback."""
    expected, downloaded = Path(expected), Path(downloaded)
    names = (
        "manifest.json",
        "completed/cloud-paper-usage-observation.json",
        "ambiguous/cloud-paper-usage-observation.json",
    )
    for root in (expected, downloaded):
        if root.is_symlink() or not root.is_dir():
            raise ValueError("SYNTHETIC_ARTIFACT_DIRECTORY_INVALID")
        actual = []
        for item in root.rglob("*"):
            if item.is_symlink():
                raise ValueError("SYNTHETIC_ARTIFACT_SYMLINK")
            if item.is_file():
                actual.append(item.relative_to(root).as_posix())
            elif not item.is_dir():
                raise ValueError("SYNTHETIC_ARTIFACT_OBJECT_INVALID")
        if sorted(actual) != sorted(names):
            raise ValueError("SYNTHETIC_ARTIFACT_FILE_SET_MISMATCH")
    for name in names:
        before = (expected / name).read_bytes()
        after = (downloaded / name).read_bytes()
        if len(before) > 8192 or before != after:
            raise ValueError("SYNTHETIC_ARTIFACT_READBACK_MISMATCH")
    manifest = json.loads((downloaded / "manifest.json").read_bytes())
    if manifest.get("evidence_type") != "SYNTHETIC_CI_ONLY":
        raise ValueError("SYNTHETIC_ARTIFACT_LABEL_MISSING")
    for scenario in ("completed", "ambiguous"):
        body = (downloaded / scenario / "cloud-paper-usage-observation.json").read_bytes()
        if hashlib.sha256(body).hexdigest() != manifest["scenarios"][scenario]["receipt_sha256"]:
            raise ValueError("SYNTHETIC_ARTIFACT_DIGEST_MISMATCH")
    return {"status": "SYNTHETIC_ARTIFACT_READBACK_VERIFIED", "files": len(names)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--synthetic-only", action="store_true", required=True)
    parser.add_argument("--verify-dir")
    args = parser.parse_args()
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("GITHUB_REPOSITORY") != "qookey109-pixel/crypto-autopilot"
            or os.environ.get("GITHUB_EVENT_NAME") not in ("pull_request", "push")):
        raise SystemExit("SYNTHETIC_EVIDENCE_GITHUB_CI_REQUIRED")
    run_id = f'github-{os.environ.get("GITHUB_RUN_ID", "")}-{os.environ.get("GITHUB_RUN_ATTEMPT", "")}'
    if args.verify_dir:
        print(json.dumps(verify_downloaded_evidence(args.output, args.verify_dir), sort_keys=True))
    else:
        manifest = produce_evidence(args.output, run_id=run_id,
                                    source_sha=os.environ.get("GITHUB_SHA", ""))
        print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
