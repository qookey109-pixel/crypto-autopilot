"""Measure the R2 S3-adapter protocol path with an in-memory fake only.

This counts application payload bytes and S3-compatible operation calls emitted
by the production R2PaperRunStore/BudgetedR2Store adapters. It performs no
network or credential access and does not measure HTTP framing, Cloudflare
account usage, billing, other writers, or production headroom.
"""
from __future__ import annotations

import io
import json
from collections import Counter
from typing import Any

from crypto_autopilot.paper.cloud_r2_store_v0_1 import (
    BudgetedR2Policy,
    BudgetedR2Store,
)
from crypto_autopilot.paper.run_store_v0_1 import (
    R2PaperRunStore,
)


class _MissingObjectError(Exception):
    def __init__(self) -> None:
        self.response = {
            "Error": {"Code": "NoSuchKey"},
            "ResponseMetadata": {"HTTPStatusCode": 404},
        }


class _MemoryS3Client:
    """Small deterministic S3-compatible client used to exercise real adapters."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, dict[str, str]]] = {}
        self.calls: list[dict[str, Any]] = []

    def put_object(self, **kwargs: Any) -> dict[str, str]:
        body = kwargs.get("Body")
        key = kwargs.get("Key")
        if not isinstance(body, bytes) or not isinstance(key, str):
            raise ValueError("fake R2 put requires bytes and a key")
        conditional = kwargs.get("IfNoneMatch") == "*"
        self.calls.append({
            "operation": "PUT",
            "key": key,
            "request_body_bytes": len(body),
            "conditional": conditional,
        })
        if conditional and key in self.objects:
            error = RuntimeError("conditional create conflict")
            setattr(error, "response", {
                "Error": {"Code": "PreconditionFailed"},
                "ResponseMetadata": {"HTTPStatusCode": 412},
            })
            raise error
        metadata = kwargs.get("Metadata", {})
        self.objects[key] = (body, dict(metadata))
        return {"ETag": "fake-etag"}

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        key = kwargs.get("Key")
        if not isinstance(key, str):
            raise ValueError("fake R2 get requires a key")
        row = self.objects.get(key)
        self.calls.append({
            "operation": "GET",
            "key": key,
            "response_body_bytes": len(row[0]) if row else 0,
            "found": row is not None,
        })
        if row is None:
            raise _MissingObjectError()
        body, metadata = row
        return {"Body": io.BytesIO(body), "Metadata": dict(metadata)}

    def list_objects_v2(self, **kwargs: Any) -> dict[str, Any]:
        prefix = kwargs.get("Prefix")
        max_keys = kwargs.get("MaxKeys")
        token = kwargs.get("ContinuationToken")
        if not isinstance(prefix, str) or not isinstance(max_keys, int) or max_keys < 1:
            raise ValueError("fake R2 list requires a prefix and positive page size")
        keys = sorted(key for key in self.objects if key.startswith(prefix))
        offset = int(token) if isinstance(token, str) and token.isdigit() else 0
        page = keys[offset:offset + max_keys]
        next_offset = offset + len(page)
        truncated = next_offset < len(keys)
        self.calls.append({
            "operation": "LIST",
            "prefix": prefix,
            "returned_keys": len(page),
            "truncated": truncated,
        })
        result: dict[str, Any] = {
            "Contents": [{"Key": key} for key in page],
            "IsTruncated": truncated,
        }
        if truncated:
            result["NextContinuationToken"] = str(next_offset)
        return result


def _snapshot(
    client: Any,
    reservations: Counter[str],
    objects_before: int,
) -> dict[str, object]:
    calls = client.calls
    operation_counts = Counter(str(call["operation"]) for call in calls)
    return {
        "s3_compatible_operation_calls": dict(sorted(operation_counts.items())),
        "budget_reservations": dict(sorted(reservations.items())),
        "put_application_payload_bytes": sum(
            int(call.get("request_body_bytes", 0)) for call in calls
            if call["operation"] == "PUT"
        ),
        "reserved_put_application_payload_bytes": sum(
            int(call.get("request_body_bytes", 0)) for call in calls
            if call["operation"] == "PUT"
        ),
        "get_application_payload_bytes": sum(
            int(call.get("response_body_bytes", 0)) for call in calls
            if call["operation"] == "GET"
        ),
        "missing_gets": sum(
            1 for call in calls if call["operation"] == "GET" and not call["found"]
        ),
        "objects_added": len(client.objects) - objects_before,
        "stored_objects": len(client.objects),
        "stored_object_payload_bytes": sum(len(body) for body, _ in client.objects.values()),
    }


def build_report() -> dict[str, object]:
    client = _MemoryS3Client()
    reservations: Counter[str] = Counter()

    def reserve(operation: str, size: int) -> None:
        reservations[operation] += 1

    r2 = BudgetedR2Store(
        client=client,
        bucket="synthetic-only",
        before_external=reserve,
        policy=BudgetedR2Policy(maximum_list_pages=10, maximum_list_keys_per_page=2),
    )
    store = R2PaperRunStore(r2, prefix="synthetic-profile/v0.1")
    scenarios: list[dict[str, object]] = []

    payload = {"account": {"cash_usd": 10000}, "state": "NO_TRADE"}
    before_objects = len(client.objects)
    store.put_json("state", "genesis", payload)
    scenarios.append({
        "scenario": "new_put_json",
        **_snapshot(client, reservations, before_objects),
    })

    before_calls = len(client.calls)
    before_reservations = reservations.copy()
    before_objects = len(client.objects)
    store.put_json("state", "genesis", payload)
    scenarios.append({
        "scenario": "identical_replay_put_json",
        **_snapshot(
            _CallSliceClient(client, before_calls),
            reservations - before_reservations,
            before_objects,
        ),
    })

    before_calls = len(client.calls)
    before_reservations = reservations.copy()
    before_objects = len(client.objects)
    store.get_json("state", "genesis")
    scenarios.append({
        "scenario": "read_existing_json",
        **_snapshot(
            _CallSliceClient(client, before_calls),
            reservations - before_reservations,
            before_objects,
        ),
    })

    before_calls = len(client.calls)
    before_reservations = reservations.copy()
    before_objects = len(client.objects)
    store.list_json_ids("state")
    scenarios.append({
        "scenario": "list_one_page",
        **_snapshot(
            _CallSliceClient(client, before_calls),
            reservations - before_reservations,
            before_objects,
        ),
    })

    before_calls = len(client.calls)
    before_reservations = reservations.copy()
    before_objects = len(client.objects)
    store.put_json_if_absent("claim", "slot-1", {"slot": "1"})
    scenarios.append({
        "scenario": "conditional_create",
        **_snapshot(
            _CallSliceClient(client, before_calls),
            reservations - before_reservations,
            before_objects,
        ),
    })

    before_calls = len(client.calls)
    before_reservations = reservations.copy()
    before_objects = len(client.objects)
    for index in range(5):
        store.put_json_if_absent("paged", f"item-{index}", {"item": index})
    store.list_json_ids("paged")
    scenarios.append({
        "scenario": "conditional_create_and_paginated_list",
        **_snapshot(
            _CallSliceClient(client, before_calls),
            reservations - before_reservations,
            before_objects,
        ),
    })

    return {
        "schema": "qookey-cloud-paper-synthetic-r2-protocol-profile-v0.1",
        "evidence_type": "SYNTHETIC_ADAPTER_PROTOCOL_ONLY",
        "scenarios": scenarios,
        "scope": {
            "network_requests": 0,
            "provider_requests": 0,
            "cloudflare_r2_requests": 0,
            "d1_requests": 0,
            "credentials_constructed": False,
            "measures_real_adapters": True,
            "measures_http_wire_bytes": False,
            "measures_account_usage_or_billing": False,
        },
        "limitations": [
            "Counts S3-compatible method calls emitted by the production adapters against an in-memory fake.",
            "Payload byte counts exclude HTTP framing, request headers, service metadata and billing aggregation.",
            "Fixtures do not establish production slot frequency, account-wide writers, free-tier headroom or zero total cost.",
            "No production provider, R2 or D1 access is performed.",
        ],
    }


class _CallSliceClient:
    """View only newly recorded calls while retaining cumulative object state."""

    def __init__(self, client: _MemoryS3Client, start: int) -> None:
        self.objects = client.objects
        self.calls = client.calls[start:]


def main() -> None:
    print(json.dumps(build_report(), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
