from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from crypto_autopilot.paper.live_v0_1 import (
    LivePaperMarketFeed,
    LivePaperPolicy,
    live_paper_tick_report_id_from_mapping,
    run_live_paper_tick,
    verify_live_paper_state,
)
from crypto_autopilot.paper.run_store_v0_1 import run_store_receipt_evidence


class PaperRunStoreLike(Protocol):
    def put_json(
        self,
        kind: str,
        object_id: str,
        payload: Mapping[str, object],
    ) -> object: ...

    def get_json(
        self,
        kind: str,
        object_id: str,
    ) -> dict[str, object] | None: ...


@dataclass(frozen=True, slots=True)
class LivePaperRunCoordinatorPolicy:
    """Append-only persistent coordination around the existing Live Paper tick."""

    require_persistent_store: bool = True
    persist_run_header: bool = True
    persist_states: bool = True
    persist_tick_reports: bool = True
    persist_run_steps: bool = True
    committed_request_replay_authorized: bool = True
    automatic_schedule_authorized: bool = False
    automatic_candidate_generation_authorized: bool = False
    scorecard_auto_selection_authorized: bool = False
    private_exchange_api_authorized: bool = False
    holdout_access_authorized: bool = False
    real_money_order_authorized: bool = False
    live_real_trading_authorized: bool = False

    def __post_init__(self) -> None:
        flags = (
            self.require_persistent_store,
            self.persist_run_header,
            self.persist_states,
            self.persist_tick_reports,
            self.persist_run_steps,
            self.committed_request_replay_authorized,
            self.automatic_schedule_authorized,
            self.automatic_candidate_generation_authorized,
            self.scorecard_auto_selection_authorized,
            self.private_exchange_api_authorized,
            self.holdout_access_authorized,
            self.real_money_order_authorized,
            self.live_real_trading_authorized,
        )
        if any(not isinstance(value, bool) for value in flags):
            raise ValueError("Live Paper Run Coordinator policy flags must be booleans")
        if not all(flags[:6]):
            raise ValueError(
                "Live Paper Run Coordinator V0.1 requires persistent append-only evidence"
            )
        if any(flags[6:]):
            raise ValueError(
                "Live Paper Run Coordinator V0.1 cannot authorize scheduling, "
                "automatic candidate selection or real trading"
            )


