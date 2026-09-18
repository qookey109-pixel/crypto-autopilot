from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from crypto_autopilot.paper.run_store_v0_1 import (
    LocalPaperRunStore,
    PaperRunStorePolicy,
    R2PaperRunStore,
    paper_run_store_policy_from_config,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "paper_run_store_v0_1.json"


class FakeR2:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def get_bytes_if_exists(self, key: str) -> bytes | None:
        return self.objects.get(key)

    def put_bytes(
        self,
        key: str,
        payload: bytes,
        *,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> SimpleNamespace:
        self.objects[key] = payload
        return SimpleNamespace(bytes=len(payload))


class PaperRunStoreV01Tests(unittest.TestCase):
    def test_local_store_is_content_addressed_and_idempotent(self) -> None:
        payload = {"schema": "fixture-v0.1", "value": 1}
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalPaperRunStore(Path(tmp).resolve())
            first = store.put_json("live-state", "state-1", payload)
            second = store.put_json("live-state", "state-1", payload)

            self.assertFalse(first.replayed)
            self.assertTrue(second.replayed)
            self.assertEqual(store.get_json("live-state", "state-1"), payload)

            with self.assertRaises(ValueError):
                store.put_json(
                    "live-state",
                    "state-1",
                    {"schema": "fixture-v0.1", "value": 2},
                )

    def test_local_store_requires_explicit_absolute_root(self) -> None:
        with self.assertRaises(ValueError):
            LocalPaperRunStore("relative/path")

    def test_r2_store_reuses_existing_r2_adapter_and_rejects_collision(self) -> None:
        fake = FakeR2()
        store = R2PaperRunStore(fake)  # type: ignore[arg-type]
        payload = {"schema": "fixture-v0.1", "value": 1}

        first = store.put_json("run-package", "package-1", payload)
        second = store.put_json("run-package", "package-1", payload)

        self.assertFalse(first.replayed)
        self.assertTrue(second.replayed)
        self.assertEqual(store.get_json("run-package", "package-1"), payload)

        with self.assertRaises(ValueError):
            store.put_json(
                "run-package",
                "package-1",
                {"schema": "fixture-v0.1", "value": 9},
            )

    def test_store_rejects_path_traversal_components(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalPaperRunStore(Path(tmp).resolve())
            with self.assertRaises(ValueError):
                store.put_json("../state", "id", {"x": 1})
            with self.assertRaises(ValueError):
                store.put_json("state", "../id", {"x": 1})

    def test_versioned_config_matches_policy(self) -> None:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(
            paper_run_store_policy_from_config(payload),
            PaperRunStorePolicy(),
        )
        self.assertTrue(payload["backends"]["cloudflare_r2"]["authorized"])
        self.assertFalse(
            payload["authority"]["stored_object_becomes_execution_authority"]
        )

        bad = json.loads(CONFIG.read_text(encoding="utf-8"))
        bad["authority"]["real_money_order_authorized"] = True
        with self.assertRaises(ValueError):
            paper_run_store_policy_from_config(bad)


if __name__ == "__main__":
    unittest.main()
