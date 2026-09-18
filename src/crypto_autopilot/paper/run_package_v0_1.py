from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from crypto_autopilot.paper.integrity_v0_1 import (
    PaperLoopIntegrityPolicy,
    audit_paper_loop_integrity,
    paper_loop_integrity_input_from_dict,
    paper_loop_integrity_report_id_from_mapping,
)


_STAGE_KEYS = (
    "start_checkpoint",
    "resume_report",
    "session_report",
    "lifecycle_batch_report",
    "account_advance_report",
    "end_checkpoint",
)


@dataclass(frozen=True, slots=True)
class PaperLoopRunPackagePolicy:
    """Portable audit transcript package policy."""

    require_exact_integrity_id_confirmation: bool = True
    require_integrity_reaudit: bool = True
    require_complete_stage_manifest: bool = True
    include_full_transcript: bool = True
    include_integrity_proof: bool = True
    persistent_state_write_authorized: bool = False
    provider_access_authorized: bool = False
    execution_authorized: bool = False
    live_trading_authorized: bool = False

    def __post_init__(self) -> None:
        flags = (
            self.require_exact_integrity_id_confirmation,
            self.require_integrity_reaudit,
            self.require_complete_stage_manifest,
            self.include_full_transcript,
            self.include_integrity_proof,
            self.persistent_state_write_authorized,
            self.provider_access_authorized,
            self.execution_authorized,
            self.live_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in flags):
            raise ValueError("paper loop run package policy flags must be booleans")
        if not all(flags[:5]):
            raise ValueError("Paper Loop Run Package V0.1 requires all proof payloads")
        if (
            self.persistent_state_write_authorized
            or self.provider_access_authorized
            or self.execution_authorized
            or self.live_trading_authorized
        ):
            raise ValueError("Paper Loop Run Package V0.1 is portable audit-only")


