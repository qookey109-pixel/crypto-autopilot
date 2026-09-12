from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("delivery", ROOT / "scripts/build_delivery_overview.py")
delivery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delivery)


class DeliveryOverviewTests(unittest.TestCase):
    def test_evidence_drives_counts_and_scope(self):
        summary, schedule, progress = delivery.overview()
        self.assertIn("8/10 分片", summary)
        self.assertIn("完整模擬尚未就緒", summary)
        self.assertIn("15 筆成交", summary)
        self.assertIn("每日偶數小時 :23", schedule)
        self.assertIn("capture 跳過", schedule)
        self.assertEqual(progress["sourceRunId"], 34680188351)
        self.assertEqual(progress["shardsComplete"], 8)

    def test_mismatched_history_and_unsafe_readiness_fail(self):
        original = delivery.read_json
        for change in ("progress", "full_ready", "provider", "authority"):
            def mutated(path, root=ROOT):
                value = copy.deepcopy(original(path, root))
                if path == "research/status/simulation-readiness-v0-1.json":
                    if change == "progress":
                        value["binance_core_100_history"]["completed_shards"] = 10
                    if change == "full_ready":
                        value["full_simulation_ready"] = True
                if path.endswith("history-run-34680188351-log-observation.json"):
                    if change == "provider":
                        value["report"]["provider"] = "pionex"
                    if change == "authority":
                        value["report"]["authority"]["live_trading_authorized"] = True
                return value
            with self.subTest(change=change), patch.object(delivery, "read_json", mutated):
                with self.assertRaises(ValueError):
                    delivery.overview()

    def test_generated_home_is_reproducible_and_missing_markers_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            site = Path(folder)
            (site / "data").mkdir()
            (site / "index.html").write_text((ROOT / "web/index.html").read_text())
            delivery.build(site)
            first = (site / "index.html").read_bytes()
            delivery.build(site)
            self.assertEqual(first, (site / "index.html").read_bytes())
            self.assertEqual(json.loads((site / "data/history-progress.json").read_text())["shardsComplete"], 8)
            (site / "index.html").write_text("missing template markers")
            with self.assertRaises(ValueError):
                delivery.build(site)

    def test_checked_in_view_matches_generated_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            site = Path(folder)
            (site / "data").mkdir()
            (site / "index.html").write_text((ROOT / "web/index.html").read_text())
            delivery.build(site)
            self.assertEqual((site / "index.html").read_bytes(), (ROOT / "web/index.html").read_bytes())
            self.assertEqual((site / "data/history-progress.json").read_bytes(), (ROOT / "web/data/history-progress.json").read_bytes())

    def test_ctk_artifact_bytes_and_report_scope(self):
        receipt = delivery.read_json("research/receipts/2026-09-12-ctk-lifecycle-v0-3-run-34687012733-evidence.json")
        payload = (ROOT / receipt["report_path"]).read_bytes()
        self.assertEqual(len(payload), receipt["report_bytes"])
        self.assertEqual(delivery.hashlib.sha256(payload).hexdigest(), receipt["report_sha256"])
        report = json.loads(payload)
        config = (ROOT / "config/ctk_lifecycle_diagnosis_v0_3.json").read_bytes()
        self.assertEqual(report["config_sha256"], delivery.hashlib.sha256(config).hexdigest())
        self.assertEqual(report["status"], "LIFECYCLE_SHAPE_CHARACTERIZED")
        self.assertFalse(receipt["authority"]["lifecycle_exception"])
        self.assertEqual(receipt["handoff_discrepancy"]["status"], "REVIEW_REQUIRED")
