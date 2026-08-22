from __future__ import annotations

import unittest

from crypto_autopilot.online_r2_training import build_online_objects, publish_online_objects
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


if __name__ == "__main__":
    unittest.main()
