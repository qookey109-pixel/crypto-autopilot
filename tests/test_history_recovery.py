import copy
import json
import unittest
from datetime import datetime, timezone
from crypto_autopilot.history_recovery import (
    Journal, RecoveryError, choose_shard, digest, quality_diagnostic, require_window,
)

DIAG = dict(provider="binance_usdm", dataset="klines", frequency="monthly",
            symbol="BNXUSDT", interval="15m", period="2022-08", archive_sha256="a"*64,
            row_count=2688, gap_count=1, missing_bars=288, misaligned_count=0, invalid_candle_count=0)


class Store:
    def __init__(self):
        self.data = {}
        self.fail_pointer = False
        self.writes = 0
    def get_bytes_if_exists(self, key):
        return self.data.get(key)
    def put_bytes(self, key, data, **kwargs):
        if self.fail_pointer and key.endswith("latest.json"):
            raise RuntimeError("synthetic pointer failure")
        self.writes += 1
        self.data[key] = data
    def get_bytes_verified(self, key, expected_sha256):
        data = self.data[key]
        if digest(data) != expected_sha256:
            raise RecoveryError("SHA mismatch")
        return data


class RecoveryTests(unittest.TestCase):
    def journal(self, store=None, gate=lambda: None):
        return Journal(store or Store(), "b"*64, "c"*64, gate)

    def test_rotation_and_completion(self):
        j = self.journal()
        j.load()
        completed = []
        self.assertEqual(choose_shard(3, completed, j.records), 0)
        j.append("r0", 0, "QUALITY_REJECT", DIAG)
        self.assertEqual(choose_shard(3, completed, j.records), 1)
        completed.append(1)
        j.append("r1", 1, "PASS")
        self.assertEqual(choose_shard(3, completed, j.records), 2)
        completed.append(2)
        j.append("r2", 2, "PASS")
        self.assertEqual(choose_shard(3, completed, j.records), 0)
        self.assertEqual(len(completed), 2)
        completed.append(0)
        self.assertIsNone(choose_shard(3, completed, j.records))
        restored = self.journal(j.store)
        self.assertEqual(restored.load(), j.records)

    def test_all_failed_fair_rotation(self):
        j = self.journal()
        j.load()
        for seq in range(12):
            i = choose_shard(3, [], j.records)
            self.assertEqual(i, seq % 3)
            j.append(f"r{seq}", i, "QUALITY_REJECT", DIAG)

    def test_fake_pass_duplicate_and_invalid_completion(self):
        j = self.journal()
        j.load()
        j.append("r0", 0, "PASS")
        for completed in ([], [0, 0], [True], [-1], [10]):
            with self.subTest(completed=completed), self.assertRaises(RecoveryError):
                choose_shard(3, completed, j.records)
        with self.assertRaises(RecoveryError):
            j.append("r0", 1, "PASS")

    def test_only_bounded_quality_diagnostic_is_accepted(self):
        self.assertEqual(quality_diagnostic("Binance Vision kline audit failed: " + json.dumps(DIAG)), DIAG)
        invalid = [dict(DIAG, provider="pionex"), dict(DIAG, period="2026-08"),
                   dict(DIAG, missing_bars=True), dict(DIAG, raw_rows=[]),
                   dict(DIAG, archive_sha256="bad")]
        for d in invalid:
            with self.subTest(d=d), self.assertRaises(RecoveryError):
                quality_diagnostic("Binance Vision kline audit failed: " + json.dumps(d))
        for message in ("SHA-256 mismatch", "headroom gate", "network error", "Binance Vision kline audit failed: {}"):
            with self.assertRaises(RecoveryError):
                quality_diagnostic(message)

    def test_orphan_record_blocks_next_run(self):
        s = Store()
        j = self.journal(s)
        j.load()
        s.fail_pointer = True
        with self.assertRaises(RuntimeError):
            j.append("r0", 0, "QUALITY_REJECT", DIAG)
        with self.assertRaises(RecoveryError):
            self.journal(s).load()

    def test_chain_tamper_and_binding_mismatch(self):
        j = self.journal()
        j.load()
        j.append("r0", 0, "QUALITY_REJECT", DIAG)
        original = copy.deepcopy(j.store.data)
        record = json.loads(j.store.data[j.key(0)])
        record["shard_index"] = 1
        j.store.data[j.key(0)] = json.dumps(record).encode()
        with self.assertRaises(RecoveryError):
            self.journal(j.store).load()
        j.store.data = original
        ptr = json.loads(j.store.data[j.pointer_key])
        ptr["binding"]["catalog_sha256"] = "d"*64
        j.store.data[j.pointer_key] = json.dumps(ptr).encode()
        with self.assertRaises(RecoveryError):
            self.journal(j.store).load()

    def test_stale_writer_stops(self):
        s = Store()
        a, b = self.journal(s), self.journal(s)
        a.load()
        b.load()
        a.append("a", 0, "QUALITY_REJECT", DIAG)
        with self.assertRaises(RecoveryError):
            b.append("b", 1, "PASS")

    def test_gates_prevent_writes_and_expiry_is_exclusive(self):
        s = Store()
        def denied():
            raise RecoveryError("headroom")
        j = self.journal(s, denied)
        with self.assertRaises(RecoveryError):
            j.load()
        with self.assertRaises(RecoveryError):
            j.append("r0", 0, "QUALITY_REJECT", DIAG)
        self.assertEqual(s.writes, 0)
        for date in ("2026-09-04T01:59:59+00:00", "2026-10-01T00:00:00+00:00"):
            with self.assertRaises(RecoveryError):
                require_window(datetime.fromisoformat(date))
        require_window(datetime(2026, 9, 8, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
