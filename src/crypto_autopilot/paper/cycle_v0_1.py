from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import cast

from crypto_autopilot.paper.account_v0_1 import (
    PaperAccountPolicy,
    PaperAccountSnapshot,
    materialize_paper_account,
    paper_account_input_from_dict,
    portfolio_exposures_from_account,
)
from crypto_autopilot.paper.execution_v0_1 import (
    PaperExecutionDecision,
    PaperExecutionPolicy,
    prepare_paper_execution,
)
from crypto_autopilot.portfolio.admission_v0_1 import (
    PortfolioPolicy,
    PortfolioProposal,
    admit_portfolio,
    build_portfolio_proposal,
    position_sizing_plan_from_mapping,
)
from crypto_autopilot.risk import PositionSizingPlan


@dataclass(frozen=True, slots=True)
class PaperCyclePolicy:
    """Manual, deterministic paper-cycle preparation policy."""

    maximum_candidates: int = 5
    require_candidate_as_of_not_before_account: bool = True
    require_all_intents_ready: bool = True
    automatic_broker_submission_authorized: bool = False
    lifecycle_simulation_authorized: bool = False
    persistent_state_write_authorized: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.maximum_candidates, int) or isinstance(
            self.maximum_candidates, bool
        ):
            raise ValueError("maximum_candidates must be an integer")
        if self.maximum_candidates < 1:
            raise ValueError("maximum_candidates must be positive")
        flags = (
            self.require_candidate_as_of_not_before_account,
            self.require_all_intents_ready,
            self.automatic_broker_submission_authorized,
            self.lifecycle_simulation_authorized,
            self.persistent_state_write_authorized,
        )
        if any(not isinstance(value, bool) for value in flags):
            raise ValueError("paper cycle policy flags must be booleans")
        if not self.require_candidate_as_of_not_before_account:
            raise ValueError(
                "Paper Cycle V0.1 requires candidate timestamps at/after account state"
            )
        if not self.require_all_intents_ready:
            raise ValueError(
                "Paper Cycle V0.1 requires the complete admitted basket to be intent-ready"
            )
        if self.automatic_broker_submission_authorized:
            raise ValueError("Paper Cycle V0.1 cannot authorize broker submission")
        if self.lifecycle_simulation_authorized:
            raise ValueError("Paper Cycle V0.1 does not run lifecycle simulation")
        if self.persistent_state_write_authorized:
            raise ValueError("Paper Cycle V0.1 cannot authorize persistent state writes")


@dataclass(frozen=True, slots=True)
class PaperCycleCandidate:
    symbol: str
    strategy_family: str
    as_of_ms: int
    family_validation_report: Mapping[str, object]
    sizing_plan: PositionSizingPlan
    proposal: PortfolioProposal


@dataclass(frozen=True, slots=True)
class PaperCyclePreparedIntent:
    proposal_id: str
    symbol: str
    strategy_family: str
    as_of_ms: int
    decision_status: str
    decision_reason: str
    intent_id: str | None
    notional_usd: float | None


