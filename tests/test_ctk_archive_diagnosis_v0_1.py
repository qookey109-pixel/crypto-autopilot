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
from crypto_autopilot.history import ctk_diagnosis_v0_1 as diagnosis

ROOT = Path(__file__).resolve().parents[1]
ENV = {
    "GITHUB_REPOSITORY": "qookey109-pixel/crypto-autopilot",
    "GITHUB_REF": "refs/heads/main",
    "GITHUB_EVENT_NAME": "workflow_dispatch",
    "GITHUB_RUN_ATTEMPT": "1",
}
NOW = datetime(2026, 9, 12, 8, tzinfo=timezone.utc)


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


class CtkFifteenMinuteDiagnosisTests(unittest.TestCase):
    def setUp(self):
        self.start = int(datetime(2025, 4, 1, tzinfo=timezone.utc).timestamp() * 1000)
        self.times = list(range(self.start, self.start + 30 * 86_400_000, 900_000))
        gap_start = 9 * 96 + 20
        self.missing = set(self.times[gap_start:gap_start + 41])
        monthly_times = [time_ms for time_ms in self.times if time_ms not in self.missing]
        self.monthly, self.monthly_checksum = self.archive(diagnosis.KEY, monthly_times)
        self.daily = {}
        missing_days = sorted({
            datetime.fromtimestamp(t / 1000, timezone.utc).day for t in self.missing
        })
        days = sorted(set(missing_days) | {1})
        for day in days:
            key = BinanceVisionArchiveKey(
                "klines", "daily", "CTKUSDT", "15m", f"2025-04-{day:02d}"
            )
            payload, checksum = self.archive(
                key, self.times[(day - 1) * 96:day * 96]
            )
            self.daily[key.url] = payload
            self.daily[key.checksum_url] = checksum.encode()

    @staticmethod
    def archive(key, timestamps, close="1.5"):
        csv_text = "\n".join(
            f"{time_ms},1,2,0.5,{close},1,{time_ms + 899_999},1,1,1,1,0"
            for time_ms in timestamps
        )
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr(key.csv_filename, csv_text)
        payload = output.getvalue()
        checksum = hashlib.sha256(payload).hexdigest() + "  " + key.filename
        return payload, checksum

    def reader(self):
        return FakeReader({
            diagnosis.KEY.url: self.monthly,
            diagnosis.KEY.checksum_url: self.monthly_checksum.encode(),
            **self.daily,
        })

    def test_candidate_proves_frozen_gap_shape_without_repair(self):
        reader = self.reader()
        with patch.object(
            diagnosis, "EXPECTED_SHA", hashlib.sha256(self.monthly).hexdigest()
        ):
            report = diagnosis.diagnose(reader)
        self.assertEqual(
            report["status"], "REPAIR_CANDIDATE_REQUIRES_PUBLICATION_AUTHORITY"
        )
        self.assertEqual(report["observed_monthly_rows"], 2839)
        self.assertEqual(report["candidate_row_count"], 2880)
        self.assertEqual(report["inserted_rows"], 41)
        self.assertEqual(report["missing_bars"], 41)
        self.assertEqual(report["gap_count"], 1)
        self.assertEqual(report["overlap_day"], "2025-04-01")
        self.assertEqual(report["raw_overlap_rows_verified"], 96)
        self.assertFalse(report["production_repair_performed"])
        self.assertFalse(report["r2_accessed"])
        self.assertNotIn("candles", report)
        self.assertLessEqual(len(reader.calls), diagnosis.MAX_REQUESTS)

    def test_revision_stops_before_daily_requests(self):
        reader = self.reader()
        with patch.object(diagnosis, "EXPECTED_SHA", "0" * 64):
            report = diagnosis.diagnose(reader)
        self.assertEqual(report["status"], "SOURCE_REVISION_REVIEW_REQUIRED")
        self.assertEqual(len(reader.calls), 2)

    def test_missing_daily_and_overlap_conflict_fail_closed(self):
        missing_reader = self.reader()
        daily_zip = next(
            key for key in missing_reader.values
            if key.endswith(".zip") and "daily" in key and "2025-04-10" in key
        )
        missing_reader.values.pop(daily_zip)
        with patch.object(
            diagnosis, "EXPECTED_SHA", hashlib.sha256(self.monthly).hexdigest()
        ):
            unavailable = diagnosis.diagnose(missing_reader)
        self.assertEqual(unavailable["status"], "DAILY_ARCHIVE_UNAVAILABLE")

        key = BinanceVisionArchiveKey(
            "klines", "daily", "CTKUSDT", "15m", "2025-04-01"
        )
        payload, checksum = self.archive(key, self.times[:96], close="1.6")
        conflict_reader = self.reader()
        conflict_reader.values[key.url] = payload
        conflict_reader.values[key.checksum_url] = checksum.encode()
        with patch.object(
            diagnosis, "EXPECTED_SHA", hashlib.sha256(self.monthly).hexdigest()
        ):
            with self.assertRaisesRegex(
                diagnosis.DiagnosisError, "RAW_OVERLAP_MISMATCH"
            ):
                diagnosis.diagnose(conflict_reader)

    def test_authority_and_workflow_preserve_boundary(self):
        diagnosis.load_authority(ROOT, ENV, NOW)
        config = json.loads((ROOT / diagnosis.CONFIG).read_text())
        receipt = json.loads((ROOT / diagnosis.RECEIPT).read_text())
        self.assertEqual(
            hashlib.sha256((ROOT / diagnosis.CONFIG).read_bytes()).hexdigest(),
            diagnosis.CONFIG_SHA,
        )
        self.assertEqual(config["symbol"], "CTKUSDT")
        self.assertEqual(config["interval"], "15m")
        self.assertEqual(config["period"], "2025-04")
        self.assertEqual(config["observed_monthly_rows"], 2839)
        self.assertEqual(config["expected_monthly_rows"], 2880)
        self.assertEqual(config["expected_missing_bars"], 41)
        self.assertEqual(config["maximum_public_requests"], 8)
        self.assertEqual(config["maximum_daily_archives"], 3)
        for key in (
            "r2_access",
            "production_repair_authorized",
            "source_switch_authorized",
            "pionex_native_relabel_authorized",
            "holdout_access_authorized",
            "trading_authorized",
            "automatic_model_promotion_authorized",
        ):
            self.assertFalse(config[key])
        for key in (
            "r2_access_authorized",
            "production_repair_authorized",
            "source_switch_authorized",
            "pionex_native_relabel_authorized",
            "holdout_access_authorized",
            "trading_authorized",
            "automatic_model_promotion_authorized",
            "automatic_schedule_authorized",
        ):
            self.assertFalse(receipt[key])

        workflow = (
            ROOT / ".github/workflows/ctk-archive-diagnosis-v0-1.yml"
        ).read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        self.assertIn("python scripts/diagnose_ctk_archive_v0_1.py", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("secrets.", workflow)
        self.assertNotIn("R2_", workflow)

    def test_wrong_origin_or_expiry_fails_closed(self):
        for key, value in (
            ("GITHUB_REPOSITORY", "other/repo"),
            ("GITHUB_REF", "refs/heads/research/test"),
            ("GITHUB_EVENT_NAME", "schedule"),
            ("GITHUB_RUN_ATTEMPT", "2"),
        ):
            with self.subTest(key=key), self.assertRaises(diagnosis.DiagnosisError):
                diagnosis.load_authority(ROOT, dict(ENV, **{key: value}), NOW)
        with self.assertRaises(diagnosis.DiagnosisError):
            diagnosis.load_authority(
                ROOT, ENV, datetime(2026, 10, 1, tzinfo=timezone.utc)
            )

    def test_transport_scope_and_byte_budget_block_before_extra_network(self):
        reader = diagnosis.PublicReader()
        with patch.object(diagnosis, "clock_gate"), patch.object(
            reader.opener, "open"
        ) as network:
            with self.assertRaises(diagnosis.DiagnosisError):
                reader("https://example.com")
            reader.requests = diagnosis.MAX_REQUESTS
            with self.assertRaises(diagnosis.DiagnosisError):
                reader(diagnosis.KEY.url)
            network.assert_not_called()

        reader = diagnosis.PublicReader()
        reader.total_bytes = diagnosis.MAX_TOTAL_BYTES - 10
        with patch.object(diagnosis, "clock_gate"), patch.object(
            reader.opener, "open"
        ) as network:
            response = network.return_value.__enter__.return_value
            response.read.return_value = b"x" * 10
            with self.assertRaises(diagnosis.DiagnosisError):
                reader(diagnosis.KEY.url)
            network.assert_called_once()


if __name__ == "__main__":
    unittest.main()
