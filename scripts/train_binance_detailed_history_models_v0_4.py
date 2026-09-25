#!/usr/bin/env python3
"""Cloud-only one-shot Core100 fingerprint V0.2 bootstrap and read-only comparator."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import importlib.util
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from crypto_autopilot.history.detailed import DetailedHistoryAuthorityError
from crypto_autopilot.storage.ephemeral import require_ephemeral_output
from crypto_autopilot.training import fingerprint_collector_v0_2 as collector
from crypto_autopilot.training.fingerprint_v0_2_execution import (
    SuccessorContractError,
    build_fingerprint,
    compare_fingerprints,
    validate_successor_contract,
)


ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_CONFIG_SCHEMA = "qookey-core100-training-fingerprint-v0.2-bootstrap-authority-v0.1"
AUTHORITY_RECEIPT_SCHEMA = "qookey-core100-training-fingerprint-v0.2-bootstrap-authority-receipt-v0.1"
IMPLEMENTATION_RECEIPT_SCHEMA = "qookey-core100-training-fingerprint-v0.2-implementation-receipt-v0.1"
IMPLEMENTATION_STATUS = "IMPLEMENTATION_READY_AFTER_MAIN_MERGE"
WORKFLOW_PATH = ".github/workflows/binance-usdm-detailed-training-v0-1.yml"
WORKFLOW_FILE = Path(WORKFLOW_PATH).name
PARENT_CONTRACT_PATH = "config/core100_training_fingerprint_v0_2.json"
DATA_CONFIG_PATH = "config/binance_usdm_detailed_history_v0_1_2.json"
DATA_AUTHORITY_PATH = "research/receipts/2026-08-29-binance-usdm-crypto-core-100-v0-1-2-authority.json"
AUTHORITY_CONFIG_PATH = "config/core100_training_fingerprint_v0_2_bootstrap_authority_v0_1.json"
AUTHORITY_RECEIPT_PATH = "research/receipts/2026-09-25-core100-training-fingerprint-v0-2-bootstrap-authority.json"
SUCCESSOR_CONTRACT_PATH = "config/core100_training_fingerprint_v0_2_successor_v0_1.json"
IMPLEMENTATION_RECEIPT_PATH = "research/receipts/2026-09-25-core100-training-fingerprint-v0-2-implementation.json"

_V03_PATH = ROOT / "scripts/train_binance_detailed_history_models_v0_3.py"
_v03_spec = importlib.util.spec_from_file_location("core100_training_v0_3_runtime", _V03_PATH)
if _v03_spec is None or _v03_spec.loader is None:
    raise RuntimeError("existing Core100 V0.3 runtime is unavailable")
v03_runtime = importlib.util.module_from_spec(_v03_spec)
_v03_spec.loader.exec_module(v03_runtime)
runner = v03_runtime.runner
training_v02 = v03_runtime.training_v02
COMPARATOR_PATH = "src/crypto_autopilot/training/fingerprint_v0_2_execution.py"
RUNNER_PATH = "scripts/train_binance_detailed_history_models_v0_4.py"
BOOTSTRAP_MARKER = "CORE100_V02_BOOTSTRAP"
V02_NAMESPACE = "training/binance_usdm/crypto-core-v0.1/fingerprint-v0.2"
HEADROOM_LIMIT = 8_000_000_000
REPOSITORY = "qookey109-pixel/crypto-autopilot"


class BootstrapBlocked(RuntimeError):
    """Fail-closed condition that must stop before the next side effect."""


def _git_blob_sha(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise BootstrapBlocked(f"{path} must contain a JSON object")
    return value


def _write_report(path: Path, report: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(report))
    print(json.dumps(dict(report), sort_keys=True))


def _base_report(status: str, reason: str, *, event: str) -> dict[str, Any]:
    return {
        "schema": "qookey-core100-training-fingerprint-v0.2-run-report",
        "status": status,
        "reason": reason,
        "event": event,
        "provider_requests_performed": 0,
        "r2_access_performed": False,
        "r2_reads_performed": False,
        "r2_writes_performed": False,
        "training_performed": False,
        "holdout_accessed": False,
    }


def _github_json(url: str, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "crypto-autopilot-core100-v02",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            value = json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise BootstrapBlocked("GitHub authority or run metadata could not be verified") from exc
    if not isinstance(value, dict):
        raise BootstrapBlocked("GitHub API returned an invalid response")
    return value


def _require_live_main() -> str:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise BootstrapBlocked("GitHub-hosted Actions runner required")
    if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY:
        raise BootstrapBlocked("unexpected GitHub repository")
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise BootstrapBlocked("execution must use protected main")
    checkout_sha = os.environ.get("GITHUB_SHA", "")
    if len(checkout_sha) != 40 or any(c not in "0123456789abcdef" for c in checkout_sha):
        raise BootstrapBlocked("invalid checkout commit")
    token = os.environ.get("GH_TOKEN", "")
    if not token:
        raise BootstrapBlocked("ephemeral actions:read token is unavailable")
    main_ref = _github_json(
        "https://api.github.com/repos/" + REPOSITORY + "/git/ref/heads/main", token
    )
    live_sha = main_ref.get("object", {}).get("sha")
    if live_sha != checkout_sha:
        raise BootstrapBlocked("checkout does not match live main")
    return checkout_sha


def _required_implementation_paths(contract: Mapping[str, Any]) -> set[str]:
    identity = contract["identity_contract"]
    paths = set(
        identity["code_paths"]
        + identity["support_paths"]
        + identity["runtime_guard_paths"]
    )
    paths.update(
        {
            WORKFLOW_PATH,
            PARENT_CONTRACT_PATH,
            DATA_CONFIG_PATH,
            DATA_AUTHORITY_PATH,
            AUTHORITY_CONFIG_PATH,
            AUTHORITY_RECEIPT_PATH,
            SUCCESSOR_CONTRACT_PATH,
            IMPLEMENTATION_RECEIPT_PATH,
            COMPARATOR_PATH,
            "src/crypto_autopilot/training/fingerprint_collector_v0_2.py",
            "src/crypto_autopilot/training/fingerprint_v0_2.py",
            RUNNER_PATH,
            "requirements/ci-constraints.txt",
            "pyproject.toml",
        }
    )
    return paths - {IMPLEMENTATION_RECEIPT_PATH}


def _source_inventory(root: Path, paths: set[str]) -> dict[str, str]:
    inventory: dict[str, str] = {}
    root_resolved = root.resolve(strict=True)
    for raw in sorted(paths):
        rel = Path(raw)
        if rel.is_absolute() or ".." in rel.parts:
            raise BootstrapBlocked("unsafe implementation inventory path")
        candidate = root_resolved.joinpath(rel).resolve(strict=True)
        if root_resolved not in candidate.parents or not candidate.is_file():
            raise BootstrapBlocked("implementation inventory file is missing")
        inventory[raw] = _git_blob_sha(candidate.read_bytes())
    return inventory


def _validate_authority_and_implementation(
    *, contract: Mapping[str, Any], contract_sha256: str, root: Path
) -> tuple[dict[str, Any], str]:
    authority = _load_json(ROOT / AUTHORITY_CONFIG_PATH)
    auth_receipt = _load_json(ROOT / AUTHORITY_RECEIPT_PATH)
    implementation = _load_json(ROOT / IMPLEMENTATION_RECEIPT_PATH)
    if (
        authority.get("schema") != AUTHORITY_CONFIG_SCHEMA
        or authority.get("status") != "AUTHORIZED_NOT_ACTIVE"
        or authority.get("user_authorization", {}).get("decision") != "AUTHORIZED"
        or authority.get("authorized_execution", {}).get("one_time_bootstrap") is not True
        or authority.get("authorized_execution", {}).get("trigger_event") != "workflow_dispatch"
        or authority.get("authorized_execution", {}).get("required_input")
        != {"name": "bootstrap_v0_2", "value": "true"}
        or authority.get("proposed_r2_access", {}).get("writes_authorized_by_this_authority") is not True
        or authority.get("proposed_r2_access", {}).get("headroom_gate_bytes") != HEADROOM_LIMIT
    ):
        raise BootstrapBlocked("versioned V0.2 authority config is invalid")
    if (
        auth_receipt.get("schema") != AUTHORITY_RECEIPT_SCHEMA
        or auth_receipt.get("status") != "AUTHORIZED_NOT_ACTIVE"
        or auth_receipt.get("user_authorization", {}).get("decision") != "AUTHORIZED"
        or auth_receipt.get("effects", {}).get("r2_access_performed") is not False
    ):
        raise BootstrapBlocked("versioned V0.2 authority receipt is invalid")
    if (
        implementation.get("schema") != IMPLEMENTATION_RECEIPT_SCHEMA
        or implementation.get("status") != IMPLEMENTATION_STATUS
        or implementation.get("repository") != REPOSITORY
        or implementation.get("successor_contract_sha256") != contract_sha256
        or implementation.get("authority_config_blob_sha") != _git_blob_sha(
            (root / AUTHORITY_CONFIG_PATH).read_bytes()
        )
        or implementation.get("authority_receipt_blob_sha") != _git_blob_sha(
            (root / AUTHORITY_RECEIPT_PATH).read_bytes()
        )
    ):
        raise BootstrapBlocked("implementation receipt does not match authorized V0.2 scope")
    required = _required_implementation_paths(contract)
    if set(implementation.get("source_inventory", {})) != required:
        raise BootstrapBlocked("implementation source inventory is incomplete or expanded")
    actual = _source_inventory(root, required)
    if actual != implementation["source_inventory"]:
        raise BootstrapBlocked("implementation source inventory changed; review required")
    workflow_anchor = contract["execution_context"]["workflow_blob_sha_at_preparation"]
    if actual.get(WORKFLOW_PATH) != workflow_anchor:
        raise BootstrapBlocked("workflow differs from the successor contract anchor")
    implementation_blob = _git_blob_sha((root / IMPLEMENTATION_RECEIPT_PATH).read_bytes())
    return implementation, implementation_blob


def _verify_one_dispatch(*, checkout_sha: str) -> None:
    if os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
        raise BootstrapBlocked("bootstrap requires workflow_dispatch")
    if os.environ.get("INPUT_BOOTSTRAP_V0_2", "").lower() != "true":
        raise BootstrapBlocked("bootstrap input was not explicitly true")
    if os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise BootstrapBlocked("workflow reruns are not authorized")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    try:
        expected_run_id = int(run_id)
    except ValueError as exc:
        raise BootstrapBlocked("invalid workflow run id") from exc
    token = os.environ.get("GH_TOKEN", "")
    query = urllib.parse.urlencode({"event": "workflow_dispatch", "per_page": 100})
    base = (
        "https://api.github.com/repos/"
        + REPOSITORY
        + "/actions/workflows/"
        + urllib.parse.quote(WORKFLOW_FILE, safe="")
        + "/runs?"
        + query
    )
    marker_runs: list[dict[str, Any]] = []
    expected_total: int | None = None
    page = 1
    seen_ids: set[int] = set()
    while page <= 100:
        response = _github_json(base + "&page=" + str(page), token)
        total = response.get("total_count")
        runs = response.get("workflow_runs")
        if not isinstance(total, int) or not isinstance(runs, list):
            raise BootstrapBlocked("Actions run history is incomplete")
        if expected_total is None:
            expected_total = total
        elif total != expected_total:
            raise BootstrapBlocked("Actions run history changed during pagination")
        for run in runs:
            if not isinstance(run, dict) or not isinstance(run.get("id"), int):
                raise BootstrapBlocked("Actions run history contains an invalid row")
            if run["id"] in seen_ids:
                raise BootstrapBlocked("Actions run history contains duplicate rows")
            seen_ids.add(run["id"])
            if str(run.get("display_title", "")).startswith(BOOTSTRAP_MARKER):
                marker_runs.append(run)
        if len(runs) < 100:
            break
        page += 1
    else:
        raise BootstrapBlocked("Actions run history exceeded the safe pagination limit")
    if expected_total is None or len(seen_ids) != expected_total:
        raise BootstrapBlocked("Actions run history pagination did not cover every dispatch")
    current = [run for run in marker_runs if run["id"] == expected_run_id]
    if (
        len(marker_runs) != 1
        or len(current) != 1
        or current[0].get("head_sha") != checkout_sha
        or current[0].get("head_branch") != "main"
        or current[0].get("run_attempt") != 1
    ):
        raise BootstrapBlocked("one-time dispatch is missing, duplicated, or stale")


def _collect_git_blobs(
    *, contract: Mapping[str, Any], root: Path, checkout_sha: str
) -> dict[str, str]:
    paths = set(
        contract["identity_contract"]["code_paths"]
        + contract["identity_contract"]["support_paths"]
        + contract["identity_contract"]["runtime_guard_paths"]
    )
    paths.update(
        {
            contract["execution_context"]["workflow_path"],
            contract["execution_context"]["current_training_authority_receipt_path"],
        }
    )
    inventory = _source_inventory(root, paths)
    return inventory


def _load_v02_latest(store) -> tuple[str, dict[str, Any] | None, dict[str, Any] | None]:
    key = V02_NAMESPACE + "/latest.json"
    payload = store.get_bytes_if_exists(key)
    if payload is None:
        return key, None, None
    latest = json.loads(payload)
    if (
        not isinstance(latest, dict)
        or latest.get("schema") != "binance-usdm-core100-fingerprint-v0.2-latest-v0.1"
        or latest.get("namespace") != V02_NAMESPACE
        or not isinstance(latest.get("run_id"), str)
        or not latest["run_id"].startswith("github-")
        or not latest["run_id"].endswith("-1")
        or runner.SAFE_RUN_ID.fullmatch(latest["run_id"]) is None
        or latest.get("manifest_key") != f"{V02_NAMESPACE}/runs/run={latest.get('run_id')}/manifest.json"
        or not isinstance(latest.get("manifest_sha256"), str)
    ):
        raise BootstrapBlocked("V0.2 latest pointer is malformed")
    manifest_payload = store.get_bytes_verified(
        latest["manifest_key"], expected_sha256=latest["manifest_sha256"]
    )
    manifest = json.loads(manifest_payload)
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema") != "binance-usdm-core100-fingerprint-v0.2-manifest-v0.1"
        or manifest.get("status") != "PASS"
        or manifest.get("run_id") != latest.get("run_id")
        or manifest.get("namespace") != V02_NAMESPACE
        or not isinstance(manifest.get("training_fingerprint_v0_2"), dict)
    ):
        raise BootstrapBlocked("V0.2 latest manifest is malformed")
    evidence = manifest["training_fingerprint_v0_2"]
    objects = manifest.get("objects")
    if (
        manifest.get("provider") != "binance_usdm"
        or latest.get("provider") != "binance_usdm"
        or not isinstance(objects, list)
        or len(objects) != 2
        or {item.get("role") for item in objects if isinstance(item, dict)}
        != {"model", "metrics"}
        or manifest.get("dataset_fingerprint") != latest.get("dataset_fingerprint")
        or manifest.get("experiment_fingerprint") != latest.get("experiment_fingerprint")
        or manifest.get("implementation_receipt_git_blob_sha")
        != latest.get("implementation_receipt_git_blob_sha")
        or evidence.get("dataset_fingerprint") != latest.get("dataset_fingerprint")
        or evidence.get("experiment_fingerprint") != latest.get("experiment_fingerprint")
        or evidence.get("runtime_guard_fingerprint") != manifest.get("runtime_guard_fingerprint")
    ):
        raise BootstrapBlocked("V0.2 latest pointer and manifest disagree")
    by_role = {item["role"]: item for item in objects}
    for role in ("model", "metrics"):
        if (
            by_role[role].get("key") != latest.get(role + "_key")
            or by_role[role].get("sha256") != latest.get(role + "_sha256")
        ):
            raise BootstrapBlocked("V0.2 output binding is inconsistent")
    return key, latest, manifest


def _current_fingerprint(
    *, contract: Mapping[str, Any], dataset_fingerprint: str, root: Path, checkout_sha: str,
) -> dict[str, Any]:
    blobs = _collect_git_blobs(contract=contract, root=root, checkout_sha=checkout_sha)
    if blobs.get(WORKFLOW_PATH) != contract["execution_context"]["workflow_blob_sha_at_preparation"]:
        raise BootstrapBlocked("active workflow differs from the prepared successor anchor")
    runtime = collector.collect_runtime_manifest()
    return build_fingerprint(
        contract=contract,
        dataset_fingerprint=dataset_fingerprint,
        git_blobs=blobs,
        runtime_manifest=runtime,
    )


def _dataset_is_exact(catalog: Mapping[str, Any], state: Mapping[str, Any]) -> bool:
    return (
        state.get("status") == "COMPLETE"
        and state.get("shard_count") == 10
        and state.get("total_partition_objects") == 14274
        and state.get("holdout_accessed") is False
        and isinstance(catalog.get("markets"), list)
        and len(catalog["markets"]) == 100
        and catalog.get("selected_market_count") == 100
    )


def _publish_baseline(
    store, *, report: dict[str, Any], model: dict[str, Any], metrics: dict[str, Any],
    dataset_fingerprint: str, fingerprint: dict[str, Any], implementation_blob_sha: str,
    run_id: str, generated_at: str,
) -> dict[str, Any]:
    namespace = V02_NAMESPACE
    run_prefix = f"{namespace}/runs/run={run_id}"
    model_payload = runner.canonical_json_bytes(model)
    metrics_payload = runner.canonical_json_bytes(metrics)
    manifest = {
        "schema": "binance-usdm-core100-fingerprint-v0.2-manifest-v0.1",
        "status": "PASS",
        "provider": "binance_usdm",
        "namespace": namespace,
        "run_id": run_id,
        "generated_at_utc": generated_at,
        "dataset_fingerprint": dataset_fingerprint,
        "experiment_fingerprint": fingerprint["experiment_fingerprint"],
        "runtime_guard_fingerprint": fingerprint["runtime_guard_fingerprint"],
        "training_fingerprint_v0_2": fingerprint,
        "implementation_receipt_git_blob_sha": implementation_blob_sha,
        "model_quality_gate": metrics["model_quality_gate"],
        "objects": [
            {"role": "model", "key": f"{run_prefix}/model.json", "bytes": len(model_payload),
             "sha256": runner.sha256_bytes(model_payload)},
            {"role": "metrics", "key": f"{run_prefix}/metrics.json", "bytes": len(metrics_payload),
             "sha256": runner.sha256_bytes(metrics_payload)},
        ],
        "authority": model["authority"],
    }
    manifest_payload = runner.canonical_json_bytes(manifest)
    latest = {
        "schema": "binance-usdm-core100-fingerprint-v0.2-latest-v0.1",
        "namespace": namespace,
        "provider": "binance_usdm",
        "run_id": run_id,
        "generated_at_utc": generated_at,
        "dataset_fingerprint": dataset_fingerprint,
        "experiment_fingerprint": fingerprint["experiment_fingerprint"],
        "manifest_key": f"{run_prefix}/manifest.json",
        "manifest_sha256": runner.sha256_bytes(manifest_payload),
        "model_key": f"{run_prefix}/model.json",
        "model_sha256": runner.sha256_bytes(model_payload),
        "metrics_key": f"{run_prefix}/metrics.json",
        "metrics_sha256": runner.sha256_bytes(metrics_payload),
        "implementation_receipt_git_blob_sha": implementation_blob_sha,
    }
    latest_payload = runner.canonical_json_bytes(latest)
    current_bytes = runner.current_bucket_bytes(store)
    planned_bytes = len(model_payload) + len(metrics_payload) + len(manifest_payload) + len(latest_payload)
    if current_bytes >= HEADROOM_LIMIT or current_bytes + planned_bytes >= HEADROOM_LIMIT:
        raise BootstrapBlocked("FREE-ONLY R2 headroom gate blocked before write")
    records = []
    for key, payload, role in (
        (f"{run_prefix}/model.json", model_payload, "model"),
        (f"{run_prefix}/metrics.json", metrics_payload, "metrics"),
        (f"{run_prefix}/manifest.json", manifest_payload, "manifest"),
    ):
        report["r2_write_attempted"] = True
        report["r2_writes_performed"] = "UNKNOWN_AFTER_WRITE_ATTEMPT"
        records.append(runner.put_immutable(store, key=key, payload=payload, role=role))
        report["r2_writes_performed"] = True
        report["written_objects"] = records.copy()
    latest_key = namespace + "/latest.json"
    report["pointer_write_attempted"] = True
    pointer_receipt = store.put_bytes(
        latest_key, latest_payload, content_type="application/json",
        metadata={"provider": "binance_usdm", "role": "training-latest", "version": "v0.2"},
    )
    restored = store.get_bytes_verified(latest_key, expected_sha256=pointer_receipt.sha256)
    if restored != latest_payload:
        raise BootstrapBlocked("V0.2 latest pointer SHA-256 readback mismatch")
    return {
        "status": "PASS",
        "stage": "CORE100_FINGERPRINT_V0_2_BASELINE_PUBLISHED",
        "r2_writes_performed": True,
        "training_performed": True,
        "latest_pointer_written_last": True,
        "objects": records,
        "model_quality_gate": metrics["model_quality_gate"],
    }


def _run(args: argparse.Namespace, report: dict[str, Any]) -> tuple[dict[str, Any], int]:
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    checkout_sha = _require_live_main()
    config_bytes = Path(args.fingerprint_contract).read_bytes()
    parent_bytes = Path(PARENT_CONTRACT_PATH).read_bytes()
    if args.bootstrap_authority != Path(AUTHORITY_CONFIG_PATH):
        raise BootstrapBlocked("unexpected bootstrap authority path")
    if args.implementation_receipt != Path(IMPLEMENTATION_RECEIPT_PATH):
        raise BootstrapBlocked("unexpected implementation receipt path")
    implementation = _load_json(args.implementation_receipt)
    expected_contract_sha = implementation.get("successor_contract_sha256")
    if not isinstance(expected_contract_sha, str):
        raise BootstrapBlocked("implementation receipt lacks successor contract SHA")
    contract = validate_successor_contract(
        contract_bytes=config_bytes, expected_sha256=expected_contract_sha,
        parent_contract_bytes=parent_bytes,
    )
    implementation, implementation_blob_sha = _validate_authority_and_implementation(
        contract=contract, contract_sha256=expected_contract_sha, root=ROOT
    )
    if event == "workflow_dispatch":
        if os.environ.get("INPUT_BOOTSTRAP_V0_2", "").lower() != "true":
            report["reason"] = "MANUAL_DISPATCH_WITHOUT_BOOTSTRAP_INPUT"
            return report, 0
        _verify_one_dispatch(checkout_sha=checkout_sha)
        operation = "training"
    elif event == "schedule":
        operation = "training"
    else:
        return report, 0

    data_config, _data_authority, _raw = runner.load_authority_pair(
        Path(args.config), Path(args.authority)
    )
    observed = datetime.now(UTC)
    runner.require_execution_window(data_config, observed_at=observed, operation=operation)
    store = runner.create_store()
    report.update({
        "r2_access_performed": True,
        "r2_reads_performed": True,
        "provider_requests_performed": 0,
        "source_main_sha": checkout_sha,
        "implementation_receipt_git_blob_sha": implementation_blob_sha,
    })
    initial_bytes = runner.current_bucket_bytes(store)
    if initial_bytes >= HEADROOM_LIMIT:
        report.update({"status": "REVIEW_REQUIRED", "reason": "FREE_ONLY_HEADROOM_HARD_STOP"})
        return report, 2

    latest_key, latest, manifest = _load_v02_latest(store)
    bootstrap = event == "workflow_dispatch"
    if bootstrap and latest is not None:
        report.update({
            "status": "REVIEW_REQUIRED",
            "reason": "V0_2_BASELINE_ALREADY_EXISTS",
            "previous_training_run_id": latest.get("run_id"),
            "latest_pointer_key": latest_key,
        })
        return report, 2
    if not bootstrap and latest is None:
        report.update({
            "status": "REVIEW_REQUIRED",
            "reason": "V0_2_BASELINE_NOT_ESTABLISHED",
            "latest_pointer_key": latest_key,
        })
        return report, 2

    catalog, state, object_records, dataset_fingerprint = runner.load_dataset_index(
        store, data_config
    )
    if not _dataset_is_exact(catalog, state):
        report.update({
            "status": "REVIEW_REQUIRED",
            "reason": "DATASET_SCOPE_OR_COMPLETENESS_MISMATCH",
            "dataset_fingerprint": dataset_fingerprint,
        })
        return report, 2
    current = _current_fingerprint(
        contract=contract, dataset_fingerprint=dataset_fingerprint,
        root=ROOT, checkout_sha=checkout_sha,
    )
    generated_at = observed.isoformat().replace("+00:00", "Z")
    report.update({
        "dataset_fingerprint": dataset_fingerprint,
        "experiment_fingerprint": current["experiment_fingerprint"],
        "runtime_guard_fingerprint": current["runtime_guard_fingerprint"],
        "dataset_rows": state.get("total_rows"),
        "dataset_partition_objects": state.get("total_partition_objects"),
    })

    if not bootstrap:
        assert manifest is not None and latest is not None
        if manifest.get("implementation_receipt_git_blob_sha") != implementation_blob_sha:
            report.update({"status": "REVIEW_REQUIRED", "reason": "IMPLEMENTATION_RECEIPT_CHANGED"})
            return report, 2
        decision = compare_fingerprints(
            contract=contract, current=current, previous=manifest["training_fingerprint_v0_2"]
        )
        report.update({
            "status": decision["status"],
            "reason": decision["reason"],
            "previous_training_run_id": latest.get("run_id"),
            "latest_pointer_key": latest_key,
            "training_performed": False,
            "r2_writes_performed": False,
        })
        return report, 0 if decision["status"] == "NO_CHANGE" else 2

    examples = training_v02.build_examples_from_r2(
        store, catalog=catalog, object_records=object_records, config=data_config
    )
    model, metrics = runner.run_intraday_training(
        examples, config=data_config, dataset_fingerprint=dataset_fingerprint,
        generated_at_utc=generated_at,
    )
    published = _publish_baseline(
        store, report=report, model=model, metrics=metrics,
        dataset_fingerprint=dataset_fingerprint, fingerprint=current,
        implementation_blob_sha=implementation_blob_sha, run_id=args.run_id,
        generated_at=generated_at,
    )
    report.update(published)
    report.update({
        "reason": "ONE_TIME_AUTHORIZED_BASELINE",
        "r2_reads_performed": True,
        "r2_writes_performed": True,
        "training_performed": True,
        "provider_requests_performed": 0,
        "dataset_fingerprint": dataset_fingerprint,
        "experiment_fingerprint": current["experiment_fingerprint"],
        "dataset_rows": state.get("total_rows"),
        "dataset_partition_objects": state.get("total_partition_objects"),
        "model_quality_gate": metrics["model_quality_gate"],
        "authority": model["authority"],
    })
    return report, 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--authority", required=True, type=Path)
    parser.add_argument("--fingerprint-contract", required=True, type=Path)
    parser.add_argument("--bootstrap-authority", required=True, type=Path)
    parser.add_argument("--implementation-receipt", required=True, type=Path)
    parser.add_argument("--run-id", default=os.getenv("GITHUB_RUN_ID", ""))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = require_ephemeral_output(args.output)
    if not runner.SAFE_RUN_ID.fullmatch(args.run_id):
        raise BootstrapBlocked("run id is not a safe object-key component")
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise BootstrapBlocked("local execution is excluded")
    report = _base_report("SKIPPED", "UNSUPPORTED_OR_NON_EXECUTION_EVENT", event=os.environ.get("GITHUB_EVENT_NAME", ""))
    try:
        report, exit_code = _run(args, report)
    except (BootstrapBlocked, DetailedHistoryAuthorityError, SuccessorContractError) as exc:
        report.update({"status": "REVIEW_REQUIRED", "reason": str(exc)})
        exit_code = 2
    except Exception:
        report.update({"status": "REVIEW_REQUIRED", "reason": "UNEXPECTED_EXECUTION_FAILURE"})
        exit_code = 2
    _write_report(output, report)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
