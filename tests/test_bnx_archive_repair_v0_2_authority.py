"""Synthetic tests for BNX 1h repair authority; no provider or R2 access."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from crypto_autopilot.history import bnx_diagnosis_v0_2 as diagnosis
from crypto_autopilot.history import bnx_repair_bundle_v0_2 as bundle
from crypto_autopilot.history import bnx_repair_v0_2 as repair_v0_2
from test_bnx_archive_diagnosis_v0_2 import BnxOneHourDiagnosisTests

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/bnx_archive_repair_v0_2.json"
RECEIPT = ROOT / "research/receipts/2026-09-12-bnx-archive-repair-v0-2-authority.json"
BUNDLE = ROOT / "config/bnx_archive_repair_bundle_v0_2.json"
BUNDLE_RECEIPT = ROOT / "research/receipts/2026-09-12-bnx-archive-repair-bundle-v0-2-authority.json"
BASE = ROOT / "config/binance_usdm_detailed_history_v0_1_2.json"
EVIDENCE = ROOT / repair_v0_2.EVIDENCE
NOW = datetime(2026, 9, 12, 3, tzinfo=timezone.utc)
ENV = {
    "GITHUB_REPOSITORY": "qookey109-pixel/crypto-autopilot",
    "GITHUB_REF": "refs/heads/main",
    "GITHUB_EVENT_NAME": "workflow_dispatch",
    "GITHUB_RUN_ATTEMPT": "1",
}

spec = importlib.util.spec_from_file_location(
    "bnx_1h_repair_wrapper", ROOT / "scripts/run_bnx_1h_repair_v0_2.py"
)
wrapper = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(wrapper)


class BnxOneHourRepairAuthorityTests(unittest.TestCase):
    def setUp(self):
        fixture = BnxOneHourDiagnosisTests()
        fixture.setUp()
        self.fixture = fixture
        self.config = json.loads(CONFIG.read_text())
        self.config["monthly_sha256"] = hashlib.sha256(fixture.monthly).hexdigest()
        self.config["daily_sha256"] = []
        for day in (1, 10, 11, 12):
            key = diagnosis.BinanceVisionArchiveKey(
                "klines", "daily", "BNXUSDT", "1h", f"2022-08-{day:02d}"
            )
            self.config["daily_sha256"].append(
                [key.period, hashlib.sha256(fixture.daily[key.url]).hexdigest()]
            )
        with patch.object(diagnosis, "EXPECTED_SHA", self.config["monthly_sha256"]):
            report = diagnosis.diagnose(fixture.reader())
        self.config["candidate_sha256"] = report["candidate_sha256"]
        self.partition = SimpleNamespace(
            symbol="BNXUSDT", interval="1h", period="2022-08",
            r2_key=repair_v0_2.DESTINATION, asset_class="crypto",
        )

    def test_authority_is_evidence_bound_and_manual_only(self):
        contract = repair_v0_2.load_contract(CONFIG, RECEIPT, BASE.read_bytes(), NOW, ENV)
        self.assertEqual(contract["candidate_rows"], 744)
        self.assertEqual(contract["shard_index"], 3)
        for key, value in (
            ("GITHUB_REPOSITORY", "other/repo"),
            ("GITHUB_REF", "refs/heads/research/test"),
            ("GITHUB_EVENT_NAME", "schedule"),
            ("GITHUB_RUN_ATTEMPT", "2"),
        ):
            with self.subTest(key=key), self.assertRaises(repair_v0_2.RepairAuthorityError):
                repair_v0_2.load_contract(
                    CONFIG, RECEIPT, BASE.read_bytes(), NOW, dict(ENV, **{key: value})
                )
        with self.assertRaises(repair_v0_2.RepairAuthorityError):
            repair_v0_2.load_contract(CONFIG, RECEIPT, BASE.read_bytes() + b" ", NOW, ENV)

    def test_tampered_frozen_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            evidence = root / repair_v0_2.EVIDENCE
            evidence.parent.mkdir(parents=True)
            (root / "config/bnx_archive_repair_v0_2.json").write_bytes(CONFIG.read_bytes())
            evidence.write_bytes(EVIDENCE.read_bytes() + b" ")
            with self.assertRaisesRegex(repair_v0_2.RepairAuthorityError, "EVIDENCE_BINDING"):
                repair_v0_2.load_contract(
                    root / "config/bnx_archive_repair_v0_2.json",
                    RECEIPT, BASE.read_bytes(), NOW, ENV,
                )

    def test_reconstruction_matches_frozen_candidate_shape(self):
        reader = self.fixture.reader()
        with patch.object(repair_v0_2, "require_clock"):
            archive, lineage = repair_v0_2.reconstruct(
                self.partition, self.config, reader_factory=lambda: reader
            )
        self.assertEqual(len(archive.candles), 744)
        self.assertEqual(lineage["original_monthly_rows"], 672)
        self.assertEqual(lineage["inserted_rows"], 72)
        self.assertEqual(lineage["overlapping_rows_verified"], 24)
        self.assertFalse(lineage["original_monthly_audit_ok"])
        self.assertEqual(lineage["diagnosis_report_sha256"], repair_v0_2.EVIDENCE_SHA)

    def test_wrong_destination_blocks_before_provider(self):
        self.partition.r2_key = "not-authorized"
        factory = Mock()
        with patch.object(repair_v0_2, "require_clock"), self.assertRaises(
            repair_v0_2.RepairAuthorityError
        ):
            repair_v0_2.reconstruct(self.partition, self.config, factory)
        factory.assert_not_called()

    def test_bundle_binds_15m_and_1h_only(self):
        loaded = bundle.load_contract(BUNDLE, BUNDLE_RECEIPT, BASE.read_bytes(), NOW, ENV)
        self.assertEqual(loaded["v0_1"]["interval"], "15m")
        self.assertEqual(loaded["v0_2"]["interval"], "1h")
        self.assertTrue(bundle.matches(SimpleNamespace(
            symbol="BNXUSDT", interval="15m", period="2022-08"
        )))
        self.assertTrue(bundle.matches(SimpleNamespace(
            symbol="BNXUSDT", interval="1h", period="2022-08"
        )))
        self.assertFalse(bundle.matches(SimpleNamespace(
            symbol="BNXUSDT", interval="4h", period="2022-08"
        )))

    def test_wrapper_serializes_correct_source_rows_from_lineage(self):
        receipt = {
            "schema": "binance-usdm-detailed-history-shard-receipt-v0.1",
            "objects": [{
                "source_archive_rows": 2688,
                "source_archive_audit_ok": False,
                "repair_lineage": {
                    "schema": "bnx-archive-repair-lineage-v0.2",
                    "original_monthly_rows": 672,
                    "original_monthly_audit_ok": False,
                },
            }],
        }
        normalized = json.loads(wrapper.canonical_json_bytes(receipt))
        self.assertEqual(normalized["objects"][0]["source_archive_rows"], 672)
        self.assertEqual(receipt["objects"][0]["source_archive_rows"], 2688)

    def test_hashes_and_workflow_keep_authority_isolated(self):
        self.assertEqual(hashlib.sha256(CONFIG.read_bytes()).hexdigest(), repair_v0_2.CONFIG_SHA)
        self.assertEqual(hashlib.sha256(BUNDLE.read_bytes()).hexdigest(), bundle.CONFIG_SHA)
        workflow = (ROOT / ".github/workflows/binance-usdm-detailed-history-v0-1.yml").read_text()
        self.assertEqual(workflow.count('cron: "23 */2 9-30 9 *"'), 1)
        backfill, rest = workflow.split("  repair-bnx-1h:", 1)
        repair_job, diagnostic = rest.split("  diagnose-bnx:", 1)
        self.assertIn("--repair-config config/bnx_archive_repair_v0_1.json", backfill)
        self.assertNotIn("bnx_archive_repair_bundle_v0_2.json", backfill)
        self.assertIn("github.event_name == 'workflow_dispatch'", repair_job)
        self.assertIn("github.ref == 'refs/heads/main'", repair_job)
        self.assertIn("--repair-config config/bnx_archive_repair_bundle_v0_2.json", repair_job)
        self.assertIn("--shard-index 3", repair_job)
        self.assertNotIn("schedule:", repair_job)
        self.assertNotIn("--repair-config", diagnostic)
        self.assertNotIn("secrets.", diagnostic)

    def test_schedule_denied_before_r2_factory(self):
        args = [
            "runner", "--output", "synthetic-report.json",
            "--recovery-config", "unused", "--recovery-authority", "unused",
            "--repair-config", str(BUNDLE), "--repair-authority", str(BUNDLE_RECEIPT),
        ]
        with patch.object(sys, "argv", args), patch.dict(
            "os.environ", dict(ENV, GITHUB_EVENT_NAME="schedule")
        ), patch.object(
            wrapper.runner, "require_ephemeral_output", side_effect=lambda p: p
        ), patch.object(wrapper.runner, "require_execution_window"), patch.object(
            wrapper.runner, "load_contract", return_value="synthetic-recovery-sha"
        ), patch.object(wrapper.runner, "create_store") as store:
            with self.assertRaises(bundle.RepairAuthorityError):
                wrapper.runner.main()
            store.assert_not_called()


if __name__ == "__main__":
    unittest.main()
