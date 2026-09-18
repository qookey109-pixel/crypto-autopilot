from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

from crypto_autopilot.paper.run_package_v0_1 import (
    verify_paper_loop_run_package,
)


@dataclass(frozen=True, slots=True)
class PaperRunPackageArtifactPolicy:
    require_verified_package: bool = True
    canonical_json_required: bool = True
    github_artifact_secondary_export_authorized: bool = True
    artifact_is_execution_authority: bool = False
    provider_access_authorized: bool = False
    r2_access_authorized: bool = False
    holdout_access_authorized: bool = False
    account_state_mutation_authorized: bool = False
    automatic_execution_authorized: bool = False
    real_money_order_authorized: bool = False
    live_real_trading_authorized: bool = False

    def __post_init__(self) -> None:
        flags = (
            self.require_verified_package,
            self.canonical_json_required,
            self.github_artifact_secondary_export_authorized,
            self.artifact_is_execution_authority,
            self.provider_access_authorized,
            self.r2_access_authorized,
            self.holdout_access_authorized,
            self.account_state_mutation_authorized,
            self.automatic_execution_authorized,
            self.real_money_order_authorized,
            self.live_real_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in flags):
            raise ValueError("artifact export policy flags must be booleans")
        if not self.require_verified_package or not self.canonical_json_required:
            raise ValueError("Artifact Export V0.1 requires verification and canonical JSON")
        if not self.github_artifact_secondary_export_authorized:
            raise ValueError("GitHub Artifact secondary export must remain authorized")
        if any(flags[3:]):
            raise ValueError("Artifact Export V0.1 cannot grant execution/provider authority")


def _canonical_bytes(payload: Mapping[str, object]) -> bytes:
    return (
        json.dumps(
            dict(payload),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def export_paper_loop_run_package_artifact(
    *,
    package: Mapping[str, object],
    output_dir: Path,
    policy: PaperRunPackageArtifactPolicy = PaperRunPackageArtifactPolicy(),
) -> dict[str, object]:
    """Verify and export one paper Run Package as secondary audit evidence."""

    if not policy.require_verified_package:
        raise ValueError("package verification cannot be disabled")
    package_id = verify_paper_loop_run_package(package)
    if package.get("package_id") != package_id:
        raise ValueError("paper Run Package id does not match verified contents")

    destination = output_dir.expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)

    package_bytes = _canonical_bytes(package)
    package_path = destination / "package.json"
    package_path.write_bytes(package_bytes)

    manifest_payload: dict[str, object] = {
        "schema": "qookey-paper-run-package-artifact-manifest-v0.1",
        "package_id": package_id,
        "files": [
            {
                "name": "package.json",
                "bytes": len(package_bytes),
                "sha256": _sha256_bytes(package_bytes),
            }
        ],
        "authority": {
            "secondary_audit_export_only": True,
            "artifact_is_execution_authority": False,
            "provider_access_authorized": False,
            "r2_access_authorized": False,
            "holdout_access_authorized": False,
            "account_state_mutation_authorized": False,
            "automatic_execution_authorized": False,
            "real_money_order_authorized": False,
            "live_real_trading_authorized": False,
        },
    }
    manifest_bytes = _canonical_bytes(manifest_payload)
    manifest_path = destination / "manifest.json"
    manifest_path.write_bytes(manifest_bytes)

    sums = (
        f"{_sha256_bytes(package_bytes)}  package.json\n"
        f"{_sha256_bytes(manifest_bytes)}  manifest.json\n"
    ).encode("utf-8")
    sums_path = destination / "SHA256SUMS"
    sums_path.write_bytes(sums)

    export_payload: dict[str, object] = {
        "schema": "qookey-paper-run-package-artifact-export-id-v0.1",
        "package_id": package_id,
        "package_sha256": _sha256_bytes(package_bytes),
        "manifest_sha256": _sha256_bytes(manifest_bytes),
        "sha256s_sha256": _sha256_bytes(sums),
    }
    export_id = (
        "paper-run-package-artifact-v0-1-"
        + hashlib.sha256(_canonical_bytes(export_payload)).hexdigest()
    )
    receipt: dict[str, object] = {
        "schema": "qookey-paper-run-package-artifact-export-receipt-v0.1",
        "export_id": export_id,
        "package_id": package_id,
        "state": "ARTIFACT_EXPORT_READY",
        "output_files": [
            {
                "name": "package.json",
                "bytes": len(package_bytes),
                "sha256": _sha256_bytes(package_bytes),
            },
            {
                "name": "manifest.json",
                "bytes": len(manifest_bytes),
                "sha256": _sha256_bytes(manifest_bytes),
            },
            {
                "name": "SHA256SUMS",
                "bytes": len(sums),
                "sha256": _sha256_bytes(sums),
            },
        ],
        "provider_requests_performed": 0,
        "r2_accessed": False,
        "holdout_accessed": False,
        "account_state_mutations_performed": 0,
        "executions_performed": 0,
        "authority": {
            "secondary_audit_export_only": True,
            "github_artifact_upload_allowed": True,
            "artifact_is_execution_authority": False,
            "provider_access_authorized": False,
            "r2_access_authorized": False,
            "holdout_access_authorized": False,
            "account_state_mutation_authorized": False,
            "automatic_execution_authorized": False,
            "real_money_order_authorized": False,
            "live_real_trading_authorized": False,
        },
        "policy": asdict(policy),
    }
    (destination / "export-receipt.json").write_bytes(_canonical_bytes(receipt))
    return receipt


def artifact_export_policy_from_config(
    payload: Mapping[str, object],
) -> PaperRunPackageArtifactPolicy:
    if payload.get("schema") != "qookey-paper-run-package-artifact-export-v0.1":
        raise ValueError("unsupported artifact export config")
    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("artifact export policy object is required")
    keys = (
        "require_verified_package",
        "canonical_json_required",
        "github_artifact_secondary_export_authorized",
        "artifact_is_execution_authority",
        "provider_access_authorized",
        "r2_access_authorized",
        "holdout_access_authorized",
        "account_state_mutation_authorized",
        "automatic_execution_authorized",
        "real_money_order_authorized",
        "live_real_trading_authorized",
    )
    values: dict[str, bool] = {}
    for key in keys:
        value = policy.get(key)
        if not isinstance(value, bool):
            raise ValueError(f"policy.{key} must be a JSON boolean")
        values[key] = value
    return PaperRunPackageArtifactPolicy(**values)
