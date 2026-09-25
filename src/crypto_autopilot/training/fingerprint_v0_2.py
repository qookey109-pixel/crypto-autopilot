"""Pure comparison prototype for the frozen Core100 V0.2 preparation contract.

Inputs are caller-supplied evidence, not authenticated observations. This module
does not collect runtime facts, read files, access storage, or invoke training.
Even NO_CHANGE is a preparation result and grants no execution authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any


CONTRACT_SHA256 = "2ee82c6d030c3ebdb49b985220f07a7e7c1109f4fef7c15b27fba0ae02922d2a"
EVIDENCE_SCHEMA = "qookey-core100-training-prepared-evidence-v0.2"
_TEXT_FIELDS = {
    "implementation", "version", "cache_tag", "platform", "system", "release", "machine",
}
_ATTESTATIONS = {
    "isolated_environment", "distribution_inventory_complete", "install_tools_complete",
}
_RUNTIME_FIELDS = _TEXT_FIELDS | _ATTESTATIONS | {
    "libc", "distributions", "install_tools", "project_version", "runner_image",
}
_EVIDENCE_FIELDS = {
    "schema", "status", "contract_sha256", "dataset_fingerprint", "git_blobs",
    "runtime_manifest", "experiment_fingerprint", "runtime_guard_fingerprint",
}


class FingerprintValidationError(ValueError):
    """Required preparation evidence is missing, malformed, or inconsistent."""


def _require(condition: bool) -> None:
    if not condition:
        # Never echo arbitrary caller-supplied values in validation errors.
        raise FingerprintValidationError("Invalid or incomplete preparation evidence")


def _text(value: Any) -> str:
    _require(isinstance(value, str) and bool(value.strip()))
    _require(not any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in value))
    return value


def _hex(value: Any, length: int) -> str:
    _require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{%d}" % length, value) is not None)
    return value


def _contract(contract_bytes: bytes) -> dict[str, Any]:
    _require(isinstance(contract_bytes, bytes))
    _require(hashlib.sha256(contract_bytes).hexdigest() == CONTRACT_SHA256)
    # The digest pins the complete reviewed contract, including path inventories,
    # execution-context anchors and all false execution-authority flags.
    return json.loads(contract_bytes)


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _distributions(rows: Any) -> list[dict[str, str]]:
    _require(isinstance(rows, list) and bool(rows))
    normalized: dict[str, str] = {}
    for row in rows:
        _require(isinstance(row, Mapping) and set(row) == {"name", "version"})
        name = _text(row["name"])
        _require(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?", name) is not None)
        name = re.sub(r"[-_.]+", "-", name).lower()
        _require(name not in normalized)
        normalized[name] = _text(row["version"])
    return [{"name": name, "version": version} for name, version in sorted(normalized.items())]


def normalize_runtime_manifest(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a complete caller-attested isolated runtime; return a fresh copy."""
    _require(isinstance(raw, Mapping) and set(raw) == _RUNTIME_FIELDS)
    runtime: dict[str, Any] = {field: _text(raw[field]) for field in sorted(_TEXT_FIELDS)}
    _require(re.match(r"^[0-9]+\.[0-9]+\.[0-9]+(?:\b|[a-z])", runtime["version"]) is not None)
    for field in sorted(_ATTESTATIONS):
        _require(raw[field] is True)
        runtime[field] = True
    libc = raw["libc"]
    _require(isinstance(libc, list) and len(libc) == 2)
    runtime["libc"] = [_text(part) for part in libc]
    runtime["distributions"] = _distributions(raw["distributions"])
    runtime["install_tools"] = _distributions(raw["install_tools"])
    distributions = {row["name"]: row["version"] for row in runtime["distributions"]}
    install_tools = {row["name"]: row["version"] for row in runtime["install_tools"]}
    _require({"pip", "qookey-crypto-autopilot"} <= set(distributions))
    _require({"pip", "setuptools"} <= set(install_tools))
    _require(all(distributions.get(name, version) == version for name, version in install_tools.items()))
    runtime["project_version"] = _text(raw["project_version"])
    _require(runtime["project_version"] == distributions["qookey-crypto-autopilot"])
    runner_image = raw["runner_image"]
    if runner_image is None:
        runtime["runner_image"] = None
    else:
        _require(isinstance(runner_image, Mapping) and set(runner_image) == {"os", "version"})
        runtime["runner_image"] = {key: _text(runner_image[key]) for key in ("os", "version")}
    return runtime


