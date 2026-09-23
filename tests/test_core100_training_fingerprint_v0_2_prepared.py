from __future__ import annotations

import ast
import hashlib
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import train_binance_detailed_history_models_v0_3 as active_trainer


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config/core100_training_fingerprint_v0_2.json"
RECEIPT_PATH = (
    ROOT
    / "research/receipts/2026-09-24-core100-training-fingerprint-v0-2-prepared.json"
)
V01_PATH = ROOT / "config/core100_training_fingerprint_v0_1.json"
BASELINE_DATASET = "91d5ac26e94fe86d175f2ec6972b648d63851c8727849f92d57f94073e377876"
BASELINE_EXPERIMENT = "25b3178ce0d13052684d20b35a0e1f6949f0d97a5ac0c5b9e8f0a52d4d12f9c8"


def _load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return value


def _static_import_closure(config: dict[str, object]) -> list[str]:
    inventory = config["source_inventory"]
    assert isinstance(inventory, dict)
    modules: dict[str, str] = {}
    packages: set[str] = set()
    for path in (ROOT / "src/crypto_autopilot").rglob("*.py"):
        relative = path.relative_to(ROOT).as_posix()
        module = relative.removeprefix("src/").removesuffix(".py").replace("/", ".")
        if module.endswith(".__init__"):
            module = module.removesuffix(".__init__")
            packages.add(module)
        modules[module] = relative

    def add_module(module: str, source: str, queue: list[str]) -> None:
        target = modules.get(module)
        if target is None:
            return
        queue.append(target)
        parts = module.split(".")
        for index in range(1, len(parts)):
            package = ".".join(parts[:index])
            if package in packages:
                queue.append(modules[package])

    entries = inventory["entry_scripts"]
    assert isinstance(entries, list)
    queue = [str(path) for path in entries]
    found: set[str] = set()
    while queue:
        relative = queue.pop()
        if relative in found:
            continue
        found.add(relative)
        package = ""
        if relative.startswith("src/"):
            current = relative.removeprefix("src/").removesuffix(".py").replace("/", ".")
            is_package = current.endswith(".__init__")
            current = current.removesuffix(".__init__") if is_package else current
            package = current if is_package else current.rpartition(".")[0]
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    add_module(alias.name, relative, queue)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    parts = package.split(".") if package else []
                    base = ".".join(parts[: len(parts) - node.level + 1])
                    if node.module:
                        base = f"{base}.{node.module}" if base else node.module
                if base:
                    add_module(base, relative, queue)
                for alias in node.names:
                    if alias.name != "*" and base:
                        add_module(f"{base}.{alias.name}", relative, queue)
    return sorted(found)


def _declared_dynamic_imports(config: dict[str, object]) -> list[dict[str, str]]:
    inventory = config["source_inventory"]
    assert isinstance(inventory, dict)
    closure = inventory["static_import_closure_paths"]
    assert isinstance(closure, list)
    discovered: list[dict[str, str]] = []
    for relative in closure:
        source = str(relative)
        tree = ast.parse((ROOT / source).read_text(encoding="utf-8"))
        constants: dict[str, str] = {}
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and isinstance(node.value, ast.BinOp)
                and isinstance(node.value.op, ast.Div)
                and isinstance(node.value.left, ast.Name)
                and node.value.left.id == "ROOT"
                and isinstance(node.value.right, ast.Constant)
                and isinstance(node.value.right.value, str)
            ):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        constants[target.id] = node.value.right.value
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            mechanism = ast.unparse(node.func)
            if mechanism != "importlib.util.spec_from_file_location":
                continue
            if len(node.args) < 2 or not isinstance(node.args[1], ast.Name):
                discovered.append(
                    {"caller": source, "target": "UNKNOWN", "mechanism": mechanism}
                )
                continue
            variable = node.args[1].id
            discovered.append(
                {
                    "caller": source,
                    "target": constants.get(variable, "UNKNOWN"),
                    "target_variable": variable,
                    "mechanism": mechanism,
                }
            )
    return sorted(discovered, key=lambda row: (row["caller"], row["target"]))


