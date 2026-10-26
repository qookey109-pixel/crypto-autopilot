"""Disabled composition: one reservation for governed research GETs and R2.

No active workflow cutover, production writer coverage or execution authority.
The injected binding validator is a trusted runtime boundary, not a flag grant.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any
from urllib.request import HTTPRedirectHandler, build_opener

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked, CloudBudgetGuard
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import (
    AdmissionQueryMeter, Query, SharedWriterReservation,
)
from crypto_autopilot.paper.shared_writer_r2_budget_v0_1 import SharedWriterR2Budget
from crypto_autopilot.research.shared_signal_publish_v0_1 import (
    WRITER, _objects, _publish_objects, _timestamp,
)
from crypto_autopilot.research.signal_ingest_v0_2 import (
    build_signal_payload, collect_sources,
)

RESERVED_BYTES = 270_336
_APPROVED = {
    "capafy_category_11": (
        "https://capafy.ai/zh-hant/?category=11", "structured_json_only",
    ),
    "capafy_btc_cycle_radar": (
        "https://capafy.ai/zh-hant/agent/bitcoin-cycle-radar-btc-health-buzz/8672024464",
        "structured_json_only",
    ),
    "x_aleabitoreddit": ("https://x.com/aleabitoreddit", "metadata_only"),
}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _selected(sources: Sequence[Mapping[str, object]]) -> list[Mapping[str, object]]:
    if not isinstance(sources, (tuple, list)) or len(sources) > 3:
        raise BudgetBlocked("BLOCKED_SIGNAL_SOURCES")
    selected = []
    seen = set()
    for row in sources:
        if (
            not isinstance(row, Mapping)
            or set(row) != {"source_id", "url", "enabled", "parse_mode"}
            or type(row.get("enabled")) is not bool
        ):
            raise BudgetBlocked("BLOCKED_SIGNAL_SOURCE_SHAPE")
        identity = row.get("source_id")
        if not isinstance(identity, str) or identity in seen or identity not in _APPROVED:
            raise BudgetBlocked("BLOCKED_SIGNAL_SOURCE_ID")
        if (row["url"], row["parse_mode"]) != _APPROVED[identity]:
            raise BudgetBlocked("BLOCKED_SIGNAL_SOURCE_SCOPE")
        seen.add(identity)
        if row["enabled"]:
            selected.append(dict(row))
    return selected


def run_shared_signal_collection(
    *, sources: Sequence[Mapping[str, object]], run_id: str,
    reservation: SharedWriterReservation, guard: CloudBudgetGuard,
    execute: Query, query_meter: AdmissionQueryMeter,
    validate_binding: Callable[[], None], credentials: Mapping[str, str],
    transport: Callable[..., Any] | None = None, execution_enabled: bool = False,
) -> dict[str, object]:
    """Trusted transport injection must preserve single-attempt HTTP semantics."""
    if type(execution_enabled) is not bool:
        raise BudgetBlocked("BLOCKED_SIGNAL_EXECUTION_FLAG")
    if not execution_enabled:
        return {"status": "SKIPPED_DISABLED", "external_access_performed": False}
    selected = _selected(sources)
    if not selected:
        return {"status": "SKIPPED_NO_ENABLED_SOURCES", "external_access_performed": False}
    if not isinstance(run_id, str) or not re.fullmatch(r"[1-9][0-9]{0,19}", run_id):
        raise BudgetBlocked("BLOCKED_SIGNAL_RUN_ID")
    reservation.validate()
    if (
        reservation.writer_id != WRITER
        or reservation.provider_requests != len(selected)
        or reservation.r2_class_a != 3 or reservation.r2_class_b != 6
        or reservation.r2_new_bytes != RESERVED_BYTES
    ):
        raise BudgetBlocked("BLOCKED_SIGNAL_ENVELOPE_MISMATCH")
    if set(credentials) != {"account_id", "bucket", "access_key_id", "secret_access_key"} or any(
        not isinstance(value, str) or not value.strip() for value in credentials.values()
    ):
        raise BudgetBlocked("BLOCKED_SIGNAL_CREDENTIAL_BINDING")
    if transport is not None and not callable(transport):
        raise BudgetBlocked("BLOCKED_SIGNAL_TRANSPORT")
    if guard.storage_capacity_state() == "HARD_STOP" or (
        guard.snapshot.storage_bytes + guard.snapshot.pending_storage_bytes + RESERVED_BYTES
        >= guard.policy.r2_hard_stop_bytes
    ):
        raise BudgetBlocked("BLOCKED_BUDGET_STORAGE_HARD_STOP")

    budget = SharedWriterR2Budget.admit(
        reservation=reservation, guard=guard, execute=execute,
        query_meter=query_meter, validate_binding=validate_binding,
    )
    used = 0
    budget_blocked = False
    snapshots = []
    forecasts = []
    # Creating an opener performs no HTTP request; no default redirect/retry path.
    send = transport if transport is not None else build_opener(NoRedirect()).open

    def before_source() -> None:
        validate_binding()
        if guard.storage_capacity_state() == "HARD_STOP":
            raise BudgetBlocked("BLOCKED_BUDGET_STORAGE_HARD_STOP")
        now = guard.clock_ms()
        if (
            type(now) is not int or now < reservation.reserved_at_ms
            or now - reservation.slot_at_ms > 600_000
            or used >= reservation.provider_requests
        ):
            raise BudgetBlocked("BLOCKED_SIGNAL_SOURCE_WINDOW_OR_LIMIT")
        guard.reserve_provider_request()

    def open_once(request, *, timeout):
        nonlocal used, budget_blocked
        try:
            before_source()
        except Exception:
            budget_blocked = True
            raise BudgetBlocked("BLOCKED_SIGNAL_SOURCE_BUDGET") from None
        if request.get_method() != "GET" or request.full_url not in {
            row["url"] for row in selected
        } or timeout != 20:
            budget_blocked = True
            raise BudgetBlocked("BLOCKED_SIGNAL_SOURCE_REQUEST")
        used += 1
        response = send(request, timeout=timeout)
        if getattr(response, "status", None) != 200:
            response.close()
            raise BudgetBlocked("BLOCKED_SIGNAL_SOURCE_HTTP_STATUS")
        return response

    def review(stage: str, reason: str) -> dict[str, object]:
        return {
            "status": "REVIEW_REQUIRED", "stage": stage, "reason_code": reason,
            "run_id": run_id, "provider_requests_performed": used,
            "attempted_usage": budget.attempted_usage(),
            "central_reservation_retained": True, "automatic_retry_allowed": False,
            "paper_activation_allowed": False,
        }

    for row in selected:
        captured = guard.clock_ms()
        items, predictions = collect_sources(
            [row], timeout_seconds=20, max_bytes=500_000, opener=open_once,
            retrieved_at_ms=captured,
        )
        if len(items) != 1 or items[0].status != "PARSED":
            return review(
                "SOURCE_ACQUISITION",
                "BUDGET_BLOCKED" if budget_blocked else "SOURCE_FETCH_FAILED",
            )
        snapshots.extend(items)
        forecasts.extend(predictions)
    try:
        validate_binding()
        if guard.storage_capacity_state() == "HARD_STOP":
            return review("PAYLOAD_BOUNDS", "BUDGET_BLOCKED")
        now = guard.clock_ms()
        if type(now) is not int or now < reservation.reserved_at_ms:
            return review("PAYLOAD_BOUNDS", "CLOCK_INVALID")
        timestamp = datetime.fromtimestamp(now // 1000, tz=UTC).replace(
            microsecond=(now % 1000) * 1000,
        ).isoformat().replace("+00:00", "Z")
        payload = build_signal_payload(
            run_id=run_id, generated_at_utc=timestamp,
            snapshots=snapshots, forecasts=forecasts,
        )
        objects = _objects(payload, run_id)
        if (
            sum(len(body) for _, body in objects) > RESERVED_BYTES
            or len(objects[0][1]) > min(262_144, guard.policy.r2_object_max_bytes)
            or any(len(body) > min(4096, guard.policy.r2_object_max_bytes)
                   for _, body in objects[1:])
        ):
            return review("PAYLOAD_BOUNDS", "PUBLICATION_TOO_LARGE")
    except Exception:
        return review("PAYLOAD_BOUNDS", "PAYLOAD_OR_EVIDENCE_INVALID")
    result = _publish_objects(
        objects=objects, run_id=run_id, generated_at=_timestamp(timestamp),
        budget=budget, credentials=credentials,
    )
    result["provider_requests_performed"] = used
    result["source_count"] = len(snapshots)
    result["reserved_new_bytes"] = RESERVED_BYTES
    return result