def _canonicalize(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(item)
            for key, item in sorted(value.items())
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    return value


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        _canonicalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _validate_run_name(run_name: str) -> str:
    clean = run_name.strip()
    if not clean:
        raise ValueError("live paper run_name is required")
    if len(clean) > 128:
        raise ValueError("live paper run_name is too long")
    if any(ord(character) < 32 for character in clean):
        raise ValueError("live paper run_name cannot contain control characters")
    return clean


def _run_id(run_name: str, initial_state_id: str) -> str:
    payload = {
        "schema": "qookey-live-paper-run-id-v0.1",
        "run_name": run_name,
        "initial_state_id": initial_state_id,
    }
    return f"live-paper-run-v0-1-{_sha256(payload)}"


def _run_header(
    *,
    run_name: str,
    initial_state_id: str,
) -> dict[str, object]:
    run_id = _run_id(run_name, initial_state_id)
    return {
        "schema": "qookey-live-paper-run-header-v0.1",
        "run_id": run_id,
        "run_name": run_name,
        "initial_state_id": initial_state_id,
        "mode": "LIVE_PAPER_SIMULATION",
        "authority": {
            "append_only_run_ledger": True,
            "public_live_market_data_authorized": True,
            "live_paper_simulation_authorized": True,
            "paper_state_persistence_authorized": True,
            "automatic_schedule_authorized": False,
            "automatic_candidate_generation_authorized": False,
            "scorecard_auto_selection_authorized": False,
            "private_exchange_api_authorized": False,
            "holdout_access_authorized": False,
            "real_money_order_authorized": False,
            "live_real_trading_authorized": False,
        },
    }


def verify_live_paper_run_header(payload: Mapping[str, object]) -> str:
    if payload.get("schema") != "qookey-live-paper-run-header-v0.1":
        raise ValueError("unsupported live paper run header schema")
    run_id = payload.get("run_id")
    run_name = payload.get("run_name")
    initial_state_id = payload.get("initial_state_id")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("live paper run header run_id is required")
    if not isinstance(run_name, str):
        raise ValueError("live paper run header run_name is required")
    clean_name = _validate_run_name(run_name)
    if not isinstance(initial_state_id, str) or not initial_state_id:
        raise ValueError("live paper run header initial_state_id is required")
    if payload.get("mode") != "LIVE_PAPER_SIMULATION":
        raise ValueError("live paper run header mode is invalid")
    _verify_coordinator_authority(payload.get("authority"), header=True)
    expected = _run_id(clean_name, initial_state_id)
    if run_id != expected:
        raise ValueError("live paper run header id mismatch")
    return expected


def _verify_coordinator_authority(
    payload: object,
    *,
    header: bool = False,
) -> None:
    if not isinstance(payload, Mapping):
        raise ValueError("live paper coordinator authority object is required")
    if header and payload.get("append_only_run_ledger") is not True:
        raise ValueError("live paper run header must be append-only")
    for key in (
        "public_live_market_data_authorized",
        "live_paper_simulation_authorized",
        "paper_state_persistence_authorized",
    ):
        if payload.get(key) is not True:
            raise ValueError(f"live paper coordinator authority missing: {key}")
    for key in (
        "automatic_schedule_authorized",
        "automatic_candidate_generation_authorized",
        "scorecard_auto_selection_authorized",
        "private_exchange_api_authorized",
        "holdout_access_authorized",
        "real_money_order_authorized",
        "live_real_trading_authorized",
    ):
        if payload.get(key) is not False:
            raise ValueError(f"live paper coordinator authority must remain closed: {key}")


def _request_id(
    *,
    run_id: str,
    sequence: int,
    previous_step_id: str | None,
    previous_state_id: str,
    tick_time_ms: int,
    candidate_specs: Sequence[object],
) -> str:
    payload = {
        "schema": "qookey-live-paper-run-request-id-v0.1",
        "run_id": run_id,
        "sequence": sequence,
        "previous_step_id": previous_step_id,
        "previous_state_id": previous_state_id,
        "tick_time_ms": tick_time_ms,
        "candidate_specs_sha256": _sha256(candidate_specs),
    }
    return f"live-paper-run-request-v0-1-{_sha256(payload)}"


def _step_id(
    *,
    run_id: str,
    sequence: int,
    previous_step_id: str | None,
    request_id: str,
    previous_state_id: str,
    tick_id: str,
    next_state_id: str,
    tick_report_sha256: str,
) -> str:
    payload = {
        "schema": "qookey-live-paper-run-step-id-v0.1",
        "run_id": run_id,
        "sequence": sequence,
        "previous_step_id": previous_step_id,
        "request_id": request_id,
        "previous_state_id": previous_state_id,
        "tick_id": tick_id,
        "next_state_id": next_state_id,
        "tick_report_sha256": tick_report_sha256,
    }
    return f"live-paper-run-step-v0-1-{_sha256(payload)}"


def verify_live_paper_run_step(payload: Mapping[str, object]) -> str:
    if payload.get("schema") != "qookey-live-paper-run-step-report-v0.1":
        raise ValueError("unsupported live paper run step schema")
    if payload.get("state") != "LIVE_PAPER_RUN_STEP_COMMITTED":
        raise ValueError("live paper run step is not committed")

    step_id = payload.get("step_id")
    run_id = payload.get("run_id")
    run_name = payload.get("run_name")
    request_id = payload.get("request_id")
    initial_state_id = payload.get("initial_state_id")
    previous_state_id = payload.get("previous_state_id")
    next_state_id = payload.get("next_state_id")
    tick_id = payload.get("tick_id")
    tick_report_sha256 = payload.get("tick_report_sha256")
    for label, value in (
        ("step_id", step_id),
        ("run_id", run_id),
        ("request_id", request_id),
        ("initial_state_id", initial_state_id),
        ("previous_state_id", previous_state_id),
        ("next_state_id", next_state_id),
        ("tick_id", tick_id),
        ("tick_report_sha256", tick_report_sha256),
    ):
        if not isinstance(value, str) or not value:
            raise ValueError(f"live paper run step {label} is required")
    if not isinstance(run_name, str):
        raise ValueError("live paper run step run_name is required")
    clean_name = _validate_run_name(run_name)
    if run_id != _run_id(clean_name, initial_state_id):
        raise ValueError("live paper run step run_id mismatch")

    sequence = payload.get("sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise ValueError("live paper run step sequence must be positive integer")
    previous_step_id = payload.get("previous_step_id")
    if sequence == 1:
        if previous_step_id is not None:
            raise ValueError("first live paper run step cannot have previous_step_id")
    elif not isinstance(previous_step_id, str) or not previous_step_id:
        raise ValueError("continued live paper run step requires previous_step_id")

    tick_report = payload.get("tick_report")
    if not isinstance(tick_report, Mapping):
        raise ValueError("live paper run step tick_report is required")
    recomputed_tick_id = live_paper_tick_report_id_from_mapping(tick_report)
    if recomputed_tick_id != tick_id or tick_report.get("tick_id") != tick_id:
        raise ValueError("live paper run step tick id mismatch")
    if _sha256(tick_report) != tick_report_sha256:
        raise ValueError("live paper run step tick report hash mismatch")
    if tick_report.get("previous_state_id") != previous_state_id:
        raise ValueError("live paper run step previous state mismatch")
    if tick_report.get("next_state_id") != next_state_id:
        raise ValueError("live paper run step next state mismatch")
    if tick_report.get("persistent_state_writes_performed") != 0:
        raise ValueError("coordinated tick report must be generated without internal store writes")
    if tick_report.get("storage_receipt") is not None:
        raise ValueError("coordinated tick report cannot contain internal storage receipt")

    tick_time_ms = payload.get("tick_time_ms")
    if tick_report.get("tick_time_ms") != tick_time_ms:
        raise ValueError("live paper run step tick time mismatch")
    if (
        not isinstance(tick_time_ms, int)
        or isinstance(tick_time_ms, bool)
        or tick_time_ms < 0
    ):
        raise ValueError("live paper run step tick_time_ms is invalid")

    candidate_specs_sha256 = payload.get("candidate_specs_sha256")
    if (
        not isinstance(candidate_specs_sha256, str)
        or len(candidate_specs_sha256) != 64
        or any(
            character not in "0123456789abcdef"
            for character in candidate_specs_sha256
        )
    ):
        raise ValueError("live paper run step candidate_specs_sha256 is invalid")
    candidate_specs = payload.get("candidate_specs")
    if not isinstance(candidate_specs, list):
        raise ValueError("live paper run step candidate_specs must be an array")

    expected_request = _request_id(
        run_id=run_id,
        sequence=sequence,
        previous_step_id=previous_step_id,
        previous_state_id=previous_state_id,
        tick_time_ms=tick_time_ms,
        candidate_specs=candidate_specs,
    )
    if payload.get("request_id") != expected_request:
        raise ValueError("live paper run step request id mismatch")
    if _sha256(candidate_specs) != candidate_specs_sha256:
        raise ValueError("live paper run step candidate specs hash mismatch")

    _verify_coordinator_authority(payload.get("authority"))

    expected_step = _step_id(
        run_id=run_id,
        sequence=sequence,
        previous_step_id=previous_step_id,
        request_id=request_id,
        previous_state_id=previous_state_id,
        tick_id=tick_id,
        next_state_id=next_state_id,
        tick_report_sha256=tick_report_sha256,
    )
    if step_id != expected_step:
        raise ValueError("live paper run step id mismatch")
    return expected_step


def _committed_result(
    *,
    request_id: str,
    step_id: str,
    run_id: str,
    sequence: int,
) -> dict[str, object]:
    return {
        "schema": "qookey-live-paper-run-request-result-v0.1",
        "request_id": request_id,
        "step_id": step_id,
        "run_id": run_id,
        "sequence": sequence,
        "state": "COMMITTED",
        "authority": {
            "append_only_result_pointer": True,
            "execution_authority": False,
            "real_money_order_authorized": False,
            "live_real_trading_authorized": False,
        },
    }


def _verify_committed_result(
    payload: Mapping[str, object],
    *,
    request_id: str,
) -> tuple[str, str, int]:
    if payload.get("schema") != "qookey-live-paper-run-request-result-v0.1":
        raise ValueError("unsupported live paper run result schema")
    if payload.get("state") != "COMMITTED":
        raise ValueError("live paper run result is not committed")
    if payload.get("request_id") != request_id:
        raise ValueError("live paper run result request id mismatch")
    step_id = payload.get("step_id")
    run_id = payload.get("run_id")
    sequence = payload.get("sequence")
    if not isinstance(step_id, str) or not step_id:
        raise ValueError("live paper run result step_id is required")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("live paper run result run_id is required")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise ValueError("live paper run result sequence is invalid")
    authority = payload.get("authority")
    if not isinstance(authority, Mapping):
        raise ValueError("live paper run result authority is required")
    if authority.get("append_only_result_pointer") is not True:
        raise ValueError("live paper run result must remain append-only")
    if authority.get("execution_authority") is not False:
        raise ValueError("live paper run result cannot grant execution authority")
    if authority.get("real_money_order_authorized") is not False:
        raise ValueError("live paper run result cannot grant real-money authority")
    if authority.get("live_real_trading_authorized") is not False:
        raise ValueError("live paper run result cannot grant real trading authority")
    return step_id, run_id, sequence



def build_live_paper_run_result(
    *,
    request_id: str,
    step_id: str,
    run_id: str,
    sequence: int,
) -> dict[str, object]:
    """Build the canonical immutable request-result seal for one committed step."""

    return _committed_result(
        request_id=request_id,
        step_id=step_id,
        run_id=run_id,
        sequence=sequence,
    )


def verify_live_paper_run_result(
    payload: Mapping[str, object],
    *,
    request_id: str,
) -> tuple[str, str, int]:
    """Validate one serialized committed request-result seal."""

    return _verify_committed_result(payload, request_id=request_id)


def _store_get(
    store: PaperRunStoreLike,
    kind: str,
    object_id: str,
) -> dict[str, object] | None:
    payload = store.get_json(kind, object_id)
    if payload is not None and not isinstance(payload, dict):
        raise ValueError("paper run store get_json must return object/null")
    return payload


def _receipt(
    store: PaperRunStoreLike,
    kind: str,
    object_id: str,
    payload: Mapping[str, object],
) -> object:
    return store.put_json(kind, object_id, payload)


def coordinate_live_paper_run_step(
    *,
    run_name: str,
    tick_time_ms: int,
    candidate_specs: Sequence[object],
    feed: LivePaperMarketFeed,
    store: PaperRunStoreLike,
    initial_state: Mapping[str, object] | None = None,
    previous_step: Mapping[str, object] | None = None,
    policy: LivePaperRunCoordinatorPolicy = LivePaperRunCoordinatorPolicy(),
    live_policy: LivePaperPolicy = LivePaperPolicy(),
) -> dict[str, object]:
    """Commit one append-only Live Paper run step.

    Exactly one of initial_state / previous_step is supplied. A completed request
    is replayed from the store without a new provider call.
    """

    if store is None:
        raise ValueError("Live Paper Run Coordinator requires a persistent store")
    if (initial_state is None) == (previous_step is None):
        raise ValueError("provide exactly one of initial_state or previous_step")

    clean_name = _validate_run_name(run_name)
    if (
        not isinstance(tick_time_ms, int)
        or isinstance(tick_time_ms, bool)
        or tick_time_ms < 0
    ):
        raise ValueError("live paper coordinator tick_time_ms is invalid")
    canonical_candidates = _canonicalize(tuple(candidate_specs))
    if not isinstance(canonical_candidates, list):
        raise AssertionError("canonical candidate specs must be a list")

    if previous_step is None:
        assert initial_state is not None
        initial_state_id = verify_live_paper_state(initial_state)
        current_state: Mapping[str, object] = initial_state
        run_id = _run_id(clean_name, initial_state_id)
        sequence = 1
        previous_step_id: str | None = None
    else:
        verified_previous_step_id = verify_live_paper_run_step(previous_step)
        if previous_step.get("step_id") != verified_previous_step_id:
            raise ValueError("previous live paper run step id mismatch")
        if previous_step.get("run_name") != clean_name:
            raise ValueError("previous live paper run step belongs to another run name")
        run_id = str(previous_step["run_id"])
        initial_state_id = str(previous_step["initial_state_id"])
        sequence = int(previous_step["sequence"]) + 1
        previous_step_id = verified_previous_step_id
        previous_tick = previous_step.get("tick_report")
        if not isinstance(previous_tick, Mapping):
            raise ValueError("previous live paper run step tick report is required")
        embedded_state = previous_tick.get("next_state")
        if not isinstance(embedded_state, Mapping):
            raise ValueError("previous live paper run step next state is required")
        current_state_id = verify_live_paper_state(embedded_state)
        if current_state_id != previous_step.get("next_state_id"):
            raise ValueError("previous live paper run step embedded state mismatch")
        persisted_state = _store_get(store, "live-state", current_state_id)
        if persisted_state is None:
            raise ValueError("previous live paper state is not present in Run Store")
        if _canonicalize(persisted_state) != _canonicalize(embedded_state):
            raise ValueError("persisted previous live paper state differs from run step")
        current_state = persisted_state

    previous_state_id = verify_live_paper_state(current_state)
    if run_id != _run_id(clean_name, initial_state_id):
        raise ValueError("live paper run lineage id mismatch")

    header = _run_header(run_name=clean_name, initial_state_id=initial_state_id)
    if verify_live_paper_run_header(header) != run_id:
        raise ValueError("live paper run header lineage mismatch")

    request_id = _request_id(
        run_id=run_id,
        sequence=sequence,
        previous_step_id=previous_step_id,
        previous_state_id=previous_state_id,
        tick_time_ms=tick_time_ms,
        candidate_specs=canonical_candidates,
    )

    committed = _store_get(store, "live-run-result", request_id)
    if committed is not None:
        step_id, committed_run_id, committed_sequence = _verify_committed_result(
            committed,
            request_id=request_id,
        )
        if committed_run_id != run_id or committed_sequence != sequence:
            raise ValueError("committed live paper request result lineage mismatch")
        stored_step = _store_get(store, "live-run-step", step_id)
        if stored_step is None:
            raise ValueError("committed live paper request references missing run step")
        if verify_live_paper_run_step(stored_step) != step_id:
            raise ValueError("committed live paper run step failed verification")
        if stored_step.get("request_id") != request_id:
            raise ValueError("committed live paper run step request lineage mismatch")
        if stored_step.get("run_id") != run_id:
            raise ValueError("committed live paper run step run lineage mismatch")
        if stored_step.get("sequence") != sequence:
            raise ValueError("committed live paper run step sequence mismatch")
        return {
            "schema": "qookey-live-paper-run-coordinator-report-v0.1",
            "state": "COMMITTED_STEP_REPLAYED",
            "run_id": run_id,
            "request_id": request_id,
            "step_id": step_id,
            "sequence": sequence,
            "provider_requests_performed": 0,
            "persistent_objects_created": 0,
            "run_step": stored_step,
            "storage_receipts": [],
            "authority": _coordinator_authority(),
        }

    receipts: list[object] = []
    receipts.append(_receipt(store, "live-run", run_id, header))
    receipts.append(
        _receipt(store, "live-state", previous_state_id, current_state)
    )

    tick_report = run_live_paper_tick(
        state=current_state,
        tick_time_ms=tick_time_ms,
        candidate_specs=canonical_candidates,
        feed=feed,
        policy=live_policy,
        store=None,
    )
    tick_id = live_paper_tick_report_id_from_mapping(tick_report)
    if tick_report.get("tick_id") != tick_id:
        raise ValueError("generated live paper tick id mismatch")
    next_state = tick_report.get("next_state")
    if not isinstance(next_state, Mapping):
        raise ValueError("generated live paper tick next_state is required")
    next_state_id = verify_live_paper_state(next_state)
    if tick_report.get("next_state_id") != next_state_id:
        raise ValueError("generated live paper tick next state id mismatch")

    tick_report_sha256 = _sha256(tick_report)
    step_id = _step_id(
        run_id=run_id,
        sequence=sequence,
        previous_step_id=previous_step_id,
        request_id=request_id,
        previous_state_id=previous_state_id,
        tick_id=tick_id,
        next_state_id=next_state_id,
        tick_report_sha256=tick_report_sha256,
    )
    step: dict[str, object] = {
        "schema": "qookey-live-paper-run-step-report-v0.1",
        "step_id": step_id,
        "state": "LIVE_PAPER_RUN_STEP_COMMITTED",
        "run_id": run_id,
        "run_name": clean_name,
        "sequence": sequence,
        "previous_step_id": previous_step_id,
        "request_id": request_id,
        "initial_state_id": initial_state_id,
        "previous_state_id": previous_state_id,
        "next_state_id": next_state_id,
        "tick_id": tick_id,
        "tick_time_ms": tick_time_ms,
        "candidate_specs_sha256": _sha256(canonical_candidates),
        "candidate_specs": canonical_candidates,
        "tick_report_sha256": tick_report_sha256,
        "tick_report": _canonicalize(tick_report),
        "authority": _coordinator_authority(),
        "limitations": [
            "V0.1 commits one tick per explicit coordinator invocation.",
            "V0.1 has no mutable latest pointer and requires the prior committed step id for continuation.",
            "Candidate generation remains upstream explicit; research Scorecard rank is not auto-selected.",
            "A crash before request-result sealing may require operator review before retry if provider evidence changed.",
        ],
    }
    if verify_live_paper_run_step(step) != step_id:
        raise ValueError("generated live paper run step failed verification")

    receipts.append(_receipt(store, "live-state", next_state_id, next_state))
    receipts.append(_receipt(store, "live-tick", tick_id, tick_report))
    receipts.append(_receipt(store, "live-run-step", step_id, step))

    result = _committed_result(
        request_id=request_id,
        step_id=step_id,
        run_id=run_id,
        sequence=sequence,
    )
    receipts.append(_receipt(store, "live-run-result", request_id, result))

    receipt_evidence = [run_store_receipt_evidence(item) for item in receipts]
    created = sum(
        evidence["receipt"]["replayed"] is False  # type: ignore[index]
        for evidence in receipt_evidence
    )
    return {
        "schema": "qookey-live-paper-run-coordinator-report-v0.1",
        "state": "LIVE_PAPER_RUN_STEP_COMMITTED",
        "run_id": run_id,
        "request_id": request_id,
        "step_id": step_id,
        "sequence": sequence,
        "provider_requests_performed": tick_report.get(
            "provider_requests_performed",
            0,
        ),
        "persistent_objects_created": created,
        "run_step": step,
        "storage_receipts": receipt_evidence,
        "authority": _coordinator_authority(),
    }


def _coordinator_authority() -> dict[str, object]:
    return {
        "public_live_market_data_authorized": True,
        "live_paper_simulation_authorized": True,
        "paper_state_persistence_authorized": True,
        "append_only_run_ledger": True,
        "automatic_schedule_authorized": False,
        "automatic_candidate_generation_authorized": False,
        "scorecard_auto_selection_authorized": False,
        "private_exchange_api_authorized": False,
        "holdout_access_authorized": False,
        "real_money_order_authorized": False,
        "live_real_trading_authorized": False,
    }


def live_paper_run_coordinator_policy_from_config(
    payload: Mapping[str, object],
) -> LivePaperRunCoordinatorPolicy:
    if payload.get("schema") != "qookey-live-paper-run-coordinator-v0.1":
        raise ValueError("unsupported live paper run coordinator config")
    policy = payload.get("policy")
    if not isinstance(policy, Mapping):
        raise ValueError("live paper run coordinator policy object is required")
    keys = (
        "require_persistent_store",
        "persist_run_header",
        "persist_states",
        "persist_tick_reports",
        "persist_run_steps",
        "committed_request_replay_authorized",
        "automatic_schedule_authorized",
        "automatic_candidate_generation_authorized",
        "scorecard_auto_selection_authorized",
        "private_exchange_api_authorized",
        "holdout_access_authorized",
        "real_money_order_authorized",
        "live_real_trading_authorized",
    )
    values: dict[str, bool] = {}
    for key in keys:
        value = policy.get(key)
        if not isinstance(value, bool):
            raise ValueError(f"policy.{key} must be a JSON boolean")
        values[key] = value
    return LivePaperRunCoordinatorPolicy(**values)


def live_paper_run_coordinator_input_from_dict(
    payload: Mapping[str, object],
) -> tuple[str, int, tuple[object, ...], Mapping[str, object] | None, str | None]:
    if payload.get("schema") != "qookey-live-paper-run-coordinator-input-v0.1":
        raise ValueError("unsupported live paper run coordinator input schema")
    run_name = payload.get("run_name")
    tick_time_ms = payload.get("tick_time_ms")
    candidate_specs = payload.get("candidate_specs")
    initial_state = payload.get("initial_state")
    previous_step_id = payload.get("previous_step_id")
    if not isinstance(run_name, str):
        raise ValueError("run_name is required")
    _validate_run_name(run_name)
    if (
        not isinstance(tick_time_ms, int)
        or isinstance(tick_time_ms, bool)
        or tick_time_ms < 0
    ):
        raise ValueError("tick_time_ms must be non-negative integer")
    if not isinstance(candidate_specs, list):
        raise ValueError("candidate_specs must be an array")
    if initial_state is not None and not isinstance(initial_state, Mapping):
        raise ValueError("initial_state must be object/null")
    if previous_step_id is not None and (
        not isinstance(previous_step_id, str) or not previous_step_id
    ):
        raise ValueError("previous_step_id must be string/null")
    if (initial_state is None) == (previous_step_id is None):
        raise ValueError("provide exactly one of initial_state / previous_step_id")
    return (
        run_name,
        tick_time_ms,
        tuple(candidate_specs),
        initial_state,
        previous_step_id,
    )
