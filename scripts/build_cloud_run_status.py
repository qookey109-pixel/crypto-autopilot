"""Project current GitHub schedule metadata into a non-authoritative Pages view.

Only GitHub Actions run metadata plus versioned Repository schedule/health policy
is read. Artifacts, logs, provider data, R2 objects, secrets and business-result
payloads are deliberately not read. Workflow success is never promoted into a
business-result claim.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

REPOSITORY = "qookey109-pixel/crypto-autopilot"
API = f"https://api.github.com/repos/{REPOSITORY}"
ROOT = Path(__file__).resolve().parents[1]
AUTOMATIC_OPERATIONS = ROOT / "config/github_automatic_research_operations_v0_5.json"
HEALTH_POLICY = ROOT / "config/research_automation_health_v0_2.json"
SCHEDULE_PROJECTION = ROOT / "config/automation_schedule_projection_v0_1.json"
EXPIRED_AUTHORITY_LINKS = {
    "provider-equivalence-v0-12-successor-metadata-capture.yml":
        "config/provider_equivalence_v0_12_successor_metadata_window_v0_1.json",
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def load_monitor_definitions() -> list[dict]:
    automatic = _load(AUTOMATIC_OPERATIONS)
    health = _load(HEALTH_POLICY)
    projection = _load(SCHEDULE_PROJECTION)
    if automatic.get("schema") != "github-automatic-research-operations-v0.5":
        raise RuntimeError("automatic operations V0.5 required")
    if health.get("schema") != "research-automation-health-v0.2":
        raise RuntimeError("research automation health V0.2 required")
    if projection.get("schema") != "qookey-automation-schedule-projection-policy-v0.1":
        raise RuntimeError("automation schedule projection V0.1 required")

    health_rows = {
        row["workflow"]: row
        for row in health.get("workflows", [])
        if isinstance(row, dict) and isinstance(row.get("workflow"), str)
    }
    projected_rows = {}
    for row in projection.get("jobs", []):
        workflow = row.get("workflow") if isinstance(row, dict) else None
        expected = row.get("expected_crons") if isinstance(row, dict) else None
        if isinstance(workflow, str) and isinstance(expected, list) and expected:
            projected_rows[Path(workflow).name] = row

    definitions: list[dict] = []
    automatic_rows = automatic.get("scheduled_workflows")
    if not isinstance(automatic_rows, list):
        raise RuntimeError("automatic operations scheduled_workflows missing")
    for row in automatic_rows:
        if not isinstance(row, dict) or not isinstance(row.get("workflow"), str):
            raise RuntimeError("automatic operations workflow row invalid")
        workflow = row["workflow"]
        health_row = health_rows.get(workflow)
        if health_row is None:
            raise RuntimeError(f"health inventory missing workflow: {workflow}")
        projected = projected_rows.get(workflow)
        lifecycle = str(row.get("lifecycle_state") or "")
        if lifecycle not in {
            "CURRENT_EFFECTIVE",
            "EXPIRED_BOUNDED_FROZEN_CRON_DECLARATION",
        }:
            raise RuntimeError(f"unknown schedule lifecycle: {workflow}: {lifecycle}")
        authority_link = (
            projected.get("authority_link")
            if projected is not None
            else EXPIRED_AUTHORITY_LINKS.get(workflow)
        )
        if not isinstance(authority_link, str) or not authority_link:
            raise RuntimeError(f"authority link missing: {workflow}")
        operation_id = (
            str(projected.get("id"))
            if projected is not None
            else workflow.removesuffix(".yml")
        )
        title = (
            str(projected.get("title"))
            if projected is not None
            else str(health_row.get("label") or workflow)
        )
        authority_state = (
            str(projected.get("status"))
            if projected is not None
            else "HISTORICAL_WINDOW_ENDED"
        )
        definitions.append({
            "operationId": operation_id,
            "title": title,
            "workflow": workflow,
            "lifecycleState": lifecycle,
            "authorityState": authority_state,
            "authorityPath": authority_link,
            "authorityUrl": f"https://github.com/{REPOSITORY}/blob/main/{authority_link}",
            "maxAgeSeconds": health_row.get("max_age_seconds"),
            "activeFromUtc": health_row.get("active_from_utc"),
            "activeUntilUtc": health_row.get("active_until_utc"),
        })

    if set(health_rows) != {row["workflow"] for row in definitions}:
        raise RuntimeError("health and automatic-operations workflow inventories diverged")
    if sum(row["lifecycleState"] == "CURRENT_EFFECTIVE" for row in definitions) != 7:
        raise RuntimeError("expected seven current-effective schedules")
    if sum(
        row["lifecycleState"] == "EXPIRED_BOUNDED_FROZEN_CRON_DECLARATION"
        for row in definitions
    ) != 1:
        raise RuntimeError("expected one expired frozen cron declaration")
    return definitions


def project_run(runs: list[dict], workflow: str) -> dict:
    candidates = [
        run for run in runs
        if run.get("head_branch") == "main"
        and run.get("event") == "schedule"
        and run.get("path") == f".github/workflows/{workflow}"
        and run.get("head_repository", {}).get("full_name") == REPOSITORY
        and type(run.get("id")) is int
        and SHA_RE.fullmatch(str(run.get("head_sha", "")))
    ]
    if not candidates:
        return {
            "state": "UNVERIFIED",
            "runId": None,
            "headSha": None,
            "evidenceTimeUtc": None,
            "workflowConclusion": None,
            "sourceUrl": None,
        }

    run = max(candidates, key=lambda row: row["id"])
    state = "RUNNING"
    if run.get("status") == "completed":
        state = {
            "success": "WORKFLOW_SUCCESS",
            "failure": "WORKFLOW_FAILED",
            "cancelled": "CANCELLED",
            "timed_out": "TIMED_OUT",
            "skipped": "SKIPPED",
        }.get(run.get("conclusion"), "UNVERIFIED")
    elif run.get("status") not in {
        "queued", "in_progress", "waiting", "requested", "pending"
    }:
        state = "UNVERIFIED"

    evidence_time = run.get("run_started_at") or run.get("created_at")
    if not isinstance(evidence_time, str):
        evidence_time = None
    return {
        "state": state,
        "runId": run["id"],
        "headSha": run["head_sha"],
        "evidenceTimeUtc": evidence_time,
        "workflowConclusion": run.get("conclusion"),
        "sourceUrl": f"https://github.com/{REPOSITORY}/actions/runs/{run['id']}",
    }


def _parse_utc(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def freshness_state(definition: dict, latest: dict, *, now: datetime) -> str:
    if definition["lifecycleState"] == "EXPIRED_BOUNDED_FROZEN_CRON_DECLARATION":
        return "EXPIRED_WINDOW"

    active_until = _parse_utc(definition.get("activeUntilUtc"))
    if active_until is not None and now > active_until:
        return "EXPIRED_WINDOW"
    if latest.get("state") == "QUERY_FAILED":
        return "QUERY_FAILED"

    evidence = _parse_utc(latest.get("evidenceTimeUtc"))
    max_age = definition.get("maxAgeSeconds")
    active_from = _parse_utc(definition.get("activeFromUtc"))
    if evidence is None:
        if isinstance(max_age, int) and active_from is not None:
            if now <= active_from + timedelta(seconds=max_age):
                return "WAITING_FIRST_SCHEDULE"
        return "NO_AUTOMATIC_RUN"

    if latest.get("state") == "RUNNING":
        if not isinstance(max_age, int):
            return "RUNNING"
        age_seconds = (now - evidence).total_seconds()
        if age_seconds < 0:
            return "UNVERIFIED"
        return "RUNNING" if age_seconds <= max_age else "STALLED"

    if not isinstance(max_age, int):
        return "NOT_APPLICABLE"
    age_seconds = (now - evidence).total_seconds()
    if age_seconds < 0:
        return "UNVERIFIED"
    return "FRESH" if age_seconds <= max_age else "STALE"


def schedule_window_state(definition: dict, *, now: datetime) -> str:
    if definition["lifecycleState"] == "EXPIRED_BOUNDED_FROZEN_CRON_DECLARATION":
        return "EXPIRED"

    active_from = _parse_utc(definition.get("activeFromUtc"))
    if active_from is not None and now < active_from:
        return "PENDING"

    active_until = _parse_utc(definition.get("activeUntilUtc"))
    if active_until is not None and now > active_until:
        return "EXPIRED"
    return "EFFECTIVE"


def collect(fetch_json, *, now: datetime | None = None) -> dict:
    observed = now or datetime.now(timezone.utc)
    definitions = load_monitor_definitions()
    items: list[dict] = []
    for definition in definitions:
        workflow = definition["workflow"]
        try:
            payload = fetch_json(
                f"{API}/actions/workflows/{workflow}/runs"
                "?branch=main&event=schedule&per_page=20"
            )
            latest = project_run(payload.get("workflow_runs", []), workflow)
        except Exception:
            latest = {
                "state": "QUERY_FAILED",
                "runId": None,
                "headSha": None,
                "evidenceTimeUtc": None,
                "workflowConclusion": None,
                "sourceUrl": None,
            }
        item = dict(definition)
        item["latestAutomaticRun"] = latest
        item["freshnessState"] = freshness_state(item, latest, now=observed)
        item["businessResult"] = {
            "status": "UNKNOWN_FROM_GITHUB_RUN_METADATA",
            "reason": "WORKFLOW_CONCLUSION_IS_NOT_BUSINESS_RESULT",
        }
        items.append(item)

    window_states = [schedule_window_state(row, now=observed) for row in items]
    current = sum(state == "EFFECTIVE" for state in window_states)
    expired = sum(state == "EXPIRED" for state in window_states)
    pending = sum(state == "PENDING" for state in window_states)
    frozen_expired = sum(
        row["lifecycleState"] == "EXPIRED_BOUNDED_FROZEN_CRON_DECLARATION"
        for row in items
    )
    return {
        "schema": "qookey-cloud-run-status-v0.2",
        "authority": False,
        "mode": "GITHUB_ACTIONS_METADATA_ONLY",
        "observedAtUtc": observed.isoformat(),
        "summary": {
            "repositoryCronDeclarationCount": len(items),
            "monitoredCronDeclarationCount": len(items),
            "currentEffectiveScheduleCount": current,
            "expiredScheduleCount": expired,
            "pendingScheduleCount": pending,
            "expiredFrozenCronDeclarationCount": frozen_expired,
        },
        "items": items,
        "safetyBoundary": {
            "providerReadsPerformed": False,
            "r2ReadsPerformed": False,
            "r2WritesPerformed": False,
            "artifactReadsPerformed": False,
            "logReadsPerformed": False,
            "holdoutAccessed": False,
            "sourceSwitchAuthorized": False,
            "tradePlanAuthorized": False,
            "realMoneyOrderAuthorized": False,
            "liveTradingAuthorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    if not token or os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit("GitHub-hosted execution with scoped token required")

    def fetch_json(url):
        request = Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urlopen(request, timeout=15) as response:  # noqa: S310 - fixed GitHub API
            return json.load(response)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(collect(fetch_json), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