def _canonicalize(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(item)
            for key, item in sorted(value.items())
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    return value


def _sha256(value: object) -> str:
    encoded = json.dumps(
        _canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _stage_id(stage_key: str, payload: Mapping[str, object]) -> str:
    key_by_stage = {
        "start_checkpoint": "checkpoint_id",
        "resume_report": "resume_id",
        "session_report": "session_id",
        "lifecycle_batch_report": "batch_id",
        "account_advance_report": "advance_id",
        "end_checkpoint": "checkpoint_id",
    }
    value = payload.get(key_by_stage[stage_key])
    if not isinstance(value, str) or not value:
        raise ValueError(f"{stage_key} deterministic id is required")
    return value


def _build_manifest(rounds: tuple[object, ...]) -> list[dict[str, object]]:
    manifest: list[dict[str, object]] = []
    for round_index, raw_round in enumerate(rounds):
        if not isinstance(raw_round, Mapping):
            raise ValueError(f"rounds[{round_index}] must be an object")
        stages: list[dict[str, str]] = []
        for stage_key in _STAGE_KEYS:
            stage = raw_round.get(stage_key)
            if not isinstance(stage, Mapping):
                raise ValueError(
                    f"rounds[{round_index}].{stage_key} must be an object"
                )
            stages.append(
                {
                    "stage": stage_key,
                    "id": _stage_id(stage_key, stage),
                    "sha256": _sha256(stage),
                }
            )
        manifest.append(
            {
                "round_index": round_index,
                "stages": stages,
                "round_sha256": _sha256(raw_round),
            }
        )
    return manifest


def build_paper_loop_run_package(
    *,
    integrity_input: Mapping[str, object],
    integrity_report: Mapping[str, object],
    confirmation_integrity_id: str,
    package_policy: PaperLoopRunPackagePolicy = PaperLoopRunPackagePolicy(),
    integrity_policy: PaperLoopIntegrityPolicy = PaperLoopIntegrityPolicy(),
) -> dict[str, object]:
    """Create one portable self-verifying multi-cycle paper transcript package."""

    integrity_id = integrity_report.get("integrity_id")
    if not isinstance(integrity_id, str) or not integrity_id:
        raise ValueError("paper loop integrity id is required")
    recomputed_integrity_id = paper_loop_integrity_report_id_from_mapping(
        integrity_report
    )
    if recomputed_integrity_id != integrity_id:
        raise ValueError("paper loop integrity id does not match report contents")
    if (
        package_policy.require_exact_integrity_id_confirmation
        and confirmation_integrity_id != integrity_id
    ):
        raise ValueError("exact integrity-id confirmation does not match report")

    start, terminal, rounds = paper_loop_integrity_input_from_dict(integrity_input)
    if package_policy.require_integrity_reaudit:
        reaudit = audit_paper_loop_integrity(
            expected_start_checkpoint_id=start,
            expected_terminal_checkpoint_id=terminal,
            rounds=rounds,
            policy=integrity_policy,
        )
        if _canonicalize(reaudit) != _canonicalize(integrity_report):
            raise ValueError("integrity proof does not match re-audited transcript")
    else:
        raise ValueError("integrity re-audit cannot be disabled in V0.1")

    if integrity_report.get("start_checkpoint_id") != start:
        raise ValueError("integrity proof start anchor differs from transcript")
    if integrity_report.get("terminal_checkpoint_id") != terminal:
        raise ValueError("integrity proof terminal anchor differs from transcript")

    manifest = _build_manifest(rounds)
    manifest_sha = _sha256({"rounds": manifest})
    integrity_input_sha = _sha256(integrity_input)
    integrity_report_sha = _sha256(integrity_report)

    terminal_checkpoint = rounds[-1]
    if not isinstance(terminal_checkpoint, Mapping):
        raise ValueError("terminal transcript round must be an object")
    terminal_checkpoint_payload = terminal_checkpoint.get("end_checkpoint")
    if not isinstance(terminal_checkpoint_payload, Mapping):
        raise ValueError("terminal checkpoint payload is required")
    if terminal_checkpoint_payload.get("checkpoint_id") != terminal:
        raise ValueError("terminal checkpoint id differs from integrity anchor")

    package_payload: dict[str, object] = {
        "schema": "qookey-paper-loop-run-package-id-v0.1",
        "integrity_id": integrity_id,
        "integrity_input_sha256": integrity_input_sha,
        "integrity_report_sha256": integrity_report_sha,
        "manifest_sha256": manifest_sha,
        "terminal_checkpoint_id": terminal,
    }
    package_id = f"paper-loop-run-package-v0-1-{_sha256(package_payload)}"

    return {
        "schema": "qookey-paper-loop-run-package-report-v0.1",
        "package_id": package_id,
        "state": "PORTABLE_RUN_PACKAGE_READY",
        "integrity_id": integrity_id,
        "round_count": len(rounds),
        "start_checkpoint_id": start,
        "terminal_checkpoint_id": terminal,
        "integrity_input_sha256": integrity_input_sha,
        "integrity_report_sha256": integrity_report_sha,
        "manifest_sha256": manifest_sha,
        "stage_manifest": manifest,
        "integrity_input": _canonicalize(integrity_input),
        "integrity_report": _canonicalize(integrity_report),
        "terminal_checkpoint": _canonicalize(terminal_checkpoint_payload),
        "provider_requests_performed": 0,
        "persistent_state_writes_performed": 0,
        "executions_performed": 0,
        "authority": {
            "portable_audit_package_only": True,
            "package_is_execution_authority": False,
            "provider_requests_performed": False,
            "r2_accessed": False,
            "holdout_accessed": False,
            "persistent_state_write_authorized": False,
            "automatic_execution_authorized": False,
            "automatic_submission_authorized": False,
            "strategy_ranking_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
        "limitations": [
            "The package is returned in-memory/stdout and is not persisted by V0.1.",
            "The package contains paper audit evidence, not execution authority.",
            "The terminal checkpoint still requires explicit Resume for a future cycle.",
        ],
    }


def verify_paper_loop_run_package(
    payload: Mapping[str, object],
    *,
    integrity_policy: PaperLoopIntegrityPolicy = PaperLoopIntegrityPolicy(),
) -> str:
    """Fully verify one serialized Run Package and return its deterministic id."""

    if payload.get("schema") != "qookey-paper-loop-run-package-report-v0.1":
        raise ValueError("unsupported paper loop run package schema")
    if payload.get("state") != "PORTABLE_RUN_PACKAGE_READY":
        raise ValueError("paper loop run package is not ready")

    package_id = payload.get("package_id")
    integrity_id = payload.get("integrity_id")
    if not isinstance(package_id, str) or not package_id:
        raise ValueError("paper loop run package package_id is required")
    if not isinstance(integrity_id, str) or not integrity_id:
        raise ValueError("paper loop run package integrity_id is required")

    integrity_input = payload.get("integrity_input")
    integrity_report = payload.get("integrity_report")
    manifest = payload.get("stage_manifest")
    terminal_checkpoint = payload.get("terminal_checkpoint")
    if not isinstance(integrity_input, Mapping):
        raise ValueError("paper loop run package integrity_input is required")
    if not isinstance(integrity_report, Mapping):
        raise ValueError("paper loop run package integrity_report is required")
    if not isinstance(manifest, list):
        raise ValueError("paper loop run package stage_manifest must be an array")
    if not isinstance(terminal_checkpoint, Mapping):
        raise ValueError("paper loop run package terminal_checkpoint is required")

    start, terminal, rounds = paper_loop_integrity_input_from_dict(integrity_input)
    reaudit = audit_paper_loop_integrity(
        expected_start_checkpoint_id=start,
        expected_terminal_checkpoint_id=terminal,
        rounds=rounds,
        policy=integrity_policy,
    )
    if _canonicalize(reaudit) != _canonicalize(integrity_report):
        raise ValueError("paper loop run package integrity proof is not reproducible")
    if paper_loop_integrity_report_id_from_mapping(integrity_report) != integrity_id:
        raise ValueError("paper loop run package integrity id mismatch")

    expected_manifest = _build_manifest(rounds)
    if _canonicalize(manifest) != _canonicalize(expected_manifest):
        raise ValueError("paper loop run package stage manifest mismatch")

    integrity_input_sha = _sha256(integrity_input)
    integrity_report_sha = _sha256(integrity_report)
    manifest_sha = _sha256({"rounds": expected_manifest})
    if payload.get("integrity_input_sha256") != integrity_input_sha:
        raise ValueError("paper loop run package transcript hash mismatch")
    if payload.get("integrity_report_sha256") != integrity_report_sha:
        raise ValueError("paper loop run package proof hash mismatch")
    if payload.get("manifest_sha256") != manifest_sha:
        raise ValueError("paper loop run package manifest hash mismatch")
    if payload.get("round_count") != len(rounds):
        raise ValueError("paper loop run package round_count mismatch")
    if payload.get("start_checkpoint_id") != start:
        raise ValueError("paper loop run package start checkpoint mismatch")
    if payload.get("terminal_checkpoint_id") != terminal:
        raise ValueError("paper loop run package terminal checkpoint mismatch")
    if terminal_checkpoint.get("checkpoint_id") != terminal:
        raise ValueError("paper loop run package embedded terminal checkpoint mismatch")
    if _canonicalize(terminal_checkpoint) != _canonicalize(
        rounds[-1]["end_checkpoint"]  # type: ignore[index]
    ):
        raise ValueError("paper loop run package terminal checkpoint payload mismatch")

    for key in (
        "provider_requests_performed",
        "persistent_state_writes_performed",
        "executions_performed",
    ):
        value = payload.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value != 0:
            raise ValueError(f"paper loop run package {key} must equal zero")

    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("paper loop run package authority object is required")
    if authority.get("portable_audit_package_only") is not True:
        raise ValueError("paper loop run package must remain portable audit-only")
    if authority.get("package_is_execution_authority") is not False:
        raise ValueError("paper loop run package cannot be execution authority")
    for key in (
        "provider_requests_performed",
        "r2_accessed",
        "holdout_accessed",
        "persistent_state_write_authorized",
        "automatic_execution_authorized",
        "automatic_submission_authorized",
        "strategy_ranking_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"paper loop run package authority must remain closed: {key}")

    package_payload: dict[str, object] = {
        "schema": "qookey-paper-loop-run-package-id-v0.1",
        "integrity_id": integrity_id,
        "integrity_input_sha256": integrity_input_sha,
        "integrity_report_sha256": integrity_report_sha,
        "manifest_sha256": manifest_sha,
        "terminal_checkpoint_id": terminal,
    }
    return f"paper-loop-run-package-v0-1-{_sha256(package_payload)}"


def paper_loop_run_package_policy_from_config(
    payload: Mapping[str, object],
) -> PaperLoopRunPackagePolicy:
    if payload.get("schema") != "qookey-paper-loop-run-package-v0.1":
        raise ValueError("unsupported paper loop run package config")
    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("policy object is required")
    keys = (
        "require_exact_integrity_id_confirmation",
        "require_integrity_reaudit",
        "require_complete_stage_manifest",
        "include_full_transcript",
        "include_integrity_proof",
        "persistent_state_write_authorized",
        "provider_access_authorized",
        "execution_authorized",
        "live_trading_authorized",
    )
    for key in keys:
        if not isinstance(policy.get(key), bool):
            raise ValueError(f"policy.{key} must be a JSON boolean")
    return PaperLoopRunPackagePolicy(
        require_exact_integrity_id_confirmation=policy[
            "require_exact_integrity_id_confirmation"
        ],
        require_integrity_reaudit=policy["require_integrity_reaudit"],
        require_complete_stage_manifest=policy["require_complete_stage_manifest"],
        include_full_transcript=policy["include_full_transcript"],
        include_integrity_proof=policy["include_integrity_proof"],
        persistent_state_write_authorized=policy[
            "persistent_state_write_authorized"
        ],
        provider_access_authorized=policy["provider_access_authorized"],
        execution_authorized=policy["execution_authorized"],
        live_trading_authorized=policy["live_trading_authorized"],
    )


def paper_loop_run_package_input_from_dict(
    payload: Mapping[str, object],
) -> tuple[Mapping[str, object], Mapping[str, object]]:
    if payload.get("schema") != "qookey-paper-loop-run-package-input-v0.1":
        raise ValueError("unsupported paper loop run package input schema")
    integrity_input = payload.get("integrity_input")
    integrity_report = payload.get("integrity_report")
    if not isinstance(integrity_input, Mapping):
        raise ValueError("integrity_input object is required")
    if not isinstance(integrity_report, Mapping):
        raise ValueError("integrity_report object is required")
    return integrity_input, integrity_report
