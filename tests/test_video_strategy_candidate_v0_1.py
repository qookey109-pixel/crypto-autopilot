from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_video_strategy_candidate_v0_1.py"
spec = importlib.util.spec_from_file_location("video_strategy_candidate_v0_1", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class VideoStrategyCandidateV01Tests(unittest.TestCase):
    def valid_analysis(self):
        return {
            "strategy_name": "EMA confirmation example",
            "summary": "Research extraction only.",
            "timeframes": ["4h"],
            "markets": ["BTCUSDT"],
            "indicators": [{"name": "EMA", "parameters": {"fast": 20}, "role": "trend"}],
            "entry_rules": ["Enter only after the stated confirmation."],
            "exit_rules": ["Exit on the stated invalidation."],
            "risk_rules": ["Risk rule stated by source."],
            "claimed_metrics": [
                {"metric": "win_rate", "value": "70%", "source_locator": "12:10"}
            ],
            "uncertainties": ["Position sizing not specified."],
            "evidence": [
                {"claim": "Uses EMA confirmation", "source_locator": "03:20", "confidence": "high"}
            ],
        }

    def test_build_candidate_is_fail_closed(self):
        candidate = module.build_candidate(
            self.valid_analysis(), source="https://www.youtube.com/watch?v=example"
        )
        self.assertEqual(candidate["status"], "UNVERIFIED_RESEARCH_CANDIDATE")
        self.assertFalse(candidate["verification"]["claimed_metrics_verified"])
        self.assertFalse(candidate["verification"]["production_backtest_performed"])
        self.assertTrue(
            all(value is False for value in candidate["authority"].values())
        )

    def test_missing_evidence_locator_is_rejected(self):
        analysis = self.valid_analysis()
        analysis["evidence"][0]["source_locator"] = ""
        with self.assertRaisesRegex(ValueError, "evidence.source_locator"):
            module.build_candidate(analysis, source="video.mp4")

    def test_cli_writes_canonical_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "analysis.json"
            output = tmp_path / "candidate.json"
            source.write_text(json.dumps(self.valid_analysis()), encoding="utf-8")
            candidate = module.build_candidate(self.valid_analysis(), source="video.mp4")
            output.write_bytes(module.canonical_json_bytes(candidate))
            restored = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(restored["schema"], "video-strategy-candidate-v0.1")
            self.assertEqual(restored["source"], "video.mp4")


if __name__ == "__main__":
    unittest.main()
