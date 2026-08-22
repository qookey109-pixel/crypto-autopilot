from __future__ import annotations

import hashlib
import json
import unittest
from unittest.mock import MagicMock

from crypto_autopilot.online_r2_training import build_online_objects, publish_online_objects
from crypto_autopilot.online_r2_training import current_bucket_bytes
from crypto_autopilot.storage.r2 import R2ObjectReceipt


class FakePaginator:
    def paginate(self, *, Bucket: str):
        del Bucket
        return [{"Contents": []}]


class FakeClient:
    def get_paginator(self, name: str):
        self.name = name
        return FakePaginator()


class FakeStore:
    def __init__(self):
        self.bucket = "test"
        self.client = FakeClient()
        self.objects: dict[str, bytes] = {}
        self.write_order: list[str] = []

    def get_bytes_if_exists(self, key: str):
        return self.objects.get(key)

    def put_bytes(self, key: str, payload: bytes, **_kwargs):
        self.objects[key] = payload
        self.write_order.append(key)
        return R2ObjectReceipt("test", key, len(payload), __import__("hashlib").sha256(payload).hexdigest(), "etag")

    def get_bytes_verified(self, key: str, *, expected_sha256: str):
        payload = self.objects[key]
        self.assert_sha = expected_sha256
        return payload


