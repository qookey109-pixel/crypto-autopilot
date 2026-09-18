from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass

from crypto_autopilot.paper.account_v0_1 import (
    PaperAccountPolicy,
    PaperMark,
    materialize_paper_account,
    paper_account_evidence,
    paper_account_input_from_dict,
    portfolio_exposures_from_account,
)
from crypto_autopilot.paper.lifecycle_batch_v0_1 import (
    paper_lifecycle_batch_report_id_from_mapping,
)


@dataclass(frozen=True, slots=True)
class PaperAccountAdvancePolicy:
    """Deterministic latest-record replacement policy for Paper Account V0.1."""

    require_exact_batch_id_confirmation: bool = True
    reject_lifecycle_id_change_for_existing_intent: bool = True
    reject_event_time_regression: bool = True
    reject_same_time_different_report: bool = True
    allow_identical_record_replay: bool = True
    persistent_state_write_authorized: bool = False
    provider_access_authorized: bool = False
    live_trading_authorized: bool = False

    def __post_init__(self) -> None:
        flags = (
            self.require_exact_batch_id_confirmation,
            self.reject_lifecycle_id_change_for_existing_intent,
            self.reject_event_time_regression,
            self.reject_same_time_different_report,
            self.allow_identical_record_replay,
            self.persistent_state_write_authorized,
            self.provider_access_authorized,
            self.live_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in flags):
            raise ValueError("paper account advance policy flags must be booleans")
        if not self.require_exact_batch_id_confirmation:
            raise ValueError("exact batch-id confirmation is required in V0.1")
        if not self.reject_lifecycle_id_change_for_existing_intent:
            raise ValueError("existing-intent lifecycle-id changes must fail closed")
        if not self.reject_event_time_regression:
            raise ValueError("lifecycle event-time regression must fail closed")
        if not self.reject_same_time_different_report:
            raise ValueError("same-time different lifecycle report must fail closed")
        if not self.allow_identical_record_replay:
            raise ValueError("identical record replay must remain idempotent in V0.1")
        if (
            self.persistent_state_write_authorized
            or self.provider_access_authorized
            or self.live_trading_authorized
        ):
            raise ValueError("Paper Account Advance V0.1 authority exceeds its scope")


@dataclass(frozen=True, slots=True)
class _RecordIdentity:
    intent_id: str
    lifecycle_id: str
    last_event_time_ms: int
    report_sha256: str


