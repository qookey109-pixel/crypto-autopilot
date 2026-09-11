"""Project latest GitHub run metadata into a non-authoritative Pages view.

No artifacts, logs, provider data or storage credentials are read. A successful
workflow is deliberately never converted into a dataset-completion claim.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

REPOSITORY = "qookey109-pixel/crypto-autopilot"
API = f"https://api.github.com/repos/{REPOSITORY}"
WORKFLOWS = {
    "history": "binance-usdm-detailed-history-v0-1.yml",
    "reach": "pionex-historical-reach-v0-3.yml",
    "universe": "pionex-research-universe-v0-1.yml",
    "funding": "pionex-funding-history-v0-1.yml",
    "health": "research-automation-health-v0-2.yml",
    "simulation": "simulation-btc-v0-1.yml",
}


def project_run(runs: list[dict], workflow: str) -> dict:
    allowed_events = {"schedule", "workflow_dispatch"}
    if workflow == "simulation-btc-v0-1.yml":
        allowed_events = {"workflow_run"}
    candidates = [run for run in runs if (
        run.get("head_branch") == "main"
        and run.get("event") in allowed_events
        and run.get("path") == f".github/workflows/{workflow}"
        and run.get("head_repository", {}).get("full_name") == REPOSITORY
        and type(run.get("id")) is int
        and re.fullmatch(r"[0-9a-f]{40}", str(run.get("head_sha", "")))
    )]
    if not candidates:
        return {"state": "UNVERIFIED", "datasetComplete": None}
    run = max(candidates, key=lambda row: row["id"])
    state = "RUNNING"
    if run.get("status") == "completed":
        state = {"success": "WORKFLOW_SUCCESS", "failure": "WORKFLOW_FAILED",
                 "cancelled": "CANCELLED", "timed_out": "TIMED_OUT"}.get(
                     run.get("conclusion"), "UNVERIFIED")
    elif run.get("status") not in {"queued", "in_progress", "waiting", "requested", "pending"}:
        state = "UNVERIFIED"
    return {"state": state, "runId": run["id"], "headSha": run["head_sha"],
            "sourceUrl": f"https://github.com/{REPOSITORY}/actions/runs/{run['id']}",
            "datasetComplete": None}


def collect(fetch_json) -> dict:
    result = {"schema": "qookey-cloud-run-status-v0.1", "authority": False,
              "observedAtUtc": datetime.now(timezone.utc).isoformat(),
              "simulationReady": False, "runs": {}}
    for key, workflow in WORKFLOWS.items():
        try:
            payload = fetch_json(f"{API}/actions/workflows/{workflow}/runs?branch=main&per_page=20")
            result["runs"][key] = project_run(payload["workflow_runs"], workflow)
        except Exception:
            # Network/body errors must not leak credentials or preserve a stale success.
            result["runs"][key] = {"state": "UNVERIFIED", "datasetComplete": None}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    if not token or os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit("GitHub-hosted execution with scoped token required")

    def fetch_json(url):
        request = Request(url, headers={"Authorization": f"Bearer {token}",
                                      "Accept": "application/vnd.github+json"})
        with urlopen(request, timeout=15) as response:  # noqa: S310 - fixed GitHub API
            return json.load(response)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(collect(fetch_json), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
