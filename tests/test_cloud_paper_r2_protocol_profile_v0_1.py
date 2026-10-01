from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path
import unittest

from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Client
from crypto_autopilot.paper.run_store_v0_1 import _canonical_bytes

PATH = Path(__file__).resolve().parents[1] / "scripts" / "measure_cloud_paper_r2_protocol_profile_v0_1.py"
SPEC = importlib.util.spec_from_file_location("r2_protocol_profile", PATH)
assert SPEC is not None and SPEC.loader is not None
profile = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(profile)


class CloudPaperR2ProtocolProfileTests(unittest.TestCase):
    def test_profiles_real_adapters_without_external_access(self):
        report = profile.build_report()
        self.assertEqual(report["evidence_type"], "SYNTHETIC_ADAPTER_PROTOCOL_ONLY")
        self.assertEqual(report["scope"]["cloudflare_r2_requests"], 0)
        scenarios = {row["scenario"]: row for row in report["scenarios"]}

        for row in scenarios.values():
            self.assertEqual(
                row["reserved_put_application_payload_bytes"],
                row["put_application_payload_bytes"],
                row["scenario"],
            )

        new_write = scenarios["new_put_json"]
        self.assertEqual(new_write["s3_compatible_operation_calls"], {"GET": 1, "PUT": 1})
        self.assertEqual(new_write["budget_reservations"]["R2_CLASS_B"], 1)
        self.assertEqual(new_write["budget_reservations"]["R2_CLASS_A"], 1)
        self.assertEqual(new_write["missing_gets"], 1)
        self.assertEqual(new_write["objects_added"], 1)

        replay = scenarios["identical_replay_put_json"]
        self.assertEqual(replay["s3_compatible_operation_calls"], {"GET": 1})
        self.assertEqual(replay["objects_added"], 0)
        self.assertGreater(replay["get_application_payload_bytes"], 0)

        read = scenarios["read_existing_json"]
        self.assertEqual(read["s3_compatible_operation_calls"], {"GET": 1})
        self.assertEqual(read["get_application_payload_bytes"], new_write["stored_object_payload_bytes"])

        listing = scenarios["list_one_page"]
        self.assertEqual(listing["s3_compatible_operation_calls"], {"LIST": 1})
        self.assertEqual(listing["budget_reservations"]["R2_CLASS_A"], 1)

        conditional = scenarios["conditional_create"]
        self.assertEqual(conditional["s3_compatible_operation_calls"], {"PUT": 1})
        self.assertEqual(conditional["missing_gets"], 0)
        self.assertEqual(conditional["objects_added"], 1)

        paginated = scenarios["conditional_create_and_paginated_list"]
        self.assertEqual(paginated["s3_compatible_operation_calls"], {"LIST": 3, "PUT": 5})
        self.assertEqual(paginated["budget_reservations"]["R2_CLASS_A"], 8)
        self.assertEqual(paginated["objects_added"], 5)
        self.assertEqual(
            paginated["put_application_payload_bytes"],
            sum(len(_canonical_bytes({"item": index})) for index in range(5)),
        )


    def test_snapshot_preserves_independent_reservation_measurement(self):
        client = profile._MemoryS3Client()
        client.put_object(Key="synthetic", Body=b"payload")
        row = profile._snapshot(
            client, Counter({"R2_CLASS_A": 1}), Counter({"R2_CLASS_A": 2}), 0,
        )
        self.assertEqual(row["put_application_payload_bytes"], 7)
        self.assertEqual(row["reserved_put_application_payload_bytes"], 2)

    def test_budget_denial_prevents_underlying_operation(self):
        for operation in ("put_object", "get_object", "list_objects_v2"):
            with self.subTest(operation=operation):
                client = profile._MemoryS3Client()
                reservations = []

                def deny(kind, size):
                    reservations.append((kind, size))
                    raise ValueError("synthetic budget denied")

                guarded = BudgetedR2Client(client=client, before_external=deny)
                arguments = {
                    "put_object": {"Key": "synthetic", "Body": b"payload"},
                    "get_object": {"Key": "synthetic"},
                    "list_objects_v2": {"Prefix": "synthetic", "MaxKeys": 2},
                }
                with self.assertRaisesRegex(ValueError, "synthetic budget denied"):
                    getattr(guarded, operation)(**arguments[operation])
                self.assertEqual(client.calls, [])
                self.assertEqual(client.objects, {})
                self.assertEqual(len(reservations), 1)
                self.assertEqual(
                    reservations[0],
                    ("R2_CLASS_B", 0) if operation == "get_object"
                    else ("R2_CLASS_A", 7 if operation == "put_object" else 0),
                )

    def test_report_is_deterministic_and_contains_no_payloads(self):
        first = profile.build_report()
        second = profile.build_report()
        self.assertEqual(first, second)
        serialized = str(first)
        self.assertNotIn("cash_usd", serialized)
        self.assertNotIn("slot-1", serialized)
        self.assertNotIn("synthetic-only", serialized)


if __name__ == "__main__":
    unittest.main()
