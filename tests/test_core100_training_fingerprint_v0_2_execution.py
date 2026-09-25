from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from crypto_autopilot.training.fingerprint_v0_2_execution import (
    SuccessorContractError,
    build_fingerprint,
    compare_fingerprints,
    validate_successor_contract,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config/core100_training_fingerprint_v0_2_successor_v0_1.json"
PARENT_PATH = ROOT / "config/core100_training_fingerprint_v0_2.json"
RECEIPT_PATH = ROOT / "research/receipts/2026-09-25-core100-training-fingerprint-v0-2-implementation.json"
SCRIPT_PATH = ROOT / "scripts/train_binance_detailed_history_models_v0_4.py"
spec = importlib.util.spec_from_file_location("core100_v02_execution_under_test", SCRIPT_PATH)
assert spec is not None and spec.loader is not None
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)


def contract():
    receipt = json.loads(RECEIPT_PATH.read_text())
    return validate_successor_contract(
        contract_bytes=CONTRACT_PATH.read_bytes(),
        expected_sha256=receipt["successor_contract_sha256"],
        parent_contract_bytes=PARENT_PATH.read_bytes(),
    )


def runtime():
    return {
        "implementation": "cpython",
        "version": "3.13.15 (synthetic test)",
        "cache_tag": "cpython-313",
        "platform": "linux-x86_64",
        "system": "Linux",
        "release": "6.11.0-test",
        "machine": "x86_64",
        "libc": ["glibc", "2.39"],
        "distributions": [
            {"name": "qookey-crypto-autopilot", "version": "0.1.0"},
            {"name": "pip", "version": "25.2"},
            {"name": "setuptools", "version": "80.9.0"},
        ],
        "install_tools": [
            {"name": "pip", "version": "25.2"},
            {"name": "setuptools", "version": "80.9.0"},
        ],
        "project_version": "0.1.0",
        "runner_image": {"os": "ubuntu24", "version": "synthetic"},
        "isolated_environment": True,
        "distribution_inventory_complete": True,
        "install_tools_complete": True,
    }


def test_successor_pins_unchanged_parent_and_every_executable_blob():
    current = contract()
    parent = json.loads(PARENT_PATH.read_text())
    receipt = json.loads(RECEIPT_PATH.read_text())
    assert current["identity_contract"] == parent["identity_contract"]
    assert set(receipt["source_inventory"]) == script._required_implementation_paths(current)
    assert receipt["source_inventory"] == script._source_inventory(
        ROOT, script._required_implementation_paths(current)
    )
    assert script._git_blob_sha(b"") == hashlib.sha1(b"blob 0\\0").hexdigest()
    implementation, blob_sha = script._validate_authority_and_implementation(
        contract=current,
        contract_sha256=receipt["successor_contract_sha256"],
        root=ROOT,
    )
    assert implementation == receipt
    assert blob_sha == script._git_blob_sha(RECEIPT_PATH.read_bytes())


def test_successor_rejects_modified_identity():
    original = json.loads(CONTRACT_PATH.read_text())
    original["identity_contract"]["code_paths"].pop()
    candidate = json.dumps(original).encode()
    with pytest.raises(SuccessorContractError):
        validate_successor_contract(
            contract_bytes=candidate,
            expected_sha256=hashlib.sha256(candidate).hexdigest(),
            parent_contract_bytes=PARENT_PATH.read_bytes(),
        )


def test_evidence_only_reuses_exact_dataset_source_and_runtime():
    current_contract = contract()
    identity = current_contract["identity_contract"]
    paths = set(identity["code_paths"] + identity["support_paths"] + identity["runtime_guard_paths"])
    paths |= {
        current_contract["execution_context"]["workflow_path"],
        current_contract["execution_context"]["current_training_authority_receipt_path"],
    }
    blobs = {path: "a" * 40 for path in paths}
    blobs[current_contract["execution_context"]["workflow_path"]] = current_contract[
        "execution_context"
    ]["workflow_blob_sha_at_preparation"]
    current = build_fingerprint(
        contract=current_contract, dataset_fingerprint="d" * 64,
        git_blobs=blobs, runtime_manifest=runtime(),
    )
    assert compare_fingerprints(
        contract=current_contract, current=current, previous=current
    )["status"] == "NO_CHANGE"
    prior = copy.deepcopy(current)
    prior["git_blobs"]["src/crypto_autopilot/features/advanced.py"] = "b" * 40
    assert compare_fingerprints(
        contract=current_contract, current=current, previous=prior
    )["status"] == "REVIEW_REQUIRED"
    bad = copy.deepcopy(current)
    bad["experiment_fingerprint"] = "0" * 64
    assert compare_fingerprints(
        contract=current_contract, current=current, previous=bad
    ) == {"status": "REVIEW_REQUIRED", "reason": "INVALID_V0_2_EVIDENCE"}


def test_dispatch_consumption_rejects_duplicate_and_rerun():
    row = {
        "id": 17, "display_title": "CORE100_V02_BOOTSTRAP 1",
        "head_sha": "a" * 40, "head_branch": "main", "run_attempt": 1,
    }
    env = {
        "GITHUB_EVENT_NAME": "workflow_dispatch",
        "INPUT_BOOTSTRAP_V0_2": "true",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_RUN_ID": "17",
        "GH_TOKEN": "synthetic",
    }
    with patch.dict(os.environ, env), patch.object(script, "_github_json", return_value={
        "total_count": 1, "workflow_runs": [row],
    }):
        script._verify_one_dispatch(checkout_sha="a" * 40)
    with patch.dict(os.environ, env), patch.object(script, "_github_json", return_value={
        "total_count": 2, "workflow_runs": [row, {**row, "id": 18}],
    }):
        with pytest.raises(script.BootstrapBlocked):
            script._verify_one_dispatch(checkout_sha="a" * 40)
    with patch.dict(os.environ, {**env, "GITHUB_RUN_ATTEMPT": "2"}):
        with pytest.raises(script.BootstrapBlocked):
            script._verify_one_dispatch(checkout_sha="a" * 40)


def test_failed_pointer_publish_keeps_partial_write_evidence():
    class Store:
        def put_bytes(self, *args, **kwargs):
            raise RuntimeError("synthetic pointer write failure")

    report = script._base_report("SKIPPED", "SYNTHETIC", event="workflow_dispatch")
    with patch.object(script.runner, "current_bucket_bytes", return_value=0), patch.object(
        script.runner, "put_immutable", return_value={"action": "created"}
    ):
        with pytest.raises(RuntimeError):
            script._publish_baseline(
                Store(), report=report, model={"authority": {}},
                metrics={"model_quality_gate": {"status": "REJECT"}},
                dataset_fingerprint="d" * 64,
                fingerprint={"experiment_fingerprint": "e" * 64,
                             "runtime_guard_fingerprint": "g" * 64},
                implementation_blob_sha="a" * 40, run_id="github-17-1",
                generated_at="2026-09-25T00:00:00Z",
            )
    assert report["r2_writes_performed"] is True
    assert len(report["written_objects"]) == 3
    assert report["pointer_write_attempted"] is True
