"""Prepare a bounded, create-once cloud-runner usage observation file.

This module does not upload artifacts or grant runtime, provider, D1 or R2
authority. A runner interruption before an artifact upload can still lose the
file. Returned counters are process observations, not billing evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
from pathlib import Path

from crypto_autopilot.paper.cloud_loop_v0_1 import digest

_NAME = "cloud-paper-usage-observation.json"
_MAX_BYTES = 8192
_RUN_ID = re.compile(r"github-[1-9][0-9]{0,19}-[1-9][0-9]{0,9}")
_SLOT_ID = re.compile(r"0|[1-9][0-9]{0,19}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_FIELDS = {
    "schema", "status", "run_id_unattested", "slot_id", "report_id",
    "r2_sdk_attempts", "r2_reserved_class_a", "r2_reserved_class_b",
    "r2_reserved_payload_bytes", "provider_reserved_attempts",
    "d1_transport_attempts", "d1_ticket_debits", "d1_rows_read",
    "d1_rows_written", "provider_confirmed_billing",
    "account_wide_coverage_proven", "identity_attested", "survives_process_loss",
}
_COUNTS = (
    "r2_reserved_class_a", "r2_reserved_class_b", "r2_reserved_payload_bytes",
    "provider_reserved_attempts", "d1_transport_attempts", "d1_ticket_debits",
)
_FALSE = (
    "provider_confirmed_billing", "account_wide_coverage_proven",
    "identity_attested", "survives_process_loss",
)


def _valid_count(value):
    return type(value) is int and 0 <= value <= 1_000_000_000


def _serialize(observation, report):
    if not isinstance(observation, dict) or set(observation) != _FIELDS:
        raise ValueError("PAPER_USAGE_RECEIPT_INVALID")
    if (observation["schema"] != "qookey-cloud-paper-usage-observation-v0.1"
            or observation["status"] not in ("OBSERVED_RETURNED", "REVIEW_REQUIRED")
            or not isinstance(observation["run_id_unattested"], str)
            or not _RUN_ID.fullmatch(observation["run_id_unattested"])
            or any(not _valid_count(observation[k]) for k in _COUNTS)
            or any(observation[k] is not False for k in _FALSE)
            or observation["d1_rows_read"] is not None
            or observation["d1_rows_written"] is not None):
        raise ValueError("PAPER_USAGE_RECEIPT_INVALID")
    sdk = observation["r2_sdk_attempts"]
    if (not isinstance(sdk, dict) or set(sdk) != {"PUT", "GET", "LIST"}
            or any(not _valid_count(v) for v in sdk.values())
            or sdk["PUT"] + sdk["LIST"] > observation["r2_reserved_class_a"]
            or sdk["GET"] > observation["r2_reserved_class_b"]
            or observation["d1_transport_attempts"] > observation["d1_ticket_debits"]):
        raise ValueError("PAPER_USAGE_RECEIPT_INVALID")

    if observation["status"] == "OBSERVED_RETURNED":
        slot, report_id = observation["slot_id"], observation["report_id"]
        if (not isinstance(slot, str) or not _SLOT_ID.fullmatch(slot)
                or not isinstance(report_id, str) or not _SHA256.fullmatch(report_id)
                or not isinstance(report, dict)
                or report.get("schema") != "qookey-cloud-paper-loop-report-v0.3"
                or report.get("state") not in ("NO_TRADE", "COMMITTED")
                or report.get("slot_id") != slot):
            raise ValueError("PAPER_USAGE_REPORT_BINDING_INVALID")
        try:
            report_digest = digest(report)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("PAPER_USAGE_REPORT_BINDING_INVALID") from None
        if report_digest != report_id:
            raise ValueError("PAPER_USAGE_REPORT_BINDING_INVALID")
    elif (report is not None or observation["slot_id"] is not None
          or observation["report_id"] is not None):
        raise ValueError("PAPER_USAGE_REPORT_BINDING_INVALID")
    try:
        body = (json.dumps(observation, sort_keys=True, separators=(",", ":"),
                           allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError, UnicodeError, OverflowError):
        raise ValueError("PAPER_USAGE_RECEIPT_INVALID") from None
    if len(body) > _MAX_BYTES:
        raise ValueError("PAPER_USAGE_RECEIPT_OVERSIZED")
    return body


def write_usage_receipt(directory, observation, *, report=None):
    """Write a fully validated receipt once into an existing trusted runner dir.

    A temporary file is fsynced before an exclusive same-directory hard link
    publishes the final name. Existing files and symlinks are never replaced.
    A completed file is still not an uploaded artifact or durable cloud proof.
    """
    body = _serialize(observation, report)
    if not isinstance(directory, (str, Path)):
        raise ValueError("PAPER_USAGE_OUTPUT_DIRECTORY_INVALID")
    directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    temporary = ".paper-usage-" + secrets.token_hex(16) + ".tmp"
    fd = None
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=directory_fd)
        with os.fdopen(fd, "wb") as handle:
            fd = None
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, _NAME, src_dir_fd=directory_fd, dst_dir_fd=directory_fd,
                follow_symlinks=False)
        os.fsync(directory_fd)
    finally:
        if fd is not None:
            os.close(fd)
        try:
            os.unlink(temporary, dir_fd=directory_fd)
        except FileNotFoundError:
            pass
        os.close(directory_fd)
    return {"name": _NAME, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
