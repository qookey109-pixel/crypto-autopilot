from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass

from crypto_autopilot.paper.account_advance_v0_1 import (
    paper_account_advance_report_id_from_mapping,
)
from crypto_autopilot.paper.account_v0_1 import (
    PaperAccountPolicy,
    materialize_paper_account,
    paper_account_input_from_dict,
    portfolio_exposures_from_account,
)


@dataclass(frozen=True, slots=True)
class PaperLoopCheckpointPolicy:
    """Portable deterministic handoff policy after Paper Account Advance V0.1."""

    require_exact_advance_id_confirmation: bool = True
    require_account_rematerialization: bool = True
    require_exposure_reconciliation: bool = True
    include_next_account_input: bool = True
    persistent_state_write_authorized: bool = False
    provider_access_authorized: bool = False
    automatic_cycle_authorized: bool = False
    live_trading_authorized: bool = False

    def __post_init__(self) -> None:
        flags = (
            self.require_exact_advance_id_confirmation,
            self.require_account_rematerialization,
            self.require_exposure_reconciliation,
            self.include_next_account_input,
            self.persistent_state_write_authorized,
            self.provider_access_authorized,
            self.automatic_cycle_authorized,
            self.live_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in flags):
            raise ValueError("paper loop checkpoint policy flags must be booleans")
        if not self.require_exact_advance_id_confirmation:
            raise ValueError("exact advance-id confirmation is required in V0.1")
        if not self.require_account_rematerialization:
            raise ValueError("account rematerialization is required in V0.1")
        if not self.require_exposure_reconciliation:
            raise ValueError("exposure reconciliation is required in V0.1")
        if not self.include_next_account_input:
            raise ValueError("V0.1 checkpoint must carry next_account_input")
        if (
            self.persistent_state_write_authorized
            or self.provider_access_authorized
            or self.automatic_cycle_authorized
            or self.live_trading_authorized
        ):
            raise ValueError("Paper Loop Checkpoint V0.1 authority exceeds its scope")


