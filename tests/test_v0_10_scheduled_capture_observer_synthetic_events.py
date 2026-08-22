from __future__ import annotations

import io
import json
import textwrap
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

import pytest


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
    assert isinstance(payload, dict)
    return payload


def _observer_python() -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    marker = "          python - <<'PY'\n"
    assert text.count(marker) == 1
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
                {
                    "name": step,
                    "conclusion": conclusions.get(step, "success"),
                }
                for step in EXPECTED_CAPTURE_STEPS
                if step != omit_step
            ]
        rows.append(row)
    return rows


def _run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    source_run_id: int,
    source_conclusion: str = "success",
    source_created_at: str = "2026-08-27T00:17:00Z",
    jobs: list[dict[str, Any]] | None = None,
) -> tuple[str, list[str]]:
    summary = tmp_path / f"summary-{source_run_id}.md"
    monkeypatch.setenv("SOURCE_RUN_ID", str(source_run_id))
    monkeypatch.setenv("SOURCE_CONCLUSION", source_conclusion)
    monkeypatch.setenv("SOURCE_CREATED_AT", source_created_at)
    monkeypatch.setenv("GITHUB_REPOSITORY", "qookey109-pixel/crypto-autopilot")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setenv("GH_TOKEN", "synthetic-not-a-secret")

    requested: list[str] = []

    def fake_urlopen(request: urllib.request.Request, timeout: int = 20) -> _Response:
        assert timeout == 20
        requested.append(request.full_url)
        return _Response({"jobs": jobs if jobs is not None else _jobs()})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exec(compile(_observer_python(), "<synthetic-observer>", "exec"), {})
    return stdout.getvalue(), requested


def test_rehearsal_matrix_is_validation_only_and_covers_required_cases() -> None:
    cfg = _load_matrix()
    assert cfg["status"] == "PREPARED_VALIDATION_ONLY"
    assert cfg["scenario_count"] == 8
    scenario_ids = {row["id"] for row in cfg["scenarios"]}
    assert scenario_ids == {
        "PIPELINE_HEALTH_PASS",
        "SOURCE_WORKFLOW_FAILURE",
        "MISSING_CAPTURE_JOB",
        "MISSING_CAPTURE_BOUNDARY_STEP",
        "STALE_PATH_CAPTURE_STEP_SKIPPED",
        "FIRST_ATTEMPT_FAIL_SECOND_ATTEMPT_PASS",
        "BOTH_ATTEMPTS_FAIL",
        "R2_BLOCKED_VISIBILITY_BOUNDARY",
    }
    execution = cfg["execution_boundary"]
    assert execution["synthetic_fixtures_only"] is True
    for key, value in execution.items():
        if key != "synthetic_fixtures_only" and isinstance(value, bool):
            assert value is False


def test_pipeline_health_pass(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    stdout, requested = _run(monkeypatch, tmp_path, source_run_id=1001)
    payload = json.loads(stdout.strip().splitlines()[-1])
    assert payload["status"] == "PASS"
    assert payload["stage"] == "V0_10_SCHEDULED_PIPELINE_EXECUTION_HEALTH_PASS"
    assert payload["capture_evidence_interpreted"] is False
    assert requested == [
        "https://api.github.com/repos/qookey109-pixel/crypto-autopilot/actions/runs/1001/jobs?per_page=100"
    ]


def test_source_workflow_failure_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    with pytest.raises(AssertionError, match="source workflow conclusion=failure"):
        _run(
            monkeypatch,
            tmp_path,
            source_run_id=1002,
            source_conclusion="failure",
        )


def test_missing_capture_job_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    with pytest.raises(AssertionError, match="missing expected V0.10 jobs"):
        _run(
            monkeypatch,
            tmp_path,
            source_run_id=1003,
            jobs=_jobs(omit_job="capture"),
        )


def test_missing_capture_boundary_step_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    with pytest.raises(AssertionError, match="missing expected capture steps"):
        _run(
            monkeypatch,
            tmp_path,
            source_run_id=1004,
            jobs=_jobs(omit_step="Assert V0.10 capture boundary"),
        )


def test_stale_path_with_capture_step_skipped_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    with pytest.raises(
        AssertionError,
        match="Capture frozen provider metadata through V0.10 successor path conclusion=skipped",
    ):
        _run(
            monkeypatch,
            tmp_path,
            source_run_id=1005,
            jobs=_jobs(
                step_conclusions={
                    "Capture frozen provider metadata through V0.10 successor path": "skipped"
                }
            ),
        )


def test_first_attempt_fail_then_second_attempt_pass(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    with pytest.raises(AssertionError, match="source workflow conclusion=failure"):
        _run(
            monkeypatch,
            tmp_path,
            source_run_id=1017,
            source_conclusion="failure",
        )
    stdout, _ = _run(monkeypatch, tmp_path, source_run_id=1047)
    payload = json.loads(stdout.strip().splitlines()[-1])
    assert payload["status"] == "PASS"


def test_both_attempts_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for run_id in (2017, 2047):
        with pytest.raises(AssertionError, match="source workflow conclusion=failure"):
            _run(
                monkeypatch,
                tmp_path,
                source_run_id=run_id,
                source_conclusion="failure",
            )


def test_r2_blocked_is_intentionally_not_classifiable_from_observer_metadata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = _load_matrix()
    visibility = cfg["observer_visibility_boundary"]
    assert visibility["may_read_capture_artifacts"] is False
    assert visibility["may_list_or_read_r2"] is False
    assert visibility["r2_blocked_must_be_classified_by_artifact_aware_monitor_not_observer"] is True

    # A BLOCKED capture can still have successful GitHub steps because the boundary
    # accepts a fail-closed BLOCKED artifact. The observer must report only pipeline
    # execution health and must not invent an R2/capture conclusion it cannot see.
    stdout, _ = _run(monkeypatch, tmp_path, source_run_id=3001, jobs=_jobs())
    payload = json.loads(stdout.strip().splitlines()[-1])
    assert payload["status"] == "PASS"
    assert payload["capture_evidence_interpreted"] is False
    assert "R2" not in payload["stage"]


def test_outside_window_exits_without_github_metadata_request(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    with pytest.raises(SystemExit) as exc:
        _run(
            monkeypatch,
            tmp_path,
            source_run_id=4001,
            source_created_at="2026-08-26T23:47:00Z",
        )
    assert exc.value.code == 0
