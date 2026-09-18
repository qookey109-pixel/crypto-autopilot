from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass

from crypto_autopilot.exchanges.paper import PaperBroker
from crypto_autopilot.paper.cycle_v0_1 import paper_cycle_report_id_from_mapping
from crypto_autopilot.paper.execution_v0_1 import (
    PaperExecutionDecision,
    PaperExecutionIntent,
    PaperExecutionPolicy,
    paper_execution_evidence,
    submit_paper_execution,
)


@dataclass(frozen=True, slots=True)
class PaperSubmissionSessionPolicy:
    maximum_intents: int = 5
    require_exact_cycle_id_confirmation: bool = True
    require_complete_ready_basket: bool = True
    explicit_paper_submission_authorized: bool = True
    automatic_submission_authorized: bool = False
    scheduled_submission_authorized: bool = False
    persistent_broker_state_authorized: bool = False
    lifecycle_simulation_authorized: bool = False
    live_trading_authorized: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.maximum_intents, int) or isinstance(
            self.maximum_intents, bool
        ):
            raise ValueError("maximum_intents must be an integer")
        if self.maximum_intents < 1:
            raise ValueError("maximum_intents must be positive")
        flags = (
            self.require_exact_cycle_id_confirmation,
            self.require_complete_ready_basket,
            self.explicit_paper_submission_authorized,
            self.automatic_submission_authorized,
            self.scheduled_submission_authorized,
            self.persistent_broker_state_authorized,
            self.lifecycle_simulation_authorized,
            self.live_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in flags):
            raise ValueError("paper submission session policy flags must be booleans")
        if not self.require_exact_cycle_id_confirmation:
            raise ValueError("exact cycle-id confirmation is required in V0.1")
        if not self.require_complete_ready_basket:
            raise ValueError("complete ready basket is required in V0.1")
        if not self.explicit_paper_submission_authorized:
            raise ValueError("V0.1 session requires explicit paper submission authority")
        if (
            self.automatic_submission_authorized
            or self.scheduled_submission_authorized
            or self.persistent_broker_state_authorized
            or self.lifecycle_simulation_authorized
            or self.live_trading_authorized
        ):
            raise ValueError("Paper Submission Session V0.1 authority exceeds its scope")


@dataclass(frozen=True, slots=True)
class _SessionItem:
    proposal_id: str
    decision: PaperExecutionDecision


def _sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(
        dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _strict_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{label} must be finite")
    return converted


def _decision_from_mapping(payload: Mapping[str, object]) -> PaperExecutionDecision:
    status = payload.get("status")
    reason = payload.get("reason")
    intent_payload = payload.get("intent")
    if status != "READY_FOR_PAPER_BROKER":
        raise ValueError("paper execution decision is not ready")
    if not isinstance(reason, str) or not reason:
        raise ValueError("paper execution decision reason is required")
    if not isinstance(intent_payload, Mapping):
        raise ValueError("ready paper execution decision requires intent")

    as_of_ms = intent_payload.get("as_of_ms")
    if not isinstance(as_of_ms, int) or isinstance(as_of_ms, bool) or as_of_ms < 0:
        raise ValueError("paper execution intent as_of_ms must be non-negative integer")
    numeric_keys = (
        "entry_price",
        "stop_price",
        "notional_usd",
        "target_risk_usd",
        "realized_risk_usd",
        "risk_utilization_fraction",
    )
    numeric: dict[str, float] = {}
    for key in numeric_keys:
        numeric[key] = _strict_number(intent_payload.get(key), f"intent.{key}")

    required_strings = (
        "intent_id",
        "symbol",
        "strategy_family",
        "family_validation_report_sha256",
        "portfolio_proposal_id",
        "portfolio_admission_report_sha256",
        "direction",
        "status",
    )
    strings: dict[str, str] = {}
    for key in required_strings:
        value = intent_payload.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"intent.{key} is required")
        strings[key] = value

    if strings["status"] != "READY_FOR_PAPER_BROKER":
        raise ValueError("paper execution intent status is not ready")
    if strings["direction"] != "LONG":
        raise ValueError("Paper Submission Session V0.1 supports LONG intents only")
    if numeric["entry_price"] <= 0.0 or numeric["stop_price"] <= 0.0:
        raise ValueError("paper execution intent prices must be positive")
    if numeric["notional_usd"] <= 0.0:
        raise ValueError("paper execution intent notional must be positive")

    intent = PaperExecutionIntent(
        intent_id=strings["intent_id"],
        symbol=strings["symbol"],
        strategy_family=strings["strategy_family"],
        family_validation_report_sha256=strings[
            "family_validation_report_sha256"
        ],
        portfolio_proposal_id=strings["portfolio_proposal_id"],
        portfolio_admission_report_sha256=strings[
            "portfolio_admission_report_sha256"
        ],
        direction=strings["direction"],
        as_of_ms=as_of_ms,
        entry_price=numeric["entry_price"],
        stop_price=numeric["stop_price"],
        notional_usd=numeric["notional_usd"],
        target_risk_usd=numeric["target_risk_usd"],
        realized_risk_usd=numeric["realized_risk_usd"],
        risk_utilization_fraction=numeric["risk_utilization_fraction"],
        status=strings["status"],
    )
    return PaperExecutionDecision(status=status, reason=reason, intent=intent)


