"""Cloud-only synthetic checks for prepaid, comparison-only Core100."""
import hashlib
import json
import unittest
from unittest.mock import Mock, patch

from crypto_autopilot.paper.cloud_budget_v0_1 import BudgetBlocked, R2UsageSnapshot
from crypto_autopilot.paper.cloud_r2_store_v0_1 import BudgetedR2Store
from crypto_autopilot.paper.shared_writer_budget_gate_v0_5 import RESERVE_SHARED_WRITER_SQL
from crypto_autopilot.training.prepaid_core100_comparison_v0_1 import (
    _Core100ReadOnlyStore, compare_prepaid_core100,
)
from crypto_autopilot.training.prepaid_core100_d1_v0_1 import WRITER
import test_prepaid_d1_runtime_v0_1 as fixtures


class Core100SharedComparisonTests(unittest.TestCase):
    def setUp(self):
        original = fixtures.authority_fixture

        def authority():
            data = original()
            data["writers"][0]["writer_id"] = WRITER
            return data

        for active in (patch.object(fixtures, "WRITER", WRITER),
                       patch.object(fixtures, "authority_fixture", side_effect=authority)):
            active.start()
            self.addCleanup(active.stop)
        self.f = fixtures.PrepaidD1RuntimeTests("test_meter_readonly_checks_never_debit_or_refresh")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.db = self.f.sqlite()
        self.statements = []

        def d1_send(request, timeout):
            body = json.loads(request.data)
            self.statements.append(body["sql"])
            cursor = self.db.execute(body["sql"], tuple(body["params"]))
            columns = tuple(row[0] for row in cursor.description or ())
            rows = [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
            self.db.commit()
            return fixtures.Response(fixtures.body(
                rows=rows, reads=1, writes=7 if "INSERT INTO" in body["sql"] else 0, size=1024,
            ))

        self.opener = Mock()
        self.opener.open.side_effect = d1_send
        original_list = self.f.sdk.list_objects_v2

        def list_objects(**kwargs):
            page = original_list(**kwargs)
            for row in page["Contents"]:
                row["Size"] = len(self.f.sdk.objects[row["Key"]][0])
            return page

        def store_factory(**kwargs):
            return BudgetedR2Store(client=self.f.sdk, bucket=kwargs["bucket"],
                                   before_external=kwargs["before_external"])

        env = {"CLOUDFLARE_D1_API_TOKEN": "fixture", "CLOUDFLARE_ACCOUNT_ID": "a" * 32,
               "CLOUDFLARE_D1_DATABASE_ID": fixtures.DB_ID, "R2_BUCKET_NAME": "fixture"}
        for active in (patch.dict("os.environ", env),
                       patch(fixtures.CLIENT_MODULE + ".build_opener", return_value=self.opener),
                       patch.object(self.f.sdk, "list_objects_v2", side_effect=list_objects),
                       patch.object(BudgetedR2Store, "from_credentials", side_effect=store_factory)):
            active.start()
            self.addCleanup(active.stop)

    def args(self, **changes):
        now = self.f.now
        snapshot = R2UsageSnapshot(
            account_wide=True, reservation_coverage_complete=True,
            observed_at_ms=now, measured_through_ms=now, storage_bytes=0,
            class_a_month=0, class_b_month=0, class_a_31_days=0, class_b_31_days=0,
            class_a_day=0, class_b_day=0, provider_requests_day=0, new_bytes_day=0,
        )
        args = dict(r2_snapshot=snapshot, d1_snapshot=self.f.guard.snapshot,
                    query_meter=self.f.meter, clock_ms=lambda: self.f.now, slot_at_ms=now,
                    database_evidence=self.f.evidence,
                    credentials={"account_id": "a" * 32, "bucket": "fixture",
                                 "access_key_id": "fixture", "secret_access_key": "fixture"},
                    verify_source=lambda: "a" * 40, execution_enabled=True)
        args.update(changes)
        return args

    def test_disabled_has_no_d1_or_r2(self):
        result = compare_prepaid_core100(**self.args(execution_enabled=False))
        self.assertEqual(result["status"], "SKIPPED_DISABLED")
        self.assertEqual(self.statements, [])
        self.assertEqual(self.f.sdk.calls, [])

    def test_comparator_uses_frozen_functions_after_shared_admission(self):
        from crypto_autopilot.training import prepaid_core100_comparison_v0_1 as module
        latest_key = "training/binance_usdm/crypto-core-v0.1/fingerprint-v0.2/latest.json"
        self.f.sdk.objects[latest_key] = (b"{}", {})
        def read_latest(store):
            self.assertEqual(self.statements, [RESERVE_SHARED_WRITER_SQL])
            self.assertEqual(store.get_bytes_if_exists(latest_key), b"{}")
            return latest_key, {}, {
                "implementation_receipt_git_blob_sha": "b" * 40,
                "training_fingerprint_v0_2": {"fixture": True},
            }
        with patch.object(module.frozen.runner, "require_execution_window"), patch.object(
            module.frozen, "_validate_authority_and_implementation", return_value=({}, "b" * 40),
        ), patch.object(module.frozen, "_load_v02_latest", side_effect=read_latest), patch.object(
            module.frozen.runner, "load_dataset_index", return_value=({}, {}, [], "d" * 64),
        ), patch.object(module.frozen, "_dataset_is_exact", return_value=True), patch.object(
            module.frozen, "_current_fingerprint", return_value={"fixture": True},
        ), patch.object(module.frozen, "compare_fingerprints", return_value={
            "status": "NO_CHANGE", "reason": "SYNTHETIC_MATCH",
        }):
            result = compare_prepaid_core100(**self.args())
            self.assertEqual(result["status"], "NO_CHANGE")
            self.assertFalse(result["training_performed"])
            self.assertFalse(result["r2_writes_performed"])
            self.assertEqual(result["provider_requests_performed"], 0)
            self.assertEqual(self.statements, [RESERVE_SHARED_WRITER_SQL])
            before = list(self.f.sdk.calls)
            with self.assertRaises(BudgetBlocked):
                compare_prepaid_core100(**self.args())
            self.assertEqual(self.f.sdk.calls, before)
        self.assertFalse(any(call["operation"] == "PUT" for call in self.f.sdk.calls))

    def test_read_facade_rejects_holdout_partitions_and_model_before_access(self):
        store = _Core100ReadOnlyStore(BudgetedR2Store(
            client=self.f.sdk, bucket="fixture", before_external=lambda *_: None,
        ))
        keys = (
            "replacement-holdout/candles.json",
            "market-data/binance_usdm/crypto-core-v0.1/data.parquet",
            "training/binance_usdm/crypto-core-v0.1/fingerprint-v0.2/runs/run=github-1-1/model.json",
            "catalogs/binance_usdm/crypto-core-v0.1/runs/../secret.json",
        )
        for key in keys:
            with self.subTest(key=key), self.assertRaises(ValueError):
                store.get_bytes_if_exists(key)
        self.assertEqual(self.f.sdk.calls, [])
        self.assertFalse(hasattr(store, "put_bytes"))

    def test_read_facade_validates_digest_and_incomplete_listing(self):
        key = "catalogs/binance_usdm/crypto-core-v0.1/latest.json"
        self.f.sdk.objects[key] = (b"fixture", {})
        store = _Core100ReadOnlyStore(BudgetedR2Store(
            client=self.f.sdk, bucket="fixture", before_external=lambda *_: None,
        ))
        self.assertEqual(store.get_bytes_verified(key, expected_sha256=hashlib.sha256(b"fixture").hexdigest()), b"fixture")
        with self.assertRaises(ValueError):
            store.get_bytes_verified(key, expected_sha256="0" * 64)
        with patch.object(self.f.sdk, "list_objects_v2", return_value={"Contents": [], "IsTruncated": True}):
            with self.assertRaises(ValueError):
                store.bucket_bytes()


if __name__ == "__main__":
    unittest.main()
