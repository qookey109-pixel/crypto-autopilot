"""Read-only health evaluation for versioned research automations."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


SUPPORTED_REPORT_SCHEMAS = {
    "research-automation-health-v0.1",
    "research-automation-health-v0.2",
}


class ResearchAutomationHealthError(ValueError):
    """Raised when automation metadata or its monitoring authority is invalid."""


@dataclass(frozen=True, slots=True)
class WorkflowExpectation:
    workflow: str
    label: str
    mode: str
    max_age_seconds: int
    active_from_utc: str | None = None
    active_until_utc: str | None = None
    allowed_conclusions: tuple[str, ...] = ("success",)
    allowed_events: tuple[str, ...] = ("schedule", "workflow_dispatch")


def parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ResearchAutomationHealthError(f"invalid UTC timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise ResearchAutomationHealthError("UTC timestamp must include an offset")
    return parsed.astimezone(timezone.utc)


def expectation_from_config(payload: Mapping[str, Any]) -> WorkflowExpectation:
    mode = str(payload.get("mode", ""))
    if mode not in {"continuous", "bounded", "conditional"}:
        raise ResearchAutomationHealthError("workflow mode must be continuous, bounded or conditional")
    maximum_age = int(payload.get("max_age_seconds", 0))
    if maximum_age <= 0:
        raise ResearchAutomationHealthError("max_age_seconds must be positive")
    workflow = str(payload.get("workflow", "")).strip()
    label = str(payload.get("label", "")).strip()
    if not workflow.endswith((".yml", ".yaml")) or not label:
        raise ResearchAutomationHealthError("workflow path and label are required")
    allowed = tuple(str(value) for value in payload.get("allowed_conclusions", ["success"]))
    if not allowed:
        raise ResearchAutomationHealthError("allowed_conclusions cannot be empty")
    allowed_events = tuple(
        str(value) for value in payload.get("allowed_events", ["schedule", "workflow_dispatch"])
    )
    if not allowed_events:
        raise ResearchAutomationHealthError("allowed_events cannot be empty")
    return WorkflowExpectation(
        workflow=workflow,
        label=label,
        mode=mode,
        max_age_seconds=maximum_age,
        active_from_utc=str(payload["active_from_utc"]) if payload.get("active_from_utc") else None,
        active_until_utc=str(payload["active_until_utc"]) if payload.get("active_until_utc") else None,
        allowed_conclusions=allowed,
        allowed_events=allowed_events,
    )


def _run_time(run: Mapping[str, Any]) -> datetime:
    value = run.get("run_started_at") or run.get("created_at") or run.get("updated_at")
    if not isinstance(value, str):
        raise ResearchAutomationHealthError("workflow run has no timestamp")
    return parse_utc(value)


def evaluate_workflow(
    expectation: WorkflowExpectation,
    runs: Sequence[Mapping[str, Any]],
    *,
    now: datetime,
) -> dict[str, Any]:
    """Classify one workflow without reading artifacts, providers or R2."""

    now = now.astimezone(timezone.utc)
    active_from = parse_utc(expectation.active_from_utc) if expectation.active_from_utc else None
    active_until = parse_utc(expectation.active_until_utc) if expectation.active_until_utc else None
    base = {
        "workflow": expectation.workflow,
        "label": expectation.label,
        "mode": expectation.mode,
        "active_from_utc": expectation.active_from_utc,
        "active_until_utc": expectation.active_until_utc,
        "max_age_seconds": expectation.max_age_seconds,
    }
    if active_from is not None and now < active_from:
        return {**base, "status": "WAITING_WINDOW", "alert": False, "last_run": None}
    if active_until is not None and now >= active_until:
        return {**base, "status": "EXPECTED_STOP", "alert": False, "last_run": None}

    eligible_runs = [
        run
        for run in runs
        if str(run.get("event") or "") in expectation.allowed_events
        and (active_from is None or _run_time(run) >= active_from)
    ]
    ordered = sorted(eligible_runs, key=_run_time, reverse=True)
    if not ordered:
        grace_start = active_from or now
        elapsed = max(0.0, (now - grace_start).total_seconds())
        if expectation.mode == "conditional" and elapsed <= expectation.max_age_seconds:
            status = "WAITING_DEPENDENCY"
        else:
            status = (
                "STARTUP_GRACE"
                if elapsed <= expectation.max_age_seconds
                else "STALE_NO_RUN"
            )
        return {
            **base,
            "status": status,
            "alert": status == "STALE_NO_RUN",
            "last_run": None,
        }

    latest = ordered[0]
    started = _run_time(latest)
    age_seconds = max(0, int((now - started).total_seconds()))
    run_status = str(latest.get("status") or "unknown")
    conclusion = str(latest.get("conclusion") or "") or None
    last_run = {
        "id": latest.get("id"),
        "event": latest.get("event"),
        "status": run_status,
        "conclusion": conclusion,
        "started_at_utc": started.isoformat().replace("+00:00", "Z"),
        "age_seconds": age_seconds,
        "html_url": latest.get("html_url"),
    }
    if run_status in {"queued", "in_progress", "requested", "waiting", "pending"}:
        stale = age_seconds > expectation.max_age_seconds
        return {
            **base,
            "status": "STALE_IN_PROGRESS" if stale else "IN_PROGRESS",
            "alert": stale,
            "last_run": last_run,
        }
    if conclusion not in expectation.allowed_conclusions:
        return {**base, "status": "FAILED", "alert": True, "last_run": last_run}
    if expectation.mode == "conditional":
        stale = age_seconds > expectation.max_age_seconds
        return {
            **base,
            "status": "STALE" if stale else "HEALTHY_CONDITIONAL",
            "alert": stale,
            "last_run": last_run,
        }
    stale = age_seconds > expectation.max_age_seconds
    return {
        **base,
        "status": "STALE" if stale else "HEALTHY",
        "alert": stale,
        "last_run": last_run,
    }


def _health_dimensions(row: Mapping[str, Any]) -> dict[str, Any]:
    """Expose execution, dependency and business-result health independently."""

    status = str(row.get("status") or "UNKNOWN")
    last = row.get("last_run")
    last_mapping = last if isinstance(last, Mapping) else {}
    return {
        **row,
        "execution": {
            "status": status,
            "alert": bool(row.get("alert")),
            "last_run_age_seconds": last_mapping.get("age_seconds"),
        },
        "dependency": {
            "status": "UNKNOWN_FROM_GITHUB_RUN_METADATA",
            "evidence_available": False,
        },
        "business_result": {
            "status": "UNKNOWN_FROM_GITHUB_RUN_METADATA",
            "workflow_conclusion": last_mapping.get("conclusion"),
        },
    }


def evaluate_automation_health(
    expectations: Sequence[WorkflowExpectation],
    runs_by_workflow: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    now: datetime,
    schema: str = "research-automation-health-v0.1",
) -> dict[str, Any]:
    if schema not in SUPPORTED_REPORT_SCHEMAS:
        raise ResearchAutomationHealthError(f"unsupported report schema: {schema}")
    rows = [
        _health_dimensions(
            evaluate_workflow(item, runs_by_workflow.get(item.workflow, ()), now=now)
        )
        for item in expectations
    ]
    alerts = [row for row in rows if row["alert"]]
    return {
        "schema": schema,
        "status": "ALERT" if alerts else "PASS",
        "evaluated_at_utc": now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "workflow_count": len(rows),
        "alert_count": len(alerts),
        "workflows": rows,
        "authority": {
            "github_metadata_read_only": True,
            "provider_access": False,
            "r2_access": False,
            "holdout_access": False,
            "automatic_model_promotion": False,
            "trade_plan": False,
            "real_money_order": False,
            "live_trading": False,
        },
    }


def scheduled_workflow_crons(workflow_dir: str | Path) -> dict[str, list[str]]:
    """Return the exact Repository cron inventory without interpreting YAML."""

    scheduled: dict[str, list[str]] = {}
    for path in sorted(Path(workflow_dir).glob("*.y*ml")):
        crons = re.findall(r'^\s+- cron: "([^"]+)"$', path.read_text(encoding="utf-8"), re.MULTILINE)
        if crons:
            scheduled[path.name] = crons
    return scheduled


def validate_schedule_coverage(
    expectations: Sequence[WorkflowExpectation],
    workflow_dir: str | Path,
) -> dict[str, Any]:
    """Require every active Repository cron to be monitored exactly once."""

    scheduled = scheduled_workflow_crons(workflow_dir)
    monitored = [item.workflow for item in expectations]
    if len(monitored) != len(set(monitored)):
        raise ResearchAutomationHealthError("duplicate monitored workflow")
    missing = sorted(set(scheduled) - set(monitored))
    unexpected = sorted(set(monitored) - set(scheduled))
    if missing or unexpected:
        raise ResearchAutomationHealthError(
            f"scheduled workflow coverage mismatch: missing={missing}, unexpected={unexpected}"
        )
    manual_health = sorted(
        item.workflow for item in expectations if item.allowed_events != ("schedule",)
    )
    if manual_health:
        raise ResearchAutomationHealthError(
            f"manual events cannot count as automatic health: {manual_health}"
        )
    return {
        "scheduled_workflow_count": len(scheduled),
        "monitored_workflow_count": len(monitored),
        "complete": True,
        "manual_events_count_as_health": False,
        "unmonitored_scheduled_workflows": [],
        "duplicate_monitored_workflows": [],
        "workflows": scheduled,
    }


def fetch_workflow_runs(
    *,
    repository: str,
    workflow: str,
    token: str,
    branch: str = "main",
    allowed_events: Sequence[str] = ("schedule",),
    per_page: int = 100,
    max_pages: int = 3,
) -> list[dict[str, Any]]:
    """Fetch bounded workflow-run history with server-side branch/event filters."""

    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ResearchAutomationHealthError("repository must use owner/name form")
    if not token:
        raise ResearchAutomationHealthError("GITHUB_TOKEN is required")
    if not re.fullmatch(r"[A-Za-z0-9_./-]+", branch) or ".." in branch:
        raise ResearchAutomationHealthError("branch is invalid")
    if not allowed_events:
        raise ResearchAutomationHealthError("allowed_events cannot be empty")
    if per_page < 1 or per_page > 100:
        raise ResearchAutomationHealthError("per_page must be between 1 and 100")
    if max_pages < 1 or max_pages > 10:
        raise ResearchAutomationHealthError("max_pages must be between 1 and 10")

    encoded = quote(workflow, safe="")
    discovered: dict[object, dict[str, Any]] = {}
    for event in allowed_events:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", event):
            raise ResearchAutomationHealthError("allowed event is invalid")
        for page in range(1, max_pages + 1):
            query = urlencode(
                {
                    "branch": branch,
                    "event": event,
                    "per_page": per_page,
                    "page": page,
                }
            )
            url = (
                f"https://api.github.com/repos/{repository}/actions/workflows/"
                f"{encoded}/runs?{query}"
            )
            request = Request(
                url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "crypto-autopilot-health-v0.2",
                },
            )
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read())
            rows = payload.get("workflow_runs")
            if not isinstance(rows, list):
                raise ResearchAutomationHealthError(
                    "GitHub workflow-runs response is malformed"
                )
            for item in rows:
                if not isinstance(item, Mapping):
                    continue
                row = dict(item)
                key = row.get("id") or row.get("html_url") or (
                    row.get("run_started_at"),
                    row.get("created_at"),
                    event,
                )
                discovered[key] = row
            if len(rows) < per_page:
                break
    return sorted(discovered.values(), key=_run_time, reverse=True)


def audit_workflow_inventory(workflow_dir: str | Path) -> dict[str, int]:
    paths = sorted(Path(workflow_dir).glob("*.y*ml"))
    scheduled = pull_request = retired = retired_pull_request = 0
    for path in paths:
        text = path.read_text(encoding="utf-8")
        is_scheduled = bool(re.search(r"^  schedule:", text, re.MULTILINE))
        is_pr = bool(re.search(r"^  pull_request:", text, re.MULTILINE))
        name_match = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
        name = name_match.group(1) if name_match else path.name
        is_retired = "retired" in name.lower()
        scheduled += int(is_scheduled)
        pull_request += int(is_pr)
        retired += int(is_retired)
        retired_pull_request += int(is_retired and is_pr)
    return {
        "total_workflows": len(paths),
        "scheduled_workflows": scheduled,
        "pull_request_workflows": pull_request,
        "retired_named_workflows": retired,
        "retired_pull_request_workflows": retired_pull_request,
    }


def markdown_summary(report: Mapping[str, Any]) -> str:
    version = "V0.2" if report.get("schema") == "research-automation-health-v0.2" else "V0.1"
    lines = [
        f"# Research Automation Health {version}",
        "",
        f"Overall: **{report['status']}** · alerts: **{report['alert_count']}**",
        "",
        "| Workflow | Status | Latest conclusion | Age seconds |",
        "| --- | --- | --- | ---: |",
    ]
    for row in report["workflows"]:
        last = row.get("last_run") or {}
        lines.append(
            f"| {row['label']} | {row['status']} | {last.get('conclusion') or '—'} | "
            f"{last.get('age_seconds', '—')} |"
        )
    inventory = report.get("workflow_inventory")
    if inventory:
        lines.extend(
            [
                "",
                "Workflow inventory: "
                f"{inventory['total_workflows']} total, "
                f"{inventory['pull_request_workflows']} PR-triggered, "
                f"{inventory['retired_pull_request_workflows']} retired PR-triggered.",
            ]
        )
    return "\n".join(lines) + "\n"
