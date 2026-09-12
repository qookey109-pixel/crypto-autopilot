import hashlib
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from crypto_autopilot.binance_historical import BINANCE_INTERVAL_MS
from crypto_autopilot.history.bnx_diagnosis_v0_2 import DiagnosisError
from crypto_autopilot.history.ctk_lifecycle_diagnosis_v0_3 import (
    CONFIG_SHA,
    INTERVALS,
    KEYS,
    MAX_REQUESTS,
    PublicReader,
    _missing_segments,
    load_authority,
)

ROOT = Path(__file__).resolve().parents[1]


class CtkLifecycleDiagnosisV03Tests(unittest.TestCase):
    def test_scope_is_exact_monthly_public_read_only(self):
        config = json.loads((ROOT / "config/ctk_lifecycle_diagnosis_v0_3.json").read_text())
        self.assertEqual(config["symbol"], "CTKUSDT")
        self.assertEqual(config["period"], "2025-04")
        self.assertEqual(tuple(config["intervals"]), INTERVALS)
        self.assertEqual(config["maximum_public_requests"], 6)
        self.assertEqual(config["maximum_monthly_archives"], 3)
        self.assertFalse(config["daily_archive_reads"])
        for key in (
            "r2_access",
            "raw_artifact",
            "production_repair_authorized",
            "lifecycle_publication_authorized",
            "training_cutoff_change_authorized",
            "source_switch_authorized",
            "pionex_native_relabel_authorized",
            "holdout_access_authorized",
            "trading_authorized",
            "automatic_model_promotion_authorized",
        ):
            self.assertFalse(config[key])

    def test_reader_allowlist_is_exactly_three_monthly_archives_plus_checksums(self):
        reader = PublicReader()
        expected = {
            url for key in KEYS.values() for url in (key.url, key.checksum_url)
        }
        self.assertEqual(reader.allowed, expected)
        self.assertEqual(len(expected), MAX_REQUESTS)
        for key in KEYS.values():
            self.assertEqual(key.dataset, "klines")
            self.assertEqual(key.frequency, "monthly")
            self.assertEqual(key.symbol, "CTKUSDT")
            self.assertEqual(key.period, "2025-04")

    def test_authority_is_hash_bound_fresh_main_manual_and_time_bounded(self):
        raw = (ROOT / "config/ctk_lifecycle_diagnosis_v0_3.json").read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), CONFIG_SHA)
        good_env = {
            "GITHUB_REPOSITORY": "qookey109-pixel/crypto-autopilot",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_RUN_ATTEMPT": "1",
        }
        load_authority(
            ROOT,
            env=good_env,
            now=datetime(2026, 9, 12, 9, 0, tzinfo=timezone.utc),
        )
        with self.assertRaises(DiagnosisError):
            load_authority(
                ROOT,
                env=dict(good_env, GITHUB_RUN_ATTEMPT="2"),
                now=datetime(2026, 9, 12, 9, 0, tzinfo=timezone.utc),
            )
        with self.assertRaises(DiagnosisError):
            load_authority(
                ROOT,
                env=good_env,
                now=datetime(2026, 10, 1, tzinfo=timezone.utc),
            )

    def test_missing_segment_summary_handles_exact_ctk_window(self):
        step = BINANCE_INTERVAL_MS["15m"]
        start = int(datetime(2025, 4, 1, tzinfo=timezone.utc).timestamp() * 1000)
        end = int(datetime(2025, 5, 1, tzinfo=timezone.utc).timestamp() * 1000)
        missing_start = int(datetime(2025, 4, 30, tzinfo=timezone.utc).timestamp() * 1000)
        relaunch = int(datetime(2025, 4, 30, 10, 15, tzinfo=timezone.utc).timestamp() * 1000)
        present = set(range(start, end, step)) - set(range(missing_start, relaunch, step))
        self.assertEqual(
            _missing_segments(present, step),
            [{
                "start_utc": "2025-04-30T00:00:00Z",
                "end_exclusive_utc": "2025-04-30T10:15:00Z",
                "missing_bars": 41,
            }],
        )

    def test_v0_2_success_evidence_is_exactly_frozen(self):
        report = ROOT / "research/receipts/2026-09-12-ctk-archive-diagnosis-v0-2-run-34683490666-report.json"
        evidence_path = ROOT / "research/receipts/2026-09-12-ctk-archive-diagnosis-v0-2-run-34683490666-evidence.json"
        self.assertEqual(
            hashlib.sha256(report.read_bytes()).hexdigest(),
            "dd86d17c7ff04b4ee765a1454d303c9cf163f396ef7654380ad2337d23b78332",
        )
        evidence = json.loads(evidence_path.read_text())
        self.assertEqual(evidence["run"]["head_sha"], "245c43d4104287375690e95ecc6e2473adfa19b2")
        self.assertEqual(evidence["artifact"]["artifact_id"], 10294243218)
        self.assertEqual(
            evidence["artifact"]["zip_sha256"],
            "8df846b5e5291752e7468d8525021a10333464f01ecf625e50b4707d00b8b625",
        )
        self.assertEqual(evidence["diagnosis"]["reason"], "DAILY_NOT_FULL_UTC_DAY")
        self.assertFalse(
            evidence["authority_boundaries"]["new_publication_authority_granted_by_this_evidence_freeze"]
        )

    def test_workflow_is_manual_only_secret_free_and_aggregate_only(self):
        text = (ROOT / ".github/workflows/ctk-lifecycle-diagnosis-v0-3.yml").read_text()
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("schedule:", text)
        self.assertIn("github.ref == 'refs/heads/main'", text)
        self.assertIn("persist-credentials: false", text)
        self.assertNotIn("secrets.", text)
        self.assertNotIn("R2_ACCESS_KEY", text)
        self.assertIn("public_requests", text)
        self.assertIn("ctk-lifecycle-diagnosis-v0-3-output/report.json", text)


if __name__ == "__main__":
    unittest.main()