def _validate_cycle_authority(payload: Mapping[str, object]) -> None:
    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("paper cycle authority object is required")
    if authority.get("manual_cycle_preparation_only") is not True:
        raise ValueError("paper cycle must remain manual-preparation-only")
    for key in (
        "provider_requests_performed",
        "r2_accessed",
        "holdout_accessed",
        "persistent_state_written",
        "strategy_ranking_authorized",
        "automatic_subset_selection_authorized",
        "automatic_broker_submission_authorized",
        "lifecycle_simulation_authorized",
        "short_paper_execution_authorized",
        "formal_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"paper cycle authority must remain closed: {key}")


def _preflight_cycle(
    cycle_report: Mapping[str, object],
    *,
    confirmation_cycle_id: str,
    broker: PaperBroker,
    policy: PaperSubmissionSessionPolicy,
) -> tuple[str, tuple[_SessionItem, ...]]:
    if cycle_report.get("schema") != "qookey-paper-cycle-report-v0.1":
        raise ValueError("unsupported paper cycle report schema")
    if cycle_report.get("state") != "PAPER_INTENTS_READY_FOR_EXPLICIT_SUBMISSION":
        raise ValueError("paper cycle is not ready for explicit submission")
    if cycle_report.get("explicit_submission_required") is not True:
        raise ValueError("paper cycle does not declare explicit submission requirement")
    if cycle_report.get("explicit_submission_allowed") is not True:
        raise ValueError("paper cycle does not allow explicit submission")
    for key in (
        "broker_submissions_performed",
        "lifecycle_simulations_performed",
        "persistent_state_writes_performed",
    ):
        value = cycle_report.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value != 0:
            raise ValueError(f"paper cycle {key} must equal zero before session")
    _validate_cycle_authority(cycle_report)

    cycle_id = cycle_report.get("cycle_id")
    if not isinstance(cycle_id, str) or not cycle_id:
        raise ValueError("paper cycle id is required")
    recomputed = paper_cycle_report_id_from_mapping(cycle_report)
    if recomputed != cycle_id:
        raise ValueError("paper cycle id does not match report contents")
    if policy.require_exact_cycle_id_confirmation and confirmation_cycle_id != cycle_id:
        raise ValueError("exact cycle-id confirmation does not match report")

    candidate_count = cycle_report.get("candidate_count")
    if (
        not isinstance(candidate_count, int)
        or isinstance(candidate_count, bool)
        or candidate_count < 1
        or candidate_count > policy.maximum_intents
    ):
        raise ValueError("paper cycle candidate_count is outside session bounds")

    portfolio = cycle_report.get("portfolio_admission")
    if not isinstance(portfolio, Mapping) or portfolio.get("state") != "PORTFOLIO_ADMITTED":
        raise ValueError("paper cycle portfolio is not admitted")
    admitted = portfolio.get("admitted_proposal_ids")
    if not isinstance(admitted, list) or any(not isinstance(item, str) for item in admitted):
        raise ValueError("portfolio admitted_proposal_ids must be an array of strings")

    decisions_raw = cycle_report.get("paper_execution_decisions")
    prepared_raw = cycle_report.get("prepared_intents")
    if not isinstance(decisions_raw, list) or not isinstance(prepared_raw, list):
        raise ValueError("paper cycle decisions/prepared intents must be arrays")
    if len(decisions_raw) != candidate_count or len(prepared_raw) != candidate_count:
        raise ValueError("paper cycle candidate/decision/prepared counts do not match")

    prepared_by_proposal: dict[str, Mapping[str, object]] = {}
    for index, row in enumerate(prepared_raw):
        if not isinstance(row, Mapping):
            raise ValueError(f"prepared_intents[{index}] must be an object")
        proposal_id = row.get("proposal_id")
        if not isinstance(proposal_id, str) or not proposal_id:
            raise ValueError(f"prepared_intents[{index}].proposal_id is required")
        if proposal_id in prepared_by_proposal:
            raise ValueError("duplicate prepared proposal id")
        prepared_by_proposal[proposal_id] = row

    items: list[_SessionItem] = []
    seen_intent_ids: set[str] = set()
    seen_proposals: set[str] = set()
    for index, row in enumerate(decisions_raw):
        if not isinstance(row, Mapping):
            raise ValueError(f"paper_execution_decisions[{index}] must be an object")
        proposal_id = row.get("proposal_id")
        decision_payload = row.get("decision")
        if not isinstance(proposal_id, str) or not proposal_id:
            raise ValueError(f"paper_execution_decisions[{index}].proposal_id is required")
        if proposal_id in seen_proposals:
            raise ValueError("duplicate paper execution proposal id")
        seen_proposals.add(proposal_id)
        if proposal_id not in admitted:
            raise ValueError("paper execution proposal is not in admitted basket")
        if not isinstance(decision_payload, Mapping):
            raise ValueError(f"paper_execution_decisions[{index}].decision must be object")
        decision = _decision_from_mapping(decision_payload)
        assert decision.intent is not None
        intent = decision.intent
        if intent.portfolio_proposal_id != proposal_id:
            raise ValueError("paper execution intent proposal id does not match cycle row")
        if intent.intent_id in seen_intent_ids:
            raise ValueError("duplicate paper execution intent id")
        seen_intent_ids.add(intent.intent_id)

        prepared = prepared_by_proposal.get(proposal_id)
        if prepared is None:
            raise ValueError("paper execution decision has no prepared-intent row")
        expected = {
            "symbol": intent.symbol,
            "strategy_family": intent.strategy_family,
            "as_of_ms": intent.as_of_ms,
            "decision_status": decision.status,
            "decision_reason": decision.reason,
            "intent_id": intent.intent_id,
            "notional_usd": intent.notional_usd,
        }
        for key, value in expected.items():
            if prepared.get(key) != value:
                raise ValueError(f"prepared intent mismatch for {proposal_id}: {key}")
        items.append(_SessionItem(proposal_id=proposal_id, decision=decision))

    if set(admitted) != seen_proposals:
        raise ValueError("session requires the complete admitted proposal basket")
    if set(prepared_by_proposal) != seen_proposals:
        raise ValueError("prepared intents do not match complete decision basket")

    items.sort(key=lambda item: item.proposal_id)

    for item in items:
        assert item.decision.intent is not None
        intent = item.decision.intent
        existing = next(
            (order for order in broker.orders if order.order_id == intent.intent_id),
            None,
        )
        if existing is None:
            continue
        if (
            existing.symbol != intent.symbol
            or existing.side != intent.direction
            or existing.notional_usd != intent.notional_usd
        ):
            raise ValueError("existing broker order conflicts with cycle intent")

    return cycle_id, tuple(items)


def submit_paper_cycle_session(
    *,
    cycle_report: Mapping[str, object],
    confirmation_cycle_id: str,
    broker: PaperBroker,
    session_policy: PaperSubmissionSessionPolicy = PaperSubmissionSessionPolicy(),
    execution_policy: PaperExecutionPolicy = PaperExecutionPolicy(),
) -> dict[str, object]:
    """Explicitly submit one fully-ready paper cycle to the in-memory PaperBroker."""

    cycle_id, items = _preflight_cycle(
        cycle_report,
        confirmation_cycle_id=confirmation_cycle_id,
        broker=broker,
        policy=session_policy,
    )

    receipts: list[dict[str, object]] = []
    evidence_rows: list[dict[str, object]] = []
    replayed_count = 0
    for item in items:
        receipt = submit_paper_execution(
            item.decision,
            broker,
            policy=execution_policy,
        )
        if receipt.replayed:
            replayed_count += 1
        receipts.append(
            {
                "proposal_id": item.proposal_id,
                "receipt": asdict(receipt),
            }
        )
        evidence_rows.append(
            {
                "proposal_id": item.proposal_id,
                "paper_execution_evidence": paper_execution_evidence(
                    item.decision,
                    receipt,
                ),
            }
        )

    intent_ids = [
        item.decision.intent.intent_id
        for item in items
        if item.decision.intent is not None
    ]
    session_payload: dict[str, object] = {
        "schema": "qookey-paper-submission-session-id-v0.1",
        "cycle_id": cycle_id,
        "intent_ids": intent_ids,
    }
    session_id = f"paper-session-v0-1-{_sha256(session_payload)}"

    return {
        "schema": "qookey-paper-submission-session-report-v0.1",
        "session_id": session_id,
        "cycle_id": cycle_id,
        "state": "PAPER_SESSION_ACCEPTED",
        "intent_count": len(items),
        "new_submission_count": len(items) - replayed_count,
        "replayed_submission_count": replayed_count,
        "broker_order_count_after": len(broker.orders),
        "receipts": receipts,
        "paper_execution_evidence": evidence_rows,
        "lifecycle_simulations_performed": 0,
        "persistent_state_writes_performed": 0,
        "authority": {
            "explicit_in_memory_paper_submission_only": True,
            "provider_requests_performed": False,
            "r2_accessed": False,
            "holdout_accessed": False,
            "automatic_submission_authorized": False,
            "scheduled_submission_authorized": False,
            "persistent_broker_state_authorized": False,
            "lifecycle_simulation_authorized": False,
            "short_paper_execution_authorized": False,
            "formal_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
        "limitations": [
            "The Repository Paper Broker remains in-memory and intent-only.",
            "Lifecycle simulation is a separate explicit downstream step.",
            "Session acceptance is not evidence of strategy profitability.",
        ],
    }


def paper_submission_session_policy_from_config(
    payload: Mapping[str, object],
) -> PaperSubmissionSessionPolicy:
    if payload.get("schema") != "qookey-paper-submission-session-v0.1":
        raise ValueError("unsupported paper submission session config")
    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("policy object is required")
    maximum = policy.get("maximum_intents")
    if not isinstance(maximum, int) or isinstance(maximum, bool):
        raise ValueError("policy.maximum_intents must be a JSON integer")
    keys = (
        "require_exact_cycle_id_confirmation",
        "require_complete_ready_basket",
        "explicit_paper_submission_authorized",
        "automatic_submission_authorized",
        "scheduled_submission_authorized",
        "persistent_broker_state_authorized",
        "lifecycle_simulation_authorized",
        "live_trading_authorized",
    )
    for key in keys:
        if not isinstance(policy.get(key), bool):
            raise ValueError(f"policy.{key} must be a JSON boolean")
    return PaperSubmissionSessionPolicy(
        maximum_intents=maximum,
        require_exact_cycle_id_confirmation=policy[
            "require_exact_cycle_id_confirmation"
        ],
        require_complete_ready_basket=policy["require_complete_ready_basket"],
        explicit_paper_submission_authorized=policy[
            "explicit_paper_submission_authorized"
        ],
        automatic_submission_authorized=policy["automatic_submission_authorized"],
        scheduled_submission_authorized=policy["scheduled_submission_authorized"],
        persistent_broker_state_authorized=policy[
            "persistent_broker_state_authorized"
        ],
        lifecycle_simulation_authorized=policy["lifecycle_simulation_authorized"],
        live_trading_authorized=policy["live_trading_authorized"],
    )