def _canonicalize(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(item)
            for key, item in sorted(value.items())
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    return value


def _sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(
        dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _account_policy_from_evidence(payload: Mapping[str, object]) -> PaperAccountPolicy:
    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("paper account evidence policy object is required")
    floor = policy.get("insolvency_equity_floor_usd")
    if isinstance(floor, bool) or not isinstance(floor, (int, float)):
        raise ValueError("account policy insolvency floor must be numeric")
    flags = (
        "require_single_mark_timestamp",
        "reject_mark_crossing_protective_boundary",
        "export_portfolio_exposures",
    )
    for key in flags:
        if not isinstance(policy.get(key), bool):
            raise ValueError(f"account policy {key} must be boolean")
    return PaperAccountPolicy(
        insolvency_equity_floor_usd=float(floor),
        require_single_mark_timestamp=policy["require_single_mark_timestamp"],
        reject_mark_crossing_protective_boundary=policy[
            "reject_mark_crossing_protective_boundary"
        ],
        export_portfolio_exposures=policy["export_portfolio_exposures"],
    )


def create_paper_loop_checkpoint(
    *,
    account_advance_report: Mapping[str, object],
    confirmation_advance_id: str,
    policy: PaperLoopCheckpointPolicy = PaperLoopCheckpointPolicy(),
) -> dict[str, object]:
    """Create one portable, stateless checkpoint for the next manual paper cycle."""

    advance_id = account_advance_report.get("advance_id")
    if not isinstance(advance_id, str) or not advance_id:
        raise ValueError("paper account advance id is required")
    recomputed_advance_id = paper_account_advance_report_id_from_mapping(
        account_advance_report
    )
    if recomputed_advance_id != advance_id:
        raise ValueError("paper account advance id does not match report contents")
    if (
        policy.require_exact_advance_id_confirmation
        and confirmation_advance_id != advance_id
    ):
        raise ValueError("exact advance-id confirmation does not match report")

    next_account_input = account_advance_report.get("next_account_input")
    account_evidence = account_advance_report.get("account")
    expected_exposures = account_advance_report.get("portfolio_existing_exposures")
    capacity = account_advance_report.get("portfolio_capacity_exported")
    if not isinstance(next_account_input, Mapping):
        raise ValueError("paper account advance next_account_input is required")
    if not isinstance(account_evidence, Mapping):
        raise ValueError("paper account advance account evidence is required")
    if not isinstance(expected_exposures, list):
        raise ValueError("paper account advance exposures must be an array")
    if not isinstance(capacity, bool):
        raise ValueError("paper account advance capacity flag must be boolean")

    account_policy = _account_policy_from_evidence(account_evidence)
    initial_equity, records, marks = paper_account_input_from_dict(next_account_input)
    snapshot = materialize_paper_account(
        initial_equity_usd=initial_equity,
        records=records,
        marks=marks,
        policy=account_policy,
    )

    expected_snapshot = account_evidence.get("snapshot")
    if not isinstance(expected_snapshot, Mapping):
        raise ValueError("paper account advance account snapshot is required")
    actual_snapshot = _canonicalize(asdict(snapshot))
    expected_snapshot_json = _canonicalize(expected_snapshot)
    if actual_snapshot != expected_snapshot_json:
        raise ValueError("next_account_input does not rematerialize declared account snapshot")
    if snapshot.snapshot_id != account_advance_report.get("next_snapshot_id"):
        raise ValueError("rematerialized snapshot id does not match advance report")

    if snapshot.status == "ACCOUNT_ACTIVE":
        actual_exposures = [
            asdict(item)
            for item in portfolio_exposures_from_account(
                snapshot,
                policy=account_policy,
            )
        ]
        next_cycle_allowed = True
        if not capacity:
            raise ValueError("active checkpoint account must export portfolio capacity")
    else:
        actual_exposures = []
        next_cycle_allowed = False
        if capacity:
            raise ValueError("insolvent checkpoint account cannot export portfolio capacity")

    if policy.require_exposure_reconciliation and actual_exposures != expected_exposures:
        raise ValueError("checkpoint portfolio exposure does not match Account Advance")

    account_input_sha = _sha256(dict(next_account_input))
    exposure_payload = {"exposures": actual_exposures}
    exposure_sha = _sha256(exposure_payload)
    checkpoint_payload: dict[str, object] = {
        "schema": "qookey-paper-loop-checkpoint-id-v0.1",
        "advance_id": advance_id,
        "batch_id": account_advance_report["batch_id"],
        "previous_snapshot_id": account_advance_report["previous_snapshot_id"],
        "next_snapshot_id": snapshot.snapshot_id,
        "next_account_input_sha256": account_input_sha,
        "portfolio_exposures_sha256": exposure_sha,
    }
    checkpoint_id = f"paper-loop-checkpoint-v0-1-{_sha256(checkpoint_payload)}"

    return {
        "schema": "qookey-paper-loop-checkpoint-report-v0.1",
        "checkpoint_id": checkpoint_id,
        "state": "PAPER_LOOP_CHECKPOINT_READY",
        "advance_id": advance_id,
        "batch_id": account_advance_report["batch_id"],
        "previous_snapshot_id": account_advance_report["previous_snapshot_id"],
        "next_snapshot_id": snapshot.snapshot_id,
        "next_account_input_sha256": account_input_sha,
        "portfolio_exposures_sha256": exposure_sha,
        "next_cycle_allowed": next_cycle_allowed,
        "next_account_input": dict(next_account_input),
        "account_snapshot": actual_snapshot,
        "portfolio_existing_exposures": actual_exposures,
        "provider_requests_performed": 0,
        "persistent_state_writes_performed": 0,
        "authority": {
            "portable_handoff_only": True,
            "provider_requests_performed": False,
            "r2_accessed": False,
            "holdout_accessed": False,
            "persistent_state_write_authorized": False,
            "automatic_cycle_authorized": False,
            "automatic_submission_authorized": False,
            "scheduled_execution_authorized": False,
            "short_paper_execution_authorized": False,
            "formal_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
        "limitations": [
            "Checkpoint V0.1 is returned in-memory/stdout only and stores nothing.",
            "next_account_input must still be supplied explicitly to the next Paper Cycle.",
            "Checkpoint readiness does not authorize automatic or live execution.",
        ],
    }


def paper_loop_checkpoint_policy_from_config(
    payload: Mapping[str, object],
) -> PaperLoopCheckpointPolicy:
    if payload.get("schema") != "qookey-paper-loop-checkpoint-v0.1":
        raise ValueError("unsupported paper loop checkpoint config")
    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("policy object is required")
    keys = (
        "require_exact_advance_id_confirmation",
        "require_account_rematerialization",
        "require_exposure_reconciliation",
        "include_next_account_input",
        "persistent_state_write_authorized",
        "provider_access_authorized",
        "automatic_cycle_authorized",
        "live_trading_authorized",
    )
    for key in keys:
        if not isinstance(policy.get(key), bool):
            raise ValueError(f"policy.{key} must be a JSON boolean")
    return PaperLoopCheckpointPolicy(
        require_exact_advance_id_confirmation=policy[
            "require_exact_advance_id_confirmation"
        ],
        require_account_rematerialization=policy[
            "require_account_rematerialization"
        ],
        require_exposure_reconciliation=policy[
            "require_exposure_reconciliation"
        ],
        include_next_account_input=policy["include_next_account_input"],
        persistent_state_write_authorized=policy[
            "persistent_state_write_authorized"
        ],
        provider_access_authorized=policy["provider_access_authorized"],
        automatic_cycle_authorized=policy["automatic_cycle_authorized"],
        live_trading_authorized=policy["live_trading_authorized"],
    )
