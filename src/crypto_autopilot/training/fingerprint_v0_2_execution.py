"""Successor execution binding for the frozen Core100 V0.2 identity contract.

This module keeps the V0.2 identity payload and comparison rules while accepting
only a reviewed successor contract that preserves the parent identity section
and pins the active workflow blob.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from .fingerprint_v0_2 import FingerprintValidationError, normalize_runtime_manifest


class SuccessorContractError(ValueError):
    """Successor contract or fingerprint evidence is invalid."""


def _require(condition: bool, message: str = "invalid successor fingerprint evidence") -> None:
    if not condition:
        raise SuccessorContractError(message)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_sha256(value: Any) -> str:
    canonical = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return _sha256(canonical)


def validate_successor_contract(
    *, contract_bytes: bytes, expected_sha256: str, parent_contract_bytes: bytes
) -> dict[str, Any]:
    _require(_sha256(contract_bytes) == expected_sha256, "successor contract digest mismatch")
    try:
        contract = json.loads(contract_bytes)
        parent = json.loads(parent_contract_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SuccessorContractError("invalid successor contract JSON") from exc
    _require(isinstance(contract, dict) and isinstance(parent, dict))
    _require(
        contract.get("schema") == "qookey-core100-training-fingerprint-v0.2-successor-v0.1"
        and contract.get("status") == "PREPARED_NOT_ACTIVE",
        "successor contract is not prepared",
    )
    _require(
        contract.get("parent_contract_sha256") == _sha256(parent_contract_bytes),
        "parent contract digest mismatch",
    )
    _require(
        contract.get("identity_contract") == parent.get("identity_contract"),
        "successor changed frozen V0.2 identity semantics",
    )
    context = contract.get("execution_context")
    _require(isinstance(context, dict))
    _require(
        context.get("workflow_path") == ".github/workflows/binance-usdm-detailed-training-v0-1.yml"
        and context.get("workflow_blob_sha_at_preparation"),
        "successor execution workflow anchor is missing",
    )
    _require(
        context.get("current_training_authority_receipt_path")
        == parent.get("execution_context", {}).get("current_training_authority_receipt_path")
        and context.get("authority_receipt_blob_sha_at_preparation")
        == parent.get("execution_context", {}).get("authority_receipt_blob_sha_at_preparation"),
        "successor changed the existing data authority anchor",
    )
    identity = contract["identity_contract"]
    paths = identity["code_paths"] + identity["support_paths"] + identity["runtime_guard_paths"]
    paths = sorted(set(paths) | {context["workflow_path"], context["current_training_authority_receipt_path"]})
    _require(len(paths) > 0 and len(paths) == len(set(paths)))
    contract["contract_sha256"] = expected_sha256
    return contract


def _context_anchors(contract: Mapping[str, Any]) -> dict[str, str]:
    context = contract["execution_context"]
    return {
        context["workflow_path"]: context["workflow_blob_sha_at_preparation"],
        context["current_training_authority_receipt_path"]:
            context["authority_receipt_blob_sha_at_preparation"],
    }


def build_fingerprint(
    *,
    contract: Mapping[str, Any],
    dataset_fingerprint: str,
    git_blobs: Mapping[str, str],
    runtime_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    identity = contract["identity_contract"]
    expected_paths = set(
        identity["code_paths"] + identity["support_paths"] + identity["runtime_guard_paths"]
    )
    expected_paths.update(_context_anchors(contract))
    _require(set(git_blobs) == expected_paths, "successor fingerprint source inventory mismatch")
    for blob in git_blobs.values():
        _require(isinstance(blob, str) and len(blob) == 40 and all(c in "0123456789abcdef" for c in blob))
    _require(
        isinstance(dataset_fingerprint, str)
        and len(dataset_fingerprint) == 64
        and all(c in "0123456789abcdef" for c in dataset_fingerprint),
        "invalid dataset fingerprint",
    )
    blobs = {path: git_blobs[path] for path in sorted(expected_paths)}
    runtime = normalize_runtime_manifest(runtime_manifest)
    payload = {
        "schema": identity["schema"],
        "dataset_fingerprint": dataset_fingerprint,
        "code_git_blobs": sorted((path, blobs[path]) for path in identity["code_paths"]),
        "support_git_blobs": sorted((path, blobs[path]) for path in identity["support_paths"]),
        "runtime_manifest": runtime,
    }
    guard = sorted((path, blobs[path]) for path in identity["runtime_guard_paths"])
    return {
        "schema": "qookey-core100-training-fingerprint-evidence-v0.2",
        "status": "PREPARED_NOT_ACTIVE",
        "contract_sha256": contract["contract_sha256"],
        "dataset_fingerprint": dataset_fingerprint,
        "git_blobs": blobs,
        "runtime_manifest": runtime,
        "experiment_fingerprint": _canonical_sha256(payload),
        "runtime_guard_fingerprint": _canonical_sha256(guard),
    }


def compare_fingerprints(
    *, current: Mapping[str, Any], previous: Mapping[str, Any] | None
) -> dict[str, Any]:
    if previous is None:
        return {"status": "REVIEW_REQUIRED", "reason": "NO_PREVIOUS_V0_2_EVIDENCE"}
    try:
        if current.get("schema") != "qookey-core100-training-fingerprint-evidence-v0.2":
            raise SuccessorContractError()
        if previous.get("schema") != "qookey-core100-training-fingerprint-evidence-v0.2":
            raise SuccessorContractError()
        if current.get("contract_sha256") != previous.get("contract_sha256"):
            return {"status": "REVIEW_REQUIRED", "reason": "SUCCESSOR_CONTRACT_CHANGED"}
        if current.get("git_blobs") != previous.get("git_blobs"):
            return {"status": "REVIEW_REQUIRED", "reason": "SOURCE_OR_EXECUTION_CONTEXT_CHANGED"}
        if current.get("runtime_guard_fingerprint") != previous.get("runtime_guard_fingerprint"):
            return {"status": "REVIEW_REQUIRED", "reason": "RUNTIME_GUARD_CHANGED"}
        if current.get("runtime_manifest") != previous.get("runtime_manifest"):
            return {"status": "REVIEW_REQUIRED", "reason": "RUNTIME_CHANGED"}
        if current.get("dataset_fingerprint") != previous.get("dataset_fingerprint"):
            return {"status": "REVIEW_REQUIRED", "reason": "DATASET_CHANGED"}
        if current.get("experiment_fingerprint") != previous.get("experiment_fingerprint"):
            return {"status": "REVIEW_REQUIRED", "reason": "RESULT_INPUT_CHANGED"}
    except (SuccessorContractError, TypeError, KeyError):
        return {"status": "REVIEW_REQUIRED", "reason": "INVALID_V0_2_EVIDENCE"}
    return {"status": "NO_CHANGE", "reason": "EXACT_V0_2_FINGERPRINT_MATCH"}