def _sha256(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(
        dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _record_identity(
    record: Mapping[str, object],
    *,
    label: str,
) -> _RecordIdentity:
    execution = record.get("paper_execution_evidence")
    lifecycle = record.get("paper_lifecycle_report")
    if not isinstance(execution, Mapping) or not isinstance(lifecycle, Mapping):
        raise ValueError(f"{label} requires execution and lifecycle evidence")

    decision = execution.get("decision")
    if not isinstance(decision, Mapping):
        raise ValueError(f"{label} paper execution decision is required")
    intent = decision.get("intent")
    if not isinstance(intent, Mapping):
        raise ValueError(f"{label} paper execution intent is required")
    intent_id = intent.get("intent_id")
    if not isinstance(intent_id, str) or not intent_id:
        raise ValueError(f"{label} intent_id is required")

    plan = lifecycle.get("plan")
    result = lifecycle.get("result")
    if not isinstance(plan, Mapping) or not isinstance(result, Mapping):
        raise ValueError(f"{label} lifecycle plan/result are required")
    lifecycle_id = plan.get("lifecycle_id")
    if not isinstance(lifecycle_id, str) or not lifecycle_id:
        raise ValueError(f"{label} lifecycle_id is required")
    if result.get("lifecycle_id") != lifecycle_id:
        raise ValueError(f"{label} lifecycle result id does not match plan")
    if plan.get("intent_id") != intent_id or result.get("intent_id") != intent_id:
        raise ValueError(f"{label} lifecycle intent id does not match execution intent")

    events = result.get("events")
    if not isinstance(events, (list, tuple)) or not events:
        raise ValueError(f"{label} lifecycle events must be non-empty")
    event_times: list[int] = []
    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            raise ValueError(f"{label} events[{index}] must be an object")
        time_ms = event.get("time_ms")
        if not isinstance(time_ms, int) or isinstance(time_ms, bool) or time_ms < 0:
            raise ValueError(f"{label} events[{index}].time_ms must be integer")
        event_times.append(time_ms)
    if event_times != sorted(event_times):
        raise ValueError(f"{label} lifecycle event times must be non-decreasing")

    return _RecordIdentity(
        intent_id=intent_id,
        lifecycle_id=lifecycle_id,
        last_event_time_ms=event_times[-1],
        report_sha256=_sha256(lifecycle),
    )


def _validate_batch_authority(payload: Mapping[str, object]) -> None:
    if payload.get("schema") != "qookey-paper-lifecycle-batch-report-v0.1":
        raise ValueError("unsupported paper lifecycle batch report schema")
    if payload.get("state") != "PAPER_LIFECYCLE_BATCH_COMPLETE":
        raise ValueError("paper lifecycle batch is not complete")
    for key in (
        "provider_requests_performed",
        "persistent_state_writes_performed",
    ):
        value = payload.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value != 0:
            raise ValueError(f"paper lifecycle batch {key} must equal zero")

    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("paper lifecycle batch authority object is required")
    if authority.get("explicit_paper_lifecycle_simulation_only") is not True:
        raise ValueError("paper lifecycle batch must remain explicit simulation-only")
    for key in (
        "provider_requests_performed",
        "r2_accessed",
        "holdout_accessed",
        "automatic_lifecycle_simulation_authorized",
        "scheduled_lifecycle_simulation_authorized",
        "persistent_state_write_authorized",
        "short_paper_execution_authorized",
        "formal_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"paper lifecycle batch authority must remain closed: {key}")


def _parse_next_marks(
    marks: Sequence[object],
    *,
    initial_equity_usd: float,
) -> tuple[PaperMark, ...]:
    payload = {
        "schema": "qookey-paper-account-state-input-v0.1",
        "initial_equity_usd": initial_equity_usd,
        "records": [],
        "marks": list(marks),
    }
    _, _, parsed_marks = paper_account_input_from_dict(payload)
    return parsed_marks


def advance_paper_account(
    *,
    previous_account_input: Mapping[str, object],
    lifecycle_batch_report: Mapping[str, object],
    confirmation_batch_id: str,
    next_marks: Sequence[object],
    advance_policy: PaperAccountAdvancePolicy = PaperAccountAdvancePolicy(),
    account_policy: PaperAccountPolicy = PaperAccountPolicy(),
) -> dict[str, object]:
    """Replace latest lifecycle evidence by intent and rematerialize the account."""

    initial_equity, previous_records, previous_marks = paper_account_input_from_dict(
        previous_account_input
    )
    previous_snapshot = materialize_paper_account(
        initial_equity_usd=initial_equity,
        records=previous_records,
        marks=previous_marks,
        policy=account_policy,
    )

    _validate_batch_authority(lifecycle_batch_report)
    batch_id = lifecycle_batch_report.get("batch_id")
    if not isinstance(batch_id, str) or not batch_id:
        raise ValueError("paper lifecycle batch id is required")
    recomputed_batch_id = paper_lifecycle_batch_report_id_from_mapping(
        lifecycle_batch_report
    )
    if recomputed_batch_id != batch_id:
        raise ValueError("paper lifecycle batch id does not match report contents")
    if (
        advance_policy.require_exact_batch_id_confirmation
        and confirmation_batch_id != batch_id
    ):
        raise ValueError("exact batch-id confirmation does not match report")

    batch_records_raw = lifecycle_batch_report.get("account_records")
    if not isinstance(batch_records_raw, list) or not batch_records_raw:
        raise ValueError("paper lifecycle batch account_records are required")

    previous_by_intent: dict[str, tuple[Mapping[str, object], _RecordIdentity]] = {}
    for index, record in enumerate(previous_records):
        identity = _record_identity(record, label=f"previous_records[{index}]")
        if identity.intent_id in previous_by_intent:
            raise ValueError("previous account contains duplicate intent ids")
        previous_by_intent[identity.intent_id] = (record, identity)

    batch_by_intent: dict[str, tuple[Mapping[str, object], _RecordIdentity]] = {}
    for index, record in enumerate(batch_records_raw):
        if not isinstance(record, Mapping):
            raise ValueError(f"batch account_records[{index}] must be an object")
        identity = _record_identity(record, label=f"batch_records[{index}]")
        if identity.intent_id in batch_by_intent:
            raise ValueError("paper lifecycle batch contains duplicate intent ids")
        batch_by_intent[identity.intent_id] = (record, identity)

    merged: dict[str, Mapping[str, object]] = {
        intent_id: record for intent_id, (record, _) in previous_by_intent.items()
    }
    added = 0
    replaced = 0
    unchanged = 0

    for intent_id, (new_record, new_identity) in batch_by_intent.items():
        previous = previous_by_intent.get(intent_id)
        if previous is None:
            merged[intent_id] = new_record
            added += 1
            continue

        old_record, old_identity = previous
        if (
            advance_policy.reject_lifecycle_id_change_for_existing_intent
            and new_identity.lifecycle_id != old_identity.lifecycle_id
        ):
            raise ValueError(
                f"existing intent {intent_id} changed lifecycle_id"
            )
        if new_identity.report_sha256 == old_identity.report_sha256:
            if not advance_policy.allow_identical_record_replay:
                raise ValueError("identical lifecycle replay is disabled")
            merged[intent_id] = old_record
            unchanged += 1
            continue
        if (
            advance_policy.reject_event_time_regression
            and new_identity.last_event_time_ms < old_identity.last_event_time_ms
        ):
            raise ValueError(
                f"existing intent {intent_id} lifecycle event time regressed"
            )
        if (
            advance_policy.reject_same_time_different_report
            and new_identity.last_event_time_ms == old_identity.last_event_time_ms
        ):
            raise ValueError(
                f"existing intent {intent_id} changed at identical event time"
            )

        merged[intent_id] = new_record
        replaced += 1

    canonical_records = [
        merged[intent_id] for intent_id in sorted(merged)
    ]
    parsed_next_marks = _parse_next_marks(
        next_marks,
        initial_equity_usd=initial_equity,
    )
    next_snapshot = materialize_paper_account(
        initial_equity_usd=initial_equity,
        records=tuple(canonical_records),
        marks=parsed_next_marks,
        policy=account_policy,
    )

    next_account_input = {
        "schema": "qookey-paper-account-state-input-v0.1",
        "initial_equity_usd": initial_equity,
        "records": [dict(record) for record in canonical_records],
        "marks": [asdict(mark) for mark in parsed_next_marks],
    }

    if next_snapshot.status == "ACCOUNT_ACTIVE":
        exposures = portfolio_exposures_from_account(
            next_snapshot,
            policy=account_policy,
        )
        portfolio_capacity_exported = True
    else:
        exposures = ()
        portfolio_capacity_exported = False

    state = (
        "ACCOUNT_ADVANCE_NO_CHANGE"
        if added == 0 and replaced == 0
        else "ACCOUNT_ADVANCED"
    )
    advance_payload: dict[str, object] = {
        "schema": "qookey-paper-account-advance-id-v0.1",
        "previous_snapshot_id": previous_snapshot.snapshot_id,
        "batch_id": batch_id,
        "next_snapshot_id": next_snapshot.snapshot_id,
        "added_record_count": added,
        "replaced_record_count": replaced,
        "unchanged_record_count": unchanged,
    }
    advance_id = f"paper-account-advance-v0-1-{_sha256(advance_payload)}"

    return {
        "schema": "qookey-paper-account-advance-report-v0.1",
        "advance_id": advance_id,
        "state": state,
        "batch_id": batch_id,
        "previous_snapshot_id": previous_snapshot.snapshot_id,
        "next_snapshot_id": next_snapshot.snapshot_id,
        "added_record_count": added,
        "replaced_record_count": replaced,
        "unchanged_record_count": unchanged,
        "total_record_count": len(canonical_records),
        "next_account_input": next_account_input,
        "account": paper_account_evidence(next_snapshot, account_policy),
        "portfolio_existing_exposures": [asdict(item) for item in exposures],
        "portfolio_capacity_exported": portfolio_capacity_exported,
        "provider_requests_performed": 0,
        "persistent_state_writes_performed": 0,
        "authority": {
            "explicit_account_rematerialization_only": True,
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
            "V0.1 stores no state; next_account_input must be carried explicitly.",
            "Existing intent records are replaced only by forward lifecycle evidence.",
            "Funding, liquidation and margin maintenance remain unmodeled.",
        ],
    }


def paper_account_advance_report_id_from_mapping(
    payload: Mapping[str, object],
) -> str:
    """Recompute one serialized Account Advance id and verify summary consistency."""

    if payload.get("schema") != "qookey-paper-account-advance-report-v0.1":
        raise ValueError("unsupported paper account advance report schema")
    if payload.get("state") not in {"ACCOUNT_ADVANCED", "ACCOUNT_ADVANCE_NO_CHANGE"}:
        raise ValueError("paper account advance report is not a successful state")

    required_ids = (
        "advance_id",
        "batch_id",
        "previous_snapshot_id",
        "next_snapshot_id",
    )
    for key in required_ids:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"paper account advance {key} is required")

    count_keys = (
        "added_record_count",
        "replaced_record_count",
        "unchanged_record_count",
        "total_record_count",
    )
    counts: dict[str, int] = {}
    for key in count_keys:
        value = payload.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"paper account advance {key} must be non-negative integer")
        counts[key] = value

    changed = counts["added_record_count"] + counts["replaced_record_count"]
    if payload.get("state") == "ACCOUNT_ADVANCE_NO_CHANGE" and changed != 0:
        raise ValueError("no-change account advance cannot add or replace records")
    if payload.get("state") == "ACCOUNT_ADVANCED" and changed == 0:
        raise ValueError("advanced account state requires added/replaced records")

    next_account_input = payload.get("next_account_input")
    account = payload.get("account")
    exposures = payload.get("portfolio_existing_exposures")
    capacity = payload.get("portfolio_capacity_exported")
    if not isinstance(next_account_input, Mapping):
        raise ValueError("paper account advance next_account_input is required")
    if not isinstance(account, Mapping):
        raise ValueError("paper account advance account evidence is required")
    if not isinstance(exposures, list):
        raise ValueError("paper account advance portfolio exposures must be an array")
    if not isinstance(capacity, bool):
        raise ValueError("paper account advance portfolio_capacity_exported must be boolean")

    if account.get("schema") != "qookey-paper-account-state-report-v0.1":
        raise ValueError("paper account advance account evidence schema is invalid")
    snapshot = account.get("snapshot")
    if not isinstance(snapshot, Mapping):
        raise ValueError("paper account advance account snapshot is required")
    if snapshot.get("snapshot_id") != payload.get("next_snapshot_id"):
        raise ValueError("paper account advance next snapshot id does not match account evidence")
    if snapshot.get("open_position_count") != len(exposures) and capacity:
        raise ValueError("paper account advance exposure count does not match open positions")
    if snapshot.get("status") == "ACCOUNT_ACTIVE" and not capacity:
        raise ValueError("active paper account must export portfolio capacity")
    if snapshot.get("status") == "ACCOUNT_INSOLVENT" and capacity:
        raise ValueError("insolvent paper account cannot export portfolio capacity")

    for key in (
        "provider_requests_performed",
        "persistent_state_writes_performed",
    ):
        value = payload.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value != 0:
            raise ValueError(f"paper account advance {key} must equal zero")

    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("paper account advance authority object is required")
    if authority.get("explicit_account_rematerialization_only") is not True:
        raise ValueError("paper account advance must remain rematerialization-only")
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
            raise ValueError(f"paper account advance authority must remain closed: {key}")

    advance_payload: dict[str, object] = {
        "schema": "qookey-paper-account-advance-id-v0.1",
        "previous_snapshot_id": payload["previous_snapshot_id"],
        "batch_id": payload["batch_id"],
        "next_snapshot_id": payload["next_snapshot_id"],
        "added_record_count": counts["added_record_count"],
        "replaced_record_count": counts["replaced_record_count"],
        "unchanged_record_count": counts["unchanged_record_count"],
    }
    return f"paper-account-advance-v0-1-{_sha256(advance_payload)}"


def paper_account_advance_policy_from_config(
    payload: Mapping[str, object],
) -> PaperAccountAdvancePolicy:
    if payload.get("schema") != "qookey-paper-account-advance-v0.1":
        raise ValueError("unsupported paper account advance config")
    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("policy object is required")
    keys = (
        "require_exact_batch_id_confirmation",
        "reject_lifecycle_id_change_for_existing_intent",
        "reject_event_time_regression",
        "reject_same_time_different_report",
        "allow_identical_record_replay",
        "persistent_state_write_authorized",
        "provider_access_authorized",
        "live_trading_authorized",
    )
    for key in keys:
        if not isinstance(policy.get(key), bool):
            raise ValueError(f"policy.{key} must be a JSON boolean")
    return PaperAccountAdvancePolicy(
        require_exact_batch_id_confirmation=policy[
            "require_exact_batch_id_confirmation"
        ],
        reject_lifecycle_id_change_for_existing_intent=policy[
            "reject_lifecycle_id_change_for_existing_intent"
        ],
        reject_event_time_regression=policy["reject_event_time_regression"],
        reject_same_time_different_report=policy[
            "reject_same_time_different_report"
        ],
        allow_identical_record_replay=policy["allow_identical_record_replay"],
        persistent_state_write_authorized=policy[
            "persistent_state_write_authorized"
        ],
        provider_access_authorized=policy["provider_access_authorized"],
        live_trading_authorized=policy["live_trading_authorized"],
    )


def paper_account_advance_input_from_dict(
    payload: Mapping[str, object],
) -> tuple[Mapping[str, object], Mapping[str, object], tuple[object, ...]]:
    if payload.get("schema") != "qookey-paper-account-advance-input-v0.1":
        raise ValueError("unsupported paper account advance input schema")
    previous_account_input = payload.get("previous_account_input")
    batch_report = payload.get("lifecycle_batch_report")
    next_marks = payload.get("next_marks")
    if not isinstance(previous_account_input, Mapping):
        raise ValueError("previous_account_input object is required")
    if not isinstance(batch_report, Mapping):
        raise ValueError("lifecycle_batch_report object is required")
    if not isinstance(next_marks, list):
        raise ValueError("next_marks must be a JSON array")
    return previous_account_input, batch_report, tuple(next_marks)
