from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Callable


_RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,96}$")


def json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class OnlineObject:
    key: str
    payload: bytes
    content_type: str
    immutable: bool
    role: str


def build_online_objects(
    *,
    config: dict[str, Any],
    run_id: str,
    dataset: bytes,
    catalog: bytes,
    dataset_receipt: bytes,
    model: bytes,
    metrics: bytes,
    weekly_review: bytes | None = None,
    generated_at_utc: str,
) -> tuple[OnlineObject, ...]:
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("run_id must be a safe 1-96 character object-key component")
    storage = config["storage"]
    dataset_prefix = f"{str(storage['dataset_runs_namespace']).rstrip('/')}/run={run_id}"
    training_prefix = str(storage["training_namespace"]).rstrip("/")
    run_prefix = f"{training_prefix}/runs/run={run_id}"
    base = [
        OnlineObject(f"{dataset_prefix}/market-catalog.json", catalog, "application/json", True, "catalog"),
        OnlineObject(f"{dataset_prefix}/binance-spot-1d.parquet", dataset, "application/vnd.apache.parquet", True, "dataset"),
        OnlineObject(f"{dataset_prefix}/dataset-receipt.json", dataset_receipt, "application/json", True, "dataset_receipt"),
        OnlineObject(f"{run_prefix}/model.json", model, "application/json", True, "model"),
        OnlineObject(f"{run_prefix}/metrics.json", metrics, "application/json", True, "metrics"),
    ]
    if weekly_review is not None:
        base.append(
            OnlineObject(
                f"{run_prefix}/weekly-review.json",
                weekly_review,
                "application/json",
                True,
                "weekly_review",
            )
        )
    schema_version = str(storage.get("schema_version", "v0.3"))
    manifest = {
        "schema": f"binance-spot-r2-automated-training-run-{schema_version}",
        "status": "PASS",
        "mode": "RESEARCH_TRAINING_ONLY",
        "provider": "binance_spot",
        "run_id": run_id,
        "generated_at_utc": generated_at_utc,
        "objects": [
            {
                "role": item.role,
                "key": item.key,
                "bytes": len(item.payload),
                "sha256": sha256_bytes(item.payload),
            }
            for item in base
        ],
        "authority": {
            "source_switch_authorized": False,
            "pionex_native_relabel_authorized": False,
            "automatic_trade_plan_authorized": False,
            "real_money_order_authorized": False,
            "live_trading_authorized": False,
        },
    }
    manifest_payload = json_bytes(manifest)
    manifest_object = OnlineObject(
        f"{run_prefix}/manifest.json",
        manifest_payload,
        "application/json",
        True,
        "manifest",
    )
    latest = {
        "schema": f"binance-spot-r2-automated-training-latest-{schema_version}",
        "provider": "binance_spot",
        "run_id": run_id,
        "generated_at_utc": generated_at_utc,
        "manifest_key": manifest_object.key,
        "manifest_sha256": sha256_bytes(manifest_payload),
        "catalog_key": f"{dataset_prefix}/market-catalog.json",
        "catalog_sha256": sha256_bytes(catalog),
        "dataset_key": f"{dataset_prefix}/binance-spot-1d.parquet",
        "dataset_sha256": sha256_bytes(dataset),
        "dataset_receipt_key": f"{dataset_prefix}/dataset-receipt.json",
        "dataset_receipt_sha256": sha256_bytes(dataset_receipt),
        "model_key": f"{run_prefix}/model.json",
        "model_sha256": sha256_bytes(model),
    }
    if weekly_review is not None:
        latest["weekly_review_key"] = f"{run_prefix}/weekly-review.json"
        latest["weekly_review_sha256"] = sha256_bytes(weekly_review)
    latest_object = OnlineObject(
        str(storage["latest_training_pointer_key"]),
        json_bytes(latest),
        "application/json",
        False,
        "latest_pointer",
    )
    return tuple([*base, manifest_object, latest_object])


def current_bucket_bytes(store: Any) -> int:
    paginator = store.client.get_paginator("list_objects_v2")
    total = 0
    for page in paginator.paginate(Bucket=store.bucket):
        for item in page.get("Contents", []) or []:
            total += int(item.get("Size", 0))
    return total


def publish_online_objects(
    *,
    store: Any,
    objects: tuple[OnlineObject, ...],
    hard_stop_bytes: int,
    inventory_fn: Callable[[Any], int] = current_bucket_bytes,
    pass_stage: str = "BINANCE_SPOT_R2_AUTOMATED_TRAINING_PUBLISHED_V0_3",
    metadata_version: str = "v0.3",
) -> dict[str, Any]:
    current_bytes = inventory_fn(store)
    planned_bytes = sum(len(item.payload) for item in objects)
    projected_bytes = current_bytes + planned_bytes
    if projected_bytes > hard_stop_bytes:
        return {
            "status": "BLOCKED",
            "stage": "R2_FREE_ONLY_HEADROOM_GATE_BLOCKED_BEFORE_WRITE",
            "current_bucket_bytes": current_bytes,
            "planned_write_bytes": planned_bytes,
            "projected_after_write_bytes": projected_bytes,
            "hard_stop_bytes": hard_stop_bytes,
            "r2_writes_performed": False,
        }

    for item in objects:
        if not item.immutable:
            continue
        existing = store.get_bytes_if_exists(item.key)
        if existing is not None and existing != item.payload:
            raise RuntimeError(f"immutable R2 training object conflict: {item.key}")

    receipts = []
    for item in objects:
        existing = store.get_bytes_if_exists(item.key) if item.immutable else None
        if existing == item.payload:
            action = "VERIFY_EXISTING"
            object_sha = sha256_bytes(existing)
            receipt = {
                "bucket": store.bucket,
                "key": item.key,
                "bytes": len(existing),
                "sha256": object_sha,
                "etag": None,
            }
        else:
            action = "UPLOAD"
            uploaded = store.put_bytes(
                item.key,
                item.payload,
                content_type=item.content_type,
                metadata={"provider": "binance_spot", "role": item.role, "version": metadata_version},
            )
            receipt = asdict(uploaded)
        verified = store.get_bytes_verified(item.key, expected_sha256=str(receipt["sha256"]))
        if verified != item.payload:
            raise RuntimeError(f"R2 exact-byte round trip mismatch: {item.key}")
        receipts.append({"role": item.role, "action": action, **receipt})

    return {
        "status": "PASS",
        "stage": pass_stage,
        "current_bucket_bytes_before_write": current_bytes,
        "planned_write_bytes": planned_bytes,
        "hard_stop_bytes": hard_stop_bytes,
        "objects": receipts,
        "latest_pointer_written_last": objects[-1].role == "latest_pointer",
        "r2_writes_performed": any(item["action"] == "UPLOAD" for item in receipts),
        "live_trading_authorized": False,
    }
