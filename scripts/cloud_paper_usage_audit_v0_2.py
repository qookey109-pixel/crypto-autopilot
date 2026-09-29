"""Bounded, one-time successor diagnostic for Cloud Paper account usage.

V0.1 remains immutable evidence. This module never persists Cloudflare identifiers,
raw GraphQL payloads, or credential values.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from scripts.cloud_paper_usage_audit_v0_1 import (
    AuditError,
    GROUP_LIMIT,
    QUERY,
    _request_json,
    summarize_usage,
)

AUTHORITY = "cloud-paper-usage-audit-v0.2"
WORKFLOW_FILE = "cloud-paper-usage-audit-v0-2.yml"
DATASETS = ("d1Rows", "d1Storage", "r2Operations", "r2Storage")
REPORT_SCHEMA = "qookey-cloud-paper-usage-audit-report-v0.2"
REQUEST_URL = "https://api.cloudflare.com/client/v4/graphql"


def _base_report(observed_at: datetime, start: datetime, end: datetime) -> dict[str, Any]:
    return {
        "schema": REPORT_SCHEMA,
        "authority": AUTHORITY,
        "status": "REVIEW_REQUIRED",
        "observed_at_utc": observed_at.astimezone(UTC).isoformat(),
        "window_start_utc": start.astimezone(UTC).isoformat(),
        "window_end_utc": end.astimezone(UTC).isoformat(),
        "coverage": {
            "account_scope": "ACCOUNT_TAG_ONLY_NO_DATABASE_OR_BUCKET_FILTER",
            "dataset_group_counts": {name: None for name in DATASETS},
            "dataset_states": {name: "NOT_OBSERVED" for name in DATASETS},
            "account_wide_writer_coverage": "UNKNOWN_NOT_PROVEN",
            "account_plan_and_billing": "UNKNOWN_NOT_QUERIED",
        },
        "account_identifiers_persisted": False,
        "database_or_bucket_names_persisted": False,
        "raw_response_persisted": False,
        "zero_cost_conclusion": "UNKNOWN",
        "activation": "REMAINS_DISABLED",
    }


def diagnose_usage(
    payload: object, *, observed_at: datetime, start_time: datetime, end_time: datetime,
) -> dict[str, Any]:
    """Record only per-dataset shape/counts; empty never means zero usage."""
    report = _base_report(observed_at, start_time, end_time)
    if not isinstance(payload, dict) or payload.get("errors"):
        report["reason_code"] = "GRAPHQL_RESPONSE_ERROR"
        return report
    data = payload.get("data")
    viewer = data.get("viewer") if isinstance(data, dict) else None
    accounts = viewer.get("accounts") if isinstance(viewer, dict) else None
    if not isinstance(accounts, list) or len(accounts) != 1 or not isinstance(accounts[0], dict):
        report["reason_code"] = "ACCOUNT_SCOPE_UNAVAILABLE"
        return report
    account = accounts[0]
    counts = report["coverage"]["dataset_group_counts"]
    states = report["coverage"]["dataset_states"]
    for name in DATASETS:
        rows = account.get(name)
        if not isinstance(rows, list):
            states[name] = "MISSING_OR_INVALID"
            continue
        counts[name] = len(rows)
        if len(rows) >= GROUP_LIMIT:
            states[name] = "LIMIT_REACHED"
        elif not rows:
            states[name] = "EMPTY_UNVERIFIED"
        elif any(not isinstance(row, dict) for row in rows):
            states[name] = "INVALID_ROW"
        else:
            states[name] = "PRESENT"
    if any(state != "PRESENT" for state in states.values()):
        report["reason_code"] = "DATASET_COVERAGE_INCOMPLETE"
        return report
    try:
        measured = summarize_usage(
            payload, observed_at=observed_at, start_time=start_time, end_time=end_time,
        )
    except AuditError as exc:
        report["reason_code"] = str(exc)
        return report
    measured["schema"] = REPORT_SCHEMA
    measured["authority"] = AUTHORITY
    measured["coverage"]["dataset_states"] = states
    measured["activation"] = "REMAINS_DISABLED"
    if measured["status"] != "READY_FOR_REVIEW":
        measured["reason_code"] = "STALE_DATASET"
    return measured


def readiness(
    *, variable_present: bool, secret_present: bool,
    token_present: bool, account_ids_match: bool,
) -> dict[str, Any]:
    if not variable_present:
        reason = "MISSING_ACCOUNT_ID_VARIABLE"
    elif not secret_present:
        reason = "MISSING_ACCOUNT_ID_SECRET"
    elif not token_present:
        reason = "MISSING_READ_ONLY_TOKEN_SECRET"
    elif not account_ids_match:
        reason = "ACCOUNT_ID_SECRET_VARIABLE_MISMATCH"
    else:
        reason = "CONFIGURATION_PRESENT"
    return {
        "schema": "qookey-cloud-paper-usage-audit-readiness-v0.2",
        "state": "READY" if reason == "CONFIGURATION_PRESENT" else "BLOCKED",
        "reason_code": reason,
        "account_id_variable_present": variable_present,
        "account_id_secret_present": secret_present,
        "account_ids_match": account_ids_match,
        "read_only_token_secret_present": token_present,
        "cloudflare_requests_performed": 0,
        "api_permission_state": "NOT_CHECKED_NO_NETWORK",
        "usage_evidence_state": "NOT_CHECKED_BY_READINESS",
        "budget_activation_state": "NOT_AUTHORIZED_BY_READINESS",
        "one_time_authority_consumed": False,
        "secret_values_printed": False,
    }


def _present(value: str | None) -> bool:
    return value == "true"


def _require_single_run() -> None:
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise AuditError("MAIN_BRANCH_REQUIRED")
    if os.environ.get("GITHUB_RUN_ATTEMPT") != "1":
        raise AuditError("RERUN_FORBIDDEN")
    run_id = os.environ.get("GITHUB_RUN_ID")
    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    api = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    if not run_id or not repo or not token:
        raise AuditError("GITHUB_RUN_METADATA_MISSING")
    url = (
        f"{api}/repos/{repo}/actions/workflows/{WORKFLOW_FILE}/runs"
        "?branch=main&event=workflow_dispatch&per_page=100"
    )
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            payload = json.loads(response.read())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise AuditError("WORKFLOW_HISTORY_UNAVAILABLE") from None
    runs = payload.get("workflow_runs") if isinstance(payload, dict) else None
    if not isinstance(runs, list) or payload.get("total_count", 0) >= 100:
        raise AuditError("WORKFLOW_HISTORY_AMBIGUOUS")
    if not any(isinstance(item, dict) and str(item.get("id")) == run_id for item in runs):
        raise AuditError("CURRENT_RUN_NOT_IN_HISTORY")
    if any(isinstance(item, dict) and str(item.get("id")) != run_id for item in runs):
        raise AuditError("ONE_TIME_AUTHORITY_ALREADY_CONSUMED")


def execute(output: Path) -> int:
    observed = datetime.now(UTC)
    end = observed
    start = end - timedelta(days=30)
    requests = 0
    try:
        account = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        token = os.environ.get("CLOUDFLARE_READONLY_API_TOKEN")
        if not account:
            raise AuditError("MISSING_ACCOUNT_ID_SECRET")
        if not token:
            raise AuditError("MISSING_READ_ONLY_TOKEN_SECRET")
        if not _present(os.environ.get("ACCOUNT_ID_PARITY_VERIFIED")):
            raise AuditError("ACCOUNT_ID_SECRET_VARIABLE_MISMATCH")
        _require_single_run()
        variables = {
            "accountTag": account,
            "startDate": start.date().isoformat(),
            "endDate": end.date().isoformat(),
            "startTime": start.isoformat().replace("+00:00", "Z"),
            "endTime": end.isoformat().replace("+00:00", "Z"),
        }
        requests = 1
        payload = _request_json(
            REQUEST_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            body=json.dumps({"query": QUERY, "variables": variables}).encode(),
        )
        report = diagnose_usage(
            payload, observed_at=datetime.now(UTC), start_time=start, end_time=end,
        )
    except AuditError as exc:
        report = _base_report(observed, start, end)
        report["reason_code"] = str(exc)
    report["github"] = {
        "repository": os.environ.get("GITHUB_REPOSITORY"),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "head_sha": os.environ.get("GITHUB_SHA"),
        "event": "workflow_dispatch",
    }
    report["cloudflare_http_requests_performed"] = requests
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Cloud Paper usage audit V0.2: {report['status']} ({report.get('reason_code', 'METRICS_CAPTURED')})")
    return 0 if report["status"] == "READY_FOR_REVIEW" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readiness", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.readiness:
        report = readiness(
            variable_present=_present(os.environ.get("ACCOUNT_ID_VARIABLE_PRESENT")),
            secret_present=_present(os.environ.get("ACCOUNT_ID_SECRET_PRESENT")),
            token_present=_present(os.environ.get("READ_ONLY_TOKEN_SECRET_PRESENT")),
            account_ids_match=_present(os.environ.get("ACCOUNT_ID_PARITY_VERIFIED")),
        )
        print(json.dumps(report, sort_keys=True))
        return 0 if report["state"] == "READY" else 1
    if args.output is None:
        parser.error("--output is required for audit")
    return execute(args.output)


if __name__ == "__main__":
    sys.exit(main())
