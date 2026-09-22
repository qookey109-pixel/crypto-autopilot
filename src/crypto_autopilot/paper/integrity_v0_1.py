from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass\nfrom typing import cast

from crypto_autopilot.paper.account_advance_v0_1 import (
    paper_account_advance_report_id_from_mapping,
)
from crypto_autopilot.paper.checkpoint_v0_1 import (
    paper_loop_checkpoint_report_id_from_mapping,
)
from crypto_autopilot.paper.cycle_v0_1 import paper_cycle_report_id_from_mapping
from crypto_autopilot.paper.lifecycle_batch_v0_1 import (
    paper_lifecycle_batch_report_id_from_mapping,
)
from crypto_autopilot.paper.resume_v0_1 import (
    paper_loop_resume_report_id_from_mapping,
)
from crypto_autopilot.paper.session_v0_1 import (
    paper_submission_session_report_id_from_mapping,
)


@dataclass(frozen=True, slots=True)
class PaperLoopIntegrityPolicy:
    """Audit-only policy for a chained multi-cycle paper transcript."""

    minimum_rounds: int = 2
    maximum_rounds: int = 8
    require_exact_checkpoint_chaining: bool = True
    require_forward_snapshot_time: bool = True
    require_unique_cycle_ids: bool = True
    require_unique_session_ids: bool = True
    require_unique_batch_ids: bool = True
    require_unique_advance_ids: bool = True
    require_unique_forward_intent_ids: bool = True
    provider_access_authorized: bool = False
    persistent_state_write_authorized: bool = False
    automatic_execution_authorized: bool = False
    live_trading_authorized: bool = False

    def __post_init__(self) -> None:
        for label, value in (
            ("minimum_rounds", self.minimum_rounds),
            ("maximum_rounds", self.maximum_rounds),
        ):
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"{label} must be an integer")
        if self.minimum_rounds < 2:
            raise ValueError("minimum_rounds must be at least two")
        if self.maximum_rounds < self.minimum_rounds:
            raise ValueError("maximum_rounds cannot be below minimum_rounds")

        flags = (
            self.require_exact_checkpoint_chaining,
            self.require_forward_snapshot_time,
            self.require_unique_cycle_ids,
            self.require_unique_session_ids,
            self.require_unique_batch_ids,
            self.require_unique_advance_ids,
            self.require_unique_forward_intent_ids,
            self.provider_access_authorized,
            self.persistent_state_write_authorized,
            self.automatic_execution_authorized,
            self.live_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in flags):
            raise ValueError("paper loop integrity policy flags must be booleans")
        if not all(flags[:7]):
            raise ValueError("Paper Loop Integrity V0.1 requires all lineage gates")
        if (
            self.provider_access_authorized
            or self.persistent_state_write_authorized
            or self.automatic_execution_authorized
            or self.live_trading_authorized
        ):
            raise ValueError("Paper Loop Integrity V0.1 is audit-only")


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


def _required_mapping(
    payload: Mapping[str, object],
    key: str,
    *,
    label: str,
) -> Mapping[str, object]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"{label}.{key} must be an object")
    return value


def _required_string(
    payload: Mapping[str, object],
    key: str,
    *,
    label: str,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label}.{key} is required")
    return value


def _strict_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{label} must be finite")
    return converted


def _verify_cycle_authority(payload: Mapping[str, object]) -> None:
    if payload.get("state") != "PAPER_INTENTS_READY_FOR_EXPLICIT_SUBMISSION":
        raise ValueError("integrity round requires a fully-ready Paper Cycle")
    if payload.get("explicit_submission_required") is not True:
        raise ValueError("integrity cycle must require explicit submission")
    if payload.get("explicit_submission_allowed") is not True:
        raise ValueError("integrity cycle must allow explicit submission")
    for key in (
        "broker_submissions_performed",
        "lifecycle_simulations_performed",
        "persistent_state_writes_performed",
    ):
        value = payload.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value != 0:
            raise ValueError(f"integrity cycle {key} must equal zero")
    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("integrity cycle authority is required")
    if authority.get("manual_cycle_preparation_only") is not True:
        raise ValueError("integrity cycle must remain manual-preparation-only")
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
            raise ValueError(f"integrity cycle authority must remain closed: {key}")


