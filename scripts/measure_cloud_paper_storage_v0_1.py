"""Measure existing synthetic Cloud Paper fixtures without external access.

This development command reuses asserted fixtures, never production credentials.
Store interface calls are not R2 service operation counts or account headroom.
"""
from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from crypto_autopilot.paper.run_store_v0_1 import _canonical_bytes

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = (
    ("no_trade", "test_cloud_paper_composition_v0_1",
     "CloudPaperCompositionTests", "test_enabled_empty_registry_composes_to_audited_no_trade"),
    ("entry_exit_no_trade", "test_cloud_paper_composition_v0_1",
     "CloudPaperCompositionTests",
     "test_qualified_fixture_completes_entry_exit_and_no_trade_through_composition"),
    ("replay_restart", "test_cloud_paper_loop_v0_1",
     "CloudPaperLoopTests", "test_empty_registry_runs_audited_no_trade_and_restarts"),
    ("verified_recovery", "test_cloud_paper_composition_v0_1",
     "CloudPaperCompositionTests",
     "test_restart_recovery_verifies_result_and_keeps_full_reservation"),
    ("failed_settlement", "test_cloud_paper_composition_v0_1",
     "CloudPaperCompositionTests",
     "test_failed_settlement_keeps_reserved_slot_and_does_not_replay_io"),
)


def summarize_objects(objects):
    """Use the real JSON store's serialization; do not expose payloads."""
    kinds = {}
    for (kind, _), payload in sorted(objects.items()):
        body = _canonical_bytes(payload)
        row = kinds.setdefault(kind, {
            "objects": 0, "canonical_json_bytes": 0, "largest_object_bytes": 0,
            "gzip_estimate_bytes": 0,
        })
        row["objects"] += 1
        row["canonical_json_bytes"] += len(body)
        row["largest_object_bytes"] = max(row["largest_object_bytes"], len(body))
        row["gzip_estimate_bytes"] += len(gzip.compress(body, mtime=0))
    return {
        "object_count": sum(row["objects"] for row in kinds.values()),
        "canonical_json_bytes": sum(row["canonical_json_bytes"] for row in kinds.values()),
        "by_kind": kinds,
        "compression_note": "OFFLINE_ESTIMATE_ONLY; no stored format was changed",
    }


def profile_scenario(name, module_name, class_name, method_name):
    path = ROOT / "tests" / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(f"storage_profile_{module_name}", path)
    if spec is None or spec.loader is None:
        raise ValueError("synthetic fixture module unavailable")
    module = importlib.util.module_from_spec(spec)
    # Dataclass resolves its defining module during fixture import.
    import sys
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        stores = []
        base_store = module.MemoryStore

        class RecordingStore(base_store):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.profile_calls = Counter()
                self.completed_slots = []
                stores.append(self)

            def get_json(self, kind, object_id):
                self.profile_calls["get_json"] += 1
                return super().get_json(kind, object_id)

            def list_json_ids(self, kind):
                self.profile_calls["list_json_ids"] += 1
                return super().list_json_ids(kind)

            def put_json(self, kind, object_id, payload):
                self.profile_calls["put_json"] += 1
                return super().put_json(kind, object_id, payload)

            def put_json_if_absent(self, kind, object_id, payload):
                self.profile_calls["put_json_if_absent"] += 1
                receipt = super().put_json_if_absent(kind, object_id, payload)
                if kind == "cloud-result":
                    self.completed_slots.append({
                        "slot_id": object_id,
                        "cumulative_storage": summarize_objects(self.objects),
                        "cumulative_interface_calls": dict(sorted(self.profile_calls.items())),
                    })
                return receipt

        result = unittest.TestResult()
        with patch.object(module, "MemoryStore", RecordingStore):
            getattr(module, class_name)(method_name).run(result)
        if not result.wasSuccessful() or result.skipped or result.testsRun != 1:
            raise ValueError(f"asserted synthetic fixture failed: {name}: {result.errors + result.failures}")
        return {
            "scenario": name,
            "fixture": f"tests/{module_name}.py::{class_name}::{method_name}",
            "fixture_assertions": "PASS",
            "stores": [
                {
                    "final_storage": summarize_objects(store.objects),
                    "interface_calls": dict(sorted(store.profile_calls.items())),
                    "completed_slots": store.completed_slots,
                }
                for store in stores
            ],
        }
    finally:
        sys.modules.pop(spec.name, None)


def build_report():
    return {
        "schema": "qookey-cloud-paper-synthetic-storage-profile-v0.1",
        "evidence_type": "SYNTHETIC_ENGINEERING_ONLY",
        "scenarios": [profile_scenario(*scenario) for scenario in SCENARIOS],
        "external_access": {
            "provider_requests": 0, "r2_requests": 0, "d1_requests": 0,
            "credential_construction": False,
        },
        "limitations": [
            "Memory-store interface calls omit R2 existence checks, pagination and service metadata.",
            "D1 ledger calls and bytes are not measured by this report.",
            "These bounded fixtures are not five-market worst-case or production measurements.",
            "JSON payload bytes exclude R2 metadata and account-wide writers.",
            "Compression is an estimate, not an implemented codec or a savings claim.",
            "No conclusion about account headroom, zero cost or activation.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    for scenario in report["scenarios"]:
        for index, store in enumerate(scenario["stores"]):
            storage = store["final_storage"]
            print(f'{scenario["scenario"]}[{index}]: {storage["object_count"]} objects, '
                  f'{storage["canonical_json_bytes"]} canonical JSON bytes')


if __name__ == "__main__":
    main()