def _context_anchors(contract: Mapping[str, Any]) -> dict[str, str]:
    context = contract["execution_context"]
    return {
        context["workflow_path"]: context["workflow_blob_sha_at_preparation"],
        context["current_training_authority_receipt_path"]:
            context["authority_receipt_blob_sha_at_preparation"],
    }


def build_fingerprint(
    *,
    contract_bytes: bytes,
    dataset_fingerprint: str,
    git_blobs: Mapping[str, str],
    runtime_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Build synthetic/prepared evidence only; invalid inputs raise validation errors.

    The dataset digest must already bind the catalog and ordered shard receipts.
    This function validates its format; it does not authenticate that binding.
    """
    contract = _contract(contract_bytes)
    identity = contract["identity_contract"]
    paths = set(identity["code_paths"] + identity["support_paths"] + identity["runtime_guard_paths"])
    paths.update(_context_anchors(contract))
    _require(isinstance(git_blobs, Mapping) and set(git_blobs) == paths)
    blobs = {path: _hex(git_blobs[path], 40) for path in sorted(paths)}
    dataset = _hex(dataset_fingerprint, 64)
    runtime = normalize_runtime_manifest(runtime_manifest)
    payload = {
        "schema": identity["schema"],
        "dataset_fingerprint": dataset,
        "code_git_blobs": sorted((path, blobs[path]) for path in identity["code_paths"]),
        "support_git_blobs": sorted((path, blobs[path]) for path in identity["support_paths"]),
        "runtime_manifest": runtime,
    }
    guard = sorted((path, blobs[path]) for path in identity["runtime_guard_paths"])
    return {
        "schema": EVIDENCE_SCHEMA,
        "status": "PREPARED_NOT_ACTIVE",
        "contract_sha256": CONTRACT_SHA256,
        "dataset_fingerprint": dataset,
        "git_blobs": blobs,
        "runtime_manifest": runtime,
        "experiment_fingerprint": _digest(payload),
        "runtime_guard_fingerprint": _digest(guard),
    }


def _validate_evidence(contract_bytes: bytes, record: Any) -> dict[str, Any]:
    _require(isinstance(record, Mapping) and set(record) == _EVIDENCE_FIELDS)
    rebuilt = build_fingerprint(
        contract_bytes=contract_bytes,
        dataset_fingerprint=record["dataset_fingerprint"],
        git_blobs=record["git_blobs"],
        runtime_manifest=record["runtime_manifest"],
    )
    _require(dict(record) == rebuilt)
    return rebuilt


def _result(reason: str, *, exact: bool = False) -> dict[str, Any]:
    return {
        "status": "NO_CHANGE" if exact else "REVIEW_REQUIRED",
        "reason": reason,
        "mode": "PREPARATION_ONLY",
        "execution_authorized": False,
        "training_performed": False,
        "r2_access_performed": False,
        "provider_requests_performed": 0,
    }


def compare_prepared_fingerprints(
    *,
    contract_bytes: bytes,
    current: Mapping[str, Any],
    previous: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Fail closed on absent/legacy/changed evidence; never request execution.

    In particular, the active V0.1 fingerprint's latest-pointer schema already
    ends in v0.2. That pointer is not evidence from this preparation prototype.
    """
    try:
        contract = _contract(contract_bytes)
    except FingerprintValidationError:
        return _result("INVALID_CONTRACT")
    try:
        current_record = _validate_evidence(contract_bytes, current)
    except FingerprintValidationError:
        return _result("INVALID_CURRENT_EVIDENCE")
    anchors = _context_anchors(contract)
    if any(current_record["git_blobs"][path] != blob for path, blob in anchors.items()):
        return _result("EXECUTION_CONTEXT_CHANGED")
    if previous is None:
        return _result("NO_PREVIOUS_EVIDENCE")
    try:
        previous_record = _validate_evidence(contract_bytes, previous)
    except FingerprintValidationError:
        return _result("LEGACY_OR_INCOMPLETE_EVIDENCE")
    if any(previous_record["git_blobs"][path] != blob for path, blob in anchors.items()):
        return _result("EXECUTION_CONTEXT_CHANGED")
    for field, reason in (
        ("runtime_guard_fingerprint", "RUNTIME_GUARD_CHANGED"),
        ("runtime_manifest", "RUNTIME_CHANGED"),
        ("dataset_fingerprint", "DATASET_CHANGED"),
        ("experiment_fingerprint", "RESULT_INPUT_CHANGED"),
    ):
        if current_record[field] != previous_record[field]:
            return _result(reason)
    return _result("EXACT_PREPARED_FINGERPRINT_MATCH", exact=True)