def _verify_session_authority(payload: Mapping[str, object]) -> None:
    if payload.get("state") != "PAPER_SESSION_ACCEPTED":
        raise ValueError("integrity session must be accepted")
    for key in ("lifecycle_simulations_performed", "persistent_state_writes_performed"):
        value = payload.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value != 0:
            raise ValueError(f"integrity session {key} must equal zero")
    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("integrity session authority is required")
    if authority.get("explicit_in_memory_paper_submission_only") is not True:
        raise ValueError("integrity session must remain in-memory paper-only")
    for key in (
        "provider_requests_performed",
        "r2_accessed",
        "holdout_accessed",
        "automatic_submission_authorized",
        "scheduled_submission_authorized",
        "persistent_broker_state_authorized",
        "lifecycle_simulation_authorized",
        "short_paper_execution_authorized",
        "formal_trade_plan_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"integrity session authority must remain closed: {key}")


def _verify_batch_authority(payload: Mapping[str, object]) -> None:
    if payload.get("state") != "PAPER_LIFECYCLE_BATCH_COMPLETE":
        raise ValueError("integrity lifecycle batch must be complete")
    for key in ("provider_requests_performed", "persistent_state_writes_performed"):
        value = payload.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value != 0:
            raise ValueError(f"integrity lifecycle batch {key} must equal zero")
    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("integrity lifecycle batch authority is required")
    if authority.get("explicit_paper_lifecycle_simulation_only") is not True:
        raise ValueError("integrity lifecycle batch must remain explicit simulation-only")
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
            raise ValueError(f"integrity lifecycle batch authority must remain closed: {key}")


def _session_intent_ids(payload: Mapping[str, object]) -> tuple[str, ...]:
    rows = payload.get("paper_execution_evidence")
    if not isinstance(rows, list) or not rows:
        raise ValueError("integrity session execution evidence is required")
    intent_ids: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"session evidence[{index}] must be an object")
        evidence = row.get("paper_execution_evidence")
        if not isinstance(evidence, Mapping):
            raise ValueError(f"session evidence[{index}] execution evidence is required")
        decision = evidence.get("decision")
        if not isinstance(decision, Mapping):
            raise ValueError(f"session evidence[{index}] decision is required")
        intent = decision.get("intent")
        if not isinstance(intent, Mapping):
            raise ValueError(f"session evidence[{index}] intent is required")
        intent_id = intent.get("intent_id")
        if not isinstance(intent_id, str) or not intent_id:
            raise ValueError(f"session evidence[{index}] intent_id is required")
        intent_ids.append(intent_id)
    return tuple(sorted(intent_ids))