def _synthetic_identity(
    *,
    schema: str,
    dataset: str,
    code_blobs: dict[str, str],
    support_blobs: dict[str, str],
    runtime: dict[str, object],
) -> str:
    payload = {
        "schema": schema,
        "dataset_fingerprint": dataset,
        "code_git_blobs": sorted(code_blobs.items()),
        "support_git_blobs": sorted(support_blobs.items()),
        "runtime_manifest": runtime,
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _synthetic_guard_digest(blobs: dict[str, str]) -> str:
    canonical = json.dumps(
        sorted(blobs.items()), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class Core100FingerprintV02PreparedTests(unittest.TestCase):
    def test_static_import_closure_and_dynamic_loads_are_complete(self) -> None:
        config = _load_json(CONTRACT_PATH)
        inventory = config["source_inventory"]
        assert isinstance(inventory, dict)
        self.assertEqual(
            _static_import_closure(config), inventory["static_import_closure_paths"]
        )
        self.assertEqual(len(inventory["static_import_closure_paths"]), 31)
        self.assertEqual(
            _declared_dynamic_imports(config),
            sorted(
                inventory["dynamic_imports"],
                key=lambda row: (row["caller"], row["target"]),
            ),
        )

    def test_identity_and_runtime_guard_paths_partition_the_closure(self) -> None:
        config = _load_json(CONTRACT_PATH)
        receipt = _load_json(RECEIPT_PATH)
        inventory = config["source_inventory"]
        assert isinstance(inventory, dict)
        closure = set(inventory["static_import_closure_paths"])
        identity = set(inventory["training_result_identity_code_paths"])
        guard = set(inventory["runtime_import_guard_paths"])
        self.assertEqual(identity & guard, set())
        self.assertEqual(identity | guard, closure)
        self.assertEqual(len(identity), 14)
        self.assertEqual(len(guard), 17)

        source_rows = receipt["source_blob_inventory"]
        self.assertEqual({row["path"] for row in source_rows}, closure)
        self.assertTrue(all(len(row["git_blob_sha"]) == 40 for row in source_rows))
        self.assertIn("src/crypto_autopilot/backtest.py", guard)
        self.assertIn("src/crypto_autopilot/risk.py", guard)

    def test_current_v01_inputs_still_reproduce_the_frozen_baseline(self) -> None:
        v01 = _load_json(V01_PATH)
        baseline = v01["baseline"]
        active_trainer.validate_fingerprint_config(v01)
        identity, rows = active_trainer.build_experiment_identity(
            dataset_fingerprint=BASELINE_DATASET,
            fingerprint_config=v01,
            root=ROOT,
        )
        self.assertEqual(identity, BASELINE_EXPERIMENT)
        self.assertEqual(rows, baseline["model_affecting_git_blobs"])
        self.assertEqual(len(rows), 10)

    def test_v01_blind_spot_is_reproduced_with_synthetic_blob_hashes(self) -> None:
        v01 = _load_json(V01_PATH)
        baseline = v01["baseline"]
        baseline_blobs = {
            row["path"]: row["git_blob_sha"]
            for row in baseline["model_affecting_git_blobs"]
        }

        def identity_with_changes(changed_paths: set[str], marker: str) -> tuple[str, list[str]]:
            calls: list[str] = []

            def fake_blob_sha(path: Path) -> str:
                relative = path.relative_to(ROOT).as_posix()
                calls.append(relative)
                if relative in changed_paths:
                    return marker * 40
                if relative not in baseline_blobs:
                    raise AssertionError(f"unexpected baseline path: {relative}")
                return baseline_blobs[relative]

            with patch.object(active_trainer, "_git_blob_sha", side_effect=fake_blob_sha):
                identity, _rows = active_trainer.build_experiment_identity(
                    dataset_fingerprint=BASELINE_DATASET,
                    fingerprint_config=v01,
                    root=ROOT,
                )
            return identity, calls

        unchanged, unchanged_calls = identity_with_changes(set(), "a")
        self.assertEqual(unchanged, BASELINE_EXPERIMENT)
        self.assertEqual(len(unchanged_calls), 10)
        for feature_path in (
            "src/crypto_autopilot/features/advanced.py",
            "src/crypto_autopilot/technical.py",
        ):
            changed_feature, calls = identity_with_changes({feature_path}, "b")
            self.assertEqual(changed_feature, unchanged)
            self.assertNotIn(feature_path, calls)
        changed_trainer, _calls = identity_with_changes(
            {"src/crypto_autopilot/training/detailed.py"}, "c"
        )
        self.assertNotEqual(changed_trainer, unchanged)
        changed_dataset, _rows = active_trainer.build_experiment_identity(
            dataset_fingerprint="f" * 64,
            fingerprint_config=v01,
            root=ROOT,
        )
        self.assertNotEqual(changed_dataset, unchanged)

    def test_proposed_identity_covers_model_inputs_runtime_and_guard(self) -> None:
        config = _load_json(CONTRACT_PATH)
        identity = config["identity_contract"]
        inventory = config["source_inventory"]
        assert isinstance(identity, dict) and isinstance(inventory, dict)
        code = {path: "a" * 40 for path in identity["code_paths"]}
        support = {path: "c" * 40 for path in identity["support_paths"]}
        runtime = {"python": "3.13.15", "platform": "linux-x86_64", "packages": ["pyarrow==21.0.0"]}
        original = _synthetic_identity(
            schema=identity["schema"],
            dataset=BASELINE_DATASET,
            code_blobs=code,
            support_blobs=support,
            runtime=runtime,
        )
        for path in (
            "src/crypto_autopilot/features/advanced.py",
            "src/crypto_autopilot/technical.py",
        ):
            changed = dict(code)
            changed[path] = "b" * 40
            self.assertNotEqual(
                _synthetic_identity(
                    schema=identity["schema"],
                    dataset=BASELINE_DATASET,
                    code_blobs=changed,
                    support_blobs=support,
                    runtime=runtime,
                ),
                original,
            )
        self.assertNotEqual(
            _synthetic_identity(
                schema=identity["schema"],
                dataset="f" * 64,
                code_blobs=code,
                support_blobs=support,
                runtime=runtime,
            ),
            original,
        )
        changed_runtime = {**runtime, "python": "3.13.16"}
        self.assertNotEqual(
            _synthetic_identity(
                schema=identity["schema"],
                dataset=BASELINE_DATASET,
                code_blobs=code,
                support_blobs=support,
                runtime=changed_runtime,
            ),
            original,
        )
        guard_paths = inventory["runtime_import_guard_paths"]
        guard = {path: "d" * 40 for path in guard_paths}
        changed_guard = dict(guard)
        changed_guard["src/crypto_autopilot/backtest.py"] = "e" * 40
        self.assertNotEqual(_synthetic_guard_digest(guard), _synthetic_guard_digest(changed_guard))
        self.assertIn("REVIEW_REQUIRED", identity["runtime_guard_change"])

    def test_legacy_baseline_migration_fails_closed(self) -> None:
        config = _load_json(CONTRACT_PATH)
        receipt = _load_json(RECEIPT_PATH)
        migration = config["baseline_migration"]
        comparison = receipt["legacy_source_comparison"]
        rows = comparison["rows"]
        self.assertEqual(migration["legacy_v0_1_latest_pointer"], "REVIEW_REQUIRED")
        self.assertFalse(migration["legacy_reuse_authorized"])
        self.assertEqual(comparison["candidate_python_path_count"], 31)
        self.assertEqual(len(rows), 31)
        by_path = {row["path"]: row["comparison"] for row in rows}
        self.assertEqual(
            by_path["src/crypto_autopilot/features/advanced.py"], "DIFF"
        )
        self.assertEqual(
            by_path["scripts/train_binance_detailed_history_models_v0_3.py"],
            "MISSING_HISTORICAL",
        )
        self.assertEqual(migration["result_identity_source_comparison"]["different"], 1)
        self.assertFalse(migration["legacy_exact_python_patch_and_distribution_inventory_available"])

    def test_preparation_has_no_execution_authority_or_side_effects(self) -> None:
        config = _load_json(CONTRACT_PATH)
        receipt = _load_json(RECEIPT_PATH)
        self.assertEqual(config["status"], "PREPARED_NOT_ACTIVE")
        self.assertEqual(receipt["status"], "PREPARED_NOT_ACTIVE")
        self.assertTrue(all(value is False for value in config["authority"].values()))
        self.assertTrue(all(value is False for value in receipt["authority_effect"].values()))
        self.assertEqual(receipt["side_effects"]["provider_requests_performed"], 0)
        self.assertEqual(receipt["side_effects"]["r2_reads_performed"], 0)
        self.assertEqual(receipt["side_effects"]["r2_writes_performed"], 0)
        self.assertFalse(receipt["side_effects"]["training_performed"])
        self.assertFalse(receipt["side_effects"]["active_runner_changed"])
        self.assertFalse(receipt["side_effects"]["workflow_changed"])


if __name__ == "__main__":
    unittest.main()
