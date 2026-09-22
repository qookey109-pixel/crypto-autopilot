from __future__ import annotations

import argparse
import io
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Iterable, Mapping


API_ROOT = "https://api.github.com"
API_VERSION = "2026-03-10"


class PreviousQualityEvidenceError(RuntimeError):
    """Raised when prior GitHub Actions evidence cannot be trusted."""


def _headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "qookey-crypto-autopilot",
        "X-GitHub-Api-Version": API_VERSION,
    }


def _read_json(url: str, *, token: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=_headers(token))
    with urllib.request.urlopen(request, timeout=20) as response:
        value = json.loads(response.read())
    if not isinstance(value, dict):
        raise PreviousQualityEvidenceError("GitHub API response must be an object")
    return value


def _read_bytes(url: str, *, token: str) -> bytes:
    request = urllib.request.Request(url, headers=_headers(token))
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def _select_previous_run(
    runs: Iterable[Mapping[str, Any]],
    *,
    current_run_id: int,
    repository: str,
) -> Mapping[str, Any] | None:
    candidates: list[Mapping[str, Any]] = []
    for run in runs:
        try:
            run_id = int(run["id"])
        except (KeyError, TypeError, ValueError):
            continue
        repo = run.get("repository")
        if not isinstance(repo, Mapping) or repo.get("full_name") != repository:
            continue
        if run_id == current_run_id:
            continue
        if run.get("conclusion") != "success" or run.get("head_branch") != "main":
            continue
        candidates.append(run)
    if not candidates:
        return None
    return max(candidates, key=lambda run: int(run["id"]))


def _select_artifact(
    artifacts: Iterable[Mapping[str, Any]],
    *,
    run_id: int,
    run_attempt: int,
) -> Mapping[str, Any] | None:
    expected = f"research-signal-quality-{run_id}-{run_attempt}"
    for artifact in artifacts:
        if artifact.get("name") == expected and artifact.get("expired") is False:
            return artifact
    return None


def _extract_quality_report(payload: bytes) -> dict[str, Any]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        matches = [
            name
            for name in archive.namelist()
            if name == "quality.json" or name.endswith("/quality.json")
        ]
        if len(matches) != 1:
            raise PreviousQualityEvidenceError(
                "previous quality artifact must contain exactly one quality.json"
            )
        if ".." in Path(matches[0]).parts:
            raise PreviousQualityEvidenceError("previous quality artifact path is unsafe")
        raw = archive.read(matches[0])
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise PreviousQualityEvidenceError("previous quality report must be an object")
    if value.get("schema") != "research-signal-quality-v0.1":
        raise PreviousQualityEvidenceError("previous quality report schema is invalid")
    return value


def fetch_previous_quality_report(
    *,
    repository: str,
    workflow: str,
    current_run_id: int,
    token: str,
) -> dict[str, Any] | None:
    if repository.count("/") != 1:
        raise PreviousQualityEvidenceError("repository must be owner/name")
    workflow_id = urllib.parse.quote(workflow, safe="")
    runs_url = (
        f"{API_ROOT}/repos/{repository}/actions/workflows/{workflow_id}/runs"
        "?branch=main&status=success&per_page=20"
    )
    runs_payload = _read_json(runs_url, token=token)
    runs = runs_payload.get("workflow_runs")
    if not isinstance(runs, list):
        raise PreviousQualityEvidenceError("workflow run listing is malformed")
    previous = _select_previous_run(
        runs,
        current_run_id=current_run_id,
        repository=repository,
    )
    if previous is None:
        return None

    run_id = int(previous["id"])
    run_attempt = int(previous.get("run_attempt", 1))
    artifacts_payload = _read_json(
        f"{API_ROOT}/repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100",
        token=token,
    )
    artifacts = artifacts_payload.get("artifacts")
    if not isinstance(artifacts, list):
        raise PreviousQualityEvidenceError("artifact listing is malformed")
    artifact = _select_artifact(
        artifacts,
        run_id=run_id,
        run_attempt=run_attempt,
    )
    if artifact is None:
        return None
    artifact_id = int(artifact["id"])
    archive = _read_bytes(
        f"{API_ROOT}/repos/{repository}/actions/artifacts/{artifact_id}/zip",
        token=token,
    )
    return _extract_quality_report(archive)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Recover the last successful Research Signal Quality evidence"
    )
    parser.add_argument("--repository", required=True)
    parser.add_argument("--current-run-id", required=True, type=int)
    parser.add_argument("--workflow", default="research-signal-quality-v0-1.yml")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("::warning::GITHUB_TOKEN unavailable; running without quality dedupe")
        return 0
    try:
        report = fetch_previous_quality_report(
            repository=args.repository,
            workflow=args.workflow,
            current_run_id=args.current_run_id,
            token=token,
        )
    except (
        PreviousQualityEvidenceError,
        urllib.error.URLError,
        TimeoutError,
        ValueError,
        json.JSONDecodeError,
        zipfile.BadZipFile,
    ) as exc:
        print(f"::warning::previous quality evidence unavailable: {exc}")
        return 0
    if report is None:
        print("No reusable previous quality evidence found.")
        return 0
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Recovered previous quality evidence to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
