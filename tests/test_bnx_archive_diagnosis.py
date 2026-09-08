import hashlib
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from crypto_autopilot.history import bnx_diagnosis as d
import test_archive_repair as fixtures

ROOT = Path(__file__).resolve().parents[1]


class FakeReader:
    def __init__(self, fixture):
        self.allowed = {d.KEY.url, d.KEY.checksum_url}
        self.data = {d.KEY.url: fixture.month, d.KEY.checksum_url: fixture.checksum.encode()}
        self.calls = []
        for day in (1, 10, 11, 12):
            key, archive, checksum = fixture.daily(day)
            self.data[key.url] = archive
            self.data[key.checksum_url] = checksum.encode()
    def allow_day(self, key):
        self.allowed.update((key.url, key.checksum_url))
    def __call__(self, url):
        if url not in self.allowed:
            raise AssertionError("unexpected URL")
        self.calls.append(url)
        if url not in self.data:
            raise d.DiagnosisError("OFFICIAL_ARCHIVE_NOT_FOUND")
        return self.data[url]


class DiagnosisTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ArchiveRepairTests()
        self.fixture.setUp()
        self.reader = FakeReader(self.fixture)
        self.sha = hashlib.sha256(self.fixture.month).hexdigest()

    def test_official_daily_candidate_stays_unpublished(self):
        with patch.object(d, "EXPECTED_SHA", self.sha):
            report = d.diagnose(self.reader)
        self.assertEqual(report["status"], "REPAIR_CANDIDATE_REQUIRES_PUBLICATION_AUTHORITY")
        self.assertEqual(report["inserted_rows"], 288)
        self.assertEqual(report["candidate_row_count"], 2976)
        self.assertEqual(len(self.reader.calls), 10)
        self.assertFalse(report["production_repair_performed"])
        self.assertNotIn("candles", report)
        self.assertNotIn("1.5", json.dumps(report))

    def test_revision_stops_before_daily_requests(self):
        with patch.object(d, "EXPECTED_SHA", "0" * 64):
            report = d.diagnose(self.reader)
        self.assertEqual(report["status"], "SOURCE_REVISION_REVIEW_REQUIRED")
        self.assertEqual(len(self.reader.calls), 2)

    def test_missing_daily_cannot_fake_completion(self):
        self.reader.data.pop(next(k for k in self.reader.data if k.endswith("2022-08-10.zip")))
        with patch.object(d, "EXPECTED_SHA", self.sha):
            report = d.diagnose(self.reader)
        self.assertEqual(report["status"], "DAILY_ARCHIVE_UNAVAILABLE")

    def test_overlap_conflict_is_rejected(self):
        key, archive, checksum = self.fixture.daily(1, close="1.6")
        self.reader.data.update({key.url: archive, key.checksum_url: checksum.encode()})
        with patch.object(d, "EXPECTED_SHA", self.sha):
            report = d.diagnose(self.reader)
        self.assertEqual(report["status"], "DAILY_RECONCILIATION_REJECTED")

    def test_contract_and_main_dispatch_gate(self):
        now = datetime(2026, 9, 9, tzinfo=timezone.utc)
        env = dict(GITHUB_REPOSITORY="qookey109-pixel/crypto-autopilot",
                   GITHUB_REF="refs/heads/main", GITHUB_EVENT_NAME="workflow_dispatch",
                   GITHUB_RUN_ATTEMPT="1")
        d.load_authority(ROOT, env, now)
        for key, val in (("GITHUB_REF", "refs/heads/test"), ("GITHUB_EVENT_NAME", "schedule"),
                         ("GITHUB_RUN_ATTEMPT", "2"), ("GITHUB_REPOSITORY", "other/repo")):
            with self.subTest(key=key), self.assertRaises(d.DiagnosisError):
                d.load_authority(ROOT, dict(env, **{key: val}), now)
        with self.assertRaises(d.DiagnosisError):
            d.load_authority(ROOT, env, datetime(2026, 10, 1, tzinfo=timezone.utc))

    def test_transport_limits_block_without_opening_network(self):
        reader = d.PublicReader()
        with patch.object(d, "clock_gate"), patch.object(reader.opener, "open") as network:
            with self.assertRaises(d.DiagnosisError):
                reader("https://example.com")
            reader.requests = 12
            with self.assertRaises(d.DiagnosisError):
                reader(d.KEY.url)
            network.assert_not_called()

    def test_denied_authority_creates_no_reader(self):
        with patch.object(d, "load_authority", side_effect=d.DiagnosisError("DENIED")), patch.object(d, "PublicReader") as reader:
            with self.assertRaises(d.DiagnosisError):
                d.run(ROOT, Path("never-written.json"))
            reader.assert_not_called()