def _sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(
        dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _canonicalize(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _canonicalize(item) for key, item in sorted(value.items())}
    if isinstance(value, tuple):
        return [_canonicalize(item) for item in value]
    if isinstance(value, list):
        return [_canonicalize(item) for item in value]
    return value


def _parse_candidates(
    payload: Sequence[object],
    *,
    account_snapshot: PaperAccountSnapshot,
    policy: PaperCyclePolicy,
) -> tuple[PaperCycleCandidate, ...]:
    if len(payload) > policy.maximum_candidates:
        raise ValueError("candidate count exceeds Paper Cycle V0.1 maximum")

    candidates: list[PaperCycleCandidate] = []
    for index, raw in enumerate(payload):
        if not isinstance(raw, Mapping):
            raise ValueError(f"candidates[{index}] must be a JSON object")
        symbol = raw.get("symbol")
        family = raw.get("strategy_family")
        as_of_ms = raw.get("as_of_ms")
        family_report = raw.get("family_validation_report")
        sizing_payload = raw.get("position_sizing_plan")

        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError(f"candidates[{index}].symbol is required")
        if not isinstance(family, str) or not family.strip():
            raise ValueError(f"candidates[{index}].strategy_family is required")
        if not isinstance(as_of_ms, int) or isinstance(as_of_ms, bool):
            raise ValueError(f"candidates[{index}].as_of_ms must be a JSON integer")
        if as_of_ms < 0:
            raise ValueError(f"candidates[{index}].as_of_ms cannot be negative")
        if (
            policy.require_candidate_as_of_not_before_account
            and as_of_ms < account_snapshot.as_of_ms
        ):
            raise ValueError(
                f"candidates[{index}].as_of_ms precedes paper account snapshot"
            )
        if not isinstance(family_report, Mapping):
            raise ValueError(
                f"candidates[{index}].family_validation_report must be an object"
            )
        if not isinstance(sizing_payload, Mapping):
            raise ValueError(
                f"candidates[{index}].position_sizing_plan must be an object"
            )

        sizing_plan = position_sizing_plan_from_mapping(sizing_payload)
        proposal = build_portfolio_proposal(
            symbol=symbol,
            strategy_family=family,
            family_validation_report=family_report,
            as_of_ms=as_of_ms,
            sizing_plan=sizing_plan,
        )
        candidates.append(
            PaperCycleCandidate(
                symbol=symbol,
                strategy_family=family,
                as_of_ms=as_of_ms,
                family_validation_report=family_report,
                sizing_plan=sizing_plan,
                proposal=proposal,
            )
        )

    candidates.sort(key=lambda item: item.proposal.proposal_id)
    proposal_ids = [item.proposal.proposal_id for item in candidates]
    if len(set(proposal_ids)) != len(proposal_ids):
        raise ValueError("paper cycle candidate proposals must be unique")
    return tuple(candidates)


def prepare_paper_cycle(
    *,
    account_input: Mapping[str, object],
    candidate_inputs: Sequence[object],
    account_policy: PaperAccountPolicy = PaperAccountPolicy(),
    portfolio_policy: PortfolioPolicy = PortfolioPolicy(),
    execution_policy: PaperExecutionPolicy = PaperExecutionPolicy(),
    cycle_policy: PaperCyclePolicy = PaperCyclePolicy(),
) -> dict[str, object]:
    """Prepare one explicit paper cycle through intent readiness, without submission."""

    initial_equity, records, marks = paper_account_input_from_dict(account_input)
    snapshot = materialize_paper_account(
        initial_equity_usd=initial_equity,
        records=records,
        marks=marks,
        policy=account_policy,
    )

    base: dict[str, object] = {
        "schema": "qookey-paper-cycle-report-v0.1",
        "account_snapshot_id": snapshot.snapshot_id,
        "account_status": snapshot.status,
        "account_as_of_ms": snapshot.as_of_ms,
        "account_equity_usd": snapshot.equity_usd,
        "candidate_count": len(candidate_inputs),
        "broker_submissions_performed": 0,
        "lifecycle_simulations_performed": 0,
        "persistent_state_writes_performed": 0,
        "explicit_submission_required": True,
        "explicit_submission_allowed": False,
        "authority": _authority(),
    }

    if snapshot.status != "ACCOUNT_ACTIVE":
        return {
            **base,
            "cycle_id": _cycle_id(
                snapshot=snapshot,
                state="ACCOUNT_BLOCKED",
                portfolio_report=None,
                decisions=(),
            ),
            "state": "ACCOUNT_BLOCKED",
            "reasons": ["paper_account_not_active"],
            "portfolio_admission": None,
            "prepared_intents": [],
        }

    existing = portfolio_exposures_from_account(snapshot, policy=account_policy)
    candidates = _parse_candidates(
        tuple(candidate_inputs),
        account_snapshot=snapshot,
        policy=cycle_policy,
    )

    if not candidates:
        return {
            **base,
            "cycle_id": _cycle_id(
                snapshot=snapshot,
                state="NO_CANDIDATES",
                portfolio_report=None,
                decisions=(),
            ),
            "state": "NO_CANDIDATES",
            "reasons": ["candidate_set_empty"],
            "portfolio_admission": None,
            "prepared_intents": [],
            "existing_exposures": [asdict(item) for item in existing],
        }

    portfolio_report = admit_portfolio(
        equity_usd=snapshot.equity_usd,
        proposals=tuple(item.proposal for item in candidates),
        existing_exposures=existing,
        policy=portfolio_policy,
    )

    if portfolio_report["state"] != "PORTFOLIO_ADMITTED":
        return {
            **base,
            "cycle_id": _cycle_id(
                snapshot=snapshot,
                state="PORTFOLIO_REVIEW_REQUIRED",
                portfolio_report=portfolio_report,
                decisions=(),
            ),
            "state": "PORTFOLIO_REVIEW_REQUIRED",
            "reasons": list(cast(Sequence[str], portfolio_report["reasons"])),
            "portfolio_admission": portfolio_report,
            "prepared_intents": [],
            "existing_exposures": [asdict(item) for item in existing],
        }

    decisions: list[tuple[PaperCycleCandidate, PaperExecutionDecision]] = []
    prepared: list[PaperCyclePreparedIntent] = []
    for candidate in candidates:
        decision = prepare_paper_execution(
            symbol=candidate.symbol,
            strategy_family=candidate.strategy_family,
            family_validation_report=candidate.family_validation_report,
            portfolio_admission_report=portfolio_report,
            as_of_ms=candidate.as_of_ms,
            sizing_plan=candidate.sizing_plan,
            policy=execution_policy,
        )
        decisions.append((candidate, decision))
        intent = decision.intent
        prepared.append(
            PaperCyclePreparedIntent(
                proposal_id=candidate.proposal.proposal_id,
                symbol=candidate.symbol,
                strategy_family=candidate.strategy_family,
                as_of_ms=candidate.as_of_ms,
                decision_status=decision.status,
                decision_reason=decision.reason,
                intent_id=None if intent is None else intent.intent_id,
                notional_usd=None if intent is None else intent.notional_usd,
            )
        )

    all_ready = all(
        decision.status == "READY_FOR_PAPER_BROKER" and decision.intent is not None
        for _, decision in decisions
    )
    state = (
        "PAPER_INTENTS_READY_FOR_EXPLICIT_SUBMISSION"
        if all_ready
        else "CYCLE_REVIEW_REQUIRED"
    )
    reasons = (
        ["all_candidates_ready_for_explicit_paper_submission"]
        if all_ready
        else sorted(
            {
                f"{candidate.proposal.proposal_id}:{decision.reason}"
                for candidate, decision in decisions
                if decision.status != "READY_FOR_PAPER_BROKER"
            }
        )
    )
    prepared_for_output = [asdict(item) for item in prepared]
    decision_output = [
        {
            "proposal_id": candidate.proposal.proposal_id,
            "decision": asdict(decision),
        }
        for candidate, decision in decisions
    ]

    return {
        **base,
        "cycle_id": _cycle_id(
            snapshot=snapshot,
            state=state,
            portfolio_report=portfolio_report,
            decisions=tuple(decisions),
        ),
        "state": state,
        "reasons": reasons,
        "portfolio_admission": portfolio_report,
        "prepared_intents": prepared_for_output,
        "paper_execution_decisions": decision_output,
        "existing_exposures": [asdict(item) for item in existing],
        "explicit_submission_allowed": all_ready,
    }


def _cycle_id(
    *,
    snapshot: PaperAccountSnapshot,
    state: str,
    portfolio_report: Mapping[str, object] | None,
    decisions: Sequence[tuple[PaperCycleCandidate, PaperExecutionDecision]],
) -> str:
    decision_rows = []
    for candidate, decision in decisions:
        decision_rows.append(
            {
                "proposal_id": candidate.proposal.proposal_id,
                "decision_status": decision.status,
                "decision_reason": decision.reason,
                "intent_id": None if decision.intent is None else decision.intent.intent_id,
            }
        )
    decision_rows.sort(key=lambda item: str(item["proposal_id"]))
    payload: dict[str, object] = {
        "schema": "qookey-paper-cycle-id-v0.1",
        "account_snapshot_id": snapshot.snapshot_id,
        "state": state,
        "portfolio_report_sha256": (
            None
            if portfolio_report is None
            else _sha256(cast(Mapping[str, object], _canonicalize(portfolio_report)))
        ),
        "decisions": decision_rows,
    }
    return f"paper-cycle-v0-1-{_sha256(payload)}"


def paper_cycle_report_id_from_mapping(
    payload: Mapping[str, object],
) -> str:
    """Recompute the deterministic cycle id from one serialized cycle report."""

    if payload.get("schema") != "qookey-paper-cycle-report-v0.1":
        raise ValueError("unsupported paper cycle report schema")
    account_snapshot_id = payload.get("account_snapshot_id")
    state = payload.get("state")
    if not isinstance(account_snapshot_id, str) or not account_snapshot_id:
        raise ValueError("paper cycle account_snapshot_id is required")
    if not isinstance(state, str) or not state:
        raise ValueError("paper cycle state is required")

    portfolio_report = payload.get("portfolio_admission")
    if portfolio_report is not None and not isinstance(portfolio_report, Mapping):
        raise ValueError("paper cycle portfolio_admission must be an object or null")

    raw_decisions = payload.get("paper_execution_decisions", [])
    if not isinstance(raw_decisions, list):
        raise ValueError("paper_execution_decisions must be a JSON array")

    decision_rows: list[dict[str, object]] = []
    for index, row in enumerate(raw_decisions):
        if not isinstance(row, Mapping):
            raise ValueError(f"paper_execution_decisions[{index}] must be an object")
        proposal_id = row.get("proposal_id")
        decision = row.get("decision")
        if not isinstance(proposal_id, str) or not proposal_id:
            raise ValueError(
                f"paper_execution_decisions[{index}].proposal_id is required"
            )
        if not isinstance(decision, Mapping):
            raise ValueError(
                f"paper_execution_decisions[{index}].decision must be an object"
            )
        decision_status = decision.get("status")
        decision_reason = decision.get("reason")
        if not isinstance(decision_status, str) or not decision_status:
            raise ValueError(
                f"paper_execution_decisions[{index}].decision.status is required"
            )
        if not isinstance(decision_reason, str) or not decision_reason:
            raise ValueError(
                f"paper_execution_decisions[{index}].decision.reason is required"
            )
        intent = decision.get("intent")
        if intent is not None and not isinstance(intent, Mapping):
            raise ValueError(
                f"paper_execution_decisions[{index}].decision.intent must be object/null"
            )
        intent_id = None
        if isinstance(intent, Mapping):
            raw_intent_id = intent.get("intent_id")
            if not isinstance(raw_intent_id, str) or not raw_intent_id:
                raise ValueError(
                    f"paper_execution_decisions[{index}].decision.intent.intent_id is required"
                )
            intent_id = raw_intent_id
        decision_rows.append(
            {
                "proposal_id": proposal_id,
                "decision_status": decision_status,
                "decision_reason": decision_reason,
                "intent_id": intent_id,
            }
        )

    decision_rows.sort(key=lambda item: str(item["proposal_id"]))
    canonical: dict[str, object] = {
        "schema": "qookey-paper-cycle-id-v0.1",
        "account_snapshot_id": account_snapshot_id,
        "state": state,
        "portfolio_report_sha256": (
            None
            if portfolio_report is None
            else _sha256(cast(Mapping[str, object], _canonicalize(portfolio_report)))
        ),
        "decisions": decision_rows,
    }
    return f"paper-cycle-v0-1-{_sha256(canonical)}"


def _authority() -> dict[str, object]:
    return {
        "manual_cycle_preparation_only": True,
        "provider_requests_performed": False,
        "r2_accessed": False,
        "holdout_accessed": False,
        "persistent_state_written": False,
        "strategy_ranking_authorized": False,
        "automatic_subset_selection_authorized": False,
        "automatic_broker_submission_authorized": False,
        "lifecycle_simulation_authorized": False,
        "short_paper_execution_authorized": False,
        "formal_trade_plan_authorized": False,
        "real_money_order_authorized": False,
        "live_trading_authorized": False,
    }


def paper_cycle_policy_from_config(payload: Mapping[str, object]) -> PaperCyclePolicy:
    if payload.get("schema") != "qookey-paper-cycle-orchestrator-v0.1":
        raise ValueError("unsupported paper cycle config")
    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("policy object is required")

    maximum = policy.get("maximum_candidates")
    if not isinstance(maximum, int) or isinstance(maximum, bool):
        raise ValueError("policy.maximum_candidates must be a JSON integer")
    for key in (
        "require_candidate_as_of_not_before_account",
        "require_all_intents_ready",
        "automatic_broker_submission_authorized",
        "lifecycle_simulation_authorized",
        "persistent_state_write_authorized",
    ):
        if not isinstance(policy.get(key), bool):
            raise ValueError(f"policy.{key} must be a JSON boolean")

    return PaperCyclePolicy(
        maximum_candidates=maximum,
        require_candidate_as_of_not_before_account=policy[
            "require_candidate_as_of_not_before_account"
        ],
        require_all_intents_ready=policy["require_all_intents_ready"],
        automatic_broker_submission_authorized=policy[
            "automatic_broker_submission_authorized"
        ],
        lifecycle_simulation_authorized=policy["lifecycle_simulation_authorized"],
        persistent_state_write_authorized=policy[
            "persistent_state_write_authorized"
        ],
    )


def paper_cycle_input_from_dict(
    payload: Mapping[str, object],
) -> tuple[Mapping[str, object], tuple[object, ...]]:
    if payload.get("schema") != "qookey-paper-cycle-input-v0.1":
        raise ValueError("unsupported paper cycle input schema")
    account_input = payload.get("account_input")
    candidates = payload.get("candidates")
    if not isinstance(account_input, Mapping):
        raise ValueError("account_input object is required")
    if not isinstance(candidates, list):
        raise ValueError("candidates must be a JSON array")
    return account_input, tuple(candidates)
