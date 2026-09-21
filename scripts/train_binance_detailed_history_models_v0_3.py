#!/usr/bin/env python3
"""Core100 training with deterministic experiment-fingerprint NO_CHANGE reuse."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from crypto_autopilot.history.detailed import DetailedHistoryAuthorityError
from crypto_autopilot.storage.ephemeral import require_ephemeral_output


ROOT = Path(__file__).resolve().parents[1]
V02 = ROOT / "scripts/train_binance_detailed_history_models_v0_2.py"
DEFAULT_CONFIG = ROOT / "config/binance_usdm_detailed_history_v0_1_2.json"
DEFAULT_AUTHORITY = (
    ROOT
    / "research/receipts/2026-08-29-binance-usdm-crypto-core-100-v0-1-2-authority.json"
)
DEFAULT_FINGERPRINT_CONFIG = ROOT / "config/core100_training_fingerprint_v0_1.json"

spec = importlib.util.spec_from_file_location("binance_detailed_training_v0_2", V02)
training_v02 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(training_v02)
runner = training_v02.runner


def _git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise DetailedHistoryAuthorityError(f"{path} must contain a JSON object")
    return payload


def _fingerprint_payload(
    *,
    dataset_fingerprint: str,
    python_runtime: str,
    model_affecting_git_blobs: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "schema": "qookey-core100-training-experiment-fingerprint-v0.1",
        "dataset_fingerprint": dataset_fingerprint,
        "python_runtime": python_runtime,
        "model_affecting_git_blobs": model_affecting_git_blobs,
    }


def _payload_sha256(payload: Mapping[str, Any]) -> str:
    return runner.sha256_bytes(runner.canonical_json_bytes(dict(payload)))


def validate_fingerprint_config(
    config: Mapping[str, Any],
) -> None:
    if (
        config.get("schema") != "qookey-core100-training-fingerprint-v0.1"
        or config.get("status") != "EFFECTIVE_ON_PROTECTED_MAIN_MERGE"
    ):
        raise DetailedHistoryAuthorityError("Core100 training fingerprint config mismatch")
    paths = config.get("model_affecting_paths")
    baseline = config.get("baseline")
    reuse = config.get("reuse_policy")
    authority = config.get("authority")
    if (
        not isinstance(paths, list)
        or not paths
        or not all(isinstance(path, str) and path for path in paths)
        or not isinstance(baseline, Mapping)
        or not isinstance(reuse, Mapping)
        or not isinstance(authority, Mapping)
    ):
        raise DetailedHistoryAuthorityError("Core100 training fingerprint config shape mismatch")
    if len(paths) != len(set(paths)):
        raise DetailedHistoryAuthorityError("Core100 training fingerprint path list is not unique")
    if any(value is not False for value in authority.values()):
        raise DetailedHistoryAuthorityError("Core100 training fingerprint gained authority")
    if (
        reuse.get("same_dataset_and_experiment_returns") != "NO_CHANGE"
        or reuse.get("no_training_on_no_change") is not True
        or reuse.get("no_r2_write_on_no_change") is not True
        or reuse.get("legacy_v0_1_latest_pointer_may_reuse_only_exact_baseline_run")
        is not True
    ):
        raise DetailedHistoryAuthorityError("Core100 training reuse policy drifted")

    baseline_rows = baseline.get("model_affecting_git_blobs")
    if not isinstance(baseline_rows, list) or [row.get("path") for row in baseline_rows] != paths:
        raise DetailedHistoryAuthorityError("Core100 training baseline path order mismatch")
    baseline_payload = _fingerprint_payload(
        dataset_fingerprint=str(baseline.get("dataset_fingerprint") or ""),
        python_runtime=str(config.get("python_runtime") or ""),
        model_affecting_git_blobs=[
            {
                "path": str(row.get("path") or ""),
                "git_blob_sha": str(row.get("git_blob_sha") or ""),
            }
            for row in baseline_rows
        ],
    )
    if _payload_sha256(baseline_payload) != baseline.get("experiment_fingerprint"):
        raise DetailedHistoryAuthorityError("Core100 training baseline fingerprint mismatch")


def build_experiment_identity(
    *,
    dataset_fingerprint: str,
    fingerprint_config: Mapping[str, Any],
    root: Path = ROOT,
) -> tuple[str, list[dict[str, str]]]:
    validate_fingerprint_config(fingerprint_config)
    paths = fingerprint_config["model_affecting_paths"]
    assert isinstance(paths, list)
    rows = [
        {
            "path": str(path),
            "git_blob_sha": _git_blob_sha(root / str(path)),
        }
        for path in paths
    ]
    payload = _fingerprint_payload(
        dataset_fingerprint=dataset_fingerprint,
        python_runtime=str(fingerprint_config["python_runtime"]),
        model_affecting_git_blobs=rows,
    )
    return _payload_sha256(payload), rows


def load_training_latest(store, config: Mapping[str, Any]) -> tuple[str, dict[str, Any] | None]:
    namespace = str(config["storage"]["training_namespace"]).rstrip("/")
    key = f"{namespace}/latest.json"
    payload = store.get_bytes_if_exists(key)
    if payload is None:
        return key, None
    latest = json.loads(payload)
    if (
        not isinstance(latest, dict)
        or latest.get("schema")
        not in {
            "binance-usdm-intraday-research-training-latest-v0.1",
            "binance-usdm-intraday-research-training-latest-v0.2",
        }
        or latest.get("provider") != "binance_usdm"
        or not latest.get("run_id")
        or not latest.get("dataset_fingerprint")
        or not latest.get("manifest_key")
        or not latest.get("manifest_sha256")
    ):
        raise DetailedHistoryAuthorityError("Core100 training latest pointer mismatch")

    manifest_payload = store.get_bytes_verified(
        str(latest["manifest_key"]),
        expected_sha256=str(latest["manifest_sha256"]),
    )
    manifest = json.loads(manifest_payload)
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema")
        not in {
            "binance-usdm-intraday-research-training-manifest-v0.1",
            "binance-usdm-intraday-research-training-manifest-v0.2",
        }
        or manifest.get("status") != "PASS"
        or manifest.get("provider") != "binance_usdm"
        or manifest.get("run_id") != latest.get("run_id")
        or manifest.get("dataset_fingerprint") != latest.get("dataset_fingerprint")
        or manifest.get("experiment_fingerprint") != latest.get("experiment_fingerprint")
    ):
        raise DetailedHistoryAuthorityError("Core100 training latest manifest mismatch")
    return key, latest


def decide_training_reuse(
    *,
    latest: Mapping[str, Any] | None,
    dataset_fingerprint: str,
    experiment_fingerprint: str,
    fingerprint_config: Mapping[str, Any],
) -> dict[str, Any]:
    if latest is None:
        return {"reuse": False, "reason": "NO_PREVIOUS_TRAINING"}

    if (
        latest.get("dataset_fingerprint") == dataset_fingerprint
        and latest.get("experiment_fingerprint") == experiment_fingerprint
    ):
        return {
            "reuse": True,
            "reason": "EXACT_EXPERIMENT_FINGERPRINT_MATCH",
            "previous_run_id": latest.get("run_id"),
        }

    baseline = fingerprint_config["baseline"]
    assert isinstance(baseline, Mapping)
    if (
        latest.get("schema") == "binance-usdm-intraday-research-training-latest-v0.1"
        and latest.get("experiment_fingerprint") is None
        and latest.get("run_id") == baseline.get("latest_pointer_run_id")
        and latest.get("dataset_fingerprint") == baseline.get("dataset_fingerprint")
        and dataset_fingerprint == baseline.get("dataset_fingerprint")
        and experiment_fingerprint == baseline.get("experiment_fingerprint")
    ):
        return {
            "reuse": True,
            "reason": "VERIFIED_LEGACY_BASELINE_MATCH",
            "previous_run_id": latest.get("run_id"),
        }

    return {
        "reuse": False,
        "reason": "DATASET_OR_MODEL_INPUT_CHANGED",
        "previous_run_id": latest.get("run_id"),
    }


def publish_training_v0_2(
    store,
    *,
    config: dict[str, Any],
    model: dict[str, Any],
    metrics: dict[str, Any],
    dataset_fingerprint: str,
    experiment_fingerprint: str,
    experiment_git_blobs: list[dict[str, str]],
    run_id: str,
    generated_at_utc: str,
) -> dict[str, Any]:
    namespace = config["storage"]["training_namespace"].rstrip("/")
    run_prefix = f"{namespace}/runs/run={run_id}"
    model_payload = runner.canonical_json_bytes(model)
    metrics_payload = runner.canonical_json_bytes(metrics)
    manifest = {
        "schema": "binance-usdm-intraday-research-training-manifest-v0.2",
        "status": "PASS",
        "provider": "binance_usdm",
        "run_id": run_id,
        "generated_at_utc": generated_at_utc,
        "dataset_fingerprint": dataset_fingerprint,
        "experiment_fingerprint": experiment_fingerprint,
        "experiment_git_blobs": experiment_git_blobs,
        "model_quality_gate": metrics["model_quality_gate"],
        "objects": [
            {
                "role": "model",
                "key": f"{run_prefix}/model.json",
                "bytes": len(model_payload),
                "sha256": runner.sha256_bytes(model_payload),
            },
            {
                "role": "metrics",
                "key": f"{run_prefix}/metrics.json",
                "bytes": len(metrics_payload),
                "sha256": runner.sha256_bytes(metrics_payload),
            },
        ],
        "authority": model["authority"],
    }
    manifest_payload = runner.canonical_json_bytes(manifest)
    latest = {
        "schema": "binance-usdm-intraday-research-training-latest-v0.2",
        "provider": "binance_usdm",
        "run_id": run_id,
        "generated_at_utc": generated_at_utc,
        "dataset_fingerprint": dataset_fingerprint,
        "experiment_fingerprint": experiment_fingerprint,
        "manifest_key": f"{run_prefix}/manifest.json",
        "manifest_sha256": runner.sha256_bytes(manifest_payload),
        "model_key": f"{run_prefix}/model.json",
        "model_sha256": runner.sha256_bytes(model_payload),
        "metrics_key": f"{run_prefix}/metrics.json",
        "metrics_sha256": runner.sha256_bytes(metrics_payload),
        "model_quality_gate": metrics["model_quality_gate"],
    }
    latest_payload = runner.canonical_json_bytes(latest)
    current = runner.current_bucket_bytes(store)
    planned = len(model_payload) + len(metrics_payload) + len(manifest_payload) + len(latest_payload)
    if current + planned > int(config["storage"]["free_only_hard_stop_bytes"]):
        raise DetailedHistoryAuthorityError("R2 training evidence headroom gate blocked")

    records = [
        runner.put_immutable(
            store,
            key=f"{run_prefix}/model.json",
            payload=model_payload,
            role="model",
        ),
        runner.put_immutable(
            store,
            key=f"{run_prefix}/metrics.json",
            payload=metrics_payload,
            role="metrics",
        ),
        runner.put_immutable(
            store,
            key=f"{run_prefix}/manifest.json",
            payload=manifest_payload,
            role="manifest",
        ),
    ]
    pointer = store.put_bytes(
        f"{namespace}/latest.json",
        latest_payload,
        content_type="application/json",
        metadata={"provider": "binance_usdm", "role": "training-latest", "version": "v0.2"},
    )
    restored = store.get_bytes_verified(
        f"{namespace}/latest.json", expected_sha256=pointer.sha256
    )
    if restored != latest_payload:
        raise DetailedHistoryAuthorityError("training latest pointer round trip mismatch")
    return {
        "status": "PASS",
        "stage": "BINANCE_USDM_INTRADAY_RESEARCH_TRAINING_PUBLISHED_V0_2",
        "training_performed": True,
        "r2_writes_performed": True,
        "model_quality_gate": metrics["model_quality_gate"],
        "example_count": metrics["example_count"],
        "symbol_count": metrics["symbol_count"],
        "objects": records,
        "latest_pointer_written_last": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Train Core100 only when its governed experiment fingerprint changes."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument(
        "--fingerprint-config",
        type=Path,
        default=DEFAULT_FINGERPRINT_CONFIG,
    )
    parser.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID") or "local")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--now-utc")
    args = parser.parse_args()

    output = require_ephemeral_output(args.output)
    if not runner.SAFE_RUN_ID.fullmatch(args.run_id):
        raise ValueError("run id must be a safe 1-96 character object-key component")

    config, _authority, _config_bytes = runner.load_authority_pair(
        args.config, args.authority
    )
    fingerprint_config = _load_json(args.fingerprint_config)
    validate_fingerprint_config(fingerprint_config)

    observed = (
        datetime.fromisoformat(args.now_utc.replace("Z", "+00:00"))
        if args.now_utc
        else datetime.now(UTC)
    )
    generated_at = observed.astimezone(UTC).isoformat().replace("+00:00", "Z")

    try:
        runner.require_execution_window(config, observed_at=observed, operation="training")
    except DetailedHistoryAuthorityError as exc:
        if "blocked until the V0.10 window has ended" not in str(exc):
            raise
        report = {
            "status": "SKIPPED",
            "stage": "DETAILED_TRAINING_NOT_BEFORE_GUARD",
            "observed_at_utc": generated_at,
            "reason": str(exc),
            "provider_requests_performed": 0,
            "r2_access_performed": False,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(runner.canonical_json_bytes(report))
        print(json.dumps(report, sort_keys=True))
        return 0

    store = runner.create_store()
    try:
        catalog, state, object_records, dataset_fingerprint = runner.load_dataset_index(
            store, config
        )
    except DetailedHistoryAuthorityError as exc:
        if str(exc) not in {
            "detailed-history catalog/backfill state is missing",
            "detailed-history dataset is not complete and bound",
        }:
            raise
        report = {
            "status": "SKIPPED",
            "stage": "DETAILED_HISTORY_DATASET_NOT_READY",
            "observed_at_utc": generated_at,
            "reason": str(exc),
            "provider_requests_performed": 0,
            "r2_writes_performed": False,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(runner.canonical_json_bytes(report))
        print(json.dumps(report, sort_keys=True))
        return 0

    experiment_fingerprint, experiment_git_blobs = build_experiment_identity(
        dataset_fingerprint=dataset_fingerprint,
        fingerprint_config=fingerprint_config,
    )
    latest_key, latest = load_training_latest(store, config)
    decision = decide_training_reuse(
        latest=latest,
        dataset_fingerprint=dataset_fingerprint,
        experiment_fingerprint=experiment_fingerprint,
        fingerprint_config=fingerprint_config,
    )
    if decision["reuse"]:
        report = {
            "status": "NO_CHANGE",
            "stage": "CORE100_TRAINING_EXPERIMENT_UNCHANGED_V0_1",
            "observed_at_utc": generated_at,
            "reason": decision["reason"],
            "dataset_fingerprint": dataset_fingerprint,
            "experiment_fingerprint": experiment_fingerprint,
            "previous_training_run_id": decision.get("previous_run_id"),
            "previous_training_latest_key": latest_key,
            "dataset_rows": state["total_rows"],
            "dataset_partition_objects": state["total_partition_objects"],
            "training_performed": False,
            "provider_requests_performed": 0,
            "r2_reads_performed": True,
            "r2_writes_performed": False,
            "authority": dict(fingerprint_config["authority"]),
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(runner.canonical_json_bytes(report))
        print(json.dumps(report, sort_keys=True))
        return 0

    examples = training_v02.build_examples_from_r2(
        store,
        catalog=catalog,
        object_records=object_records,
        config=config,
    )
    model, metrics = runner.run_intraday_training(
        examples,
        config=config,
        dataset_fingerprint=dataset_fingerprint,
        generated_at_utc=generated_at,
    )
    result = publish_training_v0_2(
        store,
        config=config,
        model=model,
        metrics=metrics,
        dataset_fingerprint=dataset_fingerprint,
        experiment_fingerprint=experiment_fingerprint,
        experiment_git_blobs=experiment_git_blobs,
        run_id=args.run_id,
        generated_at_utc=generated_at,
    )
    report = {
        **result,
        "observed_at_utc": generated_at,
        "dedupe_reason": decision["reason"],
        "dataset_fingerprint": dataset_fingerprint,
        "experiment_fingerprint": experiment_fingerprint,
        "dataset_rows": state["total_rows"],
        "dataset_partition_objects": state["total_partition_objects"],
        "authority": model["authority"],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(runner.canonical_json_bytes(report))
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
