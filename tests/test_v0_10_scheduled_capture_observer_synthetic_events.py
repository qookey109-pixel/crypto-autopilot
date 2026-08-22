from __future__ import annotations

import io
import json
import os
import tempfile
import textwrap
import unittest
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch


WORKFLOW = Path(".github/workflows/observe-v0-10-scheduled-capture.yml")
MATRIX = Path("config/v0_10_scheduled_capture_observer_synthetic_rehearsal_v0_1.json")

EXPECTED_JOBS = ("validate-atomic-cutover", "window-gate", "capture")
EXPECTED_CAPTURE_STEPS = (
    "Reject stale scheduled runs before provider or R2 access",
    "Capture frozen provider metadata through V0.10 successor path",
    "Assert V0.10 capture boundary",
)


def _load_matrix() -> dict[str, Any]:
    payload = json.loads(MATRIX.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError("synthetic rehearsal matrix must be an object")
    return payload


def _observer_python() -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    marker = "          python - <<'PY'\n"
    if text.count(marker) != 1:
        raise AssertionError("observer workflow must contain one embedded Python block")
    body = text.split(marker, 1)[1].split("\n          PY", 1)[0]
    return textwrap.dedent(body)


class _Response:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def _jobs(
    *,
    omit_job: str | None = None,
    omit_step: str | None = None,
    step_conclusions: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    conclusions = step_conclusions or {}
    rows: list[dict[str, Any]] = []
    for name in EXPECTED_JOBS:
        if name == omit_job:
            continue
        row: dict[str, Any] = {"name": name, "conclusion": "success", "steps": []}
        if name == "capture":
            row["steps"] = [
                {"name": step, "conclusion": conclusions.get(step, "success")}
                for step in EXPECTED_CAPTURE_STEPS
                if step != omit_step
            ]
        rows.append(row)
    return rows


def _run(
    *,
    source_run_id: int,
    source_conclusion: str = "success",
    source_created_at: str = "2026-08-27T00:17:00Z",
    jobs: list[dict[str, Any]] | None = None,
) -> tuple[str, list[str]]:
    requested: list[str] = []

    def fake_urlopen(request: urllib.request.Request, timeout: int = 20) -> _Response:
        if timeout != 20:
            raise AssertionError("observer timeout changed")
        requested.append(request.full_url)
        return _Response({"jobs": jobs if jobs is not None else _jobs()})

    with tempfile.TemporaryDirectory() as temp_dir:
        summary = Path(temp_dir) / f"summary-{source_run_id}.md"
        env = {
            "SOURCE_RUN_ID": str(source_run_id),
            "SOURCE_CONCLUSION": source_conclusion,
            "SOURCE_CREATED_AT": source_created_at,
            "GITHUB_REPOSITORY": "qookey109-pixel/crypto-autopilot",
            "GITHUB_STEP_SUMMARY": str(summary),
            "GH_TOKEN": "synthetic-placeholder-not-a-secret",
        }
        stdout = io.StringIO()
        with (
            patch.dict(os.environ, env, clear=False),
            patch.object(urllib.request, "urlopen", side_effect=fake_urlopen),
            redirect_stdout(stdout),
        ):
            exec(compile(_observer_python(), "<synthetic-observer>", "exec"), {})
    return stdout.getvalue(), requested


class ScheduledCaptureObserverSyntheticTests(unittest.TestCase):
    def test_rehearsal_matrix_is_validation_only_and_covers_required_cases(self) -> None:
        cfg = _load_matrix()
        self.assertEqual(cfg["status"], "PREPARED_VALIDATION_ONLY")
        self.assertEqual(cfg["scenario_count"], 8)
        scenario_ids = {row["id"] for row in cfg["scenarios"]}
        self.assertEqual(
            scenario_ids,
            {
                "PIPELINE_HEALTH_PASS",
                "SOURCE_WORKFLOW_FAILURE",
                "MISSING_CAPTURE_JOB",
                "MISSING_CAPTURE_BOUNDARY_STEP",
                "STALE_PATH_CAPTURE_STEP_SKIPPED",
                "FIRST_ATTEMPT_FAIL_SECOND_ATTEMPT_PASS",
                "BOTH_ATTEMPTS_FAIL",
                "R2_BLOCKED_VISIBILITY_BOUNDARY",
            },
        )
        execution = cfg["execution_boundary"]
        self.assertIs(execution["synthetic_fixtures_only"], True)
        for key, value in execution.items():
            if key != "synthetic_fixtures_only" and isinstance(value, bool):
                self.assertIs(value, False)

    def test_pipeline_health_pass(self) -> None:
        stdout, requested = _run(source_run_id=1001)
        payload = json.loads(stdout.strip().splitlines()[-1])
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["stage"], "V0_10_SCHEDULED_PIPELINE_EXECUTION_HEALTH_PASS")
        self.assertIs(payload["capture_evidence_interpreted"], False)
        self.assertEqual(
            requested,
            [
                "https://api.github.com/repos/qookey109-pixel/crypto-autopilot/"
                "actions/runs/1001/jobs?per_page=100"
            ],
        )

    def test_source_workflow_failure_fails_closed(self) -> None:
        with self.assertRaisesRegex(AssertionError, "source workflow conclusion=failure"):
            _run(source_run_id=1002, source_conclusion="failure")

    def test_missing_capture_job_fails_closed(self) -> None:
        with self.assertRaisesRegex(AssertionError, "missing expected V0.10 jobs"):
            _run(source_run_id=1003, jobs=_jobs(omit_job="capture"))

    def test_missing_capture_boundary_step_fails_closed(self) -> None:
        with self.assertRaisesRegex(AssertionError, "missing expected capture steps"):
            _run(
                source_run_id=1004,
                jobs=_jobs(omit_step="Assert V0.10 capture boundary"),
            )

    def test_stale_path_with_capture_step_skipped_fails_closed(self) -> None:
        with self.assertRaisesRegex(
            AssertionError,
            "Capture frozen provider metadata through V0.10 successor path conclusion=skipped",
        ):
            _run(
                source_run_id=1005,
                jobs=_jobs(
                    step_conclusions={
                        "Capture frozen provider metadata through V0.10 successor path": "skipped"
                    }
                ),
            )

    def test_first_attempt_fail_then_second_attempt_pass(self) -> None:
        with self.assertRaisesRegex(AssertionError, "source workflow conclusion=failure"):
            _run(source_run_id=1017, source_conclusion="failure")
        stdout, _ = _run(source_run_id=1047)
        payload = json.loads(stdout.strip().splitlines()[-1])
        self.assertEqual(payload["status"], "PASS")

    def test_both_attempts_fail_closed(self) -> None:
        for run_id in (2017, 2047):
            with self.assertRaisesRegex(AssertionError, "source workflow conclusion=failure"):
                _run(source_run_id=run_id, source_conclusion="failure")

    def test_r2_blocked_is_intentionally_not_classifiable_from_observer_metadata(self) -> None:
        cfg = _load_matrix()
        visibility = cfg["observer_visibility_boundary"]
        self.assertIs(visibility["may_read_capture_artifacts"], False)
        self.assertIs(visibility["may_list_or_read_r2"], False)
        self.assertIs(
            visibility["r2_blocked_must_be_classified_by_artifact_aware_monitor_not_observer"],
            True,
        )

        stdout, _ = _run(source_run_id=3001, jobs=_jobs())
        payload = json.loads(stdout.strip().splitlines()[-1])
        self.assertEqual(payload["status"], "PASS")
        self.assertIs(payload["capture_evidence_interpreted"], False)
        self.assertNotIn("R2", payload["stage"])

    def test_outside_window_exits_before_github_metadata_request(self) -> None:
        with self.assertRaises(SystemExit) as exc:
            _run(source_run_id=4001, source_created_at="2026-08-26T23:47:00Z")
        self.assertEqual(exc.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
