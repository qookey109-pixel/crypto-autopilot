import hashlib
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from crypto_autopilot.binance.vision import BinanceVisionEvidenceError
from crypto_autopilot.history.bnx_diagnosis_v0_2 import DiagnosisError
from crypto_autopilot.history.ctk_diagnosis_v0_2 import (
    CONFIG_SHA,
    REASON_ALLOWLIST,
    REASON_MAP,
    _safe_reconcile_reason,
    load_authority,
)

ROOT = Path(__file__).resolve().parents[1]


class CtkFifteenMinuteDiagnosisV02Tests(unittest.TestCase):
    def test_v0_2_keeps_v0_1_read_budget_and_zero_write_authority(self):
        v1 = json.loads((ROOT / "config/ctk_archive_diagnosis_v0_1.json").read_text())
        v2 = json.loads((ROOT / "config/ctk_archive_diagnosis_v0_2.json").read_text())
        for key in (
            "provider",
            "delivery",
            "symbol",
            "interval",
            "period",
            "monthly_sha256",
            "observed_monthly_rows",
            "expected_monthly_rows",
            "expected_missing_bars",
            "expected_gap_count",
            "maximum_public_requests",
            "maximum_daily_archives",
            "maximum_response_bytes",
            "maximum_total_response_bytes",
            "retries",
            "redirects",
        ):
            self.assertEqual(v2[key], v1[key])
        for key in (
            "r2_access",
            "raw_artifact",
            "production_repair_authorized",
            "source_switch_authorized",
            "pionex_native_relabel_authorized",
            "holdout_access_authorized",
            "trading_authorized",
            "automatic_model_promotion_authorized",
        ):
            self.assertFalse(v2[key])
        self.assertEqual(v2["source_failure_run_id"], 34682130869)
        self.assertEqual(
            v2["source_failure_report_sha256"],
            "c972f754c8e03bba606f7392e2ac46c2822aade7d8287cf631315b073d6c63ad",
        )
        self.assertEqual(set(v2["reconciliation_reason_allowlist"]), REASON_ALLOWLIST)

    def test_authority_is_hash_bound_fresh_main_manual_and_time_bounded(self):
        raw = (ROOT / "config/ctk_archive_diagnosis_v0_2.json").read_bytes()
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
            now=datetime(2026, 9, 12, 8, 1, tzinfo=timezone.utc),
        )
        bad_env = dict(good_env, GITHUB_RUN_ATTEMPT="2")
        with self.assertRaises(DiagnosisError):
            load_authority(
                ROOT,
                env=bad_env,
                now=datetime(2026, 9, 12, 8, 1, tzinfo=timezone.utc),
            )
        with self.assertRaises(DiagnosisError):
            load_authority(
                ROOT,
                env=good_env,
                now=datetime(2026, 10, 1, tzinfo=timezone.utc),
            )

    def test_reconciliation_reason_is_allowlisted_and_never_leaks_unknown_text(self):
        for raw, safe in REASON_MAP.items():
            self.assertEqual(
                _safe_reconcile_reason(BinanceVisionEvidenceError(raw)),
                safe,
            )
            self.assertIn(safe, REASON_ALLOWLIST)
        unknown = _safe_reconcile_reason(
            BinanceVisionEvidenceError("provider-private-message-should-not-leak")
        )
        self.assertEqual(unknown, "RECONCILIATION_REJECTED_UNKNOWN")
        self.assertNotIn("provider-private", unknown)

    def test_v0_1_failure_evidence_and_report_are_exactly_frozen(self):
        report = ROOT / "research/receipts/2026-09-12-ctk-archive-diagnosis-v0-1-run-34682130869-report.json"
        evidence_path = ROOT / "research/receipts/2026-09-12-ctk-archive-diagnosis-v0-1-run-34682130869-evidence.json"
        self.assertEqual(
            hashlib.sha256(report.read_bytes()).hexdigest(),
            "c972f754c8e03bba606f7392e2ac46c2822aade7d8287cf631315b073d6c63ad",
        )
        evidence = json.loads(evidence_path.read_text())
        self.assertEqual(evidence["run"]["head_sha"], "e44b810069fc25e34ab5485d0e915d4b010f7b2d")
        self.assertEqual(evidence["artifact"]["artifact_id"], 10294405989)
        self.assertEqual(
            evidence["artifact"]["zip_sha256"],
            "de04fdeaa722118adb7015eeff0fb86dcd8c3488d181b4e40f9b0ddf00bbc14c",
        )
        self.assertEqual(
            evidence["diagnosis"]["status"],
            "DAILY_RECONCILIATION_REJECTED",
        )
        self.assertFalse(
            evidence["authority_boundaries"]["new_repair_authority_granted_by_this_evidence_freeze"]
        )

    def test_workflow_is_manual_only_secret_free_and_aggregate_only(self):
        text = (ROOT / ".github/workflows/ctk-archive-diagnosis-v0-2.yml").read_text()
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("schedule:", text)
        self.assertIn("github.ref == 'refs/heads/main'", text)
        self.assertIn("persist-credentials: false", text)
        self.assertNotIn("secrets.", text)
        self.assertNotIn("R2_ACCESS_KEY", text)
        self.assertIn("raw_rows_emitted", text)
        self.assertIn("reconciliation_rejection_reason", text)
        self.assertIn("ctk-diagnosis-v0-2-output/report.json", text)


if __name__ == "__main__":
    unittest.main()
