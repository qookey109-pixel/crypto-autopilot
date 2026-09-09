"""Synthetic cloud tests: no provider or R2 access."""
import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from crypto_autopilot.history import bnx_repair as r
from crypto_autopilot.storage.parquet import candles_to_parquet
import test_archive_repair as fixtures
from test_bnx_archive_diagnosis import FakeReader

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/bnx_archive_repair_v0_1.json"
RECEIPT = ROOT / "research/receipts/2026-09-09-bnx-archive-repair-v0-1-authority.json"
BASE = ROOT / "config/binance_usdm_detailed_history_v0_1_2.json"
NOW = datetime(2026, 9, 9, tzinfo=timezone.utc)
ENV = dict(GITHUB_REPOSITORY="qookey109-pixel/crypto-autopilot",
           GITHUB_REF="refs/heads/main", GITHUB_EVENT_NAME="schedule",
           GITHUB_RUN_ATTEMPT="1")
spec = importlib.util.spec_from_file_location("bnx_repair_history_runner", ROOT / "scripts/run_binance_detailed_history.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class MemoryStore:
    bucket = "synthetic"
    def __init__(self):
        self.data = {}
        self.writes = []
    def get_bytes_if_exists(self, key):
        return self.data.get(key)
    def put_bytes(self, key, payload, **kwargs):
        self.writes.append(key)
        self.data[key] = payload
        # The existing _put_immutable helper serializes this dataclass.
        from crypto_autopilot.storage.r2 import R2ObjectReceipt
        return R2ObjectReceipt(self.bucket, key, len(payload), hashlib.sha256(payload).hexdigest(), None)
    def get_bytes_verified(self, key, *, expected_sha256):
        payload = self.data[key]
        if hashlib.sha256(payload).hexdigest() != expected_sha256:
            raise ValueError("round-trip mismatch")
        return payload


class BNXRepairTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(CONFIG.read_text())
        self.fixture = fixtures.ArchiveRepairTests()
        self.fixture.setUp()
        self.reader = FakeReader(self.fixture)
        daily = [self.fixture.daily(day) for day in (1, 10, 11, 12)]
        # Use the reader's exact synthetic ZIP bytes, avoiding ZIP timestamp drift.
        self.config["monthly_sha256"] = hashlib.sha256(self.fixture.month).hexdigest()
        self.config["daily_sha256"] = [
            [key.period, hashlib.sha256(self.reader.data[key.url]).hexdigest()]
            for key, _, _ in daily
        ]
        candidate = self.fixture.run_repair(daily)
        payload = json.dumps([[c.time_ms, c.open, c.high, c.low, c.close, c.volume]
                              for c in candidate.candles], separators=(",", ":"), allow_nan=False).encode()
        self.config["candidate_sha256"] = hashlib.sha256(payload).hexdigest()
        self.partition = SimpleNamespace(symbol="BNXUSDT", interval="15m", period="2022-08",
                                         r2_key=r.DESTINATION, asset_class="crypto")
    def reconstruct(self):
        with patch.object(r, "require_clock"):
            return r.reconstruct(self.partition, self.config, lambda: self.reader)

    def test_authority_hash_base_and_exact_receipt(self):
        result = r.load_contract(CONFIG, RECEIPT, BASE.read_bytes(), NOW, ENV)
        self.assertEqual(result["candidate_sha256"], "24d441889b173fa85205b189c8c63d316eac34461a29476f618a640b079f26ad")
        with self.assertRaises(r.RepairAuthorityError):
            r.load_contract(CONFIG, RECEIPT, BASE.read_bytes() + b" ", NOW, ENV)
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_bytes(CONFIG.read_bytes() + b" ")
            with self.assertRaises(r.RepairAuthorityError):
                r.load_contract(bad, RECEIPT, BASE.read_bytes(), NOW, ENV)
            obj = json.loads(RECEIPT.read_text())
            obj["existing_partition_overwrite_authorized"] = True
            bad.write_text(json.dumps(obj))
            with self.assertRaises(r.RepairAuthorityError):
                r.load_contract(CONFIG, bad, BASE.read_bytes(), NOW, ENV)

    def test_main_event_attempt_and_real_window_gate(self):
        for name, value in (("GITHUB_REF", "refs/heads/test"), ("GITHUB_EVENT_NAME", "push"),
                            ("GITHUB_RUN_ATTEMPT", "2"), ("GITHUB_REPOSITORY", "other/repo")):
            with self.subTest(name=name), self.assertRaises(r.RepairAuthorityError):
                r.load_contract(CONFIG, RECEIPT, BASE.read_bytes(), NOW, dict(ENV, **{name: value}))
        r.load_contract(CONFIG, RECEIPT, BASE.read_bytes(), NOW,
                        dict(ENV, GITHUB_EVENT_NAME="workflow_dispatch"))
        for now in (datetime(2026, 9, 8, tzinfo=timezone.utc), datetime(2026, 10, 1, tzinfo=timezone.utc)):
            with self.assertRaises(r.RepairAuthorityError):
                r.load_contract(CONFIG, RECEIPT, BASE.read_bytes(), now, ENV)

    def test_reconstruction_has_full_lineage_and_preserves_failed_monthly(self):
        archive, lineage = self.reconstruct()
        self.assertEqual(len(archive.candles), 2976)
        self.assertEqual(len(self.reader.calls), 10)
        self.assertEqual(lineage["inserted_rows"], 288)
        self.assertEqual(lineage["overlapping_rows_verified"], 96)
        self.assertFalse(lineage["original_monthly_audit_ok"])
        self.assertFalse(lineage["original_monthly_archive_regraded"])
        self.assertEqual(lineage["provider"], "binance_usdm")
        self.assertEqual(lineage["config_sha256"], r.CONFIG_SHA)

    def test_monthly_revision_stops_before_daily_access(self):
        self.config["monthly_sha256"] = "0" * 64
        with self.assertRaises(r.RepairAuthorityError):
            self.reconstruct()
        self.assertEqual(len(self.reader.calls), 2)

    def test_daily_revision_stops_before_candidate(self):
        self.config["daily_sha256"][0][1] = "0" * 64
        with self.assertRaises(r.RepairAuthorityError):
            self.reconstruct()
        self.assertEqual(len(self.reader.calls), 4)

    def test_candidate_hash_mismatch_rejected(self):
        self.config["candidate_sha256"] = "0" * 64
        with self.assertRaises(r.RepairAuthorityError):
            self.reconstruct()

    def test_wrong_destination_has_no_provider_access(self):
        self.partition.r2_key = "not-authorized"
        factory = Mock()
        with patch.object(r, "require_clock"), self.assertRaises(r.RepairAuthorityError):
            r.reconstruct(self.partition, self.config, factory)
        factory.assert_not_called()

    def test_no_authority_keeps_original_ingestion_failure(self):
        with patch.object(runner, "download", return_value=b"synthetic"), \
             patch.object(runner, "ingest_kline_archive", side_effect=ValueError("original reject")), \
             patch.object(runner.bnx_repair, "reconstruct") as repair:
            with self.assertRaisesRegex(ValueError, "original reject"):
                runner.fetch_partition(self.partition, timeout_seconds=1, retries=1)
            repair.assert_not_called()

    def materialize(self, store, *, headroom=None, run_id="synthetic", clock=None):
        archive, lineage = self.reconstruct()
        item = dict(partition=self.partition, archive=archive,
                    parquet=candles_to_parquet(archive.candles), repair_lineage=lineage)
        config = json.loads(BASE.read_text())
        config["execution"]["download_workers"] = 1
        with patch.object(runner, "build_shard_plan", return_value=[self.partition]), \
             patch.object(runner, "fetch_partition", return_value=item), \
             patch.object(runner, "current_bucket_bytes", return_value=0), \
             patch.object(runner, "_ensure_reservation_headroom", side_effect=headroom), \
             patch.object(r, "require_clock", side_effect=clock):
            return runner.materialize_shard(
                store, config=config, latest=dict(catalog_key="synthetic", catalog_sha256="b" * 64),
                catalog={}, state=dict(completed_shards=[], shard_count=10),
                shard_index=0, run_id=run_id, generated_at_utc="2026-09-09T00:00:00Z",
                repair=copy.deepcopy(self.config),
            )

    def test_real_writer_lineage_receipt_state_last_and_idempotent_partition(self):
        store = MemoryStore()
        result = self.materialize(store)
        self.assertEqual(result["dataset_status"], "IN_PROGRESS")
        self.assertEqual(result["shards_complete"], 1)
        self.assertEqual(store.writes[0], r.DESTINATION)
        self.assertTrue(store.writes[-1].endswith("backfill-state.json"))
        receipt = json.loads(store.data[store.writes[-2]])
        record = receipt["objects"][0]
        self.assertEqual(record["source_archive_rows"], 2688)
        self.assertFalse(record["source_archive_audit_ok"])
        self.assertEqual(record["source_rows"], 2976)
        self.assertIn("monthly_daily", record["delivery"])
        self.assertEqual(record["repair_lineage"]["candidate_sha256"], self.config["candidate_sha256"])
        store.writes.clear()
        self.materialize(store, run_id="synthetic-resume")
        self.assertNotIn(r.DESTINATION, store.writes)

    def test_existing_conflict_never_overwrites(self):
        store = MemoryStore()
        store.data[r.DESTINATION] = b"conflicting"
        with self.assertRaises(Exception):
            self.materialize(store)
        self.assertEqual(store.writes, [])
        self.assertEqual(store.data[r.DESTINATION], b"conflicting")

    def test_headroom_blocks_all_writes(self):
        store = MemoryStore()
        with self.assertRaisesRegex(ValueError, "headroom"):
            self.materialize(store, headroom=ValueError("headroom"))
        self.assertEqual(store.writes, [])

    def test_workflow_keeps_exact_cron_and_existing_secret_boundary(self):
        workflow = (ROOT / ".github/workflows/binance-usdm-detailed-history-v0-1.yml").read_text()
        self.assertEqual(workflow.count('cron: "23 */6 4-30 9 *"'), 1)
        self.assertIn("--repair-config config/bnx_archive_repair_v0_1.json", workflow)
        diagnostic = workflow.split("  diagnose-bnx:")[1]
        self.assertNotIn("--repair-config", diagnostic)
        self.assertNotIn("secrets.", diagnostic)

    def test_expiry_after_download_prevents_all_writes(self):
        store = MemoryStore()
        with self.assertRaisesRegex(r.RepairAuthorityError, "expired"):
            self.materialize(store, clock=[None, r.RepairAuthorityError("expired")])
        self.assertEqual(store.writes, [])

    def test_failed_readback_cannot_publish_receipt_or_complete_state(self):
        store = MemoryStore()
        with patch.object(store, "get_bytes_verified", side_effect=ValueError("bad readback")):
            with self.assertRaisesRegex(ValueError, "bad readback"):
                self.materialize(store)
        self.assertEqual(store.writes, [r.DESTINATION])

    def test_actual_cli_denies_push_before_r2_factory(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = ["runner", "--output", str(Path(tmp) / "report.json"),
                    "--recovery-config", "unused", "--recovery-authority", "unused",
                    "--repair-config", str(CONFIG), "--repair-authority", str(RECEIPT)]
            with patch("sys.argv", args), patch.dict("os.environ", dict(ENV, GITHUB_EVENT_NAME="push")), \
                 patch.object(runner, "require_ephemeral_output", side_effect=lambda p: p), \
                 patch.object(runner, "require_execution_window"), \
                 patch.object(runner, "load_contract", return_value="synthetic-recovery-sha"), \
                 patch.object(runner, "create_store") as store, \
                 patch.object(r, "require_clock"):
                with self.assertRaises(r.RepairAuthorityError):
                    runner.main()
                store.assert_not_called()
