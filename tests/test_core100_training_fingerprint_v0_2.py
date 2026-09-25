from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from crypto_autopilot.training.fingerprint_v0_2 import (
    FingerprintValidationError,
    build_fingerprint,
    compare_prepared_fingerprints,
    normalize_runtime_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_BYTES = (ROOT / "config/core100_training_fingerprint_v0_2.json").read_bytes()
CONTRACT = json.loads(CONTRACT_BYTES)
DATASET = "d" * 64


def runtime_fixture() -> dict[str, object]:
    return {
        "implementation": "cpython",
        "version": "3.13.15 (main, Sep 23 2026, 00:00:00) [GCC 13.3.0]",
        "cache_tag": "cpython-313",
        "platform": "linux-x86_64",
        "system": "Linux",
        "release": "6.11.0-test",
        "machine": "x86_64",
        "libc": ["glibc", "2.39"],
        "distributions": [
            {"name": "PyArrow", "version": "21.0.0"},
            {"name": "qookey_crypto.autopilot", "version": "0.1.0"},
            {"name": "pip", "version": "25.2"},
        ],
        "install_tools": [
            {"name": "Setuptools", "version": "80.9.0"},
            {"name": "PIP", "version": "25.2"},
        ],
        "project_version": "0.1.0",
        "runner_image": {"os": "ubuntu24", "version": "20260920.1.0"},
        "isolated_environment": True,
        "distribution_inventory_complete": True,
        "install_tools_complete": True,
    }


def blob_fixture() -> dict[str, str]:
    inventory = CONTRACT["source_inventory"]
    paths = inventory["static_import_closure_paths"] + inventory["identity_support_paths"]
    blobs = {path: "a" * 40 for path in paths}
    context = CONTRACT["execution_context"]
    blobs[context["workflow_path"]] = context["workflow_blob_sha_at_preparation"]
    blobs[context["current_training_authority_receipt_path"]] = context[
        "authority_receipt_blob_sha_at_preparation"
    ]
    return blobs


def evidence_fixture(**changes: object) -> dict[str, object]:
    inputs = {
        "contract_bytes": CONTRACT_BYTES,
        "dataset_fingerprint": DATASET,
        "git_blobs": blob_fixture(),
        "runtime_manifest": runtime_fixture(),
    }
    inputs.update(changes)
    return build_fingerprint(**inputs)


class Core100FingerprintV02Tests(unittest.TestCase):
    def assert_prepared_decision(self, result: dict[str, object], status: str) -> None:
        self.assertEqual(result["status"], status)
        self.assertEqual(result["mode"], "PREPARATION_ONLY")
        self.assertIs(result["execution_authorized"], False)
        self.assertIs(result["training_performed"], False)
        self.assertIs(result["r2_access_performed"], False)
        self.assertEqual(result["provider_requests_performed"], 0)

    def compare(self, current: dict[str, object], previous: object) -> dict[str, object]:
        return compare_prepared_fingerprints(
            contract_bytes=CONTRACT_BYTES, current=current, previous=previous
        )

    def test_exact_evidence_is_bound_to_contract_and_remains_preparation_only(self) -> None:
        evidence = evidence_fixture()
        self.assertEqual(evidence["schema"], "qookey-core100-training-prepared-evidence-v0.2")
        self.assertEqual(evidence["status"], "PREPARED_NOT_ACTIVE")
        self.assertEqual(evidence["contract_sha256"], hashlib.sha256(CONTRACT_BYTES).hexdigest())
        self.assertEqual(len(evidence["git_blobs"]), 36)
        self.assert_prepared_decision(self.compare(evidence, copy.deepcopy(evidence)), "NO_CHANGE")

    def test_runtime_normalization_and_input_order_are_deterministic(self) -> None:
        runtime = runtime_fixture()
        reordered = copy.deepcopy(runtime)
        reordered["distributions"] = list(reversed(reordered["distributions"]))
        reordered["install_tools"] = list(reversed(reordered["install_tools"]))
        reordered["distributions"][1]["name"] = "QOOKEY---CRYPTO_AUTOPILOT"
        self.assertEqual(normalize_runtime_manifest(runtime), normalize_runtime_manifest(reordered))
        normalized = normalize_runtime_manifest(runtime)
        self.assertEqual(
            [row["name"] for row in normalized["distributions"]],
            ["pip", "pyarrow", "qookey-crypto-autopilot"],
        )
        original = evidence_fixture(runtime_manifest=runtime)
        shuffled = evidence_fixture(
            runtime_manifest=reordered,
            git_blobs=dict(reversed(list(blob_fixture().items()))),
        )
        self.assertEqual(original, shuffled)
        self.assert_prepared_decision(self.compare(original, shuffled), "NO_CHANGE")

    def test_build_copies_inputs_and_allows_explicit_unavailable_runner_metadata(self) -> None:
        runtime = runtime_fixture()
        runtime["runner_image"] = None
        blobs = blob_fixture()
        evidence = evidence_fixture(runtime_manifest=runtime, git_blobs=blobs)
        saved = copy.deepcopy(evidence)
        runtime["distributions"][0]["version"] = "99.0.0"
        blobs[next(iter(blobs))] = "f" * 40
        self.assertEqual(evidence, saved)
        self.assert_prepared_decision(self.compare(evidence, saved), "NO_CHANGE")

    def test_every_result_code_and_support_path_changes_identity(self) -> None:
        original = evidence_fixture()
        paths = CONTRACT["identity_contract"]["code_paths"] + CONTRACT["identity_contract"][
            "support_paths"
        ]
        for path in paths:
            with self.subTest(path=path):
                blobs = blob_fixture()
                blobs[path] = "b" * 40
                changed = evidence_fixture(git_blobs=blobs)
                self.assertNotEqual(changed["experiment_fingerprint"], original["experiment_fingerprint"])
                self.assertEqual(changed["runtime_guard_fingerprint"], original["runtime_guard_fingerprint"])
                self.assert_prepared_decision(self.compare(changed, original), "REVIEW_REQUIRED")

    def test_every_guard_path_requires_review_without_changing_result_identity(self) -> None:
        original = evidence_fixture()
        for path in CONTRACT["identity_contract"]["runtime_guard_paths"]:
            with self.subTest(path=path):
                blobs = blob_fixture()
                blobs[path] = "b" * 40
                changed = evidence_fixture(git_blobs=blobs)
                self.assertEqual(changed["experiment_fingerprint"], original["experiment_fingerprint"])
                self.assertNotEqual(changed["runtime_guard_fingerprint"], original["runtime_guard_fingerprint"])
                self.assert_prepared_decision(self.compare(changed, original), "REVIEW_REQUIRED")

    def test_dataset_and_exact_runtime_changes_require_review(self) -> None:
        original = evidence_fixture()
        changed_dataset = evidence_fixture(dataset_fingerprint="e" * 64)
        self.assertNotEqual(changed_dataset["experiment_fingerprint"], original["experiment_fingerprint"])
        self.assert_prepared_decision(self.compare(changed_dataset, original), "REVIEW_REQUIRED")
        mutations = {
            "version": "3.13.16 (main, Sep 24 2026, 00:00:00) [GCC 13.3.0]",
            "release": "6.12.0-test",
            "libc": ["glibc", "2.40"],
            "runner_image": {"os": "ubuntu24", "version": "20260924.1.0"},
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                runtime = runtime_fixture()
                runtime[field] = value
                changed = evidence_fixture(runtime_manifest=runtime)
                self.assertNotEqual(changed["experiment_fingerprint"], original["experiment_fingerprint"])
                self.assert_prepared_decision(self.compare(changed, original), "REVIEW_REQUIRED")
        runtime = runtime_fixture()
        runtime["distributions"][0]["version"] = "21.0.1"
        changed = evidence_fixture(runtime_manifest=runtime)
        self.assertNotEqual(changed["experiment_fingerprint"], original["experiment_fingerprint"])
        self.assert_prepared_decision(self.compare(changed, original), "REVIEW_REQUIRED")

    def test_context_changes_require_review_even_when_both_records_agree(self) -> None:
        original = evidence_fixture()
        context = CONTRACT["execution_context"]
        for path in (context["workflow_path"], context["current_training_authority_receipt_path"]):
            with self.subTest(path=path):
                blobs = blob_fixture()
                blobs[path] = "b" * 40
                changed = evidence_fixture(git_blobs=blobs)
                self.assertEqual(changed["experiment_fingerprint"], original["experiment_fingerprint"])
                self.assertEqual(changed["runtime_guard_fingerprint"], original["runtime_guard_fingerprint"])
                self.assert_prepared_decision(self.compare(changed, original), "REVIEW_REQUIRED")
                self.assert_prepared_decision(self.compare(changed, changed), "REVIEW_REQUIRED")
                changed_dataset = evidence_fixture(git_blobs=blobs, dataset_fingerprint="e" * 64)
                self.assert_prepared_decision(self.compare(changed_dataset, original), "REVIEW_REQUIRED")

    def test_runtime_missing_unknown_or_incomplete_fields_are_rejected(self) -> None:
        for field in runtime_fixture():
            with self.subTest(missing=field):
                runtime = runtime_fixture()
                del runtime[field]
                with self.assertRaises(FingerprintValidationError):
                    normalize_runtime_manifest(runtime)
        cases = [
            ("extra", "unknown"),
            ("version", "3.13"),
            ("version", "unknown"),
            ("libc", ["glibc", ""]),
            ("libc", "glibc 2.39"),
            ("runner_image", {}),
            ("runner_image", {"os": "ubuntu24", "version": ""}),
            ("runner_image", {"os": "ubuntu24", "version": "1", "extra": "x"}),
            ("project_version", "0.2.0"),
        ]
        for field in ("implementation", "cache_tag", "platform", "system", "release", "machine"):
            cases.extend([(field, ""), (field, None), (field, True)])
        for field in ("isolated_environment", "distribution_inventory_complete", "install_tools_complete"):
            cases.extend([(field, False), (field, 1), (field, "true")])
        for field, value in cases:
            with self.subTest(field=field, value=value):
                runtime = runtime_fixture()
                runtime[field] = value
                with self.assertRaises(FingerprintValidationError):
                    normalize_runtime_manifest(runtime)

    def test_distribution_inventory_and_install_tool_consistency_fail_closed(self) -> None:
        for field in ("distributions", "install_tools"):
            for value in ([], {}, ["pip==25.2"], [{"name": "pip", "version": ""}]):
                with self.subTest(field=field, value=value):
                    runtime = runtime_fixture()
                    runtime[field] = value
                    with self.assertRaises(FingerprintValidationError):
                        normalize_runtime_manifest(runtime)
            for version in ("25.2", "25.3"):
                with self.subTest(duplicate=field, version=version):
                    runtime = runtime_fixture()
                    runtime[field].append({"name": "PiP", "version": version})
                    with self.assertRaises(FingerprintValidationError):
                        normalize_runtime_manifest(runtime)
        for name in ("pip", "qookey_crypto.autopilot"):
            with self.subTest(missing_distribution=name):
                runtime = runtime_fixture()
                runtime["distributions"] = [row for row in runtime["distributions"] if row["name"] != name]
                with self.assertRaises(FingerprintValidationError):
                    normalize_runtime_manifest(runtime)
        for name in ("PIP", "Setuptools"):
            with self.subTest(missing_tool=name):
                runtime = runtime_fixture()
                runtime["install_tools"] = [row for row in runtime["install_tools"] if row["name"] != name]
                with self.assertRaises(FingerprintValidationError):
                    normalize_runtime_manifest(runtime)
        runtime = runtime_fixture()
        runtime["install_tools"][1]["version"] = "25.3"
        with self.assertRaises(FingerprintValidationError):
            normalize_runtime_manifest(runtime)
        runtime = runtime_fixture()
        runtime["distributions"].append({"name": "setuptools", "version": "79.0.0"})
        with self.assertRaises(FingerprintValidationError):
            normalize_runtime_manifest(runtime)

    def test_invalid_dataset_blob_inventory_or_contract_is_rejected(self) -> None:
        for dataset in ("D" * 64, "a" * 63, "g" * 64, "", None):
            with self.subTest(dataset=dataset):
                with self.assertRaises(FingerprintValidationError):
                    evidence_fixture(dataset_fingerprint=dataset)
        path = next(iter(blob_fixture()))
        cases = []
        missing = blob_fixture()
        del missing[path]
        cases.append(missing)
        extra = blob_fixture()
        extra["src/crypto_autopilot/unknown_dynamic_import.py"] = "a" * 40
        cases.append(extra)
        for value in ("A" * 40, "a" * 39, "g" * 40, None):
            changed = blob_fixture()
            changed[path] = value
            cases.append(changed)
        for blobs in cases:
            with self.subTest(blobs=blobs):
                with self.assertRaises(FingerprintValidationError):
                    evidence_fixture(git_blobs=blobs)
        for contract in (b"{}", b"not json", CONTRACT_BYTES + b"\n"):
            with self.subTest(contract_sha=hashlib.sha256(contract).hexdigest()):
                with self.assertRaises(FingerprintValidationError):
                    evidence_fixture(contract_bytes=contract)

    def test_legacy_absent_or_tampered_evidence_requires_review(self) -> None:
        current = evidence_fixture()
        legacy_pointer = {
            "schema": "binance-usdm-intraday-research-training-latest-v0.2",
            "dataset_fingerprint": DATASET,
            "experiment_fingerprint": current["experiment_fingerprint"],
            "run_id": "github-34918219864-1",
        }
        for previous in (None, {}, legacy_pointer):
            with self.subTest(previous=previous):
                self.assert_prepared_decision(self.compare(current, previous), "REVIEW_REQUIRED")
        edits = [
            ("schema", "qookey-core100-training-prepared-evidence-v0.1"),
            ("status", "ACTIVE"),
            ("contract_sha256", "f" * 64),
            ("dataset_fingerprint", "e" * 64),
            ("experiment_fingerprint", "f" * 64),
            ("runtime_guard_fingerprint", "f" * 64),
            ("unknown", "unbound input"),
        ]
        for field, value in edits:
            with self.subTest(field=field):
                tampered = copy.deepcopy(current)
                tampered[field] = value
                self.assert_prepared_decision(self.compare(current, tampered), "REVIEW_REQUIRED")
                self.assert_prepared_decision(self.compare(tampered, current), "REVIEW_REQUIRED")
        for field in current:
            with self.subTest(missing=field):
                incomplete = copy.deepcopy(current)
                del incomplete[field]
                self.assert_prepared_decision(self.compare(current, incomplete), "REVIEW_REQUIRED")
        tampered = copy.deepcopy(current)
        tampered["git_blobs"][next(iter(tampered["git_blobs"]))] = "b" * 40
        self.assert_prepared_decision(self.compare(current, tampered), "REVIEW_REQUIRED")
        tampered = copy.deepcopy(current)
        tampered["runtime_manifest"]["version"] = "3.13.16 changed"
        self.assert_prepared_decision(self.compare(current, tampered), "REVIEW_REQUIRED")

    def test_fresh_interpreter_needs_no_external_packages_or_execution_clients(self) -> None:
        script = r'''
import builtins
import json
import socket
import subprocess
import sys

payload = json.loads(sys.stdin.read())

def forbidden(*args, **kwargs):
    raise AssertionError("fingerprint preparation attempted an external effect")

socket.socket.connect = forbidden
socket.socket.connect_ex = forbidden
socket.create_connection = forbidden
subprocess.Popen = forbidden
original_import = builtins.__import__

def isolated_import(name, *args, **kwargs):
    if name.startswith(("crypto_autopilot.storage", "scripts", "boto3", "botocore", "pyarrow")):
        raise AssertionError("unexpected production dependency: " + name)
    return original_import(name, *args, **kwargs)

builtins.__import__ = isolated_import
from crypto_autopilot.training.fingerprint_v0_2 import build_fingerprint, compare_prepared_fingerprints
builtins.open = forbidden
record = build_fingerprint(
    contract_bytes=payload["contract"].encode("utf-8"),
    dataset_fingerprint=payload["dataset"],
    git_blobs=payload["blobs"],
    runtime_manifest=payload["runtime"],
)
result = compare_prepared_fingerprints(
    contract_bytes=payload["contract"].encode("utf-8"), current=record, previous=record
)
assert result["status"] == "NO_CHANGE"
assert result["mode"] == "PREPARATION_ONLY"
assert result["execution_authorized"] is False
assert result["training_performed"] is False
assert result["r2_access_performed"] is False
assert result["provider_requests_performed"] == 0
assert not any(name.startswith(("crypto_autopilot.storage", "scripts.train_")) for name in sys.modules)
print("PURE_PREPARATION_PASS")
'''
        payload = {
            "contract": CONTRACT_BYTES.decode("utf-8"),
            "dataset": DATASET,
            "blobs": blob_fixture(),
            "runtime": runtime_fixture(),
        }
        environment = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
        result = subprocess.run(
            [sys.executable, "-S", "-c", script],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
            env=environment,
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "PURE_PREPARATION_PASS")


if __name__ == "__main__":
    unittest.main()
