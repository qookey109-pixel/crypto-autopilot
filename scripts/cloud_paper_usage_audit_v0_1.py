"""One-shot, read-only Cloudflare analytics capture for Cloud Paper budgeting."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

AUTHORITY = "cloud-paper-usage-audit-v0.1"
WORKFLOW_FILE = "cloud-paper-usage-audit-v0-1.yml"
GROUP_LIMIT = 10_000
FRESHNESS_LIMIT_SECONDS = 172_800

QUERY = """
query CloudPaperUsageAudit(
  $accountTag: string!
  $startDate: Date
  $endDate: Date
  $startTime: Time
  $endTime: Time
) {
  viewer {
    accounts(filter: { accountTag: $accountTag }) {
      d1Rows: d1AnalyticsAdaptiveGroups(
        limit: 10000
        filter: { date_geq: $startDate, date_leq: $endDate }
      ) {
        sum { rowsRead rowsWritten }
        dimensions { date }
      }
      d1Storage: d1StorageAdaptiveGroups(
        limit: 10000
        filter: { datetime_geq: $startTime, datetime_leq: $endTime }
        orderBy: [datetime_DESC]
      ) {
        max { databaseSizeBytes }
        dimensions { databaseId datetime }
      }
      r2Operations: r2OperationsAdaptiveGroups(
        limit: 10000
        filter: { datetime_geq: $startTime, datetime_leq: $endTime }
      ) {
        sum { requests }
        dimensions { actionType datetime }
      }
      r2Storage: r2StorageAdaptiveGroups(
        limit: 10000
        filter: { datetime_geq: $startTime, datetime_leq: $endTime }
        orderBy: [datetime_DESC]
      ) {
        max { objectCount uploadCount payloadSize metadataSize }
        dimensions { bucketName datetime }
      }
    }
  }
}
"""


class AuditError(ValueError):
    """Fixed safe error code; never includes response bodies or credentials."""


def _int(value: object, code: str) -> int:
    if type(value) is not int or value < 0:
        raise AuditError(code)
    return value


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise AuditError("METRIC_TIMESTAMP_MISSING")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.combine(date.fromisoformat(value), datetime.min.time(), UTC)
        except ValueError:
            raise AuditError("METRIC_TIMESTAMP_INVALID") from None
    if parsed.tzinfo is None:
        raise AuditError("METRIC_TIMESTAMP_TIMEZONE_MISSING")
    return parsed.astimezone(UTC)


def _account_data(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("errors"):
        raise AuditError("GRAPHQL_RESPONSE_ERROR")
    data = payload.get("data")
    viewer = data.get("viewer") if isinstance(data, dict) else None
    accounts = viewer.get("accounts") if isinstance(viewer, dict) else None
    if not isinstance(accounts, list) or len(accounts) != 1:
        raise AuditError("ACCOUNT_SCOPE_UNAVAILABLE")
    account = accounts[0]
    if not isinstance(account, dict):
        raise AuditError("ACCOUNT_SCOPE_UNAVAILABLE")
    names = ("d1Rows", "d1Storage", "r2Operations", "r2Storage")
    for name in names:
        rows = account.get(name)
        if not isinstance(rows, list):
            raise AuditError("DATASET_MISSING")
        if len(rows) >= GROUP_LIMIT:
            raise AuditError("DATASET_LIMIT_REACHED")
        if not rows:
            raise AuditError("DATASET_EMPTY_UNVERIFIED")
        if any(not isinstance(row, dict) for row in rows):
            raise AuditError("DATASET_ROW_INVALID")
    return account


def summarize_usage(
    payload: object, *, observed_at: datetime,
    start_time: datetime, end_time: datetime,
) -> dict[str, Any]:
    """Summarize only complete account-wide dataset responses."""
    account = _account_data(payload)
    if any(value.tzinfo is None for value in (observed_at, start_time, end_time)):
        raise AuditError("AUDIT_TIMEZONE_MISSING")
    observed = observed_at.astimezone(UTC)
    start = start_time.astimezone(UTC)
    end = end_time.astimezone(UTC)
    if end <= start or end > observed or end - start > timedelta(days=30, minutes=1):
        raise AuditError("AUDIT_WINDOW_INVALID")

    def latest_timestamp(rows: list[dict[str, Any]], key: str) -> datetime:
        values = []
        for row in rows:
            dimensions = row.get("dimensions")
            if not isinstance(dimensions, dict):
                raise AuditError("DATASET_DIMENSION_MISSING")
            values.append(_timestamp(dimensions.get(key)))
        return max(values)

    d1_rows = account["d1Rows"]
    daily = []
    for row in d1_rows:
        total = row.get("sum")
        dims = row.get("dimensions")
        if not isinstance(total, dict) or not isinstance(dims, dict):
            raise AuditError("D1_USAGE_FIELDS_MISSING")
        daily.append({
            "date_utc": _timestamp(dims.get("date")).date().isoformat(),
            "rows_read": _int(total.get("rowsRead"), "D1_ROWS_READ_INVALID"),
            "rows_written": _int(total.get("rowsWritten"), "D1_ROWS_WRITTEN_INVALID"),
        })

    def latest_storage(rows: list[dict[str, Any]], key: str, metric_fields: tuple[str, ...]) -> dict[str, int]:
        by_resource: dict[str, tuple[datetime, dict[str, int]]] = {}
        for row in rows:
            dims = row.get("dimensions")
            metrics = row.get("max")
            if not isinstance(dims, dict) or not isinstance(metrics, dict):
                raise AuditError("STORAGE_FIELDS_MISSING")
            resource = dims.get(key)
            if not isinstance(resource, str) or not resource:
                raise AuditError("STORAGE_RESOURCE_ID_MISSING")
            stamp = _timestamp(dims.get("datetime"))
            values = {field: _int(metrics.get(field), "STORAGE_METRIC_INVALID") for field in metric_fields}
            if resource not in by_resource or stamp > by_resource[resource][0]:
                by_resource[resource] = (stamp, values)
        totals = {field: sum(values[field] for _, values in by_resource.values()) for field in metric_fields}
        return totals

    d1_storage = latest_storage(
        account["d1Storage"], "databaseId", ("databaseSizeBytes",),
    )
    r2_storage = latest_storage(
        account["r2Storage"], "bucketName",
        ("objectCount", "uploadCount", "payloadSize", "metadataSize"),
    )
    operations: dict[str, int] = {}
    for row in account["r2Operations"]:
        dims, total = row.get("dimensions"), row.get("sum")
        if not isinstance(dims, dict) or not isinstance(total, dict):
            raise AuditError("R2_OPERATION_FIELDS_MISSING")
        action = dims.get("actionType")
        if not isinstance(action, str) or not action:
            raise AuditError("R2_ACTION_TYPE_MISSING")
        operations[action] = operations.get(action, 0) + _int(
            total.get("requests"), "R2_REQUEST_COUNT_INVALID",
        )

    fresh = {
        "d1_rows_latest_utc": latest_timestamp(d1_rows, "date").isoformat(),
        "d1_storage_latest_utc": latest_timestamp(account["d1Storage"], "datetime").isoformat(),
        "r2_operations_latest_utc": latest_timestamp(account["r2Operations"], "datetime").isoformat(),
        "r2_storage_latest_utc": latest_timestamp(account["r2Storage"], "datetime").isoformat(),
    }
    ages = {
        key: max(0, int((observed - datetime.fromisoformat(value)).total_seconds()))
        for key, value in fresh.items()
    }
    stale = any(age > FRESHNESS_LIMIT_SECONDS for age in ages.values())
    return {
        "schema": "qookey-cloud-paper-usage-audit-report-v0.1",
        "authority": AUTHORITY,
        "status": "REVIEW_REQUIRED" if stale else "READY_FOR_REVIEW",
        "observed_at_utc": observed.isoformat(),
        "window_start_utc": start.isoformat(),
        "window_end_utc": end.isoformat(),
        "account_identifiers_persisted": False,
        "database_or_bucket_names_persisted": False,
        "raw_response_persisted": False,
        "freshness": {"latest_metric_timestamps_utc": fresh, "ages_seconds": ages, "limit_seconds": FRESHNESS_LIMIT_SECONDS},
        "coverage": {
            "account_scope": "ACCOUNT_TAG_ONLY_NO_DATABASE_OR_BUCKET_FILTER",
            "dataset_group_counts": {name: len(account[name]) for name in (
                "d1Rows", "d1Storage", "r2Operations", "r2Storage",
            )},
            "any_dataset_truncated": False,
            "account_wide_writer_coverage": "UNKNOWN_NOT_PROVEN",
            "account_plan_and_billing": "UNKNOWN_NOT_QUERIED",
        },
        "d1": {
            "daily_usage": sorted(daily, key=lambda item: item["date_utc"]),
            "latest_storage_total_bytes": d1_storage["databaseSizeBytes"],
            "free_tier_comparison": {
                "rows_read_daily_limit": 5_000_000,
                "rows_written_daily_limit": 100_000,
                "storage_limit_bytes": 5_000_000_000,
            },
        },
        "r2": {
            "operations_by_action": dict(sorted(operations.items())),
            "latest_storage": r2_storage,
            "project_hard_stop_bytes": 8_000_000_000,
            "standard_free_tier_comparison": {
                "storage_gb_month": 10,
                "class_a_requests_month": 1_000_000,
                "class_b_requests_month": 10_000_000,
            },
        },
        "zero_cost_conclusion": "UNKNOWN_PLAN_AND_BILLING_NOT_QUERIED",
        "activation": "REMAINS_DISABLED",
        "limitations": [
            "Analytics data is an account-wide usage snapshot, not proof of the subscribed plan or invoice amount.",
            "Aggregated usage does not identify every credential, workflow, Worker, or external writer.",
            "This report does not authorize production acceptance, D1 provisioning, R2 object access, or a schedule.",
        ],
    }


def _request_json(url: str, *, headers: dict[str, str], body: bytes | None = None) -> dict[str, Any]:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST" if body else "GET")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            parsed = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise AuditError(f"CLOUDFLARE_HTTP_{exc.code}") from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise AuditError("CLOUDFLARE_REQUEST_FAILED") from None
    if not isinstance(parsed, dict):
        raise AuditError("CLOUDFLARE_RESPONSE_INVALID")
    return parsed


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
    url = f"{api}/repos/{repo}/actions/workflows/{WORKFLOW_FILE}/runs?branch=main&event=workflow_dispatch&per_page=100"
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
    if not any(str(item.get("id")) == run_id for item in runs if isinstance(item, dict)):
        raise AuditError("CURRENT_RUN_NOT_IN_HISTORY")
    if any(str(item.get("id")) != run_id for item in runs if isinstance(item, dict)):
        raise AuditError("ONE_TIME_AUTHORITY_ALREADY_CONSUMED")


def execute(output: Path) -> int:
    report: dict[str, Any]
    observed = datetime.now(UTC)
    try:
        token = os.environ.get("CLOUDFLARE_READONLY_API_TOKEN")
        account = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        if not token or not account:
            raise AuditError("READ_ONLY_CLOUDFLARE_CREDENTIALS_MISSING")
        _require_single_run()
        end = datetime.now(UTC)
        start = end - timedelta(days=30)
        variables = {
            "accountTag": account,
            "startDate": start.date().isoformat(),
            "endDate": end.date().isoformat(),
            "startTime": start.isoformat().replace("+00:00", "Z"),
            "endTime": end.isoformat().replace("+00:00", "Z"),
        }
        body = json.dumps({"query": QUERY, "variables": variables}).encode()
        payload = _request_json(
            "https://api.cloudflare.com/client/v4/graphql",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            body=body,
        )
        report = summarize_usage(
            payload, observed_at=datetime.now(UTC), start_time=start, end_time=end,
        )
        report["github"] = {
            "repository": os.environ.get("GITHUB_REPOSITORY"),
            "run_id": os.environ.get("GITHUB_RUN_ID"),
            "run_attempt": 1,
            "head_sha": os.environ.get("GITHUB_SHA"),
            "event": "workflow_dispatch",
        }
        report["cloudflare_http_requests_performed"] = 1
    except AuditError as exc:
        report = {
            "schema": "qookey-cloud-paper-usage-audit-report-v0.1",
            "authority": AUTHORITY,
            "status": "REVIEW_REQUIRED",
            "observed_at_utc": observed.isoformat(),
            "reason_code": str(exc),
            "cloudflare_http_requests_performed": 0 if str(exc) in {
                "READ_ONLY_CLOUDFLARE_CREDENTIALS_MISSING",
                "MAIN_BRANCH_REQUIRED",
                "RERUN_FORBIDDEN",
                "GITHUB_RUN_METADATA_MISSING",
                "WORKFLOW_HISTORY_UNAVAILABLE",
                "WORKFLOW_HISTORY_AMBIGUOUS",
                "CURRENT_RUN_NOT_IN_HISTORY",
                "ONE_TIME_AUTHORITY_ALREADY_CONSUMED",
            } else None,
            "account_identifiers_persisted": False,
            "raw_response_persisted": False,
            "zero_cost_conclusion": "UNKNOWN",
            "activation": "REMAINS_DISABLED",
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Cloud Paper usage audit: {report['status']} ({report.get('reason_code', 'METRICS_CAPTURED')})")
    return 0 if report["status"] == "READY_FOR_REVIEW" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    return execute(args.output)


if __name__ == "__main__":
    sys.exit(main())
