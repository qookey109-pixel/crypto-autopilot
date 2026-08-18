from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from crypto_autopilot.storage.m1a_dataset import materialize_m1a_dataset
from crypto_autopilot.storage.r2 import R2ObjectReceipt


class FakeStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_bytes(
        self,
        key: str,
        payload: bytes,
        *,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> R2ObjectReceipt:
        del content_type, metadata
        self.objects[key] = payload
        return R2ObjectReceipt(
            bucket="test-bucket",
            key=key,
            bytes=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
            etag="test-etag",
        )

    def get_bytes_verified(self, key: str, *, expected_sha256: str) -> bytes:
        payload = self.objects[key]
        actual = hashlib.sha256(payload).hexdigest()
        if actual != expected_sha256:
            raise ValueError("sha mismatch")
        return payload


class M1ADatasetStorageTest(unittest.TestCase):
    def test_materializes_objects_manifest_and_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "acquisition"
            input_dir.mkdir()

            intervals = ["15M", "60M", "4H"]
            results = []
            for interval, step_ms in [("15M", 900_000), ("60M", 3_600_000), ("4H", 14_400_000)]:
                relative = Path("candles") / "BTC_USDT_PERP" / f"{interval}.json"
                source_path = input_dir / relative
                source_path.parent.mkdir(parents=True, exist_ok=True)
                candles = [
                    {
                        "time_ms": 1786348800000,
                        "open": 100.0,
                        "high": 102.0,
                        "low": 99.0,
                        "close": 101.0,
                        "volume": 10.0,
                    },
                    {
                        "time_ms": 1786348800000 + step_ms,
                        "open": 101.0,
                        "high": 103.0,
                        "low": 100.0,
                        "close": 102.0,
                        "volume": 11.0,
                    },
                ]
                source_path.write_text(
                    json.dumps(
                        {
                            "audit": {"ok": True},
                            "candles": candles,
                            "interval": interval,
                            "requested_end_ms": 1786953599999,
                            "requested_start_ms": 1786348800000,
                            "symbol": "BTC_USDT_PERP",
                        }
                    ),
                    encoding="utf-8",
                )
                results.append(
                    {
                        "audit_ok": True,
                        "candles": 2,
                        "file": str(relative),
                        "interval": interval,
                        "symbol": "BTC_USDT_PERP",
                    }
                )

            source_receipt = {
                "audit_pass": True,
                "intervals": intervals,
                "requested_end_ms": 1786953599999,
                "requested_start_ms": 1786348800000,
                "results": results,
            }
            (input_dir / "receipt.json").write_text(json.dumps(source_receipt), encoding="utf-8")

            authority = {
                "acquisition_summary": {"total_candles": 6},
                "audit": {"pass": True},
                "authority": {
                    "artifact_sha256": "a" * 64,
                    "commit": "b" * 40,
                    "github_actions_run_id": 12345,
                },
                "sample": {"intervals": intervals},
                "selected_universe": [{"symbol": "BTC_USDT_PERP"}],
                "source": "pionex_public_futures",
            }
            authority_path = root / "authority.json"
            authority_path.write_text(json.dumps(authority), encoding="utf-8")

            store = FakeStore()
            manifest, receipt = materialize_m1a_dataset(
                input_dir=input_dir,
                authority_receipt_path=authority_path,
                store=store,
                storage_run_id="m1b-m1a-test-1",
                created_at=datetime(2026, 8, 18, 2, 30, tzinfo=timezone.utc),
            )

            self.assertEqual(manifest["object_count"], 3)
            self.assertEqual(manifest["total_rows"], 6)
            self.assertEqual(receipt["status"], "PASS")
            self.assertEqual(receipt["total_rows"], 6)
            self.assertIn(
                "market-data/pionex/perp/BTC_USDT_PERP/15m/year=2026/month=08/candles.parquet",
                store.objects,
            )
            self.assertIn(
                "market-data/pionex/perp/BTC_USDT_PERP/1h/year=2026/candles.parquet",
                store.objects,
            )
            self.assertIn(
                "market-data/pionex/perp/BTC_USDT_PERP/4h/year=2026/candles.parquet",
                store.objects,
            )
            self.assertEqual(
                receipt["manifest"]["key"],
                "manifests/historical/year=2026/month=08/manifest-20260818T023000Z.json",
            )
            self.assertEqual(
                receipt["receipt"]["key"],
                "receipts/historical/m1b-m1a-test-1.json",
            )


if __name__ == "__main__":
    unittest.main()
