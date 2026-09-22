from __future__ import annotations

import io
import json
import unittest
import zipfile

from scripts.fetch_previous_research_signal_quality import (
    PreviousQualityEvidenceError,
    _extract_quality_report,
    _select_artifact,
    _select_previous_run,
)


class PreviousResearchSignalQualityEvidenceTests(unittest.TestCase):
    def test_previous_run_selection_requires_same_repo_main_and_success(self) -> None:
        runs = [
            {
                "id": 100,
                "run_attempt": 1,
                "conclusion": "success",
                "head_branch": "main",
                "repository": {"full_name": "qookey109-pixel/crypto-autopilot"},
            },
            {
                "id": 101,
                "run_attempt": 1,
                "conclusion": "failure",
                "head_branch": "main",
                "repository": {"full_name": "qookey109-pixel/crypto-autopilot"},
            },
            {
                "id": 102,
                "run_attempt": 1,
                "conclusion": "success",
                "head_branch": "feature",
                "repository": {"full_name": "qookey109-pixel/crypto-autopilot"},
            },
            {
                "id": 103,
                "run_attempt": 1,
                "conclusion": "success",
                "head_branch": "main",
                "repository": {"full_name": "someone/fork"},
            },
            {
                "id": 104,
                "run_attempt": 2,
                "conclusion": "success",
                "head_branch": "main",
                "repository": {"full_name": "qookey109-pixel/crypto-autopilot"},
            },
        ]
        selected = _select_previous_run(
            runs,
            current_run_id=105,
            repository="qookey109-pixel/crypto-autopilot",
        )
        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual(selected["id"], 104)

    def test_artifact_selection_is_exact_and_rejects_expired(self) -> None:
        artifacts = [
            {"id": 1, "name": "research-signal-quality-104-2", "expired": True},
            {"id": 2, "name": "research-signal-quality-104-1", "expired": False},
            {"id": 3, "name": "research-signal-quality-104-2", "expired": False},
        ]
        selected = _select_artifact(artifacts, run_id=104, run_attempt=2)
        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual(selected["id"], 3)

    def test_quality_zip_requires_exactly_one_safe_quality_report(self) -> None:
        report = {
            "schema": "research-signal-quality-v0.1",
            "status": "PASS",
            "quality": "METADATA_ONLY",
        }
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("quality.json", json.dumps(report))
        self.assertEqual(_extract_quality_report(buffer.getvalue()), report)

        unsafe = io.BytesIO()
        with zipfile.ZipFile(unsafe, "w") as archive:
            archive.writestr("../quality.json", json.dumps(report))
        with self.assertRaises(PreviousQualityEvidenceError):
            _extract_quality_report(unsafe.getvalue())


if __name__ == "__main__":
    unittest.main()
