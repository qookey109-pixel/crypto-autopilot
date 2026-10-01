"""Profile complete asserted Cloud Paper fixtures through real R2 adapters.

All services are deterministic in-memory fakes. No credentials or external
requests are constructed. This is protocol evidence, not production billing.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("synthetic fixture module unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def profile_fixture(name, method, *, page_size=1000):
    protocol_name = "full_cycle_r2_protocol"
    fixture_name = "full_cycle_composition_fixture"
    protocol = _load(
        protocol_name, ROOT / "scripts" / "measure_cloud_paper_r2_protocol_profile_v0_1.py",
    )
    fixture = _load(
        fixture_name, ROOT / "tests" / "test_cloud_paper_composition_v0_1.py",
    )
    stores = []

    class RecordingR2Store(protocol.R2PaperRunStore):
        def __init__(self, budget_guard=None):
            self.budget_guard = budget_guard
            self.s3 = protocol._MemoryS3Client()
            self.reservations = Counter()
            self.reservation_bytes = Counter()
            self.calls = []
            self.completed_slots = []

            def reserve(operation, size):
                if self.budget_guard is None:
                    raise ValueError("synthetic composition budget guard missing")
                self.budget_guard.reserve(operation, size)
                self.reservations[operation] += 1
                self.reservation_bytes[operation] += size

            adapter = protocol.BudgetedR2Store(
                client=self.s3, bucket="synthetic-only", before_external=reserve,
                policy=protocol.BudgetedR2Policy(
                    maximum_list_pages=100, maximum_list_keys_per_page=page_size,
                ),
            )
            super().__init__(adapter, prefix="synthetic-full-cycle/v0.1")
            stores.append(self)

        @property
        def objects(self):
            return {
                (metadata["paper-run-kind"], metadata["paper-run-id"]): json.loads(body)
                for body, metadata in self.s3.objects.values()
            }

        def get_json(self, kind, object_id):
            self.calls.append(("get", kind, object_id))
            return super().get_json(kind, object_id)

        def list_json_ids(self, kind):
            self.calls.append(("list", kind))
            return super().list_json_ids(kind)

        def put_json(self, kind, object_id, payload):
            self.calls.append(("put", kind, object_id))
            return super().put_json(kind, object_id, payload)

        def put_json_if_absent(self, kind, object_id, payload):
            self.calls.append(("put_if_absent", kind, object_id))
            receipt = super().put_json_if_absent(kind, object_id, payload)
            if kind == "cloud-result":
                self.completed_slots.append({
                    "ordinal": len(self.completed_slots) + 1,
                    **protocol._snapshot(
                        self.s3, self.reservations, self.reservation_bytes, 0,
                    ),
                })
            return receipt

    try:
        result = unittest.TestResult()
        with patch.object(fixture, "MemoryStore", RecordingR2Store):
            fixture.CloudPaperCompositionTests(method).run(result)
        if not result.wasSuccessful() or result.skipped or result.testsRun != 1:
            raise ValueError(
                f"real-adapter synthetic fixture failed: {name}: "
                f"{result.errors + result.failures}"
            )
        return {
            "scenario": name,
            "fixture": f"tests/test_cloud_paper_composition_v0_1.py::{method}",
            "fixture_assertions": "PASS",
            "list_page_size": page_size,
            "stores": [{
                **protocol._snapshot(
                    store.s3, store.reservations, store.reservation_bytes, 0,
                ),
                "completed_slots": store.completed_slots,
                "guard_attempted_usage": {
                    "provider_requests": store.budget_guard.attempted_usage().provider_requests,
                    "class_a": store.budget_guard.attempted_usage().class_a_requests,
                    "class_b": store.budget_guard.attempted_usage().class_b_requests,
                    "new_bytes": store.budget_guard.attempted_usage().new_bytes,
                },
            } for store in stores],
        }
    finally:
        sys.modules.pop(protocol_name, None)
        sys.modules.pop(fixture_name, None)


def build_report():
    scenarios = (
        ("no_trade", "test_enabled_empty_registry_composes_to_audited_no_trade"),
        ("entry_exit_no_trade",
         "test_qualified_fixture_completes_entry_exit_and_no_trade_through_composition"),
        ("verified_recovery",
         "test_restart_recovery_verifies_result_and_keeps_full_reservation"),
        ("failed_settlement",
         "test_failed_settlement_keeps_reserved_slot_and_does_not_replay_io"),
    )
    return {
        "schema": "qookey-cloud-paper-synthetic-full-cycle-r2-profile-v0.1",
        "evidence_type": "SYNTHETIC_FULL_CYCLE_REAL_R2_ADAPTERS",
        "scenarios": [profile_fixture(*row) for row in scenarios],
        "external_access": {
            "provider_requests": 0, "r2_requests": 0, "d1_requests": 0,
            "credentials_constructed": False,
        },
        "limitations": [
            "Provider and D1 services remain fakes; their HTTP payloads and D1 row costs are not measured.",
            "R2 operations are S3-compatible method calls; bytes exclude HTTP framing and service metadata.",
            "Completed-slot metrics are cumulative through the result write, before subsequent verification reads.",
            "These fixtures are not a five-market worst-case or long-history capacity bound.",
            "No account-wide writer coverage, production headroom, billing or activation claim.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    for scenario in report["scenarios"]:
        for row in scenario["stores"]:
            print(
                f'{scenario["scenario"]}: {row["stored_objects"]} objects; '
                f'{row["stored_object_payload_bytes"]} stored bytes; '
                f'operations={row["s3_compatible_operation_calls"]}; '
                f'guard={row["guard_attempted_usage"]}'
            )


if __name__ == "__main__":
    main()