class OnlineR2TrainingTests(unittest.TestCase):
    def config(self):
        return {
            "storage": {
                "dataset_runs_namespace": "market-data/binance_spot/v0.3/runs",
                "training_namespace": "training/binance_spot/v0.3",
                "latest_training_pointer_key": "training/binance_spot/v0.3/latest.json",
            }
        }

    def test_latest_pointer_is_built_and_written_last(self) -> None:
        objects = build_online_objects(
            config=self.config(),
            run_id="github-123-1",
            dataset=b"parquet",
            catalog=b"{}\n",
            dataset_receipt=b"{}\n",
            model=b"{}\n",
            metrics=b"{}\n",
            generated_at_utc="2026-08-22T00:00:00Z",
        )
        self.assertEqual(objects[-1].role, "latest_pointer")
        self.assertTrue(all(item.immutable for item in objects[:-1]))
        store = FakeStore()
        result = publish_online_objects(store=store, objects=objects, hard_stop_bytes=100000)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(store.write_order[-1], "training/binance_spot/v0.3/latest.json")
        self.assertTrue(result["latest_pointer_written_last"])

    def test_weekly_review_is_immutable_and_linked_from_latest(self) -> None:
        objects = build_online_objects(
            config=self.config(),
            run_id="github-weekly-1",
            dataset=b"parquet",
            catalog=b"{}\n",
            dataset_receipt=b"{}\n",
            model=b"{}\n",
            metrics=b"{}\n",
            weekly_review=b'{"status":"PASS"}\n',
            generated_at_utc="2026-08-22T00:00:00Z",
        )
        review = next(item for item in objects if item.role == "weekly_review")
        self.assertTrue(review.immutable)
        self.assertTrue(review.key.endswith("/weekly-review.json"))
        latest = json.loads(objects[-1].payload)
        self.assertEqual(latest["weekly_review_key"], review.key)
        metrics = next(item for item in objects if item.role == "metrics")
        self.assertEqual(latest["metrics_key"], metrics.key)
        self.assertEqual(
            latest["metrics_sha256"], hashlib.sha256(metrics.payload).hexdigest()
        )

    def test_v05_manifest_and_latest_persist_governance_evidence(self) -> None:
        config = self.config()
        config["storage"]["schema_version"] = "v0.5"
        governance = {
            "config": {"status": "PASS", "config_sha256": "a" * 64},
            "comparison_baseline": {
                "source": "FROZEN_V0_3_PASS_RECEIPT",
                "sha256": "b" * 64,
            },
        }
        objects = build_online_objects(
            config=config,
            run_id="governed-1",
            dataset=b"parquet",
            catalog=b"{}\n",
            dataset_receipt=b"{}\n",
            model=b"{}\n",
            metrics=b"{}\n",
            governance_evidence=governance,
            generated_at_utc="2026-08-22T00:00:00Z",
        )
        manifest = json.loads(next(item for item in objects if item.role == "manifest").payload)
        latest = json.loads(objects[-1].payload)
        self.assertEqual(manifest["governance"], governance)
        self.assertEqual(latest["governance"], governance)
        self.assertEqual(
            latest["governance_sha256"],
            hashlib.sha256(
                (
                    json.dumps(
                        governance, ensure_ascii=False, sort_keys=True, indent=2
                    )
                    + "\n"
                ).encode()
            ).hexdigest(),
        )

    def test_write_deadline_guard_runs_before_each_upload(self) -> None:
        objects = build_online_objects(
            config=self.config(),
            run_id="deadline-1",
            dataset=b"parquet",
            catalog=b"{}\n",
            dataset_receipt=b"{}\n",
            model=b"{}\n",
            metrics=b"{}\n",
            generated_at_utc="2026-08-22T00:00:00Z",
        )
        store = FakeStore()
        guard = MagicMock(side_effect=[None, RuntimeError("deadline closed")])
        with self.assertRaisesRegex(RuntimeError, "deadline closed"):
            publish_online_objects(
                store=store,
                objects=objects,
                hard_stop_bytes=100000,
                before_write=guard,
            )
        self.assertEqual(guard.call_count, 2)
        self.assertEqual(len(store.write_order), 1)

    def test_access_deadline_guard_blocks_before_inventory(self) -> None:
        objects = build_online_objects(
            config=self.config(),
            run_id="access-deadline-1",
            dataset=b"parquet",
            catalog=b"{}\n",
            dataset_receipt=b"{}\n",
            model=b"{}\n",
            metrics=b"{}\n",
            generated_at_utc="2026-08-22T00:00:00Z",
        )
        store = FakeStore()
        guard = MagicMock(side_effect=RuntimeError("access deadline closed"))
        with self.assertRaisesRegex(RuntimeError, "access deadline closed"):
            publish_online_objects(
                store=store,
                objects=objects,
                hard_stop_bytes=100000,
                before_access=guard,
            )
        guard.assert_called_once_with()
        self.assertEqual(store.write_order, [])

    def test_inventory_rechecks_access_deadline_before_each_page(self) -> None:
        yielded: list[int] = []

        class Paginator:
            def paginate(self, *, Bucket: str):
                del Bucket
                for index in range(2):
                    yielded.append(index)
                    yield {"Contents": [{"Size": 10}]}

        store = FakeStore()
        store.client.get_paginator = lambda _name: Paginator()
        guard = MagicMock(side_effect=[None, RuntimeError("inventory deadline")])
        with self.assertRaisesRegex(RuntimeError, "inventory deadline"):
            current_bucket_bytes(store, before_access=guard)
        self.assertEqual(yielded, [0])

    def test_headroom_blocks_before_any_write(self) -> None:
        objects = build_online_objects(
            config=self.config(),
            run_id="run-1",
            dataset=b"large",
            catalog=b"{}",
            dataset_receipt=b"{}",
            model=b"{}",
            metrics=b"{}",
            generated_at_utc="2026-08-22T00:00:00Z",
        )
        store = FakeStore()
        result = publish_online_objects(
            store=store,
            objects=objects,
            hard_stop_bytes=1,
            inventory_fn=lambda _store: 0,
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(store.write_order, [])

    def test_immutable_conflict_fails_closed(self) -> None:
        objects = build_online_objects(
            config=self.config(),
            run_id="run-2",
            dataset=b"data",
            catalog=b"{}",
            dataset_receipt=b"{}",
            model=b"model",
            metrics=b"metrics",
            generated_at_utc="2026-08-22T00:00:00Z",
        )
        store = FakeStore()
        immutable = next(item for item in objects if item.immutable)
        store.objects[immutable.key] = b"conflict"
        with self.assertRaises(RuntimeError):
            publish_online_objects(store=store, objects=objects, hard_stop_bytes=100000)
        self.assertEqual(store.write_order, [])

    def test_before_write_stop_guard_blocks_first_upload(self) -> None:
        objects = build_online_objects(
            config=self.config(),
            run_id="run-stop-guard",
            dataset=b"data",
            catalog=b"{}",
            dataset_receipt=b"{}",
            model=b"model",
            metrics=b"metrics",
            generated_at_utc="2026-08-22T00:00:00Z",
        )
        store = FakeStore()
        guard_calls = 0

        def stop_guard() -> None:
            nonlocal guard_calls
            guard_calls += 1
            raise RuntimeError("online write window is closed")

        with self.assertRaisesRegex(RuntimeError, "online write window is closed"):
            publish_online_objects(
                store=store,
                objects=objects,
                hard_stop_bytes=100000,
                before_write=stop_guard,
            )
        self.assertEqual(guard_calls, 1)
        self.assertEqual(store.write_order, [])


if __name__ == "__main__":
    unittest.main()
