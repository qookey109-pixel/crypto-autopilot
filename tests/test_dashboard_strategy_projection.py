from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_strategy_projection as builder


ROOT = Path(__file__).resolve().parents[1]


class DashboardStrategyProjectionTests(unittest.TestCase):
    def test_checked_in_projection_matches_current_configs(self) -> None:
        expected = builder.build_projection(checked_in_fixture=True)
        actual = json.loads((ROOT / "web/data/strategy.json").read_text(encoding="utf-8"))
        self.assertEqual(actual, expected)
        self.assertIs(actual["authority"], False)
        self.assertIsNone(actual["generatedAtUtc"])
        self.assertEqual(actual["summary"]["candidateCount"], 120)
        self.assertEqual(actual["summary"]["edgeMethodCount"], 6)
        self.assertEqual(actual["summary"]["shadowFeatureGroupCount"], 8)
        self.assertTrue(all(value is False for value in actual["safetyBoundary"].values()))

    def test_projection_fails_closed_if_shadow_gains_provider_access(self) -> None:
        shadow = json.loads(builder.SOURCES["shadow"].read_text(encoding="utf-8"))
        shadow["authority"]["provider_reads_authorized"] = True
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "shadow.json"
            changed.write_text(json.dumps(shadow), encoding="utf-8")
            with patch.dict(builder.SOURCES, {"shadow": changed}):
                with self.assertRaisesRegex(RuntimeError, "must remain false"):
                    builder.build_projection(checked_in_fixture=True)

    def test_projection_fails_closed_if_research_loop_gains_automatic_promotion(self) -> None:
        loop = json.loads(builder.SOURCES["research_loop"].read_text(encoding="utf-8"))
        loop["composition"]["automatic_promotion"] = True
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "loop.json"
            changed.write_text(json.dumps(loop), encoding="utf-8")
            with patch.dict(builder.SOURCES, {"research_loop": changed}):
                with self.assertRaisesRegex(RuntimeError, "automatic promotion"):
                    builder.build_projection(checked_in_fixture=True)


if __name__ == "__main__":
    unittest.main()
