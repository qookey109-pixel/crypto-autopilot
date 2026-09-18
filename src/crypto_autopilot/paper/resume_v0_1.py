from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from crypto_autopilot.paper.checkpoint_v0_1 import (
    paper_loop_checkpoint_account_policy_from_mapping,
    paper_loop_checkpoint_report_id_from_mapping,
)
from crypto_autopilot.paper.cycle_v0_1 import (
    PaperCyclePolicy,
    paper_cycle_report_id_from_mapping,
    prepare_paper_cycle,
)
from crypto_autopilot.paper.execution_v0_1 import PaperExecutionPolicy
from crypto_autopilot.portfolio.admission_v0_1 import PortfolioPolicy


@dataclass(frozen=True, slots=True)
class PaperLoopResumePolicy:
    """Explicit checkpoint-to-next-cycle resume policy."""

    require_exact_checkpoint_id_confirmation: bool = True
    require_checkpoint_lineage_validation: bool = True
    require_cycle_account_snapshot_match: bool = True
    require_cycle_exposure_match: bool = True
    explicit_manual_cycle_resume_authorized: bool = True
    automatic_cycle_authorized: bool = False
    automatic_submission_authorized: bool = False
    persistent_state_write_authorized: bool = False
    provider_access_authorized: bool = False
    live_trading_authorized: bool = False

    def __post_init__(self) -> None:
        flags = (
            self.require_exact_checkpoint_id_confirmation,
            self.require_checkpoint_lineage_validation,
            self.require_cycle_account_snapshot_match,
            self.require_cycle_exposure_match,
            self.explicit_manual_cycle_resume_authorized,
            self.automatic_cycle_authorized,
            self.automatic_submission_authorized,
            self.persistent_state_write_authorized,
            self.provider_access_authorized,
            self.live_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in flags):
            raise ValueError("paper loop resume policy flags must be booleans")
        if not self.require_exact_checkpoint_id_confirmation:
            raise ValueError("exact checkpoint-id confirmation is required in V0.1")
        if not self.require_checkpoint_lineage_validation:
            raise ValueError("checkpoint lineage validation is required in V0.1")
        if not self.require_cycle_account_snapshot_match:
            raise ValueError("cycle account snapshot reconciliation is required in V0.1")
        if not self.require_cycle_exposure_match:
            raise ValueError("cycle exposure reconciliation is required in V0.1")
        if not self.explicit_manual_cycle_resume_authorized:
            raise ValueError("explicit manual cycle resume must remain authorized")
        if (
            self.automatic_cycle_authorized
            or self.automatic_submission_authorized
            or self.persistent_state_write_authorized
            or self.provider_access_authorized
            or self.live_trading_authorized
        ):
            raise ValueError("Paper Loop Resume V0.1 authority exceeds its scope")


