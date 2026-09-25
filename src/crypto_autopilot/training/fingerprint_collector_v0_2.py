"""Cloud-runner-only evidence collection prototype for Core100 fingerprint V0.2.

This module collects checkout blob IDs and runtime metadata only. It does not
fetch dataset or provider data, read R2, compare production pointers, train, or
write artifacts. It is not imported by the active weekly training workflow.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import re
import sys
import sysconfig
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from .fingerprint_v0_2 import CONTRACT_SHA256, FingerprintValidationError, normalize_runtime_manifest


class EvidenceCollectionError(RuntimeError):
    """Cloud runner evidence is missing, stale, or outside the prepared contract."""


def _require_github_actions(environ: Mapping[str, str]) -> None:
    if environ.get("GITHUB_ACTIONS") != "true":
        raise EvidenceCollectionError("GitHub Actions runner required")


def _contract(contract_bytes: bytes) -> dict[str, Any]:
    if not isinstance(contract_bytes, bytes):
        raise EvidenceCollectionError("Invalid fingerprint contract")
    if hashlib.sha256(contract_bytes).hexdigest() != CONTRACT_SHA256:
        raise EvidenceCollectionError("Fingerprint contract digest mismatch")
    try:
        contract = json.loads(contract_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceCollectionError("Invalid fingerprint contract") from exc
    if not isinstance(contract, dict):
        raise EvidenceCollectionError("Invalid fingerprint contract")
    return contract


def _required_paths(contract: Mapping[str, Any]) -> list[str]:
    try:
        identity = contract["identity_contract"]
        context = contract["execution_context"]
        paths = set(identity["code_paths"])
        paths.update(identity["support_paths"])
        paths.update(identity["runtime_guard_paths"])
        paths.update((context["workflow_path"], context["current_training_authority_receipt_path"]))
    except (KeyError, TypeError) as exc:
        raise EvidenceCollectionError("Incomplete fingerprint contract inventory") from exc
    if not paths or any(not isinstance(path, str) or not path for path in paths):
        raise EvidenceCollectionError("Invalid fingerprint contract inventory")
    return sorted(paths)


def _safe_file(root: Path, relative_path: str) -> Path:
    rel = PurePosixPath(relative_path)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise EvidenceCollectionError("Unsafe source inventory path")
    root_resolved = root.resolve(strict=True)
    try:
        candidate = root_resolved.joinpath(*rel.parts).resolve(strict=True)
    except OSError as exc:
        raise EvidenceCollectionError("Required source inventory file is missing") from exc
    if root_resolved not in candidate.parents or not candidate.is_file():
        raise EvidenceCollectionError("Required source inventory file is invalid")
    return candidate


def _git_blob_sha(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def collect_git_blob_map(
    *,
    contract_bytes: bytes,
    project_root: Path,
    checkout_sha: str,
    live_main_sha: str,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Collect exact contract-input blobs after a fresh main/checkout match.

    checkout_sha and live_main_sha must be obtained by the cloud workflow from
    GitHub. This function makes no network calls and does not authenticate them.
    """
    env = os.environ if environ is None else environ
    _require_github_actions(env)
    contract = _contract(contract_bytes)
    sha_pattern = re.compile(r"[0-9a-f]{40}")
    if not isinstance(checkout_sha, str) or sha_pattern.fullmatch(checkout_sha) is None:
        raise EvidenceCollectionError("Invalid checkout SHA")
    if not isinstance(live_main_sha, str) or sha_pattern.fullmatch(live_main_sha) is None:
        raise EvidenceCollectionError("Invalid live main SHA")
    if checkout_sha != live_main_sha:
        raise EvidenceCollectionError("Checkout is not the current main commit")

    blobs: dict[str, str] = {}
    for relative_path in _required_paths(contract):
        try:
            payload = _safe_file(Path(project_root), relative_path).read_bytes()
        except OSError as exc:
            raise EvidenceCollectionError("Unable to read required source inventory file") from exc
        blobs[relative_path] = _git_blob_sha(payload)
    return blobs


def _distribution_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    try:
        installed = importlib.metadata.distributions()
        for distribution in installed:
            name = distribution.metadata.get("Name")
            version = distribution.version
            if not isinstance(name, str) or not name.strip():
                raise EvidenceCollectionError("Installed distribution name is unavailable")
            if not isinstance(version, str) or not version.strip():
                raise EvidenceCollectionError("Installed distribution version is unavailable")
            rows.append({"name": name, "version": version})
    except EvidenceCollectionError:
        raise
    except Exception as exc:
        raise EvidenceCollectionError("Installed distribution inventory is unavailable") from exc
    if not rows:
        raise EvidenceCollectionError("Installed distribution inventory is empty")
    return rows


def collect_runtime_manifest(
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Collect an isolated Python runtime manifest on a GitHub Actions runner.

    The workflow must create the isolated project environment and set
    CORE100_FINGERPRINT_ISOLATED_ENVIRONMENT=true only after doing so.
    """
    env = os.environ if environ is None else environ
    _require_github_actions(env)
    if env.get("CORE100_FINGERPRINT_ISOLATED_ENVIRONMENT") != "true":
        raise EvidenceCollectionError("Isolated project environment is not attested")

    distributions = _distribution_rows()
    normalized_versions: dict[str, str] = {}
    for row in distributions:
        normalized = re.sub(r"[-_.]+", "-", row["name"]).lower()
        if normalized in normalized_versions:
            raise EvidenceCollectionError("Installed distribution names are ambiguous")
        normalized_versions[normalized] = row["version"]

    required_tools = ("pip", "setuptools")
    if any(name not in normalized_versions for name in required_tools):
        raise EvidenceCollectionError("Required install-tool versions are unavailable")
    project_version = normalized_versions.get("qookey-crypto-autopilot")
    if project_version is None:
        raise EvidenceCollectionError("Installed project version is unavailable")

    image_os, image_version = env.get("ImageOS"), env.get("ImageVersion")
    runner_image = {"os": image_os, "version": image_version} if image_os and image_version else None
    raw: dict[str, Any] = {
        "implementation": sys.implementation.name,
        "version": sys.version,
        "cache_tag": sys.implementation.cache_tag,
        "platform": sysconfig.get_platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "libc": list(platform.libc_ver()),
        "distributions": distributions,
        "install_tools": [
            {"name": name, "version": normalized_versions[name]}
            for name in required_tools
        ],
        "project_version": project_version,
        "runner_image": runner_image,
        "isolated_environment": True,
        "distribution_inventory_complete": True,
        "install_tools_complete": True,
    }
    try:
        return normalize_runtime_manifest(raw)
    except FingerprintValidationError as exc:
        raise EvidenceCollectionError("Runtime manifest failed contract validation") from exc
