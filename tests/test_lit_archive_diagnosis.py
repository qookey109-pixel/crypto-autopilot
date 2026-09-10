from __future__ import annotations

import hashlib
import io
import json
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from crypto_autopilot.binance.vision import BinanceVisionArchiveKey
from crypto_autopilot.history import lit_diagnosis as diagnosis

ROOT = Path(__file__).resolve().parents[1]
ENV = {
    "GITHUB_REPOSITORY": "qookey109-pixel/crypto-autopilot",
    "GITHUB_REF": "refs/heads/main",
    "GITHUB_EVENT_NAME": "workflow_dispatch",
    "GITHUB_RUN_ATTEMPT": "1",
}
NOW = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)


class FakeReader:
    def __init__(self, values):
        self.values = values
        self.allowed = {diagnosis.KEY.url, diagnosis.KEY.checksum_url}
        self.calls = []

    def allow_day(self, key):
        self.allowed.update((key.url, key.checksum_url))

    def __call__(self, url):
        if url not in self.allowed:
            raise AssertionError("unexpected URL")
        self.calls.append(url)
        if url not in self.values:
            raise diagnosis.DiagnosisError("OFFICIAL_ARCHIVE_NOT_FOUND")
        return self.values[url]


class LitDiagnosisTests(unittest.TestCase):
    def setUp(self):
        self.start = int(datetime(2025, 12, 1, tzinfo=timezone.utc).timestamp() * 1000)
        self.times = list(range(self.start, self.start + 31 * 86_400_000, 900_000))
        self.missing = set(self.times[120:190])
        self.monthly, self.monthly_checksum = self.archive(diagnosis.KEY, [x for x in self.times if x not in self.missing])
        self.daily = {}
        for day in (1, 2, 3):
            key = BinanceVisionArchiveKey("klines", "daily", "LITUSDT", "15m", f"2025-12-{day:02d}")
            payload, checksum = self.archive(key, self.times[(day - 1) * 96:day * 96])
            self.daily[key.url] = payload
            self.daily[key.checksum_url] = checksum

    @staticmethod
    def archive(key, timestamps, close="1.5"):
        csv = "\n".join(f"{t},1,2,0.5,{close},1,{t + 899999}" for t in timestamps)
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w") as zip_file:
            zip_file.writestr(key.csv_filename, csv)
        payload = out.getvalue()
        return payload, hashlib.sha256(payload).hexdigest() + "  " + key.filename

    def reader(self):
        return FakeReader({
            diagnosis.KEY.url: self.monthly,
            diagnosis.KEY.checksum_url: self.monthly_checksum.encode(),
            **self.daily,
        })

    def test_candidate_is_aggregate_only_and_never_repairs(self):
        with patch.object(diagnosis, "EXPECTED_SHA", hashlib.sha256(self.monthly).hexdigest()):
            report = diagnosis.diagnose(self.reader())
        self.assertEqual(report["status"], "REPAIR_CANDIDATE_REQUIRES_PUBLICATION_AUTHORITY")
        self.assertEqual(report["inserted_rows"], 70)
        self.assertEqual(report["candidate_row_count"], 2976)
        self.assertFalse(report["production_repair_performed"])
        self.assertFalse(report["r2_accessed"])
        self.assertNotIn("candles", report)

    def test_revision_or_unavailable_daily_fails_closed(self):
        with patch.object(diagnosis, "EXPECTED_SHA", "0" * 64):
            revision = diagnosis.diagnose(self.reader())
        self.assertEqual(revision["status"], "SOURCE_REVISION_REVIEW_REQUIRED")
        self.daily.clear()
        with patch.object(diagnosis, "EXPECTED_SHA", hashlib.sha256(self.monthly).hexdigest()):
            unavailable = diagnosis.diagnose(self.reader())
        self.assertEqual(unavailable["status"], "DAILY_ARCHIVE_UNAVAILABLE")

    def test_authority_rejects_other_event_ref_rerun_and_expiry(self):
        diagnosis.load_authority(ROOT, ENV, NOW)
        for key, value in (
            ("GITHUB_EVENT_NAME", "schedule"),
            ("GITHUB_REF", "refs/heads/elsewhere"),
            ("GITHUB_RUN_ATTEMPT", "2"),
        ):
            with self.subTest(key=key), self.assertRaises(diagnosis.DiagnosisError):
                diagnosis.load_authority(ROOT, dict(ENV, **{key: value}), NOW)
        with self.assertRaises(diagnosis.DiagnosisError):
            diagnosis.load_authority(ROOT, ENV, datetime(2026, 10, 1, tzinfo=timezone.utc))

    def test_workflow_has_manual_diagnosis_without_secrets(self):
        text = (ROOT / ".github/workflows/lit-archive-diagnosis-v0-1.yml").read_text()
        self.assertIn("workflow_dispatch:", text)
        block = text
        self.assertIn("python scripts/diagnose_lit_archive.py", block)
        self.assertIn("lit-archive-diagnosis-", block)
        self.assertNotIn("secrets.", block)
        self.assertNotIn("R2_", block)

    def test_config_and_receipt_do_not_grant_repair_or_trading(self):
        config = json.loads((ROOT / diagnosis.CONFIG).read_text())
        receipt = json.loads((ROOT / diagnosis.RECEIPT).read_text())
        self.assertEqual(hashlib.sha256((ROOT / diagnosis.CONFIG).read_bytes()).hexdigest(), diagnosis.CONFIG_SHA)
        self.assertFalse(config["r2_access"])
        self.assertFalse(config["production_repair_authorized"])
        self.assertFalse(config["holdout_access_authorized"])
        self.assertFalse(config["trading_authorized"])
        self.assertFalse(receipt["r2_access_authorized"])
        self.assertFalse(receipt["production_repair_authorized"])