def audit_paper_loop_integrity(
    *,
    expected_start_checkpoint_id: str,
    expected_terminal_checkpoint_id: str,
    rounds: Sequence[object],
    policy: PaperLoopIntegrityPolicy = PaperLoopIntegrityPolicy(),
) -> dict[str, object]:
    """Audit two or more complete forward paper-loop rounds without executing them."""

    if not isinstance(expected_start_checkpoint_id, str) or not expected_start_checkpoint_id:
        raise ValueError("expected_start_checkpoint_id is required")
    if (
        not isinstance(expected_terminal_checkpoint_id, str)
        or not expected_terminal_checkpoint_id
    ):
        raise ValueError("expected_terminal_checkpoint_id is required")
    if not policy.minimum_rounds <= len(rounds) <= policy.maximum_rounds:
        raise ValueError("paper loop integrity round count is outside policy bounds")

    summaries: list[dict[str, object]] = []
    cycle_ids: set[str] = set()
    session_ids: set[str] = set()
    batch_ids: set[str] = set()
    advance_ids: set[str] = set()
    forward_intent_ids: set[str] = set()
    prior_end_checkpoint: Mapping[str, object] | None = None

    for index, raw_round in enumerate(rounds):
        label = f"rounds[{index}]"
        if not isinstance(raw_round, Mapping):
            raise ValueError(f"{label} must be an object")

        start_checkpoint = _required_mapping(
            raw_round, "start_checkpoint", label=label
        )
        resume_report = _required_mapping(raw_round, "resume_report", label=label)
        session_report = _required_mapping(raw_round, "session_report", label=label)
        batch_report = _required_mapping(
            raw_round, "lifecycle_batch_report", label=label
        )
        advance_report = _required_mapping(
            raw_round, "account_advance_report", label=label
        )
        end_checkpoint = _required_mapping(raw_round, "end_checkpoint", label=label)

        start_checkpoint_id = _required_string(
            start_checkpoint, "checkpoint_id", label=f"{label}.start_checkpoint"
        )
        if paper_loop_checkpoint_report_id_from_mapping(start_checkpoint) != start_checkpoint_id:
            raise ValueError(f"{label} start checkpoint id mismatch")

        if index == 0 and start_checkpoint_id != expected_start_checkpoint_id:
            raise ValueError("first integrity checkpoint does not match expected start")
        if prior_end_checkpoint is not None:
            prior_id = _required_string(
                prior_end_checkpoint,
                "checkpoint_id",
                label=f"{label}.prior_end_checkpoint",
            )
            if start_checkpoint_id != prior_id:
                raise ValueError(f"{label} start checkpoint does not chain from prior round")
            if (
                policy.require_exact_checkpoint_chaining
                and _canonicalize(start_checkpoint) != _canonicalize(prior_end_checkpoint)
            ):
                raise ValueError(f"{label} start checkpoint payload differs from prior end")

        resume_id = _required_string(
            resume_report, "resume_id", label=f"{label}.resume_report"
        )
        if paper_loop_resume_report_id_from_mapping(resume_report) != resume_id:
            raise ValueError(f"{label} resume id mismatch")
        if resume_report.get("state") != "PAPER_LOOP_RESUMED":
            raise ValueError(f"{label} must contain a successful resumed cycle")
        if resume_report.get("checkpoint_id") != start_checkpoint_id:
            raise ValueError(f"{label} resume checkpoint does not match round start")

        cycle_report = _required_mapping(
            resume_report, "cycle_report", label=f"{label}.resume_report"
        )
        cycle_id = _required_string(cycle_report, "cycle_id", label=f"{label}.cycle")
        if paper_cycle_report_id_from_mapping(cycle_report) != cycle_id:
            raise ValueError(f"{label} cycle id mismatch")
        _verify_cycle_authority(cycle_report)
        if resume_report.get("cycle_id") != cycle_id:
            raise ValueError(f"{label} resume cycle id does not match embedded cycle")
        if cycle_report.get("account_snapshot_id") != start_checkpoint.get(
            "next_snapshot_id"
        ):
            raise ValueError(f"{label} cycle snapshot does not match start checkpoint")
        if cycle_report.get("existing_exposures") != start_checkpoint.get(
            "portfolio_existing_exposures"
        ):
            raise ValueError(f"{label} cycle exposure does not match start checkpoint")

        session_id = _required_string(
            session_report, "session_id", label=f"{label}.session_report"
        )
        if paper_submission_session_report_id_from_mapping(session_report) != session_id:
            raise ValueError(f"{label} session id mismatch")
        _verify_session_authority(session_report)
        if session_report.get("cycle_id") != cycle_id:
            raise ValueError(f"{label} session does not belong to cycle")

        batch_id = _required_string(
            batch_report, "batch_id", label=f"{label}.lifecycle_batch_report"
        )
        if paper_lifecycle_batch_report_id_from_mapping(batch_report) != batch_id:
            raise ValueError(f"{label} lifecycle batch id mismatch")
        _verify_batch_authority(batch_report)
        if batch_report.get("session_id") != session_id:
            raise ValueError(f"{label} lifecycle batch does not belong to session")

        advance_id = _required_string(
            advance_report, "advance_id", label=f"{label}.account_advance_report"
        )
        if paper_account_advance_report_id_from_mapping(advance_report) != advance_id:
            raise ValueError(f"{label} account advance id mismatch")
        if advance_report.get("batch_id") != batch_id:
            raise ValueError(f"{label} account advance does not belong to batch")
        if advance_report.get("previous_snapshot_id") != start_checkpoint.get(
            "next_snapshot_id"
        ):
            raise ValueError(f"{label} account advance starts from wrong snapshot")

        end_checkpoint_id = _required_string(
            end_checkpoint, "checkpoint_id", label=f"{label}.end_checkpoint"
        )
        if paper_loop_checkpoint_report_id_from_mapping(end_checkpoint) != end_checkpoint_id:
            raise ValueError(f"{label} end checkpoint id mismatch")
        if end_checkpoint.get("advance_id") != advance_id:
            raise ValueError(f"{label} end checkpoint does not belong to advance")
        if end_checkpoint.get("batch_id") != batch_id:
            raise ValueError(f"{label} end checkpoint does not belong to batch")
        if end_checkpoint.get("previous_snapshot_id") != advance_report.get(
            "previous_snapshot_id"
        ):
            raise ValueError(f"{label} end checkpoint previous snapshot mismatch")
        if end_checkpoint.get("next_snapshot_id") != advance_report.get(
            "next_snapshot_id"
        ):
            raise ValueError(f"{label} end checkpoint next snapshot mismatch")
        if _canonicalize(end_checkpoint.get("next_account_input")) != _canonicalize(
            advance_report.get("next_account_input")
        ):
            raise ValueError(f"{label} end checkpoint account input differs from advance")
        if end_checkpoint.get("portfolio_existing_exposures") != advance_report.get(
            "portfolio_existing_exposures"
        ):
            raise ValueError(f"{label} end checkpoint exposures differ from advance")

        start_snapshot = _required_mapping(
            start_checkpoint, "account_snapshot", label=f"{label}.start_checkpoint"
        )
        end_snapshot = _required_mapping(
            end_checkpoint, "account_snapshot", label=f"{label}.end_checkpoint"
        )
        start_as_of = start_snapshot.get("as_of_ms")
        end_as_of = end_snapshot.get("as_of_ms")
        if (
            not isinstance(start_as_of, int)
            or isinstance(start_as_of, bool)
            or not isinstance(end_as_of, int)
            or isinstance(end_as_of, bool)
        ):
            raise ValueError(f"{label} checkpoint as_of_ms values must be integers")
        if policy.require_forward_snapshot_time and end_as_of < start_as_of:
            raise ValueError(f"{label} account snapshot time regressed")

        start_equity = _strict_number(
            start_snapshot.get("equity_usd"), f"{label}.start equity"
        )
        end_equity = _strict_number(
            end_snapshot.get("equity_usd"), f"{label}.end equity"
        )
        intent_ids = _session_intent_ids(session_report)

        if policy.require_unique_cycle_ids and cycle_id in cycle_ids:
            raise ValueError(f"{label} cycle id was reused across forward rounds")
        if policy.require_unique_session_ids and session_id in session_ids:
            raise ValueError(f"{label} session id was reused across forward rounds")
        if policy.require_unique_batch_ids and batch_id in batch_ids:
            raise ValueError(f"{label} batch id was reused across forward rounds")
        if policy.require_unique_advance_ids and advance_id in advance_ids:
            raise ValueError(f"{label} advance id was reused across forward rounds")
        if policy.require_unique_forward_intent_ids:
            duplicate_intents = set(intent_ids) & forward_intent_ids
            if duplicate_intents:
                raise ValueError(
                    f"{label} reused forward intent ids: {sorted(duplicate_intents)}"
                )
        if start_checkpoint_id == end_checkpoint_id:
            raise ValueError(f"{label} forward round did not advance checkpoint identity")

        cycle_ids.add(cycle_id)
        session_ids.add(session_id)
        batch_ids.add(batch_id)
        advance_ids.add(advance_id)
        forward_intent_ids.update(intent_ids)

        summaries.append(
            {
                "round_index": index,
                "start_checkpoint_id": start_checkpoint_id,
                "resume_id": resume_id,
                "cycle_id": cycle_id,
                "session_id": session_id,
                "batch_id": batch_id,
                "advance_id": advance_id,
                "end_checkpoint_id": end_checkpoint_id,
                "start_snapshot_id": start_checkpoint["next_snapshot_id"],
                "end_snapshot_id": end_checkpoint["next_snapshot_id"],
                "start_as_of_ms": start_as_of,
                "end_as_of_ms": end_as_of,
                "start_equity_usd": start_equity,
                "end_equity_usd": end_equity,
                "equity_change_usd": round(end_equity - start_equity, 8),
                "new_intent_ids": list(intent_ids),
            }
        )
        prior_end_checkpoint = end_checkpoint

    assert prior_end_checkpoint is not None
    terminal_checkpoint_id = _required_string(
        prior_end_checkpoint,
        "checkpoint_id",
        label="terminal_checkpoint",
    )
    if terminal_checkpoint_id != expected_terminal_checkpoint_id:
        raise ValueError("terminal integrity checkpoint does not match expected terminal")

    transcript_sha = _sha256({"rounds": list(rounds)})
    integrity_payload = {
        "schema": "qookey-paper-loop-integrity-id-v0.1",
        "start_checkpoint_id": expected_start_checkpoint_id,
        "terminal_checkpoint_id": expected_terminal_checkpoint_id,
        "transcript_sha256": transcript_sha,
        "round_summaries": summaries,
    }
    integrity_id = f"paper-loop-integrity-v0-1-{_sha256(integrity_payload)}"

    return {
        "schema": "qookey-paper-loop-integrity-report-v0.1",
        "integrity_id": integrity_id,
        "state": "MULTI_CYCLE_INTEGRITY_PASS",
        "round_count": len(rounds),
        "start_checkpoint_id": expected_start_checkpoint_id,
        "terminal_checkpoint_id": expected_terminal_checkpoint_id,
        "start_snapshot_id": summaries[0]["start_snapshot_id"],
        "terminal_snapshot_id": summaries[-1]["end_snapshot_id"],
        "start_equity_usd": summaries[0]["start_equity_usd"],
        "terminal_equity_usd": summaries[-1]["end_equity_usd"],
        "net_equity_change_usd": round(
            cast(float, summaries[-1]["end_equity_usd"])
            - cast(float, summaries[0]["start_equity_usd"]),
            8,
        ),
        "unique_forward_intent_count": len(forward_intent_ids),
        "transcript_sha256": transcript_sha,
        "rounds": summaries,
        "provider_requests_performed": 0,
        "persistent_state_writes_performed": 0,
        "executions_performed": 0,
        "authority": {
            "audit_only": True,
            "provider_requests_performed": False,
            "r2_accessed": False,
            "holdout_accessed": False,
            "persistent_state_write_authorized": False,
            "automatic_execution_authorized": False,
            "strategy_ranking_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
        "limitations": [
            "Integrity V0.1 audits supplied paper artifacts; it executes no trades.",
            "Equity change is reported descriptively and is not a profitability claim.",
            "Deterministic replay means the same transcript yields the same integrity id.",
        ],
    }


def paper_loop_integrity_report_id_from_mapping(
    payload: Mapping[str, object],
) -> str:
    """Validate and recompute one serialized Paper Loop Integrity report id."""

    if payload.get("schema") != "qookey-paper-loop-integrity-report-v0.1":
        raise ValueError("unsupported paper loop integrity report schema")
    if payload.get("state") != "MULTI_CYCLE_INTEGRITY_PASS":
        raise ValueError("paper loop integrity report is not a PASS state")

    integrity_id = payload.get("integrity_id")
    start_checkpoint_id = payload.get("start_checkpoint_id")
    terminal_checkpoint_id = payload.get("terminal_checkpoint_id")
    transcript_sha256 = payload.get("transcript_sha256")
    if not isinstance(integrity_id, str) or not integrity_id:
        raise ValueError("paper loop integrity integrity_id is required")
    if not isinstance(start_checkpoint_id, str) or not start_checkpoint_id:
        raise ValueError("paper loop integrity start_checkpoint_id is required")
    if not isinstance(terminal_checkpoint_id, str) or not terminal_checkpoint_id:
        raise ValueError("paper loop integrity terminal_checkpoint_id is required")
    if not isinstance(transcript_sha256, str) or len(transcript_sha256) != 64:
        raise ValueError("paper loop integrity transcript_sha256 is invalid")

    round_count = payload.get("round_count")
    unique_forward_intent_count = payload.get("unique_forward_intent_count")
    if (
        not isinstance(round_count, int)
        or isinstance(round_count, bool)
        or round_count < 2
    ):
        raise ValueError("paper loop integrity round_count must be >= 2")
    if (
        not isinstance(unique_forward_intent_count, int)
        or isinstance(unique_forward_intent_count, bool)
        or unique_forward_intent_count < 1
    ):
        raise ValueError("paper loop integrity unique intent count must be positive")

    rounds = payload.get("rounds")
    if not isinstance(rounds, list) or len(rounds) != round_count:
        raise ValueError("paper loop integrity round summaries do not match round_count")

    seen_intents: set[str] = set()
    prior_end_checkpoint_id: str | None = None
    for index, row in enumerate(rounds):
        if not isinstance(row, Mapping):
            raise ValueError(f"integrity rounds[{index}] must be an object")
        required_strings = (
            "start_checkpoint_id",
            "resume_id",
            "cycle_id",
            "session_id",
            "batch_id",
            "advance_id",
            "end_checkpoint_id",
            "start_snapshot_id",
            "end_snapshot_id",
        )
        for key in required_strings:
            value = row.get(key)
            if not isinstance(value, str) or not value:
                raise ValueError(f"integrity rounds[{index}].{key} is required")
        if row.get("round_index") != index:
            raise ValueError("integrity round_index sequence is invalid")
        if index == 0 and row["start_checkpoint_id"] != start_checkpoint_id:
            raise ValueError("integrity first round start checkpoint mismatch")
        if prior_end_checkpoint_id is not None and row["start_checkpoint_id"] != prior_end_checkpoint_id:
            raise ValueError("integrity round summary checkpoint chain is broken")
        prior_end_checkpoint_id = str(row["end_checkpoint_id"])

        for key in ("start_as_of_ms", "end_as_of_ms"):
            value = row.get(key)
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError(f"integrity rounds[{index}].{key} must be integer")
        if row["end_as_of_ms"] < row["start_as_of_ms"]:
            raise ValueError("integrity round summary time regressed")

        start_equity = _strict_number(
            row.get("start_equity_usd"), f"integrity rounds[{index}].start_equity"
        )
        end_equity = _strict_number(
            row.get("end_equity_usd"), f"integrity rounds[{index}].end_equity"
        )
        equity_change = _strict_number(
            row.get("equity_change_usd"), f"integrity rounds[{index}].equity_change"
        )
        if round(end_equity - start_equity, 8) != equity_change:
            raise ValueError("integrity round summary equity change mismatch")

        intent_ids = row.get("new_intent_ids")
        if not isinstance(intent_ids, list) or not intent_ids:
            raise ValueError("integrity round summary new_intent_ids are required")
        if any(not isinstance(item, str) or not item for item in intent_ids):
            raise ValueError("integrity round summary intent ids are invalid")
        if len(set(intent_ids)) != len(intent_ids):
            raise ValueError("integrity round summary contains duplicate intent ids")
        duplicate = seen_intents.intersection(intent_ids)
        if duplicate:
            raise ValueError("integrity report reuses forward intent ids")
        seen_intents.update(intent_ids)

    if prior_end_checkpoint_id != terminal_checkpoint_id:
        raise ValueError("integrity terminal checkpoint does not match round summaries")
    if len(seen_intents) != unique_forward_intent_count:
        raise ValueError("integrity unique intent count mismatch")

    start_equity = _strict_number(
        payload.get("start_equity_usd"), "integrity start_equity_usd"
    )
    terminal_equity = _strict_number(
        payload.get("terminal_equity_usd"), "integrity terminal_equity_usd"
    )
    net_change = _strict_number(
        payload.get("net_equity_change_usd"), "integrity net_equity_change_usd"
    )
    if round(terminal_equity - start_equity, 8) != net_change:
        raise ValueError("integrity net equity change mismatch")
    if rounds[0].get("start_snapshot_id") != payload.get("start_snapshot_id"):
        raise ValueError("integrity start snapshot mismatch")
    if rounds[-1].get("end_snapshot_id") != payload.get("terminal_snapshot_id"):
        raise ValueError("integrity terminal snapshot mismatch")
    if rounds[0].get("start_equity_usd") != start_equity:
        raise ValueError("integrity start equity does not match first round")
    if rounds[-1].get("end_equity_usd") != terminal_equity:
        raise ValueError("integrity terminal equity does not match last round")

    for key in (
        "provider_requests_performed",
        "persistent_state_writes_performed",
        "executions_performed",
    ):
        value = payload.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value != 0:
            raise ValueError(f"paper loop integrity {key} must equal zero")

    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("paper loop integrity authority object is required")
    if authority.get("audit_only") is not True:
        raise ValueError("paper loop integrity must remain audit-only")
    for key in (
        "provider_requests_performed",
        "r2_accessed",
        "holdout_accessed",
        "persistent_state_write_authorized",
        "automatic_execution_authorized",
        "strategy_ranking_authorized",
        "real_money_order_authorized",
        "live_trading_authorized",
    ):
        if authority.get(key) is not False:
            raise ValueError(f"paper loop integrity authority must remain closed: {key}")

    canonical = {
        "schema": "qookey-paper-loop-integrity-id-v0.1",
        "start_checkpoint_id": start_checkpoint_id,
        "terminal_checkpoint_id": terminal_checkpoint_id,
        "transcript_sha256": transcript_sha256,
        "round_summaries": rounds,
    }
    return f"paper-loop-integrity-v0-1-{_sha256(canonical)}"


def paper_loop_integrity_policy_from_config(
    payload: Mapping[str, object],
) -> PaperLoopIntegrityPolicy:
    if payload.get("schema") != "qookey-paper-loop-integrity-v0.1":
        raise ValueError("unsupported paper loop integrity config")
    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("policy object is required")

    minimum = policy.get("minimum_rounds")
    maximum = policy.get("maximum_rounds")
    if not isinstance(minimum, int) or isinstance(minimum, bool):
        raise ValueError("policy.minimum_rounds must be a JSON integer")
    if not isinstance(maximum, int) or isinstance(maximum, bool):
        raise ValueError("policy.maximum_rounds must be a JSON integer")

    keys = (
        "require_exact_checkpoint_chaining",
        "require_forward_snapshot_time",
        "require_unique_cycle_ids",
        "require_unique_session_ids",
        "require_unique_batch_ids",
        "require_unique_advance_ids",
        "require_unique_forward_intent_ids",
        "provider_access_authorized",
        "persistent_state_write_authorized",
        "automatic_execution_authorized",
        "live_trading_authorized",
    )
    for key in keys:
        if not isinstance(policy.get(key), bool):
            raise ValueError(f"policy.{key} must be a JSON boolean")

    return PaperLoopIntegrityPolicy(
        minimum_rounds=minimum,
        maximum_rounds=maximum,
        require_exact_checkpoint_chaining=policy[
            "require_exact_checkpoint_chaining"
        ],
        require_forward_snapshot_time=policy["require_forward_snapshot_time"],
        require_unique_cycle_ids=policy["require_unique_cycle_ids"],
        require_unique_session_ids=policy["require_unique_session_ids"],
        require_unique_batch_ids=policy["require_unique_batch_ids"],
        require_unique_advance_ids=policy["require_unique_advance_ids"],
        require_unique_forward_intent_ids=policy[
            "require_unique_forward_intent_ids"
        ],
        provider_access_authorized=policy["provider_access_authorized"],
        persistent_state_write_authorized=policy[
            "persistent_state_write_authorized"
        ],
        automatic_execution_authorized=policy[
            "automatic_execution_authorized"
        ],
        live_trading_authorized=policy["live_trading_authorized"],
    )


def paper_loop_integrity_input_from_dict(
    payload: Mapping[str, object],
) -> tuple[str, str, tuple[object, ...]]:
    if payload.get("schema") != "qookey-paper-loop-integrity-input-v0.1":
        raise ValueError("unsupported paper loop integrity input schema")
    start = payload.get("expected_start_checkpoint_id")
    terminal = payload.get("expected_terminal_checkpoint_id")
    rounds = payload.get("rounds")
    if not isinstance(start, str) or not start:
        raise ValueError("expected_start_checkpoint_id is required")
    if not isinstance(terminal, str) or not terminal:
        raise ValueError("expected_terminal_checkpoint_id is required")
    if not isinstance(rounds, list):
        raise ValueError("rounds must be a JSON array")
    return start, terminal, tuple(rounds)
