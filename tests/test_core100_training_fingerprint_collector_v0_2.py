from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from crypto_autopilot.training.fingerprint_collector_v0_2 import (
    EvidenceCollectionError,
    collect_git_blob_map,
    collect_runtime_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_BYTES = (ROOT / "config/core100_training_fingerprint_v0_2.json").read_bytes()
CONTRACT = json.loads(CONTRACT_BYTES)
SHA = "a" * 40
GITHUB_ENV = {
    "GITHUB_ACTIONS": "true",
    "CORE100_FINGERPRINT_ISOLATED_ENVIRONMENT": "true",
}


def distribution(name: str, version: str) -> SimpleNamespace:
    return SimpleNamespace(metadata={"Name": name}, version=version)


class Core100FingerprintCollectorV02Tests(unittest.TestCase):
    def required_paths(self) -> set[str]:
        identity = CONTRACT["identity_contract"]
        context = CONTRACT["execution_context"]
        return set(identity["code_paths"] + identity["support_paths"] + identity["runtime_guard_paths"]) | {
            context["workflow_path"],
            context["current_training_authority_receipt_path"],
        }

    def test_collector_refuses_non_github_runtime(self) -> None:
        with self.assertRaises(EvidenceCollectionError):
            collect_runtime_manifest(environ={"GITHUB_ACTIONS": "false"})

    def test_runtime_requires_isolated_environment_attestation(self) -> None:
        with self.assertRaises(EvidenceCollectionError):
            collect_runtime_manifest(environ={"GITHUB_ACTIONS": "true"})

    def test_runtime_inventory_is_complete_and_normalized(self) -> None:
        installed = [
            distribution("qookey_crypto.autopilot", "0.1.0"),
            distribution("PIP", "25.2"),
            distribution("Setuptools", "80.9.0"),
            distribution("PyArrow", "21.0.0"),
        ]
        with patch(
            "crypto_autopilot.training.fingerprint_collector_v0_2.importlib.metadata.distributions",
            return_value=installed,
        ):
            runtime = collect_runtime_manifest(
                environ={
                    **GITHUB_ENV,
                    "ImageOS": "ubuntu24",
                    "ImageVersion": "20260920.1.0",
                }
            )
        self.assertEqual(runtime["implementation"], "cpython")
        self.assertTrue(runtime["isolated_environment"])
        self.assertEqual(runtime["project_version"], "0.1.0")
        self.assertEqual(
            [row["name"] for row in runtime["install_tools"]],
            ["pip", "setuptools"],
        )
        self.assertEqual(runtime["runner_image"], {"os": "ubuntu24", "version": "20260920.1.0"})

    def test_missing_required_install_tool_fails_closed(self) -> None:
        installed = [
            distribution("qookey-crypto-autopilot", "0.1.0"),
            distribution("pip", "25.2"),
        ]
        with patch(
            "crypto_autopilot.training.fingerprint_collector_v0_2.importlib.metadata.distributions",
            return_value=installed,
        ):
            with self.assertRaises(EvidenceCollectionError):
                collect_runtime_manifest(environ=GITHUB_ENV)

    def test_git_blob_inventory_requires_exact_live_main_and_complete_files(self) -> None:
        required = self.required_paths()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for relative in required:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(("fixture:" + relative).encode("utf-8"))
            blobs = collect_git_blob_map(
                contract_bytes=CONTRACT_BYTES,
                project_root=root,
                checkout_sha=SHA,
                live_main_sha=SHA,
                environ={"GITHUB_ACTIONS": "true"},
            )
            self.assertEqual(set(blobs), required)
            sample = "src/crypto_autopilot/features/advanced.py"
            payload = ("fixture:" + sample).encode("utf-8")
            expected = hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()
            self.assertEqual(blobs[sample], expected)

    def test_stale_checkout_or_missing_inventory_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self.assertRaises(EvidenceCollectionError):
                collect_git_blob_map(
                    contract_bytes=CONTRACT_BYTES,
                    project_root=root,
                    checkout_sha=SHA,
                    live_main_sha="b" * 40,
                    environ={"GITHUB_ACTIONS": "true"},
                )
            with self.assertRaises(EvidenceCollectionError):
                collect_git_blob_map(
                    contract_bytes=CONTRACT_BYTES,
                    project_root=root,
                    checkout_sha=SHA,
                    live_main_sha=SHA,
                    environ={"GITHUB_ACTIONS": "true"},
                )


if __name__ == "__main__":
    unittest.main()