def _sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(
        dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def resume_paper_loop(
    *,
    checkpoint_report: Mapping[str, object],
    confirmation_checkpoint_id: str,
    candidate_inputs: Sequence[object],
    resume_policy: PaperLoopResumePolicy = PaperLoopResumePolicy(),
    portfolio_policy: PortfolioPolicy = PortfolioPolicy(),
    execution_policy: PaperExecutionPolicy = PaperExecutionPolicy(),
    cycle_policy: PaperCyclePolicy = PaperCyclePolicy(),
) -> dict[str, object]:
    """Validate one portable checkpoint and prepare the next explicit Paper Cycle."""

    checkpoint_id = checkpoint_report.get("checkpoint_id")
    if not isinstance(checkpoint_id, str) or not checkpoint_id:
        raise ValueError("paper loop checkpoint id is required")

    recomputed_checkpoint_id = paper_loop_checkpoint_report_id_from_mapping(
        checkpoint_report
    )
    if recomputed_checkpoint_id != checkpoint_id:
        raise ValueError("paper loop checkpoint id does not match report contents")
    if (
        resume_policy.require_exact_checkpoint_id_confirmation
        and confirmation_checkpoint_id != checkpoint_id
    ):
        raise ValueError("exact checkpoint-id confirmation does not match report")

    next_cycle_allowed = checkpoint_report.get("next_cycle_allowed")
    if not isinstance(next_cycle_allowed, bool):
        raise ValueError("paper loop checkpoint next_cycle_allowed must be boolean")

    base: dict[str, object] = {
        "schema": "qookey-paper-loop-resume-report-v0.1",
        "checkpoint_id": checkpoint_id,
        "candidate_count": len(candidate_inputs),
        "provider_requests_performed": 0,
        "broker_submissions_performed": 0,
        "lifecycle_simulations_performed": 0,
        "persistent_state_writes_performed": 0,
        "authority": {
            "explicit_manual_cycle_resume_only": True,
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
    }

    if not next_cycle_allowed:
        resume_payload = {
            "schema": "qookey-paper-loop-resume-id-v0.1",
            "checkpoint_id": checkpoint_id,
            "state": "CHECKPOINT_BLOCKED",
            "cycle_id": None,
        }
        return {
            **base,
            "resume_id": f"paper-loop-resume-v0-1-{_sha256(resume_payload)}",
            "state": "CHECKPOINT_BLOCKED",
            "reason": "checkpoint_disallows_next_cycle",
            "cycle_report": None,
        }

    next_account_input = checkpoint_report.get("next_account_input")
    expected_snapshot_id = checkpoint_report.get("next_snapshot_id")
    expected_exposures = checkpoint_report.get("portfolio_existing_exposures")
    if not isinstance(next_account_input, Mapping):
        raise ValueError("paper loop checkpoint next_account_input is required")
    if not isinstance(expected_snapshot_id, str) or not expected_snapshot_id:
        raise ValueError("paper loop checkpoint next_snapshot_id is required")
    if not isinstance(expected_exposures, list):
        raise ValueError("paper loop checkpoint exposures must be an array")

    account_policy = paper_loop_checkpoint_account_policy_from_mapping(
        checkpoint_report
    )
    cycle_report = prepare_paper_cycle(
        account_input=next_account_input,
        candidate_inputs=tuple(candidate_inputs),
        account_policy=account_policy,
        portfolio_policy=portfolio_policy,
        execution_policy=execution_policy,
        cycle_policy=cycle_policy,
    )

    if (
        resume_policy.require_cycle_account_snapshot_match
        and cycle_report.get("account_snapshot_id") != expected_snapshot_id
    ):
        raise ValueError("resumed cycle account snapshot does not match checkpoint")

    actual_exposures = cycle_report.get("existing_exposures")
    if resume_policy.require_cycle_exposure_match:
        if not isinstance(actual_exposures, list):
            raise ValueError("resumed cycle did not emit existing exposures")
        if actual_exposures != expected_exposures:
            raise ValueError("resumed cycle exposure does not match checkpoint")

    cycle_id = cycle_report.get("cycle_id")
    cycle_state = cycle_report.get("state")
    if not isinstance(cycle_id, str) or not cycle_id:
        raise ValueError("resumed Paper Cycle id is required")
    if not isinstance(cycle_state, str) or not cycle_state:
        raise ValueError("resumed Paper Cycle state is required")

    resume_payload = {
        "schema": "qookey-paper-loop-resume-id-v0.1",
        "checkpoint_id": checkpoint_id,
        "state": "PAPER_LOOP_RESUMED",
        "cycle_id": cycle_id,
    }
    return {
        **base,
        "resume_id": f"paper-loop-resume-v0-1-{_sha256(resume_payload)}",
        "state": "PAPER_LOOP_RESUMED",
        "cycle_id": cycle_id,
        "cycle_state": cycle_state,
        "cycle_report": cycle_report,
        "limitations": [
            "Resume V0.1 prepares one manual Paper Cycle only.",
            "No PaperBroker submission or lifecycle simulation is performed.",
            "Checkpoint consumption grants no automatic or live execution authority.",
        ],
    }


def paper_loop_resume_report_id_from_mapping(
    payload: Mapping[str, object],
) -> str:
    """Fully validate and recompute one serialized Paper Loop Resume id."""

    if payload.get("schema") != "qookey-paper-loop-resume-report-v0.1":
        raise ValueError("unsupported paper loop resume report schema")
    state = payload.get("state")
    if state not in {"PAPER_LOOP_RESUMED", "CHECKPOINT_BLOCKED"}:
        raise ValueError("paper loop resume report state is invalid")

    checkpoint_id = payload.get("checkpoint_id")
    resume_id = payload.get("resume_id")
    if not isinstance(checkpoint_id, str) or not checkpoint_id:
        raise ValueError("paper loop resume checkpoint_id is required")
    if not isinstance(resume_id, str) or not resume_id:
        raise ValueError("paper loop resume resume_id is required")

    candidate_count = payload.get("candidate_count")
    if (
        not isinstance(candidate_count, int)
        or isinstance(candidate_count, bool)
        or candidate_count < 0
    ):
        raise ValueError("paper loop resume candidate_count must be non-negative integer")

    for key in (
        "provider_requests_performed",
        "broker_submissions_performed",
        "lifecycle_simulations_performed",
        "persistent_state_writes_performed",
    ):
        value = payload.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value != 0:
            raise ValueError(f"paper loop resume {key} must equal zero")

    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("paper loop resume authority object is required")
    if authority.get("explicit_manual_cycle_resume_only") is not True:
        raise ValueError("paper loop resume must remain explicit-manual-only")
    for key in (
        "provider_requests_performed",
        "r2_accessed",
        "holdout_accessed",
        "persistent_state_write_authorized",
        "automatic_cycle_authorized",
        "automatic_submission_authorized",
        "scheduled_execution_authorized",
        "short_paper_execution_authorized",
        "formal_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"paper loop resume authority must remain closed: {key}")

    if state == "CHECKPOINT_BLOCKED":
        if payload.get("reason") != "checkpoint_disallows_next_cycle":
            raise ValueError("blocked paper loop resume reason is invalid")
        if payload.get("cycle_report") is not None:
            raise ValueError("blocked paper loop resume cannot contain cycle report")
        cycle_id = None
    else:
        cycle_id = payload.get("cycle_id")
        cycle_state = payload.get("cycle_state")
        cycle_report = payload.get("cycle_report")
        if not isinstance(cycle_id, str) or not cycle_id:
            raise ValueError("resumed paper loop cycle_id is required")
        if not isinstance(cycle_state, str) or not cycle_state:
            raise ValueError("resumed paper loop cycle_state is required")
        if not isinstance(cycle_report, Mapping):
            raise ValueError("resumed paper loop cycle_report is required")
        recomputed_cycle_id = paper_cycle_report_id_from_mapping(cycle_report)
        if recomputed_cycle_id != cycle_id:
            raise ValueError("resumed paper loop cycle id does not match cycle report")
        if cycle_report.get("cycle_id") != cycle_id:
            raise ValueError("resumed paper loop embedded cycle id mismatch")
        if cycle_report.get("state") != cycle_state:
            raise ValueError("resumed paper loop cycle state mismatch")

    canonical: dict[str, object] = {
        "schema": "qookey-paper-loop-resume-id-v0.1",
        "checkpoint_id": checkpoint_id,
        "state": state,
        "cycle_id": cycle_id,
    }
    return f"paper-loop-resume-v0-1-{_sha256(canonical)}"


def paper_loop_resume_policy_from_config(
    payload: Mapping[str, object],
) -> PaperLoopResumePolicy:
    if payload.get("schema") != "qookey-paper-loop-resume-v0.1":
        raise ValueError("unsupported paper loop resume config")
    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("policy object is required")
    keys = (
        "require_exact_checkpoint_id_confirmation",
        "require_checkpoint_lineage_validation",
        "require_cycle_account_snapshot_match",
        "require_cycle_exposure_match",
        "explicit_manual_cycle_resume_authorized",
        "automatic_cycle_authorized",
        "automatic_submission_authorized",
        "persistent_state_write_authorized",
        "provider_access_authorized",
        "live_trading_authorized",
    )
    for key in keys:
        if not isinstance(policy.get(key), bool):
            raise ValueError(f"policy.{key} must be a JSON boolean")
    return PaperLoopResumePolicy(
        require_exact_checkpoint_id_confirmation=policy[
            "require_exact_checkpoint_id_confirmation"
        ],
        require_checkpoint_lineage_validation=policy[
            "require_checkpoint_lineage_validation"
        ],
        require_cycle_account_snapshot_match=policy[
            "require_cycle_account_snapshot_match"
        ],
        require_cycle_exposure_match=policy["require_cycle_exposure_match"],
        explicit_manual_cycle_resume_authorized=policy[
            "explicit_manual_cycle_resume_authorized"
        ],
        automatic_cycle_authorized=policy["automatic_cycle_authorized"],
        automatic_submission_authorized=policy[
            "automatic_submission_authorized"
        ],
        persistent_state_write_authorized=policy[
            "persistent_state_write_authorized"
        ],
        provider_access_authorized=policy["provider_access_authorized"],
        live_trading_authorized=policy["live_trading_authorized"],
    )


def paper_loop_resume_input_from_dict(
    payload: Mapping[str, object],
) -> tuple[Mapping[str, object], tuple[object, ...]]:
    if payload.get("schema") != "qookey-paper-loop-resume-input-v0.1":
        raise ValueError("unsupported paper loop resume input schema")
    checkpoint_report = payload.get("checkpoint_report")
    candidates = payload.get("candidates")
    if not isinstance(checkpoint_report, Mapping):
        raise ValueError("checkpoint_report object is required")
    if not isinstance(candidates, list):
        raise ValueError("candidates must be a JSON array")
    return checkpoint_report, tuple(candidates)
