from __future__ import annotations

import hashlib
import unittest
from datetime import datetime, timezone

from crypto_autopilot.models import Candle
from crypto_autopilot.storage.historical_backfill import (
    CanonicalConflictError,
    PlannedInterruption,
    partition_specs_for_year,
    run_historical_backfill_pilot,
)
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

    def get_bytes_if_exists(self, key: str) -> bytes | None:
        return self.objects.get(key)


class FakeClient:
    def __init__(self, year: int) -> None:
        year_start_ms = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
        self.rows = {
            "15M": [
                Candle(
                    time_ms=int(datetime(year, month, 1, tzinfo=timezone.utc).timestamp() * 1000),
                    open=100.0 + month,
                    high=102.0 + month,
                    low=99.0 + month,
                    close=101.0 + month,
                    volume=10.0 + month,
                )
                for month in range(1, 13)
            ],
            "60M": [
                Candle(
                    time_ms=year_start_ms,
                    open=100.0,
                    high=102.0,
                    low=99.0,
                    close=101.0,
                    volume=10.0,
                )
            ],
            "4H": [
                Candle(
                    time_ms=year_start_ms,
                    open=100.0,
                    high=102.0,
                    low=99.0,
                    close=101.0,
                    volume=10.0,
                )
            ],
        }
        self.calls: list[tuple[str, str, int | None]] = []

    def get_klines(self, symbol, interval, *, limit=500, end_time_ms=None):
        self.calls.append((symbol, interval, end_time_ms))
        eligible = [
            item
            for item in self.rows[interval]
            if end_time_ms is None or item.time_ms <= end_time_ms
        ]
        return eligible[-limit:]


class HistoricalBackfillStorageTest(unittest.TestCase):
    def test_planned_stop_resumes_from_staging_and_then_skips_finalized(self) -> None:
        store = FakeStore()
        client = FakeClient(2025)
        fixed_now = lambda: datetime(2026, 8, 18, 4, 0, tzinfo=timezone.utc)

        with self.assertRaises(PlannedInterruption) as caught:
            run_historical_backfill_pilot(
                client=client,
                store=store,
                symbols=["BTC_USDT_PERP"],
                year=2025,
                storage_run_id="pilot-test",
                planned_stop_after_staged=1,
                now_fn=fixed_now,
            )
        self.assertEqual(caught.exception.summary["status"], "PLANNED_STOP")
        calls_after_stop = len(client.calls)
        self.assertGreater(calls_after_stop, 0)

        resumed = run_historical_backfill_pilot(
            client=client,
            store=store,
            symbols=["BTC_USDT_PERP"],
            year=2025,
            storage_run_id="pilot-test",
            now_fn=fixed_now,
        )
        self.assertEqual(resumed["status"], "PASS")
        self.assertEqual(resumed["resumed_from_staged"], 1)
        self.assertEqual(resumed["finalized_new"], 14)

        jan = partition_specs_for_year(["BTC_USDT_PERP"], 2025)[0]
        self.assertIn(jan.canonical_key, store.objects)
        self.assertIn(jan.receipt_key, store.objects)
        self.assertIn(jan.checkpoint_key, store.objects)

        calls_after_resume = len(client.calls)
        third = run_historical_backfill_pilot(
            client=client,
            store=store,
            symbols=["BTC_USDT_PERP"],
            year=2025,
            storage_run_id="pilot-test-rerun",
            now_fn=fixed_now,
        )
        self.assertEqual(third["status"], "PASS")
        self.assertEqual(third["skipped_finalized"], 14)
        self.assertEqual(len(client.calls), calls_after_resume)

    def test_refuses_to_overwrite_canonical_object_without_authority(self) -> None:
        store = FakeStore()
        client = FakeClient(2025)
        partition = partition_specs_for_year(["BTC_USDT_PERP"], 2025)[0]
        store.objects[partition.canonical_key] = b"protected-existing-object"

        with self.assertRaises(CanonicalConflictError):
            run_historical_backfill_pilot(
                client=client,
                store=store,
                symbols=["BTC_USDT_PERP"],
                year=2025,
                storage_run_id="pilot-conflict-test",
            )
        self.assertEqual(client.calls, [])


if __name__ == "__main__":
    unittest.main()
