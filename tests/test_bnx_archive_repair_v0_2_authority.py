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
from crypto_autopilot.history import bnx_repair as repair_v0_1
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
        daily_sha = []
        for day in (1, 10, 11, 12):
            key = diagnosis.BinanceVisionArchiveKey(
                "klines", "daily", "BNXUSDT", "1h", f"2022-08-{day:02d}"
            )
            daily_sha.append([key.period, hashlib.sha256(fixture.daily[key.url]).hexdigest()])
        self.config["daily_sha256"] = daily_sha
        reader = fixture.reader()
        with patch.object(diagnosis, "EXPECTED_SHA", self.config["monthly_sha256"]):
            report = diagnosis.diagnose(reader)
        self.config["candidate_sha256"] = report["candidate_sha256"]
        self.partition = SimpleNamespace(
            symbol="BNXUSDT",
            interval="1h",
            period="2022-08",
            r2_key=repair_v0_2.DESTINATION,
            asset_class="crypto",
        )

    def reconstruct(self):
        reader = self.fixture.reader()
        with patch.object(repair_v0_2, "require_clock"):
            return repair_v0_2.reconstruct(
                self.partition, self.config, reader_factory=lambda: reader
            )

    def test_authority_binds_base_frozen_evidence_and_manual_main(self):
        contract = repair_v0_2.load_contract(
            CONFIG, RECEIPT, BASE.read_bytes(), now=NOW, env=ENV
        )
        self.assertEqual(contract["candidate_sha256"], "acdaee9f7aca8516040c6c8219e9c1fc4538d7beda8d7c8bc6789c97b43f200b")
        self.assertEqual(contract["shard_index"], 3)
        for key, value in (
            ("GITHUB_REPOSITORY", "other/repo"),
            ("GITHUB_REF", "refs/heads/research/test"),
            ("GITHUB_EVENT_NAME", "schedule"),
            ("GITHUB_RUN_ATTEMPT", "2"),
        ):
            with self.subTest(key=key), self.assertRaises(repair_v0_2.RepairAuthorityError):
                repair_v0_2.load_contract(
                    CONFIG, RECEIPT, BASE.read_bytes(), now=NOW, env=dict(ENV, **{key: value})
                )
        with self.assertRaises(repair_v0_2.RepairAuthorityError):
            repair_v0_2.load_contract(
                CONFIG, RECEIPT, BASE.read_bytes() + b" ", now=NOW, env=ENV
            )

    def test_tampered_frozen_evidence_fails_before_contract_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            target = root / repair_v0_2.EVIDENCE
            target.parent.mkdir(parents=True)
            (root / "config/bnx_archive_repair_v0_2.json").write_bytes(CONFIG.read_bytes())
            target.write_bytes(EVIDENCE.read_bytes() + b" ")
            with self.assertRaisesRegex(
                repair_v0_2.RepairAuthorityError, "EVIDENCE_BINDING"
            ):
                repair_v0_2.load_contract(
                    root / "config/bnx_archive_repair_v0_2.json",
                    RECEIPT,
                    BASE.read_bytes(),
                    now=NOW,
                    env=ENV,
                )

    def test_reconstruction_matches_frozen_shape_and_lineage(self):
        archive, lineage = self.reconstruct()
        self.assertEqual(len(archive.candles), 744)
        self.assertEqual(lineage["original_monthly_rows"], 672)
        self.assertEqual(lineage["inserted_rows"], 72)
        self.assertEqual(lineage["overlapping_rows_verified"], 24)
        self.assertFalse(lineage["original_monthly_audit_ok"])
        self.assertEqual(lineage["config_sha256"], repair_v0_2.CONFIG_SHA)
        self.assertEqual(lineage["diagnosis_report_sha256"], repair_v0_2.EVIDENCE_SHA)

    def test_wrong_destination_and_candidate_revision_fail_closed(self):
        self.partition.r2_key = "not-authorized"
        factory = Mock()
        with patch.object(repair_v0_2, "require_clock"), self.assertRaises(
            repair_v0_2.RepairAuthorityError
        ):
            repair_v0_2.reconstruct(self.partition, self.config, factory)
        factory.assert_not_called()

        self.partition.r2_key = repair_v0_2.DESTINATION
        self.config["candidate_sha256"] = "0" * 64
        with self.assertRaisesRegex(repair_v0_2.RepairAuthorityError, "CANDIDATE_MISMATCH"):
            self.reconstruct()

    def test_bundle_binds_both_existing_15m_and_new_1h_contracts(self):
        loaded = bundle.load_contract(
            BUNDLE, BUNDLE_RECEIPT, BASE.read_bytes(), now=NOW, env=ENV
        )
        self.assertEqual(loaded["v0_1"]["interval"], "15m")
        self.assertEqual(loaded["v0_2"]["interval"], "1h")
        self.assertEqual(bundle.SHARD_INDEX, 3)
        p15 = SimpleNamespace(symbol="BNXUSDT", interval="15m", period="2022-08")
        p1h = SimpleNamespace(symbol="BNXUSDT", interval="1h", period="2022-08")
        p4h = SimpleNamespace(symbol="BNXUSDT", interval="4h", period="2022-08")
        self.assertTrue(bundle.matches(p15))
        self.assertTrue(bundle.matches(p1h))
        self.assertFalse(bundle.matches(p4h))

    def test_wrapper_normalizes_legacy_receipt_constant_from_lineage(self):
        receipt = {
            "schema": "binance-usdm-detailed-history-shard-receipt-v0.1",
            "objects": [
                {
                    "source_archive_rows": 2688,
                    "source_archive_audit_ok": False,
                    "repair_lineage": {
                        "schema": "bnx-archive-repair-lineage-v0.2",
                        "original_monthly_rows": 672,
                        "original_monthly_audit_ok": False,
                    },
                }
            ],
        }
        normalized = json.loads(wrapper.canonical_json_bytes(receipt))
        record = normalized["objects"][0]
        self.assertEqual(record["source_archive_rows"], 672)
        self.assertFalse(record["source_archive_audit_ok"])
        self.assertEqual(receipt["objects"][0]["source_archive_rows"], 2688)

    def test_config_bundle_and_workflow_keep_new_authority_manual_only(self):
        self.assertEqual(hashlib.sha256(CONFIG.read_bytes()).hexdigest(), repair_v0_2.CONFIG_SHA)
        self.assertEqual(hashlib.sha256(BUNDLE.read_bytes()).hexdigest(), bundle.CONFIG_SHA)
        config = json.loads(CONFIG.read_text())
        bundle_config = json.loads(BUNDLE.read_text())
        self.assertFalse(config["existing_partition_overwrite_authorized"])
        self.assertFalse(config["new_schedule_authorized"])
        self.assertEqual(config["destination_key"], repair_v0_2.DESTINATION)
        self.assertFalse(bundle_config["existing_partition_overwrite_authorized"])
        self.assertFalse(bundle_config["new_schedule_authorized"])

        workflow = (ROOT / ".github/workflows/binance-usdm-detailed-history-v0-1.yml").read_text()
        self.assertEqual(workflow.count('cron: "23 */2 9-30 9 *"'), 1)
        backfill, rest = workflow.split("  repair-bnx-1h:", 1)
        repair_job, diagnostic = rest.split("  diagnose-bnx:", 1)
        self.assertIn("--repair-config config/bnx_archive_repair_v0_1.json", backfill)
        self.assertNotIn("bnx_archive_repair_bundle_v0_2.json", backfill)
        self.assertIn("github.event_name == 'workflow_dispatch'", repair_job)
        self.assertIn("github.ref == 'refs/heads/main'", repair_job)
        self.assertIn("scripts/run_bnx_1h_repair_v0_2.py", repair_job)
        self.assertIn("--repair-config config/bnx_archive_repair_bundle_v0_2.json", repair_job)
        self.assertIn("--shard-index 3", repair_job)
        self.assertNotIn("schedule:", repair_job)
        self.assertNotIn("--repair-config", diagnostic)
        self.assertNotIn("secrets.", diagnostic)

    def test_schedule_is_denied_before_r2_factory_in_manual_wrapper(self):
        args = [
            "runner",
            "--output", "synthetic-report.json",
            "--recovery-config", "unused",
            "--recovery-authority", "unused",
            "--repair-config", str(BUNDLE),
            "--repair-authority", str(BUNDLE_RECEIPT),
        ]
        with patch.object(sys, "argv", args), patch.dict(
            "os.environ", dict(ENV, GITHUB_EVENT_NAME="schedule")
        ), patch.object(wrapper.runner, "require_ephemeral_output", side_effect=lambda p: p), patch.object(
            wrapper.runner, "require_execution_window"
        ), patch.object(
            wrapper.runner, "load_contract", return_value="synthetic-recovery-sha"
        ), patch.object(wrapper.runner, "create_store") as store:
            with self.assertRaises(bundle.RepairAuthorityError):
                wrapper.runner.main()
            store.assert_not_called()


if __name__ == "__main__":
    unittest.main()
