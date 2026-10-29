"""Shared-admission successor for research signal publication, disabled by default.

The legacy scheduled collector is unchanged. This publisher alone does not
authorize collection, prove all-writer coverage, or enable Cloud Paper.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable, Mapping
from datetime import UTC, datetime

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked, CloudBudgetGuard
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.shared_writer_budget_gate_v0_4 import (
    AdmissionQueryMeter, Query, SharedWriterReservation,
)
from crypto_autopilot.paper.shared_writer_r2_budget_v0_1 import SharedWriterR2Budget

WRITER = "crypto-autopilot:research-signal-layer-v0-2"
NAMESPACE = "research/signal-layer/v0-2"
MAX_BYTES = 2_500_000


def _validate_target(credentials: Mapping[str, str]) -> None:
    required = {"account_id", "bucket", "access_key_id", "secret_access_key"}
    if not isinstance(credentials, Mapping) or set(credentials) != required or any(
        not isinstance(value, str) or not value.strip() for value in credentials.values()
    ):
        raise BudgetBlocked("BLOCKED_SIGNAL_CREDENTIAL_BINDING")
    if credentials["account_id"] != os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""):
        raise BudgetBlocked("BLOCKED_SIGNAL_ACCOUNT_MISMATCH")
    if credentials["bucket"] != os.environ.get("R2_BUCKET_NAME", ""):
        raise BudgetBlocked("BLOCKED_SIGNAL_BUCKET_MISMATCH")


def _encode(value: Mapping[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       indent=2, allow_nan=False) + "\n").encode()


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value,
    ):
        raise BudgetBlocked("BLOCKED_SIGNAL_TIMESTAMP")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise BudgetBlocked("BLOCKED_SIGNAL_TIMESTAMP") from None
    return result.astimezone(UTC)


def _latest_condition(
    store: BudgetedR2Store, *, generated_at: datetime,
) -> dict[str, str]:
    """Read one bounded pointer and bind publication to that exact S3 version."""
    try:
        response = store.client.get_object(Bucket=store.bucket, Key=f"{NAMESPACE}/latest.json")
    except Exception as exc:
        response_data = getattr(exc, "response", {}) or {}
        if (
            str(response_data.get("Error", {}).get("Code", "")) in
            {"NoSuchKey", "NotFound", "404"}
            or response_data.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404
        ):
            return {"IfNoneMatch": "*"}
        raise
    stream = response["Body"]
    try:
        body = stream.read(MAX_BYTES + 1)
    finally:
        stream.close()
    if not isinstance(body, bytes) or len(body) > MAX_BYTES:
        raise BudgetBlocked("BLOCKED_SIGNAL_POINTER_SIZE")
    etag = response.get("ETag")
    if not isinstance(etag, str) or not re.fullmatch(r'"[^"\r\n]{1,128}"', etag):
        raise BudgetBlocked("BLOCKED_SIGNAL_POINTER_ETAG")
    previous = json.loads(body)
    if not isinstance(previous, dict):
        raise BudgetBlocked("BLOCKED_SIGNAL_POINTER_SCHEMA")
    previous_run = previous.get("run_id")
    if (
        previous.get("schema") != "research-signal-layer-latest-v0.2"
        or not isinstance(previous_run, str)
        or not re.fullmatch(r"[1-9][0-9]{0,19}", previous_run)
        or previous.get("manifest_key") !=
        f"{NAMESPACE}/runs/run={previous_run}/manifest.json"
        or not isinstance(previous.get("manifest_sha256"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", previous["manifest_sha256"])
    ):
        raise BudgetBlocked("BLOCKED_SIGNAL_POINTER_SCHEMA")
    expected = response.get("Metadata", {}).get("sha256")
    if expected != hashlib.sha256(body).hexdigest():
        raise BudgetBlocked("BLOCKED_SIGNAL_POINTER_HASH")
    if _timestamp(previous.get("generated_at_utc")) >= generated_at:
        raise BudgetBlocked("BLOCKED_SIGNAL_POINTER_NOT_NEWER")
    return {"IfMatch": etag}


def _objects(payload: Mapping[str, object], run_id: str) -> tuple[tuple[str, bytes], ...]:
    if not isinstance(run_id, str) or not re.fullmatch(r"[1-9][0-9]{0,19}", run_id):
        raise BudgetBlocked("BLOCKED_SIGNAL_RUN_ID")
    authority = payload.get("authority")
    if (
        payload.get("schema") != "research-signal-layer-run-v0.2"
        or payload.get("mode") != "RESEARCH_ONLY"
        or payload.get("run_id") != run_id
        or not isinstance(authority, Mapping)
        or any(authority.get(key) is not False for key in (
            "automatic_model_promotion", "direct_trade_trigger",
            "real_money_order", "live_trading",
        ))
        or not isinstance(payload.get("generated_at_utc"), str)
        or not payload["generated_at_utc"]
    ):
        raise BudgetBlocked("BLOCKED_SIGNAL_PAYLOAD_BINDING")
    _timestamp(payload["generated_at_utc"])
    prefix = f"{NAMESPACE}/runs/run={run_id}"
    body = _encode(payload)
    manifest = _encode({
        "schema": "research-signal-layer-manifest-v0.2",
        "run_id": run_id, "payload_key": f"{prefix}/signals.json",
        "payload_sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body),
    })
    latest = _encode({
        "schema": "research-signal-layer-latest-v0.2",
        "run_id": run_id, "manifest_key": f"{prefix}/manifest.json",
        "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
        "generated_at_utc": payload["generated_at_utc"],
    })
    objects = ((f"{prefix}/signals.json", body),
               (f"{prefix}/manifest.json", manifest),
               (f"{NAMESPACE}/latest.json", latest))
    if sum(len(body) for _, body in objects) > MAX_BYTES:
        raise BudgetBlocked("BLOCKED_SIGNAL_PAYLOAD_TOO_LARGE")
    return objects


def publish_shared_signal_payload(
    *, payload: Mapping[str, object], run_id: str,
    reservation: SharedWriterReservation, guard: CloudBudgetGuard,
    execute: Query, query_meter: AdmissionQueryMeter,
    validate_binding: Callable[[], None], credentials: Mapping[str, str],
    execution_enabled: bool = False,
) -> dict[str, object]:
    """Admit before constructing S3; read back both immutable objects before latest.

    The trusted caller must supply the exact merged execution authority through
    validate_binding. No CLI/workflow wires this successor yet. All existing
    freshness, headroom and per-operation checks remain mandatory.
    """
    if type(execution_enabled) is not bool:
        raise BudgetBlocked("BLOCKED_SIGNAL_EXECUTION_FLAG")
    if not execution_enabled:
        return {"status": "SKIPPED_DISABLED", "external_access_performed": False}
    objects = _objects(payload, run_id)
    planned_bytes = sum(len(body) for _, body in objects)
    reservation.validate()
    now_ms = guard.clock_ms()
    generated_ms = int(_timestamp(payload["generated_at_utc"]).timestamp() * 1000)
    if type(now_ms) is not int or not reservation.slot_at_ms <= generated_ms <= now_ms:
        raise BudgetBlocked("BLOCKED_SIGNAL_GENERATION_TIME")
    if (
        reservation.writer_id != WRITER or reservation.provider_requests != 0
        or reservation.r2_class_a != 3 or reservation.r2_class_b != 6
        or reservation.r2_new_bytes != planned_bytes
    ):
        raise BudgetBlocked("BLOCKED_SIGNAL_ENVELOPE_MISMATCH")
    _validate_target(credentials)
    credentials = dict(credentials)

    def validate_target_binding() -> None:
        _validate_target(credentials)
        validate_binding()

    budget = SharedWriterR2Budget.admit(
        reservation=reservation, guard=guard, execute=execute,
        query_meter=query_meter, validate_binding=validate_target_binding,
    )
    return _publish_objects(
        objects=objects, run_id=run_id, generated_at=_timestamp(payload["generated_at_utc"]),
        budget=budget, credentials=credentials,
    )


def _publish_objects(
    *, objects: tuple[tuple[str, bytes], ...], run_id: str, generated_at: datetime,
    budget: SharedWriterR2Budget, credentials: Mapping[str, str],
) -> dict[str, object]:
    """Trusted admitted callers only; preserve one publication implementation."""
    planned_bytes = sum(len(body) for _, body in objects)
    verified = 0
    stage = "CONSTRUCT_STORE"
    try:
        store = BudgetedR2Store.from_credentials(
            account_id=credentials["account_id"], bucket=credentials["bucket"],
            access_key_id=credentials["access_key_id"],
            secret_access_key=credentials["secret_access_key"],
            before_external=budget.reserve,
        )
        stage = "LATEST_POINTER_PREFLIGHT"
        condition = _latest_condition(
            store, generated_at=generated_at,
        )
        for index, (key, body) in enumerate(objects):
            stage = f"IMMUTABLE_{index + 1}" if index < 2 else "LATEST_POINTER"
            if index < 2:
                existing = store.get_bytes_if_exists(key)
                if existing is not None and existing != body:
                    raise BudgetBlocked("IMMUTABLE_CONFLICT")
            else:
                existing = None
            if existing != body:
                if index < 2:
                    store.client.put_object(
                        Bucket=store.bucket, Key=key, Body=body,
                        ContentType="application/json", IfNoneMatch="*",
                        Metadata={"sha256": hashlib.sha256(body).hexdigest(),
                                  "provider": "public_research", "version": "v0.2"},
                    )
                else:
                    store.client.put_object(
                        Bucket=store.bucket, Key=key, Body=body,
                        ContentType="application/json", **condition,
                        Metadata={"sha256": hashlib.sha256(body).hexdigest(),
                                  "provider": "public_research", "version": "v0.2"},
                    )
            store.get_bytes_verified(key, expected_sha256=hashlib.sha256(body).hexdigest())
            verified += 1
    except Exception:
        # Never expose response bodies, credential values or exception text.
        return {
            "status": "REVIEW_REQUIRED", "stage": stage, "run_id": run_id,
            "objects_verified": verified, "latest_pointer_verified": False,
            "partial_writes_possible": True, "central_reservation_retained": True,
            "attempted_usage": budget.attempted_usage(),
            "automatic_retry_allowed": False,
        }
    return {
        "status": "PUBLISHED", "run_id": run_id, "objects_verified": verified,
        "latest_pointer_verified": True, "central_reservation_retained": True,
        "attempted_usage": budget.attempted_usage(),
        "planned_write_bytes": planned_bytes,
        "provider_requests_performed": 0, "bucket_scans_performed": 0,
        "account_wide_coverage_proven": False,
        "paper_activation_allowed": False,
    }
